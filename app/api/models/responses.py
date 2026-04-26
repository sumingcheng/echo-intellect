from pydantic import BaseModel, Field
from typing import Dict, Any, Optional


class QueryResponse(BaseModel):
    question: str = Field(description="用户问题")
    answer: str = Field(description="生成的答案")
    query_id: str = Field(description="查询ID")
    session_id: Optional[str] = Field(description="会话ID")
    processing_time: float = Field(description="处理时间(秒)")
    tokens_used: int = Field(description="使用的token数")
    relevance_score: float = Field(description="平均相关性得分")
    retrieved_chunks_count: int = Field(description="检索到的内容块数量")
    metadata: Dict[str, Any] = Field(description="元数据")


class ChatSpeechResponse(BaseModel):
    endpoint: str = Field(description="文字转语音接口路径")
    text: str = Field(description="需要合成语音的文本")
    voice: Optional[str] = Field(description="建议使用的声音名称")
    response_format: Optional[str] = Field(description="建议使用的音频格式")


class ChatResponse(BaseModel):
    message: str = Field(description="用户消息")
    answer: str = Field(description="助手回答")
    query_id: str = Field(description="查询ID")
    session_id: Optional[str] = Field(description="会话ID")
    processing_time: float = Field(description="处理时间(秒)")
    tokens_used: int = Field(description="使用的token数")
    relevance_score: float = Field(description="平均相关性得分")
    retrieved_chunks_count: int = Field(description="检索到的内容块数量")
    metadata: Dict[str, Any] = Field(description="元数据")
    speech: Optional[ChatSpeechResponse] = Field(None, description="语音响应信息")


class HealthResponse(BaseModel):
    status: str = Field(description="系统状态")
    components: Dict[str, str] = Field(description="组件状态")
    timestamp: str = Field(description="检查时间")


class SpeechTranscriptionResponse(BaseModel):
    text: str = Field(description="语音识别后的文本")
    model: str = Field(description="使用的语音识别模型")