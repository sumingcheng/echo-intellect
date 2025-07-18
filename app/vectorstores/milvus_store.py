import logging
from typing import List, Dict, Any, Optional
from pymilvus import (
    connections,
    Collection,
    FieldSchema,
    CollectionSchema,
    DataType,
    utility,
)
from pymilvus.exceptions import MilvusException
import numpy as np

from config.settings import app_config
from app.models.data_models import EmbeddingVector, RetrievalResult

logger = logging.getLogger()


class MilvusVectorStore:
    """Milvus向量数据库存储管理器"""

    def __init__(self):
        self.collection: Optional[Collection] = None
        self.collection_name = app_config.milvus_collection
        self.dimension: Optional[int] = None
        self.connected = False

    def connect(self, dimension: int = 1024):
        """连接Milvus数据库"""
        try:
            connections.connect(alias="default", uri=app_config.milvus_uri)

            self.dimension = dimension
            self.connected = True

            self._setup_collection()

            logger.info(f"Milvus连接成功，集合: {self.collection_name}")

        except Exception as e:
            logger.error(f"Milvus连接失败: {e}")
            raise

    def _setup_collection(self):
        """设置集合（创建或加载）"""
        try:
            if utility.has_collection(self.collection_name):
                self.collection = Collection(self.collection_name)
                self.collection.load()
                logger.info(f"加载现有集合: {self.collection_name}")
            else:
                self._create_collection()
                logger.info(f"创建新集合: {self.collection_name}")

        except Exception as e:
            logger.error(f"设置集合失败: {e}")
            raise

    def _create_collection(self):
        """创建新集合"""
        try:
            fields = [
                FieldSchema(
                    name="id",
                    dtype=DataType.VARCHAR,
                    max_length=128,
                    is_primary=True,
                    auto_id=False,
                    description="向量ID",
                ),
                FieldSchema(
                    name="data_id",
                    dtype=DataType.VARCHAR,
                    max_length=128,
                    description="数据ID",
                ),
                FieldSchema(
                    name="embedding",
                    dtype=DataType.FLOAT_VECTOR,
                    dim=self.dimension,
                    description="嵌入向量",
                ),
            ]

            schema = CollectionSchema(
                fields=fields,
                description=f"RAG知识库向量集合",
                enable_dynamic_field=True,
            )

            self.collection = Collection(name=self.collection_name, schema=schema)

            self._create_index()

            self.collection.load()

        except Exception as e:
            logger.error(f"创建集合失败: {e}")
            raise

    def _create_index(self):
        """创建向量索引"""
        try:
            index_params = {
                "metric_type": "COSINE",
                "index_type": "HNSW",
                "params": {"M": 16, "efConstruction": 200},
            }

            self.collection.create_index(
                field_name="embedding", index_params=index_params
            )

            logger.info("向量索引创建成功")

        except Exception as e:
            logger.error(f"创建索引失败: {e}")
            raise

    def insert_vectors(self, vectors: List[EmbeddingVector]) -> bool:
        """批量插入向量"""
        try:
            if not self.collection:
                raise RuntimeError("集合未初始化")

            data = []
            for vector in vectors:
                data.append(
                    {
                        "id": vector.id,
                        "data_id": vector.data_id,
                        "embedding": vector.vector,
                    }
                )

            insert_result = self.collection.insert(data)

            self.collection.flush()

            logger.info(f"成功插入 {len(vectors)} 个向量")
            return True

        except Exception as e:
            logger.error(f"插入向量失败: {e}")
            return False

    def search_vectors(
        self, query_vector: List[float], top_k: int = 10, score_threshold: float = 0.0
    ) -> List[RetrievalResult]:
        """向量搜索"""
        try:
            if not self.collection:
                raise RuntimeError("集合未初始化")

            search_params = {
                "metric_type": "COSINE",
                "params": {"ef": max(top_k * 2, 64)},
            }

            search_results = self.collection.search(
                data=[query_vector],
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                output_fields=["id", "data_id"],
            )

            results = []
            for hits in search_results:
                for hit in hits:
                    if hit.score >= score_threshold:
                        result = RetrievalResult(
                            data_id=hit.entity.get("data_id", ""),
                            collection_id="",
                            content="",
                            score=hit.score,
                            source="embedding",
                            metadata={"vector_id": hit.id},
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
            if not self.collection:
                raise RuntimeError("集合未初始化")

            id_list = "', '".join(vector_ids)
            expr = f"id in ['{id_list}']"

            delete_result = self.collection.delete(expr)

            self.collection.flush()

            logger.info(f"成功删除 {len(vector_ids)} 个向量")
            return True

        except Exception as e:
            logger.error(f"删除向量失败: {e}")
            return False

    def close(self):
        """关闭连接"""
        try:
            if self.collection:
                self.collection.release()

            connections.disconnect("default")
            self.connected = False

            logger.info("Milvus连接已关闭")

        except Exception as e:
            logger.warning(f"关闭Milvus连接时出现警告: {e}")


# 全局实例
milvus_store = MilvusVectorStore()
