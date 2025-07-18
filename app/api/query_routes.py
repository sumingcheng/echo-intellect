from fastapi import APIRouter, HTTPException
import logging
import uuid

from app.api.models.requests import QueryRequest
from app.api.models.responses import QueryResponse
from app.chains.retrieval_chain import retrieval_chain

logger = logging.getLogger()

router = APIRouter(prefix="/query", tags=["查询"])


@router.post("/", response_model=QueryResponse, summary="查询问答")
async def query_endpoint(request: QueryRequest) -> QueryResponse:
    """执行RAG查询"""
    try:
        # 生成会话ID（如果未提供）
        session_id = request.session_id or str(uuid.uuid4())

        # 执行RAG检索
        result = retrieval_chain.run(
            question=request.question,
            session_id=session_id,
            template_name=request.template_name,
            max_tokens=request.max_tokens,
            relevance_threshold=request.relevance_threshold,
            enable_rerank=request.enable_rerank,
            enable_optimization=request.enable_optimization,
            enable_expansion=request.enable_expansion,
        )

        # 检查是否有错误
        if result.get("error"):
            raise HTTPException(status_code=500, detail=result["answer"])

        return QueryResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询处理失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询处理失败: {str(e)}") 