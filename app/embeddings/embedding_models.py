import logging
import httpx
from typing import List, Dict, Any, Optional
from langchain_core.embeddings import Embeddings

from config.settings import app_config

logger = logging.getLogger()


class OllamaEmbeddings(Embeddings):
    """Ollama嵌入模型客户端"""

    def __init__(
        self, model: str = "bge-m3:latest", base_url: str = None, timeout: int = 60
    ):
        self.model = model
        self.base_url = base_url or app_config.embedding_service
        self.timeout = timeout
        self.client = httpx.Client(timeout=timeout)

        logger.info(f"初始化Ollama嵌入模型: {model} @ {self.base_url}")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """批量生成文档嵌入向量"""
        try:
            embeddings = []

            for text in texts:
                response = self.client.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": self.model, "prompt": text},
                )
                response.raise_for_status()

                result = response.json()
                if "embedding" in result:
                    embeddings.append(result["embedding"])
                else:
                    logger.error(f"Ollama响应中缺少embedding字段: {result}")
                    embeddings.append([0.0] * 1024)

            logger.debug(f"成功生成 {len(embeddings)} 个文档嵌入向量")
            return embeddings

        except Exception as e:
            logger.error(f"生成文档嵌入向量失败: {e}")
            raise

    def embed_query(self, text: str) -> List[float]:
        """生成查询嵌入向量"""
        try:
            response = self.client.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": text},
            )
            response.raise_for_status()

            result = response.json()
            if "embedding" in result:
                logger.debug(f"成功生成查询嵌入向量，维度: {len(result['embedding'])}")
                return result["embedding"]
            else:
                logger.error(f"Ollama响应中缺少embedding字段: {result}")
                return [0.0] * 1024

        except Exception as e:
            logger.error(f"生成查询嵌入向量失败: {e}")
            raise

    def get_embedding_dimension(self) -> int:
        """获取嵌入向量维度"""
        try:
            test_embedding = self.embed_query("test")
            dimension = len(test_embedding)
            logger.info(f"嵌入向量维度: {dimension}")
            return dimension

        except Exception as e:
            logger.error(f"获取嵌入向量维度失败: {e}")
            return 1024

    def health_check(self) -> bool:
        """健康检查"""
        try:
            # 测试Ollama服务可用性
            test_response = self.client.get(f"{self.base_url}/api/tags")
            test_response.raise_for_status()

            # 测试模型可用性
            embed_response = self.client.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": "health check"},
            )
            embed_response.raise_for_status()

            result = embed_response.json()
            return "embedding" in result

        except Exception as e:
            logger.error(f"嵌入服务健康检查失败: {e}")
            return False

    def close(self):
        """关闭客户端连接"""
        if self.client:
            self.client.close()
            logger.info("Ollama客户端连接已关闭")


class EmbeddingManager:
    """嵌入模型管理器"""

    def __init__(self):
        self.embeddings: Optional[OllamaEmbeddings] = None
        self.dimension: Optional[int] = None
        self.model: str = "bge-m3:latest"

    def initialize(self) -> bool:
        """初始化嵌入模型"""
        try:
            self.embeddings = OllamaEmbeddings()

            if not self.embeddings.health_check():
                raise Exception("Ollama嵌入服务健康检查失败")

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
