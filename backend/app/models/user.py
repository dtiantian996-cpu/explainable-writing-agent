"""用户 ORM 模型及其关联关系。"""

from datetime import datetime
import uuid

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    """系统账号，用于会话认证和用户级评估数据归属。"""

    __tablename__ = "users"

    # 登录身份与展示信息。
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="demo_user")

    # 账号审计时间戳。
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)

    # 当前用户拥有的数据。
    assessments = relationship("Assessment", back_populates="user")
    notebook_items = relationship("NotebookItem", back_populates="user")
