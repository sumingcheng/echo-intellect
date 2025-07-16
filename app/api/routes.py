from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
import logging

from config.settings import app_config

# 创建路由器
router = APIRouter()

# 获取日志实例
logger = logging.getLogger("echo-intellect")


# 请求模型
class QueryRequest(BaseModel):
    question: str
    max_tokens: int = 4000


class QueryResponse(BaseModel):
    question: str
    answer: str
    tokens_used: int
    relevance_score: float


@router.get("/", tags=["健康检查"])
async def root():
    """根路径"""
    return {
        "message": "🤖 Echo Intellect RAG 系统运行中",
        "version": "1.0.0",
        "status": "healthy",
    }


@router.get("/health", tags=["健康检查"])
async def health_check():
    """健康检查端点"""
    logger.info("健康检查请求")

    return {
        "status": "healthy",
        "environment": app_config.environment,
        "services": {
            "milvus": app_config.milvus_uri,
            "mongodb": "ready",
            "redis": "ready",
            "meilisearch": app_config.meilisearch_uri,
            "embedding": app_config.embedding_service,
            "rerank": app_config.rerank_service,
        },
    }


@router.post("/query", response_model=QueryResponse, tags=["RAG查询"])
async def rag_query(request: QueryRequest):
    """RAG查询demo接口"""
    logger.info(f"收到查询请求: {request.question}")

    try:
        # 这里是demo实现，后续会替换为真实的RAG逻辑
        demo_answer = (
            f"这是对问题「{request.question}」的演示回答。\n\n"
            f"系统配置:\n"
            f"- 最大tokens: {app_config.max_tokens_limit}\n"
            f"- 相关性阈值: {app_config.relevance_threshold}\n"
            f"- LLM模型: {app_config.llm_model}\n\n"
            f"后续将集成完整的RAG检索流程。"
        )

        response = QueryResponse(
            question=request.question,
            answer=demo_answer,
            tokens_used=len(demo_answer) // 4,  # 粗略估算token数
            relevance_score=0.85,
        )

        logger.info(f"查询完成，返回 {response.tokens_used} tokens")
        return response

    except Exception as e:
        logger.error(f"查询处理失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询处理失败: {str(e)}")


@router.get("/config", tags=["系统配置"])
async def get_config():
    """获取系统配置信息"""
    logger.info("获取系统配置请求")

    return {
        "app_config": {
            "environment": app_config.environment,
            "max_tokens_limit": app_config.max_tokens_limit,
            "relevance_threshold": app_config.relevance_threshold,
            "llm_model": app_config.llm_model,
        },
        "services": {
            "milvus_collection": app_config.milvus_collection,
            "meilisearch_index": app_config.meilisearch_index,
        },
    }
