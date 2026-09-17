"""认证接口相关 Schema。"""

from __future__ import annotations

import re

from pydantic import AliasChoices, Field, field_validator

from app.schemas.common import APIModel


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AuthUserResponse(APIModel):
    """返回给前端的用户公开信息。"""

    id: str
    email: str
    displayName: str = Field(validation_alias=AliasChoices("displayName", "display_name"))
    role: str


class AuthSessionResponse(APIModel):
    """登录、注册和当前用户接口共用的会话响应。"""

    user: AuthUserResponse


class AuthRegisterRequest(APIModel):
    """注册请求体。"""

    email: str
    displayName: str = Field(validation_alias=AliasChoices("displayName", "display_name"))
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        """规范化并校验邮箱格式。"""

        normalized = value.strip().lower()
        if not EMAIL_RE.match(normalized):
            raise ValueError("请输入有效邮箱")
        return normalized

    @field_validator("displayName")
    @classmethod
    def normalize_display_name(cls, value: str) -> str:
        """清理并校验昵称。"""

        normalized = value.strip()
        if not normalized:
            raise ValueError("请输入昵称")
        if len(normalized) > 100:
            raise ValueError("昵称不能超过 100 个字符")
        return normalized

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        """校验密码复杂度的最低长度要求。"""

        if len(value) < 8:
            raise ValueError("密码至少需要 8 位")
        return value


class AuthLoginRequest(APIModel):
    """登录请求体。"""

    email: str
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        """规范化并校验登录邮箱。"""

        normalized = value.strip().lower()
        if not EMAIL_RE.match(normalized):
            raise ValueError("请输入有效邮箱")
        return normalized

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        """校验登录密码的最低长度。"""

        if len(value) < 8:
            raise ValueError("密码至少需要 8 位")
        return value
