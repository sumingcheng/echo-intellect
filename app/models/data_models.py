from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


# 核心数据模型


class Dataset(BaseModel):
    """数据集模型"""

    id: str = Field(description="数据集ID")
    name: str = Field(description="数据集名称")
    description: str = Field(description="数据集描述")

    # 统计信息
    collection_count: int = Field(default=0, description="集合数量")
    data_count: int = Field(default=0, description="数据条目数量")
    total_tokens: int = Field(default=0, description="总token数")

    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")


class Collection(BaseModel):
    """集合模型 - 文件级管理"""

    id: str = Field(description="集合ID")
    dataset_id: str = Field(description="所属数据集ID")
    name: str = Field(description="集合名称")
    description: str = Field(description="集合描述")

    # 元数据
    source_file: Optional[str] = Field(default=None, description="源文件路径")
    file_type: Optional[str] = Field(default=None, description="文件类型")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="集合元数据")

    # 统计信息
    data_count: int = Field(default=0, description="数据条目数量")
    total_tokens: int = Field(default=0, description="总token数")

    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")


class Data(BaseModel):
    """数据模型 - 支持多向量映射"""

    id: str = Field(description="数据ID")
    collection_id: str = Field(description="所属集合ID")
    content: str = Field(description="数据内容")
    title: Optional[str] = Field(default=None, description="数据标题")

    # 多向量映射
    vector_ids: List[str] = Field(default_factory=list, description="对应的向量ID数组")

    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict, description="数据元数据")
    sequence: Optional[int] = Field(default=None, description="在集合中的序号")
    tokens: int = Field(default=0, description="token数量")

    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")


class EmbeddingVector(BaseModel):
    """向量数据模型"""

    id: str = Field(description="向量ID")
    data_id: str = Field(description="对应的数据ID")
    vector: List[float] = Field(description="向量数据")
    model: str = Field(description="使用的嵌入模型")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")


# 查询和结果模型


class Query(BaseModel):
    """查询模型"""

    id: str = Field(description="查询唯一标识")
    question: str = Field(description="原始问题")
    optimized_question: Optional[str] = Field(default=None, description="优化后的问题")
    expanded_queries: List[str] = Field(
        default_factory=list, description="扩展查询列表"
    )
    concat_query: Optional[str] = Field(default=None, description="合并查询")

    # 配置参数
    max_tokens: int = Field(default=4000, description="最大token限制")
    relevance_threshold: float = Field(default=0.6, description="相关性阈值")
    top_k: int = Field(default=10, description="召回数量")


class RetrievalResult(BaseModel):
    """检索结果模型"""

    data_id: str = Field(description="数据ID")
    collection_id: str = Field(description="集合ID")
    content: str = Field(description="内容")
    score: float = Field(description="相似度得分")
    source: str = Field(description="检索来源：embedding/bm25")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    tokens: int = Field(default=0, description="token数量")


class RerankResult(BaseModel):
    """重排结果模型"""

    data_id: str = Field(description="数据ID")
    collection_id: str = Field(description="集合ID")
    content: str = Field(description="内容")
    original_score: float = Field(description="原始检索得分")
    rerank_score: float = Field(description="重排得分")
    final_score: float = Field(description="最终得分")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    tokens: int = Field(default=0, description="token数量")


class ConversationTurn(BaseModel):
    """对话轮次模型"""

    id: str = Field(description="对话轮次ID")
    session_id: str = Field(description="会话ID")
    question: str = Field(description="用户问题")
    answer: str = Field(description="系统回答")
    retrieved_chunks: List[RetrievalResult] = Field(
        default_factory=list, description="检索到的内容"
    )
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")

    # 统计信息
    tokens_used: int = Field(default=0, description="使用的token数")
    relevance_score: float = Field(default=0.0, description="相关性得分")
    response_time: float = Field(default=0.0, description="响应时间(秒)")
