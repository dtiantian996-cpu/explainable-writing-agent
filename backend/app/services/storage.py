"""运行时文件存储辅助模块。

上传的图片或 PDF 会按评估任务保存到独立目录中，方便 HTTP 请求返回后，
异步工作流继续读取这些文件并执行 OCR。
"""

from __future__ import annotations

from pathlib import Path
import shutil

from fastapi import UploadFile

from app.core.config import get_settings


class RuntimeStorage:
    """基于文件系统的评估上传文件存储服务。"""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.settings.storage_dir.mkdir(parents=True, exist_ok=True)

    async def persist_uploads(self, assessment_id: str, files: list[UploadFile]) -> list[str]:
        """持久化上传文件，并返回供工作流 OCR 使用的文件路径。"""

        upload_dir = self.settings.storage_dir / "uploads" / assessment_id
        upload_dir.mkdir(parents=True, exist_ok=True)
        saved_paths: list[str] = []
        for index, file in enumerate(files, start=1):
            suffix = Path(file.filename or f"upload-{index}").suffix or ".bin"
            target = upload_dir / f"{index:02d}{suffix}"
            with target.open("wb") as handle:
                shutil.copyfileobj(file.file, handle)
            saved_paths.append(str(target))
        return saved_paths

    def list_uploads(self, assessment_id: str) -> list[str]:
        """列出某次评估已保存的上传文件。"""

        upload_dir = self.settings.storage_dir / "uploads" / assessment_id
        if not upload_dir.exists():
            return []
        return sorted(str(path) for path in upload_dir.iterdir() if path.is_file())
