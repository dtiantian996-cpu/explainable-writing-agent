"""上传作文图片的 OCR 服务。

该服务会延迟初始化一次 PaddleOCR，并用异步锁保护初始化过程。
阻塞型 OCR 工作会放到线程中执行，避免图片识别阻塞 FastAPI 事件循环。
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Iterable

from app.core.config import get_settings


class OCRService:
    """评估工作流使用的延迟加载 PaddleOCR 封装。"""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._ocr = None
        self._ocr_lock = asyncio.Lock()

    def _build_ocr(self):
        """使用轻量英文 OCR 模型创建 PaddleOCR 实例。"""

        os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
        from paddleocr import PaddleOCR  # type: ignore[import-untyped]

        return PaddleOCR(
            lang=self.settings.paddle_ocr_lang,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            text_detection_model_name="PP-OCRv5_mobile_det",
            text_recognition_model_name="en_PP-OCRv5_mobile_rec",
            cpu_threads=2,
            enable_mkldnn=False,
        )

    async def _get_ocr(self):
        """返回共享 OCR 实例；首次使用时完成初始化。"""

        if self._ocr is not None:
            return self._ocr
        async with self._ocr_lock:
            if self._ocr is None:
                self._ocr = await asyncio.to_thread(self._build_ocr)
        return self._ocr

    def _read_single_image(self, ocr, image_path: str) -> list[str]:
        """读取单张图片并返回非空识别文本行。"""

        result = ocr.predict(str(Path(image_path)))[0]
        texts = result.get("rec_texts", [])
        return [text.strip() for text in texts if isinstance(text, str) and text.strip()]

    async def read_images(self, image_paths: Iterable[str]) -> str:
        """识别所有上传图片，并将识别文本行合并为作文文本。"""

        lines: list[str] = []
        ocr = await self._get_ocr()
        for image_path in image_paths:
            lines.extend(await asyncio.to_thread(self._read_single_image, ocr, image_path))
        return "\n".join(lines).strip()
