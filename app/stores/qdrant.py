import logging
from typing import List, Optional

from qdrant_client import QdrantClient, models

from app.models.data_models import EmbeddingVector, RetrievalResult
from config.settings import app_config

logger = logging.getLogger()


class QdrantVectorStore:
    """Qdrant向量数据库存储管理器"""

    def __init__(self):
        self.client: Optional[QdrantClient] = None
        self.collection_name = app_config.qdrant_collection
        self.dimension: Optional[int] = None
        self.connected = False

    def connect(self, dimension: int = 1536):
        """连接Qdrant数据库"""
        try:
            api_key = app_config.qdrant_api_key or None
            self.client = QdrantClient(url=app_config.qdrant_url, api_key=api_key)
            self.dimension = dimension
            self._setup_collection()
            self.connected = True
            logger.info(f"Qdrant连接成功，集合: {self.collection_name}")

        except Exception as e:
            logger.error(f"Qdrant连接失败: {e}")
            raise

    def _setup_collection(self):
        """设置集合（创建或复用）"""
        if not self.client:
            raise RuntimeError("Qdrant客户端未初始化")

        try:
            self.client.get_collection(self.collection_name)
            logger.info(f"加载现有集合: {self.collection_name}")
            return
        except Exception:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=self.dimension,
                    distance=models.Distance.COSINE,
                ),
            )
            logger.info(f"创建新集合: {self.collection_name}")

    def insert_vectors(self, vectors: List[EmbeddingVector]) -> bool:
        """批量插入向量"""
        try:
            if not self.client:
                raise RuntimeError("Qdrant客户端未初始化")

            points = [
                models.PointStruct(
                    id=vector.id,
                    vector=vector.vector,
                    payload={
                        "data_id": vector.data_id,
                        "model": vector.model,
                    },
                )
                for vector in vectors
            ]

            self.client.upsert(
                collection_name=self.collection_name,
                points=points,
                wait=True,
            )

            logger.info(f"成功插入 {len(vectors)} 个向量")
            return True

        except Exception as e:
            logger.error(f"插入向量失败: {e}")
            return False

    def search_vectors(
        self,
        query_vector: List[float],
        top_k: int = 10,
        score_threshold: float = 0.0,
    ) -> List[RetrievalResult]:
        """向量搜索"""
        try:
            if not self.client:
                raise RuntimeError("Qdrant客户端未初始化")

            search_result = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                limit=top_k,
                score_threshold=score_threshold,
                with_payload=True,
            )

            results = []
            for point in search_result.points:
                payload = point.payload or {}
                result = RetrievalResult(
                    data_id=str(payload.get("data_id", "")),
                    collection_id="",
                    content="",
                    score=point.score,
                    source="embedding",
                    metadata={"vector_id": str(point.id)},
                    tokens=0,
                )
                results.append(result)

            logger.debug(f"向量搜索返回 {len(results)} 个结果")
            return results

        except Exception as e:
            logger.error(f"向量搜索失败: {e}")
            return []

    def delete_vectors(self, vector_ids: List[str]) -> bool:
        """删除向量"""
        try:
            if not self.client:
                raise RuntimeError("Qdrant客户端未初始化")

            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(points=vector_ids),
                wait=True,
            )

            logger.info(f"成功删除 {len(vector_ids)} 个向量")
            return True

        except Exception as e:
            logger.error(f"删除向量失败: {e}")
            return False

    def delete_collection(self) -> bool:
        """删除整个集合"""
        try:
            if not self.client:
                raise RuntimeError("Qdrant客户端未初始化")

            self.client.delete_collection(collection_name=self.collection_name)
            logger.info(f"Qdrant集合已删除: {self.collection_name}")
            return True

        except Exception as e:
            logger.error(f"删除Qdrant集合失败: {e}")
            return False

    def close(self):
        """关闭连接"""
        self.connected = False
        if self.client:
            self.client.close()
            logger.info("Qdrant连接已关闭")


# 全局实例
qdrant_store = QdrantVectorStore()
