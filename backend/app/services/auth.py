"""认证与会话辅助函数。

该模块负责密码哈希、签名 Cookie 会话，以及保护登录态接口的 FastAPI 依赖。
会话本身是无状态的：Cookie 中保存签名后的用户 ID 和过期时间，每次访问受保护
接口时再到数据库确认用户是否存在。
"""

from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import json
import secrets
from typing import TypedDict

from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_db_session
from app.models import User


PBKDF2_ITERATIONS = 200_000


class SessionPayload(TypedDict):
    """保存在认证 Cookie 中的最小签名会话载荷。"""

    uid: str
    exp: int


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _b64url_decode(raw: str) -> bytes:
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + padding)


def hash_password(password: str) -> str:
    """使用 PBKDF2 和随机盐对明文密码进行哈希。"""

    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    """校验明文密码是否匹配已保存的 PBKDF2 哈希字符串。"""

    try:
        algorithm, iterations, salt_hex, digest_hex = password_hash.split("$", 3)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt_hex),
        int(iterations),
    )
    return hmac.compare_digest(digest.hex(), digest_hex)


def _sign_session_payload(encoded_payload: str, settings: Settings) -> str:
    return hmac.new(
        settings.auth_secret.encode("utf-8"),
        encoded_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def create_session_token(user_id: str, settings: Settings | None = None) -> str:
    """为指定用户 ID 创建带签名且 URL 安全的会话令牌。"""

    current_settings = settings or get_settings()
    expires_at = datetime.now(UTC) + timedelta(days=current_settings.auth_session_days)
    payload: SessionPayload = {
        "uid": user_id,
        "exp": int(expires_at.timestamp()),
    }
    encoded_payload = _b64url_encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signature = _sign_session_payload(encoded_payload, current_settings)
    return f"{encoded_payload}.{signature}"


def parse_session_token(token: str, settings: Settings | None = None) -> SessionPayload | None:
    """当令牌有效且未过期时，返回其中的会话载荷。"""

    current_settings = settings or get_settings()
    try:
        encoded_payload, signature = token.split(".", 1)
    except ValueError:
        return None
    if not hmac.compare_digest(signature, _sign_session_payload(encoded_payload, current_settings)):
        return None
    try:
        payload = json.loads(_b64url_decode(encoded_payload))
    except (ValueError, json.JSONDecodeError):
        return None
    user_id = payload.get("uid")
    expires_at = payload.get("exp")
    if not isinstance(user_id, str) or not isinstance(expires_at, int):
        return None
    if expires_at <= int(datetime.now(UTC).timestamp()):
        return None
    return {"uid": user_id, "exp": expires_at}


def set_session_cookie(response: Response, user_id: str, settings: Settings | None = None) -> None:
    current_settings = settings or get_settings()
    token = create_session_token(user_id, current_settings)
    response.set_cookie(
        key=current_settings.auth_cookie_name,
        value=token,
        max_age=current_settings.auth_session_days * 24 * 60 * 60,
        httponly=True,
        samesite="lax",
        secure=current_settings.auth_cookie_secure,
        path="/",
    )


def clear_session_cookie(response: Response, settings: Settings | None = None) -> None:
    current_settings = settings or get_settings()
    response.delete_cookie(
        key=current_settings.auth_cookie_name,
        httponly=True,
        samesite="lax",
        secure=current_settings.auth_cookie_secure,
        path="/",
    )


async def resolve_current_user(request: Request, session: AsyncSession) -> User | None:
    """从签名认证 Cookie 中解析当前登录用户。"""

    settings = get_settings()
    token = request.cookies.get(settings.auth_cookie_name)
    if not token:
        return None
    payload = parse_session_token(token, settings)
    if payload is None:
        return None
    return await session.scalar(select(User).where(User.id == payload["uid"]))


async def require_current_user(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> User:
    """FastAPI 依赖：未登录请求返回 401。"""

    user = await resolve_current_user(request, session)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录")
    return user
