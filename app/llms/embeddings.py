import logging
from typing import List, Optional

from langchain_core.embeddings import Embeddings
from openai import OpenAI

from config.settings import app_config

logger = logging.getLogger()


class OpenAIEmbeddings(Embeddings):
    """OpenAI嵌入模型客户端"""

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        timeout: int = 60,
    ):
        self.model = model or app_config.openai_embedding_model
        self.dimension = app_config.openai_embedding_dimension
        self.timeout = timeout

        resolved_api_key = api_key or app_config.openai_api_key
        if not resolved_api_key:
            raise RuntimeError("OPENAI_API_KEY 未配置")

        self.client = OpenAI(api_key=resolved_api_key, timeout=timeout)
        logger.info(f"初始化OpenAI嵌入模型: {self.model}")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """批量生成文档嵌入向量"""
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=texts,
            )
            embeddings = [item.embedding for item in response.data]

            logger.debug(f"成功生成 {len(embeddings)} 个文档嵌入向量")
            return embeddings

        except Exception as e:
            logger.error(f"生成文档嵌入向量失败: {e}")
            raise

    def embed_query(self, text: str) -> List[float]:
        """生成查询嵌入向量"""
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text,
            )
            embedding = response.data[0].embedding
            logger.debug(f"成功生成查询嵌入向量，维度: {len(embedding)}")
            return embedding

        except Exception as e:
            logger.error(f"生成查询嵌入向量失败: {e}")
            raise

    def get_embedding_dimension(self) -> int:
        """获取嵌入向量维度"""
        return self.dimension

    def health_check(self) -> bool:
        """健康检查"""
        try:
            embedding = self.embed_query("health check")
            return len(embedding) == self.dimension

        except Exception as e:
            logger.error(f"嵌入服务健康检查失败: {e}")
            return False

    def close(self):
        """关闭客户端连接"""
        logger.info("OpenAI嵌入客户端无需显式关闭")


class EmbeddingManager:
    """嵌入模型管理器"""

    def __init__(self):
        self.embeddings: Optional[OpenAIEmbeddings] = None
        self.dimension: Optional[int] = None
        self.model: str = app_config.openai_embedding_model

    def initialize(self) -> bool:
        """初始化嵌入模型"""
        try:
            self.embeddings = OpenAIEmbeddings(model=self.model)

            if not self.embeddings.health_check():
                raise Exception("OpenAI嵌入服务健康检查失败")

            self.dimension = self.embeddings.get_embedding_dimension()

            logger.info(f"嵌入模型初始化成功，维度: {self.dimension}")
            return True

        except Exception as e:
            logger.error(f"初始化嵌入模型失败: {e}")
            return False

    def embed_text(self, text: str) -> List[float]:
        """单个文本嵌入"""
        if not self.embeddings:
            raise RuntimeError("嵌入模型未初始化")

        return self.embeddings.embed_query(text)

    def embed_query(self, text: str) -> List[float]:
        """单个查询嵌入"""
        return self.embed_text(text)

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """批量文本嵌入"""
        if not self.embeddings:
            raise RuntimeError("嵌入模型未初始化")

        return self.embeddings.embed_documents(texts)

    def get_dimension(self) -> int:
        """获取向量维度"""
        if self.dimension is None:
            raise RuntimeError("嵌入模型未初始化")

        return self.dimension

    def close(self):
        """关闭连接"""
        if self.embeddings:
            self.embeddings.close()


# 全局实例
embedding_manager = EmbeddingManager()
