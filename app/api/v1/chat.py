import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_container
from app.api.models.requests import ChatRequest
from app.api.models.responses import ChatResponse, ChatSpeechResponse
from app.core.container import AppContainer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["对话"])


@router.post("", response_model=ChatResponse, summary="统一对话入口")
async def chat_endpoint(
    request: ChatRequest,
    container: AppContainer = Depends(get_container),
) -> ChatResponse:
    """统一文本和语音前端的对话入口。"""
    try:
        session_id = request.session_id or str(uuid.uuid4())

        result = container.retrieval_chain.run(
            question=request.message,
            session_id=session_id,
            model=request.model,
            template_name=request.template_name,
            max_tokens=request.max_tokens,
            relevance_threshold=request.relevance_threshold,
            enable_rerank=request.enable_rerank,
            enable_optimization=request.enable_optimization,
            enable_expansion=request.enable_expansion,
        )

        if result.get("error"):
            raise HTTPException(status_code=500, detail=result["answer"])

        speech = None
        if request.response_mode == "voice":
            # 前端拿到回答后调用TTS接口，避免JSON接口混入二进制音频。
            speech = ChatSpeechResponse(
                endpoint="/api/v1/speech/audio",
                text=result["answer"],
                voice=request.tts_voice,
                response_format=request.tts_format,
            )

        return ChatResponse(
            message=request.message,
            answer=result["answer"],
            query_id=result["query_id"],
            session_id=result["session_id"],
            processing_time=result["processing_time"],
            tokens_used=result["tokens_used"],
            relevance_score=result["relevance_score"],
            retrieved_chunks_count=result["retrieved_chunks_count"],
            metadata=result["metadata"],
            speech=speech,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("对话处理失败: %s", e)
        raise HTTPException(status_code=500, detail=f"对话处理失败: {e}")


@router.post("/stream", summary="流式对话")
async def chat_stream(
    request: ChatRequest,
    container: AppContainer = Depends(get_container),
):
    """SSE 流式输出，前端逐 token 渲染。"""
    session_id = request.session_id or str(uuid.uuid4())

    return StreamingResponse(
        container.retrieval_chain.run_stream(
            question=request.message,
            session_id=session_id,
            model=request.model,
            template_name=request.template_name,
            max_tokens=request.max_tokens,
            relevance_threshold=request.relevance_threshold,
            enable_rerank=request.enable_rerank,
            enable_optimization=request.enable_optimization,
            enable_expansion=request.enable_expansion,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
