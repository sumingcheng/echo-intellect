from pydantic import BaseModel, Field
from typing import Optional


class QueryRequest(BaseModel):
    question: str = Field(..., description="用户问题")
    session_id: Optional[str] = Field(None, description="会话ID")
    max_tokens: int = Field(4000, description="最大token数量")
    relevance_threshold: float = Field(0.6, description="相关性阈值")
    template_name: str = Field("basic_rag", description="提示模板名称")
    enable_rerank: bool = Field(True, description="是否启用重排")
    enable_optimization: bool = Field(True, description="是否启用查询优化")
    enable_expansion: bool = Field(True, description="是否启用查询扩展") 