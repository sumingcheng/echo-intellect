from typing import Literal, Optional

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(..., description="用户问题")
    session_id: Optional[str] = Field(None, description="会话ID")
    max_tokens: int = Field(4000, description="最大token数量")
    relevance_threshold: float = Field(0.6, description="相关性阈值")
    template_name: str = Field("basic_rag", description="提示模板名称")
    enable_rerank: bool = Field(False, description="是否启用重排")
    enable_optimization: bool = Field(True, description="是否启用查询优化")
    enable_expansion: bool = Field(True, description="是否启用查询扩展")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="用户消息")
    session_id: Optional[str] = Field(None, description="会话ID")
    model: Optional[str] = Field(None, description="LLM模型ID，不填使用默认模型")
    response_mode: Literal["text", "voice"] = Field("text", description="响应模式")
    max_tokens: int = Field(4000, description="最大token数量")
    relevance_threshold: float = Field(0.6, description="相关性阈值")
    template_name: str = Field("basic_rag", description="提示模板名称")
    enable_rerank: bool = Field(False, description="是否启用重排")
    enable_optimization: bool = Field(True, description="是否启用查询优化")
    enable_expansion: bool = Field(True, description="是否启用查询扩展")
    tts_voice: Optional[str] = Field(None, description="语音响应声音名称")
    tts_format: Optional[Literal["mp3", "opus", "aac", "flac", "wav", "pcm"]] = Field(
        None,
        description="语音响应音频格式",
    )


class SpeechSynthesisRequest(BaseModel):
    text: str = Field(..., min_length=1, description="需要转换为语音的文本")
    voice: Optional[str] = Field(None, description="OpenAI TTS声音名称")
    response_format: Optional[Literal["mp3", "opus", "aac", "flac", "wav", "pcm"]] = (
        Field(None, description="音频输出格式")
    )