"""FastAPI 应用启动时使用的服务统一导出入口。"""
from app.services.agent_runtime import AgentRuntime
from app.services.knowledge import KnowledgeRetriever
from app.services.ocr import OCRService
from app.services.storage import RuntimeStorage

__all__ = ["AgentRuntime", "KnowledgeRetriever", "OCRService", "RuntimeStorage"]
