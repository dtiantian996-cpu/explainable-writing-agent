"""ORM 模型统一导出入口。

路由和服务模块统一从 ``app.models`` 导入模型，避免依赖具体模型文件布局。
"""
from app.models.assessment import Assessment
from app.models.assessment_result import AssessmentResult
from app.models.notebook_item import NotebookItem
from app.models.user import User

__all__ = ["Assessment", "AssessmentResult", "NotebookItem", "User"]
