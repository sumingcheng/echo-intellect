from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging
import time

from app.api.models.responses import HealthResponse
from app.chains.retrieval_chain import retrieval_chain
from config.settings import app_config

logger = logging.getLogger()

router = APIRouter(prefix="/health", tags=["健康检查"])


@router.get("/", response_model=HealthResponse, summary="健康检查")
async def health_check() -> HealthResponse:
    """系统健康检查"""
    try:
        components = {
            "retrieval_chain": "ok" if retrieval_chain.initialized else "error",
            "llm": "ok" if retrieval_chain.llm else "error",
            "config": "ok" if app_config.llm_api_key else "error",
        }

        overall_status = (
            "ok" if all(status == "ok" for status in components.values()) else "error"
        )

        return HealthResponse(
            status=overall_status,
            components=components,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
        )

    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        raise HTTPException(status_code=500, detail="健康检查失败")


@router.get("/info", summary="系统信息")
async def system_info() -> Dict[str, Any]:
    """获取系统信息"""
    try:
        return {
            "service_name": "RAG智能问答服务",
            "version": "1.0.0",
            "model": app_config.llm_model,
            "max_tokens": app_config.max_tokens_limit,
            "relevance_threshold": app_config.relevance_threshold,
        }

    except Exception as e:
        logger.error(f"获取系统信息失败: {e}")
        raise HTTPException(status_code=500, detail="获取系统信息失败") 