#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${1:-"$ROOT_DIR/verification/customer-delivery"}"
TIMESTAMP="$(date +"%Y%m%d-%H%M%S")"
PACKAGE_NAME="yasi-customer-windows-native-${TIMESTAMP}"
STAGE_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/yasi-customer-package.XXXXXX")"
STAGE_DIR="$STAGE_ROOT/$PACKAGE_NAME"
ARCHIVE_PATH="$OUTPUT_DIR/$PACKAGE_NAME.zip"

cleanup() {
  rm -rf "$STAGE_ROOT"
}
trap cleanup EXIT

mkdir -p "$STAGE_DIR" "$OUTPUT_DIR"

rsync -a \
  --exclude ".git/" \
  --exclude ".agents/" \
  --exclude ".beads/" \
  --exclude ".github/" \
  --exclude ".idea/" \
  --exclude ".vscode/" \
  --exclude ".mypy_cache/" \
  --exclude ".pytest_cache/" \
  --exclude ".ruff_cache/" \
  --exclude ".runtime/" \
  --exclude ".venv/" \
  --exclude "node_modules/" \
  --exclude "__pycache__/" \
  --exclude "frontend/dist/" \
  --exclude "frontend/test-results/" \
  --exclude "playwright*.ts" \
  --exclude "verification/" \
  --exclude "docs/" \
  --exclude "scripts/windows/" \
  --exclude "AGENTS.md" \
  --exclude "CLAUDE.md" \
  --exclude "GEMINI.md" \
  --exclude ".env.local" \
  --exclude ".gitattributes" \
  --exclude ".gitignore" \
  --exclude "RELEASE_NOTES.md" \
  --exclude "scripts/check.sh" \
  --exclude "*.log" \
  --exclude "*.pyc" \
  --exclude "*.tsbuildinfo" \
  --exclude ".DS_Store" \
  "$ROOT_DIR/" "$STAGE_DIR/"

rm -rf "$STAGE_DIR/backend/tests" "$STAGE_DIR/frontend/e2e"
find "$STAGE_DIR/frontend/src" \( -name "*.test.ts" -o -name "*.spec.ts" \) -delete
rm -f "$STAGE_DIR/backend/README.md" "$STAGE_DIR/backend/knowledge_base/README.md"

cp "$ROOT_DIR/docs/deploy/windows-native-local.md" "$STAGE_DIR/WINDOWS_DEPLOY.md"
mkdir -p "$STAGE_DIR/verification/runtime-assets"
cp "$ROOT_DIR/verification/runtime-assets/ocr-essay-source.png" "$STAGE_DIR/verification/runtime-assets/ocr-essay-source.png"
cp "$ROOT_DIR/verification/runtime-assets/ocr-essay-source.pdf" "$STAGE_DIR/verification/runtime-assets/ocr-essay-source.pdf"

cat > "$STAGE_DIR/.env.example" <<'EOF'
DATABASE_URL=mysql+asyncmy://yasi:yasi@127.0.0.1:3306/yasi
DEEPSEEK_API_KEY=replace-with-your-deepseek-key
DASHSCOPE_API_KEY=replace-with-your-dashscope-key
YASI_AUTH_SECRET=change-this-to-a-random-secret
VITE_API_BASE_URL=http://127.0.0.1:8000
YASI_RAG_ENABLED=true
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat
PADDLE_OCR_LANG=en
EOF

cat > "$STAGE_DIR/README.md" <<'EOF'
# YASI 客户交付包

这个压缩包用于在 Windows 本机本地部署 YASI。

## 包内内容

- `backend/`：后端服务
- `frontend/`：前端页面
- `scripts/run_runtime_warmup.py`：OCR 预热脚本
- `.env.example`：精简后的 Windows 本地环境变量模板
- `docker-compose.yml`：Docker 组合启动文件
- `verification/runtime-assets/`：OCR 预热与图片链验收样本
- `WINDOWS_DEPLOY.md`：Windows 原生本地部署说明

## 默认端口

- Frontend: `4173`
- Backend: `8000`
- MySQL: `3306`

## 使用方式

请直接阅读根目录下的 `WINDOWS_DEPLOY.md`，按文档完成：

1. 环境准备
2. `.env.local` 配置
3. MySQL 初始化
4. backend / frontend 启动
5. OCR 预热
6. 文本、图片 OCR、PDF 导出验证

文档主入口现在优先使用 `CMD` 直接命令，例如：

- `copy .env.example .env.local`
- `uv sync --project backend`
- `cd /d backend && uv run uvicorn ...`
- `cd /d frontend && pnpm dev ...`
- `uv run --project backend python scripts\\run_runtime_warmup.py`

## 说明

- 这个交付包已经移除了开发过程文档、验收材料、AI 运行规则和测试目录。
- RAG 在这个交付包里默认就是开启的；只要填了 `DASHSCOPE_API_KEY`，结果页就会尝试展示参考依据。
- `.env.example` 已经按 Windows 原生交付做过瘦身，通常只需要改 `DEEPSEEK_API_KEY`、`DASHSCOPE_API_KEY`、`YASI_AUTH_SECRET`。
- 若需要真实模型能力，请把客户提供的 API Key 写入 `.env.local`，不要直接写回仓库文件。
EOF

if command -v zip >/dev/null 2>&1; then
  (
    cd "$STAGE_ROOT"
    zip -qr "$ARCHIVE_PATH" "$PACKAGE_NAME"
  )
elif command -v ditto >/dev/null 2>&1; then
  ditto -c -k --keepParent "$STAGE_DIR" "$ARCHIVE_PATH"
else
  echo "缺少 zip 或 ditto，无法生成压缩包" >&2
  exit 1
fi

echo "$ARCHIVE_PATH"
