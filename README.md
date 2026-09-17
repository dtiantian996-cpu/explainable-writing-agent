# YASI：可解释英语写作评估与反馈系统

YASI（Your AI Scoring Instructor）是一个面向英语学习者的智能写作评估系统。系统基于 FastAPI、LangGraph 和大语言模型构建，通过多个专业 Agent 协作完成语言分析、语篇分析、综合评分和个性化学习建议。

系统支持文本作文提交、图片 OCR 识别、知识库检索、结构化评估、历史记录、错题整理、用户画像和 PDF 报告导出。

## 项目功能

* 支持文本和图片两种作文提交方式
* 使用 PaddleOCR 识别英文作文图片
* 使用 LangGraph 编排多 Agent 写作评估流程
* 使用 DeepSeek API 生成结构化评估结果
* 使用 Pydantic 约束大模型 JSON 输出
* 使用 RAG 检索写作评分标准和参考知识
* 生成雅思写作四维评分及评分理由
* 提供逐句错误分析和修改建议
* 生成文章亮点、学习建议和个性化学习路径
* 支持历史记录、错题本和用户画像
* 支持中文 PDF 评估报告导出
* RAG不可用时自动降级，不影响主评估流程完成

## 系统演示

### 作文提交

![作文提交页面](docs/images/writing-submission.png)

### 写作评估结果

![写作评估结果](docs/images/assessment-result.png)

### 逐句分析与修改建议

![逐句分析](docs/images/sentence-feedback.png)

## 系统架构

```mermaid
flowchart TD
    U["用户"] --> F["前端<br/>Vite + TypeScript"]
    F --> API["FastAPI RESTful API"]

    API --> AUTH["用户认证与业务接口"]
    API --> EVAL["异步写作评估流程"]
    API --> DB[("MySQL")]

    EVAL --> OCR["PaddleOCR<br/>图片文字识别"]
    EVAL --> RAG["RAG知识检索"]
    EVAL --> LG["LangGraph工作流"]

    RAG --> KB[("Chroma知识库")]
    RAG --> EMB["DashScope Embedding"]

    LG --> AGENTS["Language / Discourse<br/>Scoring / Tutor Agents"]
    AGENTS --> LLM["DeepSeek API"]
    AGENTS --> RESULT["Pydantic校验<br/>评分归一化与结果融合"]

    RESULT --> DB
    DB --> API
    API --> PDF["PDF报告导出"]
    API --> F
```

## Agent工作流

系统使用 LangGraph 编排四类专业 Agent：

| Agent           | 主要职责               |
| --------------- | ------------------ |
| Language Agent  | 分析语法、词汇、拼写和句子表达    |
| Discourse Agent | 分析文章结构、衔接、连贯性和论证逻辑 |
| Scoring Agent   | 生成雅思写作四维评分及评分理由    |
| Tutor Agent     | 生成逐句修改、亮点分析和学习建议   |

各Agent输出经过Pydantic模型校验、评分归一化和结果融合，最终形成统一的评估报告。

基本流程：

```text
作文提交
    ↓
文本提取 / OCR识别
    ↓
RAG知识检索
    ↓
Language Agent + Discourse Agent
    ↓
Scoring Agent
    ↓
Tutor Agent
    ↓
结构化结果校验与持久化
    ↓
评估结果与PDF报告
```

## 技术栈

### 后端

* Python 3.12
* FastAPI
* LangGraph
* Pydantic
* SQLAlchemy
* Alembic
* MySQL 8
* DeepSeek API
* PaddleOCR
* Chroma
* DashScope Embedding
* uv

### 前端

* TypeScript
* Vite
* pnpm

### 工程能力

* RESTful API
* 异步评估工作流
* 数据库迁移
* 结构化大模型输出
* RAG失败降级
* OCR运行时预热
* Docker配置
* PDF报告导出

## 项目结构

```text
explainable-writing-agent/
├── agents/                    # Agent定义与提示词
├── backend/
│   ├── alembic/              # 数据库迁移
│   ├── app/                  # FastAPI后端代码
│   ├── assets/               # 后端静态资源
│   ├── knowledge_base/       # RAG知识库
│   ├── alembic.ini
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── uv.lock
├── frontend/
│   ├── public/
│   ├── src/                  # 前端源代码
│   ├── Dockerfile
│   ├── package.json
│   ├── pnpm-lock.yaml
│   └── vite.config.ts
├── docs/
│   └── images/               # README演示图片
├── scripts/                  # 初始化与运行脚本
├── verification/             # 测试及运行验证资源
├── .env.example
├── .gitignore
├── README.en.md
└── README.md
```

## 环境要求

Windows原生运行环境：

* Windows 10或Windows 11 x64
* Python 3.12
* Node.js 22
* MySQL 8
* uv
* pnpm

确认环境：

```cmd
python --version
uv --version
node --version
pnpm --version
mysql --version
```

默认服务端口：

| 服务       | 地址                      |
| -------- | ----------------------- |
| Frontend | `http://127.0.0.1:4173` |
| Backend  | `http://127.0.0.1:8000` |
| MySQL    | `127.0.0.1:3306`        |

## 环境变量

复制环境变量示例：

```cmd
copy .env.example .env.local
```

编辑`.env.local`：

```env
DATABASE_URL=mysql+asyncmy://your_username:your_password@127.0.0.1:3306/your_database

DEEPSEEK_API_KEY=your_deepseek_api_key
DASHSCOPE_API_KEY=your_dashscope_api_key
YASI_AUTH_SECRET=replace_with_a_long_random_string

VITE_API_BASE_URL=http://127.0.0.1:8000

YASI_RAG_ENABLED=true
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat
PADDLE_OCR_LANG=en
```

## 安装与运行

以下命令均使用Windows CMD执行。

### 1. 安装后端依赖

在仓库根目录执行：

```cmd
uv sync --project backend
```

项目使用`pyproject.toml`和`uv.lock`管理Python依赖，因此不需要`requirements.txt`。

### 2. 安装Windows OCR运行环境

```cmd
uv run --project backend python -m pip install paddlepaddle==3.3.0 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/
```

验证Paddle安装：

```cmd
uv run --project backend python -c "import paddle; print(paddle.__version__)"
```

### 3. 安装前端依赖

```cmd
pnpm install --dir frontend
```

项目使用`pnpm-lock.yaml`锁定前端依赖，因此不需要`package-lock.json`。

### 4. 初始化MySQL数据库

先在MySQL中创建数据库和本地开发账号。请自行设置安全密码：

```sql
CREATE DATABASE yasi
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

CREATE USER 'your_username'@'127.0.0.1'
IDENTIFIED BY 'your_password';

GRANT ALL PRIVILEGES ON yasi.*
TO 'your_username'@'127.0.0.1';

FLUSH PRIVILEGES;
```

确保`.env.local`中的`DATABASE_URL`与实际数据库用户名、密码和端口一致。

### 5. 执行数据库迁移

```cmd
cd backend
uv run alembic -c alembic.ini upgrade head
cd ..
```

### 6. 启动后端

打开一个新的CMD窗口：

```cmd
cd /d 你的项目路径\backend
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

健康检查：

```text
http://127.0.0.1:8000/api/healthz
```

正常响应：

```json
{"status": "ok"}
```

### 7. 启动前端

打开另一个CMD窗口：

```cmd
cd /d 你的项目路径\frontend
set VITE_API_BASE_URL=http://127.0.0.1:8000
pnpm build
pnpm preview --host 127.0.0.1 --port 4173
```

打开：

```text
http://127.0.0.1:4173/login
```

本地开发时也可以使用：

```cmd
cd /d 你的项目路径\frontend
set VITE_API_BASE_URL=http://127.0.0.1:8000
pnpm dev --host 127.0.0.1 --port 5173
```

## OCR预热

第一次OCR运行需要初始化模型。正式演示前，建议在仓库根目录执行：

```cmd
uv run --project backend python scripts\run_runtime_warmup.py
```

预热成功时，终端会显示：

```text
OCR warm-up succeeded
```

仓库中的OCR验证文件位于：

```text
verification\runtime-assets\ocr-essay-source.png
verification\runtime-assets\ocr-essay-source.pdf
```

## 功能验证

建议按照以下顺序测试系统：

1. 注册或登录测试账号。
2. 使用文本模式提交英文作文。
3. 检查四维评分、评分理由、错误分析和学习建议。
4. 使用图片模式上传清晰的英文作文图片。
5. 确认OCR识别字数大于0。
6. 检查评估报告中的RAG参考依据。
7. 导出PDF并确认中文内容和排版正常。

## 常见问题

### `No module named 'paddle'`

重新安装Windows CPU版本的Paddle：

```cmd
uv run --project backend python -m pip install paddlepaddle==3.3.0 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/
```

### 后端无法连接MySQL

确认：

* MySQL服务正在运行；
* 数据库已经创建；
* 用户名和密码正确；
* `DATABASE_URL`中的端口正确；
* 修改`.env.local`后已经重启后端。

Windows可以运行：

```cmd
services.msc
```

然后检查MySQL服务状态。

### 登录页面能够打开，但提交失败

先访问：

```text
http://127.0.0.1:8000/api/healthz
```

如果健康检查失败，请查看后端CMD窗口中的错误信息。

### 评估完成但没有RAG参考依据

检查：

* `.env.local`中是否配置`DASHSCOPE_API_KEY`；
* 后端是否在修改配置后重启；
* `backend\knowledge_base\chroma`是否存在；
* `backend\knowledge_base\data`是否存在。

RAG检索失败时，系统会自动降级，不会阻止主评估流程完成。

## 项目说明

本项目用于课程实践、技术学习和个人作品集展示，重点展示：

* LangGraph多Agent工作流设计
* 大语言模型API封装
* FastAPI异步后端开发
* OCR与RAG集成
* 结构化输出和结果融合
* 数据持久化与异常降级

This repository is provided for portfolio and educational demonstration purposes.
