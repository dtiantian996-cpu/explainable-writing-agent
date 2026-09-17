# ruff: noqa: E402

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import get_settings
from app.services.ocr import OCRService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Warm up YASI local runtime assets.")
    parser.add_argument(
        "--image",
        default=str(REPO_ROOT / "verification" / "runtime-assets" / "ocr-essay-source.png"),
        help="Path to the OCR sample image used for warm-up.",
    )
    return parser.parse_args()


async def main() -> int:
    args = parse_args()
    image_path = Path(args.image).resolve()
    if not image_path.exists():
        print(f"[yasi-warmup] sample image not found: {image_path}", file=sys.stderr)
        return 1

    settings = get_settings()
    print(f"[yasi-warmup] repo={REPO_ROOT}")
    print(f"[yasi-warmup] OCR lang={settings.paddle_ocr_lang}")
    print(f"[yasi-warmup] RAG enabled={settings.rag_enabled}")
    print(f"[yasi-warmup] DeepSeek enabled={settings.deepseek_enabled}")
    print(f"[yasi-warmup] warming OCR with {image_path}")

    service = OCRService()
    text = await service.read_images([str(image_path)])
    if not text:
        print("[yasi-warmup] OCR returned empty text", file=sys.stderr)
        return 1

    preview = text.replace("\n", " ")[:160]
    print("[yasi-warmup] OCR warm-up succeeded")
    print(f"[yasi-warmup] preview={preview}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
