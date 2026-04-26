import logging
from io import BytesIO

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.api.models.requests import SpeechSynthesisRequest
from app.api.models.responses import SpeechTranscriptionResponse
from app.llms.speech import get_speech_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/speech", tags=["语音"])

MEDIA_TYPES = {
    "mp3": "audio/mpeg",
    "opus": "audio/opus",
    "aac": "audio/aac",
    "flac": "audio/flac",
    "wav": "audio/wav",
    "pcm": "audio/L16",
}


@router.post(
    "/transcriptions",
    response_model=SpeechTranscriptionResponse,
    summary="语音转文字",
)
async def transcribe_audio(
    file: UploadFile = File(...),
) -> SpeechTranscriptionResponse:
    """接收前端录音文件，返回识别后的文本。"""
    try:
        content = await file.read()
        text = get_speech_client().transcribe(
            content=content,
            filename=file.filename or "audio.webm",
            content_type=file.content_type,
        )
        return SpeechTranscriptionResponse(
            text=text,
            model=get_speech_client().transcription_model,
        )

    except Exception as e:
        logger.error("语音识别失败: %s", e)
        raise HTTPException(status_code=500, detail=f"语音识别失败: {e}")


@router.post("/audio", summary="文字转语音")
async def synthesize_speech(request: SpeechSynthesisRequest) -> StreamingResponse:
    """接收文本，返回可直接播放的音频流。"""
    try:
        audio_bytes, audio_format = get_speech_client().synthesize(
            text=request.text,
            voice=request.voice,
            response_format=request.response_format,
        )
        media_type = MEDIA_TYPES.get(audio_format, "application/octet-stream")
        return StreamingResponse(
            BytesIO(audio_bytes),
            media_type=media_type,
            headers={
                "Content-Disposition": f'inline; filename="speech.{audio_format}"',
                "X-Audio-Format": audio_format,
            },
        )

    except Exception as e:
        logger.error("语音合成失败: %s", e)
        raise HTTPException(status_code=500, detail=f"语音合成失败: {e}")
