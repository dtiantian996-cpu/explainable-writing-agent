"""评估任务 ORM 模型。

该表保存一次作文评估请求的完整生命周期，包括用户原始输入、OCR 输出、
标准化文本、进度状态，以及异步评估工作流和结果页轮询需要的时间戳。
"""

from datetime import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Assessment(Base):
    """用户提交的一次作文评估任务。"""

    __tablename__ = "assessments"
    __table_args__ = (Index("idx_assessments_user_created", "user_id", "created_at"),)

    # 任务唯一标识与所属用户。
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)

    # 用户提交时提供的作文元信息。
    topic: Mapped[str] = mapped_column(String(500), nullable=False)
    task_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_mode: Mapped[str] = mapped_column(String(16), nullable=False)

    # 输入内容的不同形态；normalized_text 是智能体实际使用的标准文本。
    essay_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalized_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # 异步评估流程状态，用于前端轮询展示进度。
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued")
    progress_message: Mapped[str | None] = mapped_column(String(255), nullable=True)
    progress_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # 生命周期时间戳；为兼容现有数据库结构，这里保存无时区 UTC 时间。
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)

    # ORM 关系，供读取模型和报告导出使用。
    user = relationship("User", back_populates="assessments")
    result = relationship("AssessmentResult", back_populates="assessment", uselist=False)
    notebook_items = relationship("NotebookItem", back_populates="assessment")
