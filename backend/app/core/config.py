"""
配置文件模块：负责加载环境变量、定义系统配置（Settings），并提供全局单例配置对象。
与 Prompt 工程、LLM 调用、RAG 知识库、用户认证、存储路径等密切相关。
"""

from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path


def _load_local_env() -> None:
    """
    从项目根目录或 backend 目录下的多个候选 .env 文件中加载环境变量。
    支持 .env.local, .env, .env.example 等常见命名，并按顺序读取，已存在的 key 不会被覆盖（setdefault）。
    用途：为整个系统提供配置源，例如 DeepSeek API Key、数据库 URL 等。
    """
    backend_root = Path(__file__).resolve().parents[2]          # 当前文件在 backend/app/core/config.py，回退到 backend 目录
    repo_root = backend_root.parent                            # 项目根目录（包含 backend、frontend 等）
    for env_path in (
        repo_root / ".env.local",
        repo_root / ".env.loacl",      # 可能是手误，但保留兼容
        repo_root / ".env",
        repo_root / ".env.example",
        backend_root / ".env.local",
        backend_root / ".env.loacl",
        backend_root / ".env",
        backend_root / ".env.example",
    ):
        if not env_path.exists():
            continue
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def _as_bool(value: str | None, default: bool = False) -> bool:
    """将字符串转换为布尔值，支持 '1', 'true', 'yes', 'on' 等常见真值表示。"""
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _resolve_repo_path(raw: str | Path, repo_root: Path) -> Path:
    """
    将配置中的相对路径转换为基于项目根目录的绝对路径。
    如果 raw 已经是绝对路径则直接返回，否则拼接 repo_root。
    用于确保 RAG 数据目录、存储目录等路径正确。
    """
    candidate = raw if isinstance(raw, Path) else Path(raw)
    return candidate if candidate.is_absolute() else (repo_root / candidate)


@dataclass(frozen=True)
class Settings:
    """
    系统核心配置类，所有配置项通过环境变量或默认值注入。
    使用 frozen=True 保证配置不可变，避免运行时被意外修改。
    """

    # ----- 基础应用配置 -----
    app_name: str           # 应用名称，例如 "YASI Backend"
    app_version: str        # 版本号
    app_env: str            # 运行环境: development / production 等
    app_port: int           # 后端服务监听端口

    # ----- 数据库配置 -----
    database_url: str       # 数据库连接串（支持 MySQL + asyncmy）

    # ----- AI 模型配置（LLM）-----
    deepseek_api_key: str   # DeepSeek API Key（用于调用 LLM）
    deepseek_base_url: str  # DeepSeek API 端点
    deepseek_model: str     # 模型名称，如 deepseek-chat

    # ----- OCR 配置（图片上传识别）-----
    dashscope_api_key: str  # 阿里云 DashScope API Key（用于 PaddleOCR 或其他 OCR 服务）
    paddle_ocr_lang: str    # OCR 语言，默认为英文 "en"

    # ----- 演示用户（方便测试）-----
    demo_user_email: str
    demo_user_name: str
    demo_user_password: str

    # ----- 认证与安全 -----
    auth_secret: str                # JWT 或 session 加密密钥
    auth_cookie_name: str           # session cookie 名称
    auth_cookie_secure: bool        # 是否仅 HTTPS 传输
    auth_session_days: int          # 登录态有效天数

    # ----- 文件存储路径 -----
    storage_dir: Path               # 用户上传图片、临时文件等存储根目录

    # ----- RAG（检索增强生成）配置 -----
    rag_enabled: bool               # 是否启用 RAG 知识库增强评估
    rag_chroma_dir: Path            # Chroma 向量数据库存储目录
    rag_data_dir: Path              # 原始知识库数据目录（评分标准、范文、错误案例）
    rag_top_k: int                  # 最终返回给 LLM 的检索片段数量
    rag_recall_top_k: int           # 初次召回（候选）片段数量，用于后续重排序
    rag_rerank_enabled: bool        # 是否启用重排序模型提升检索质量
    rag_timeout_seconds: int        # RAG 检索 + 生成的总超时时间

    # ----- 模拟 AI 模式（开发/测试用）-----
    use_mock_ai: bool               # 若为 True，则不真正调用 LLM，返回模拟数据（方便前端调试）

    # ----- 前端跨域白名单 -----
    frontend_origins: tuple[str, ...]   # 允许的 CORS 源，例如 http://localhost:5173

    @property
    def deepseek_enabled(self) -> bool:
        """判断 DeepSeek API 是否可用（有真实 key 且非占位符）"""
        return bool(self.deepseek_api_key and self.deepseek_api_key != "replace-me")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    全局单例配置获取函数（基于 lru_cache，只执行一次）。
    首先加载 .env 文件中的变量，然后从 os.environ 中读取具体配置并构建 Settings 对象。
    整个系统其它模块（API、服务层、工作流）通过调用此函数获得配置。
    """
    _load_local_env()                               # 1. 加载环境变量
    backend_root = Path(__file__).resolve().parents[2]   # backend 目录绝对路径
    repo_root = backend_root.parent                      # 项目根目录
    app_env = os.getenv("YASI_ENV", "development")

    # 存储目录默认为 backend/.runtime
    storage_dir = Path(
        os.getenv(
            "YASI_STORAGE_DIR",
            backend_root / ".runtime",
        )
    )
    # 知识库根目录（backend/knowledge_base）
    knowledge_root = backend_root / "knowledge_base"

    # 数据库连接（默认 MySQL 本地）
    database_url = os.getenv(
        "DATABASE_URL",
        "mysql+asyncmy://yasi:yasi@127.0.0.1:19306/yasi",
    )

    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY", "")
    dashscope_api_key = os.getenv("DASHSCOPE_API_KEY", "")

    # 前端跨域来源，默认包含常见本地开发端口
    frontend_origins = tuple(
        origin.strip()
        for origin in os.getenv(
            "YASI_FRONTEND_ORIGINS",
            "http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:4173,http://localhost:4173,http://127.0.0.1:19173,http://localhost:19173",
        ).split(",")
        if origin.strip()
    )

    return Settings(
        app_name=os.getenv("YASI_APP_NAME", "YASI Backend"),
        app_version=os.getenv("YASI_APP_VERSION", "0.1.0"),
        app_env=app_env,
        app_port=int(os.getenv("YASI_APP_PORT", "8000")),
        database_url=database_url,
        deepseek_api_key=deepseek_api_key,
        deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
        deepseek_model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        dashscope_api_key=dashscope_api_key,
        paddle_ocr_lang=os.getenv("PADDLE_OCR_LANG", "en"),
        demo_user_email=os.getenv("YASI_DEMO_USER_EMAIL", "demo@yasi.local"),
        demo_user_name=os.getenv("YASI_DEMO_USER_NAME", "Demo User"),
        demo_user_password=os.getenv("YASI_DEMO_USER_PASSWORD", "demo123456"),
        auth_secret=os.getenv("YASI_AUTH_SECRET", "yasi-dev-secret"),
        auth_cookie_name=os.getenv("YASI_AUTH_COOKIE_NAME", "yasi_session"),
        auth_cookie_secure=_as_bool(os.getenv("YASI_AUTH_COOKIE_SECURE"), default=False),
        auth_session_days=int(os.getenv("YASI_AUTH_SESSION_DAYS", "7")),
        storage_dir=storage_dir,
        rag_enabled=_as_bool(os.getenv("YASI_RAG_ENABLED"), default=True),
        rag_chroma_dir=_resolve_repo_path(os.getenv("YASI_RAG_CHROMA_DIR", str(knowledge_root / "chroma")), repo_root),
        rag_data_dir=_resolve_repo_path(os.getenv("YASI_RAG_DATA_DIR", str(knowledge_root / "data")), repo_root),
        rag_top_k=int(os.getenv("YASI_RAG_TOP_K", "6")),
        rag_recall_top_k=int(os.getenv("YASI_RAG_RECALL_TOP_K", "12")),
        rag_rerank_enabled=_as_bool(os.getenv("YASI_RAG_RERANK_ENABLED"), default=True),
        rag_timeout_seconds=int(os.getenv("YASI_RAG_TIMEOUT_SECONDS", "20")),
        use_mock_ai=_as_bool(os.getenv("YASI_USE_MOCK_AI"), default=not bool(deepseek_api_key)),
        frontend_origins=frontend_origins,
    )