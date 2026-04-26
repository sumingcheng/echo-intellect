# Echo Intellect

**[中文](./README.zh-CN.md)**

A voice-first personal knowledge assistant powered by RAG. Upload your documents, ask questions via voice or text, and get answers grounded in your own knowledge base.

## Features

- **Voice & Text Chat** — Continuous voice conversation with interrupt support, plus streaming text chat with real-time Markdown rendering
- **RAG Pipeline** — Query optimization, parallel retrieval, RRF merging, optional reranking, and relevance filtering
- **Knowledge Base** — Upload `.txt`, `.md`, `.pdf` files directly from chat; background processing with status tracking
- **Multi-LLM** — Configure multiple providers (OpenAI, DeepSeek, etc.) and switch models on the fly
- **References** — Each response shows which knowledge chunks were used, with relevance scores
- **i18n** — English and Chinese UI

## Architecture

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
 vectors   metadata    cache
```

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| Backend | Python 3.11+, FastAPI, LangChain, OpenAI, Qdrant, MongoDB, Redis |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS 4, Zustand, Streamdown |
| Speech | OpenAI Whisper (STT), OpenAI TTS |
| Infra | Docker Compose, Nginx |

## Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) & Docker Compose
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [Node.js](https://nodejs.org/) 20+ & [pnpm](https://pnpm.io/)
- An OpenAI API key (or compatible provider)

### 1. Start infrastructure

```bash
cd deploy
docker compose up -d
```

This brings up MongoDB, Qdrant, and Redis.

### 2. Configure

Copy and edit the local config:

```bash
cp config.yaml config.local.yaml
```

Set your API keys and model preferences in `config.local.yaml`. This file is gitignored.

### 3. Run backend

```bash
uv sync
uv run python main.py
```

Backend starts at `http://localhost:8000`.

### 4. Run frontend

```bash
cd web
pnpm install
pnpm dev
```

Frontend starts at `http://localhost:5173`.

## Project Structure

```
echo-intellect/
├── app/
│   ├── api/v1/          # REST endpoints (chat, import, models, speech)
│   ├── core/            # App factory, DI container, initialization
│   ├── ingestion/       # File readers, chunking, import service
│   ├── llms/            # Reranker
│   ├── models/          # Pydantic data models
│   ├── rag/             # RAG pipeline (retriever, filter, prompts, memory)
│   └── stores/          # Qdrant, MongoDB, Redis adapters
├── config/              # Settings, logging
├── deploy/              # Docker Compose, Dockerfile
├── tests/               # Unit & integration tests
├── web/                 # React frontend
│   ├── src/features/    # Feature modules (chat, voice, knowledge)
│   ├── src/i18n/        # Internationalization
│   └── deploy/          # Frontend Dockerfile + Nginx
├── config.yaml          # Default configuration
├── main.py              # Entry point
└── pyproject.toml       # Python dependencies
```

## Configuration

All configuration is in `config.yaml`, overridable by `config.local.yaml`.

| Key | Description |
|-----|-------------|
| `llm_providers` | List of LLM providers with `api_key`, `api_base`, `models` |
| `default_llm` | Default model ID |
| `openai.embedding_model` | Embedding model for vector search |
| `qdrant` | Qdrant connection and collection settings |
| `mongodb` | MongoDB URI and database name |
| `redis` | Redis URI |

## License

[Apache-2.0](./LICENSE)
