from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.core.config import get_settings
from app.db.bootstrap import bootstrap_database
from app.db.migrations import run_migrations
from app.db.session import SessionLocal
from app.services import AgentRuntime, KnowledgeRetriever, OCRService, RuntimeStorage
from app.workers.runtime import AssessmentRuntime
from app.workflows import AssessmentWorkflow


@asynccontextmanager
async def lifespan(app: FastAPI):
    await asyncio.to_thread(run_migrations)
    await bootstrap_database()
    storage = RuntimeStorage()
    knowledge_retriever = KnowledgeRetriever()
    workflow = AssessmentWorkflow(
        session_factory=SessionLocal,
        agent_runtime=AgentRuntime(),
        knowledge_retriever=knowledge_retriever,
        ocr_service=OCRService(),
        storage=storage,
    )
    app.state.storage = storage
    app.state.knowledge_retriever = knowledge_retriever
    app.state.assessment_runtime = AssessmentRuntime(
        workflow=workflow,
        session_factory=SessionLocal,
    )
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.frontend_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)
    return app


app = create_app()
