# Echo Intellect

**[English](./README.md)**

基于 RAG 的语音优先个人知识助手。上传文档，通过语音或文字提问，获得基于你自己知识库的回答。

## 功能

- **语音 & 文字聊天** — 支持打断的持续语音对话，流式文字聊天实时渲染 Markdown
- **RAG 管线** — 查询优化、并行检索、RRF 融合、可选重排、相关性过滤
- **知识库管理** — 在聊天框直接上传 `.txt`、`.md`、`.pdf`，后台处理并追踪状态
- **多模型切换** — 配置多个 LLM 供应商（OpenAI、DeepSeek 等），前端实时切换
- **引用溯源** — 每条回复展示引用的知识片段和相关度分数
- **国际化** — 支持中英文界面

## 架构

```
┌────────────────────────────────────┐
│            React + Vite            │
│  Zustand · Tailwind · Streamdown  │
└──────────────┬─────────────────────┘
               │ HTTP / SSE
┌──────────────▼─────────────────────┐
│          FastAPI (uvicorn)         │
│  RAG Chain · STT/TTS · Ingestion  │
└──┬──────────┬──────────┬──────────┘
   │          │          │
 Qdrant    MongoDB     Redis
 向量存储    元数据      缓存
```

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.11+、FastAPI、LangChain、OpenAI、Qdrant、MongoDB、Redis |
| 前端 | React 19、TypeScript、Vite、Tailwind CSS 4、Zustand、Streamdown |
| 语音 | OpenAI Whisper (STT)、OpenAI TTS |
| 基础设施 | Docker Compose、Nginx |

## 快速开始

### 前置条件

- [Docker](https://docs.docker.com/get-docker/) & Docker Compose
- [uv](https://docs.astral.sh/uv/)（Python 包管理器）
- [Node.js](https://nodejs.org/) 20+ & [pnpm](https://pnpm.io/)
- OpenAI API Key（或兼容供应商）

### 1. 启动基础服务

```bash
cd deploy
docker compose up -d
```

启动 MongoDB、Qdrant、Redis。

### 2. 配置

```bash
cp config.yaml config.local.yaml
```

在 `config.local.yaml` 中填写 API Key 和模型配置，该文件已被 gitignore。

### 3. 启动后端

```bash
uv sync
uv run python main.py
```

后端运行在 `http://localhost:8000`。

### 4. 启动前端

```bash
cd web
pnpm install
pnpm dev
```

前端运行在 `http://localhost:5173`。

## 项目结构

```
echo-intellect/
├── app/
│   ├── api/v1/          # REST 接口（chat、import、models、speech）
│   ├── core/            # 应用工厂、依赖注入容器、初始化
│   ├── ingestion/       # 文件读取、分块、导入服务
│   ├── llms/            # 重排器
│   ├── models/          # Pydantic 数据模型
│   ├── rag/             # RAG 管线（检索、过滤、提示词、记忆）
│   └── stores/          # Qdrant、MongoDB、Redis 适配器
├── config/              # 配置、日志
├── deploy/              # Docker Compose、Dockerfile
├── tests/               # 单元测试 & 集成测试
├── web/                 # React 前端
│   ├── src/features/    # 功能模块（聊天、语音、知识库）
│   ├── src/i18n/        # 国际化
│   └── deploy/          # 前端 Dockerfile + Nginx
├── config.yaml          # 默认配置
├── main.py              # 入口
└── pyproject.toml       # Python 依赖
```

## 配置说明

所有配置在 `config.yaml`，可通过 `config.local.yaml` 覆盖。

| 字段 | 说明 |
|------|------|
| `llm_providers` | LLM 供应商列表，包含 `api_key`、`api_base`、`models` |
| `default_llm` | 默认模型 ID |
| `openai.embedding_model` | 向量搜索使用的 Embedding 模型 |
| `qdrant` | Qdrant 连接和集合配置 |
| `mongodb` | MongoDB URI 和数据库名 |
| `redis` | Redis URI |

## 许可证

[Apache-2.0](./LICENSE)
