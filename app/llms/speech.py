import logging
from io import BytesIO

from openai import OpenAI

from config.settings import app_config

logger = logging.getLogger(__name__)


class OpenAISpeechClient:
    """OpenAI语音能力客户端，统一处理STT和TTS。"""

    def __init__(self, api_key: str | None = None, timeout: int = 60):
        resolved_api_key = api_key or app_config.openai_api_key
        if not resolved_api_key:
            raise RuntimeError("OPENAI_API_KEY 未配置")

        self.client = OpenAI(api_key=resolved_api_key, timeout=timeout)
        self.transcription_model = app_config.openai_transcription_model
        self.tts_model = app_config.openai_tts_model
        self.tts_voice = app_config.openai_tts_voice
        self.tts_format = app_config.openai_tts_format

    def transcribe(
        self,
        content: bytes,
        filename: str,
        content_type: str | None = None,
    ) -> str:
        """把音频字节转成文本。"""
        if not content:
            raise ValueError("音频内容不能为空")

        audio_file = BytesIO(content)
        audio_file.name = filename or "audio.webm"

        transcription = self.client.audio.transcriptions.create(
            model=self.transcription_model,
            file=(audio_file.name, audio_file, content_type or "application/octet-stream"),
        )
        text = transcription.text.strip()
        logger.info("语音识别完成，文本长度: %s", len(text))
        return text

    def synthesize(
        self,
        text: str,
        voice: str | None = None,
        response_format: str | None = None,
    ) -> tuple[bytes, str]:
        """把文本转成语音字节。"""
        clean_text = text.strip()
        if not clean_text:
            raise ValueError("语音合成文本不能为空")

        audio_format = response_format or self.tts_format
        with self.client.audio.speech.with_streaming_response.create(
            model=self.tts_model,
            voice=voice or self.tts_voice,
            input=clean_text,
            response_format=audio_format,
        ) as response:
            audio_bytes = response.read()

        logger.info("语音合成完成，音频大小: %s bytes", len(audio_bytes))
        return audio_bytes, audio_format
_speech_client: OpenAISpeechClient | None = None


def get_speech_client() -> OpenAISpeechClient:
    """按需创建语音客户端，避免应用导入阶段强依赖API Key。"""
    global _speech_client
    if _speech_client is None:
        _speech_client = OpenAISpeechClient()
    return _speech_client
