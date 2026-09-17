"""错题本条目 ORM 模型。

错题本条目在每次评估完成后从 Tutor Agent 的修改建议中提取生成。
用户可以脱离原始结果页，单独复习这些反复出现的写作问题。
"""

from datetime import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class NotebookItem(Base):
    """由一次评估建议生成的一条可复习错题。"""

    __tablename__ = "notebook_items"
    __table_args__ = (Index("idx_notebook_user_status", "user_id", "status", "created_at"),)

    # 条目标识，以及与用户和来源评估任务的关联。
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    assessment_id: Mapped[str] = mapped_column(String(36), ForeignKey("assessments.id"), nullable=False)

    # 从 Tutor Agent 输出中复制过来的建议详情。
    error_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    revision: Mapped[str] = mapped_column(Text, nullable=False)
    revised_sentence: Mapped[str] = mapped_column(Text, nullable=False)
    position_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    position_end: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # 复习状态，用于错题本页面筛选。
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="new")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)

    user = relationship("User", back_populates="notebook_items")
    assessment = relationship("Assessment", back_populates="notebook_items")
