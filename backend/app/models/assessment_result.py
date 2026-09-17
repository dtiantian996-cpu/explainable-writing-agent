"""评估结果 ORM 模型。

每个已完成的评估任务都会写入一条结构化结果记录。多数结果字段使用 JSON，
因为它们与前端结果页和 PDF 导出模块使用的 Pydantic 响应结构保持一致。
"""

from datetime import datetime
import uuid
from typing import Any

from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AssessmentResult(Base):
    """一次已完成评估对应的持久化 AI 输出。"""

    __tablename__ = "assessment_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    assessment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("assessments.id"), nullable=False, unique=True
    )

    # /api/assessments/{id} 返回的结构化结果片段。
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    report: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    suggestions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    highlights: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    charts_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    profile_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    notebook_summary: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    # 结果记录的审计时间戳。
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)

    assessment = relationship("Assessment", back_populates="result")
