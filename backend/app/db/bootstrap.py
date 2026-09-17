from datetime import UTC, datetime

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import User
from app.services.auth import hash_password


async def bootstrap_database() -> None:
    settings = get_settings()
    now = datetime.now(UTC).replace(tzinfo=None)

    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.email == settings.demo_user_email))
        demo_user = result.scalar_one_or_none()
        if demo_user is None:
            session.add(
                User(
                    email=settings.demo_user_email,
                    display_name=settings.demo_user_name,
                    password_hash=hash_password(settings.demo_user_password),
                    role="demo_user",
                    created_at=now,
                    updated_at=now,
                )
            )
            await session.commit()
            return

        if not demo_user.password_hash:
            demo_user.password_hash = hash_password(settings.demo_user_password)
            demo_user.updated_at = now
            await session.commit()
