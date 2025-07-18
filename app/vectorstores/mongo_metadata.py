import logging
from typing import List, Optional, Dict, Any
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection as PyMongoCollection
from datetime import datetime

from config.settings import app_config
from app.models.data_models import Dataset, Collection, Data, ConversationTurn

logger = logging.getLogger()


class MongoMetadataStore:
    """MongoDB元数据存储管理器 - 支持Dataset->Collection->Data三层架构"""

    def __init__(self):
        self.client: Optional[MongoClient] = None
        self.db: Optional[Database] = None
        self._collections: Dict[str, PyMongoCollection] = {}

    def connect(self):
        """连接MongoDB"""
        try:
            self.client = MongoClient(app_config.mongodb_uri)
            self.db = self.client.get_default_database()

            self._collections = {
                "datasets": self.db.datasets,
                "collections": self.db.collections,
                "data": self.db.data,
                "conversations": self.db.conversations,
            }

            self._create_indexes()

            logger.info("MongoDB连接成功，支持三层架构")

        except Exception as e:
            logger.error(f"MongoDB连接失败: {e}")
            raise

    def _create_indexes(self):
        """创建必要的索引"""
        try:
            self._collections["datasets"].create_index("id", unique=True)
            self._collections["datasets"].create_index("name")

            self._collections["collections"].create_index("id", unique=True)
            self._collections["collections"].create_index("dataset_id")
            self._collections["collections"].create_index("name")

            self._collections["data"].create_index("id", unique=True)
            self._collections["data"].create_index("collection_id")
            self._collections["data"].create_index("vector_ids")
            self._collections["data"].create_index([("content", "text")])

            self._collections["conversations"].create_index("session_id")
            self._collections["conversations"].create_index("timestamp")

            logger.info("MongoDB索引创建完成")

        except Exception as e:
            logger.warning(f"创建索引时出现警告: {e}")

    def close(self):
        """关闭连接"""
        if self.client:
            self.client.close()
            logger.info("MongoDB连接已关闭")

    # 数据集操作

    def create_dataset(self, dataset: Dataset) -> bool:
        """创建数据集"""
        try:
            result = self._collections["datasets"].insert_one(dataset.model_dump())
            logger.info(f"创建数据集: {dataset.name} (ID: {dataset.id})")
            return result.acknowledged

        except Exception as e:
            logger.error(f"创建数据集失败: {e}")
            return False

    def get_dataset(self, dataset_id: str) -> Optional[Dataset]:
        """获取数据集"""
        try:
            doc = self._collections["datasets"].find_one({"id": dataset_id})
            if doc:
                doc.pop("_id", None)
                return Dataset(**doc)
            return None

        except Exception as e:
            logger.error(f"获取数据集失败: {e}")
            return None

    def update_dataset_stats(self, dataset_id: str, data_count: int, total_tokens: int):
        """更新数据集统计信息"""
        try:
            self._collections["datasets"].update_one(
                {"id": dataset_id},
                {
                    "$inc": {"data_count": data_count, "total_tokens": total_tokens},
                    "$set": {"updated_at": datetime.now()},
                },
            )
            logger.debug(f"更新数据集统计: {dataset_id}")

        except Exception as e:
            logger.error(f"更新数据集统计失败: {e}")

    # 集合操作

    def create_collection(self, collection: Collection) -> bool:
        """创建集合"""
        try:
            result = self._collections["collections"].insert_one(
                collection.model_dump()
            )
            logger.info(f"创建集合: {collection.name} (ID: {collection.id})")
            return result.acknowledged

        except Exception as e:
            logger.error(f"创建集合失败: {e}")
            return False

    def get_collection(self, collection_id: str) -> Optional[Collection]:
        """获取集合"""
        try:
            doc = self._collections["collections"].find_one({"id": collection_id})
            if doc:
                doc.pop("_id", None)
                return Collection(**doc)
            return None

        except Exception as e:
            logger.error(f"获取集合失败: {e}")
            return None

    def update_collection_stats(
        self, collection_id: str, data_count: int, total_tokens: int
    ):
        """更新集合统计信息"""
        try:
            self._collections["collections"].update_one(
                {"id": collection_id},
                {
                    "$inc": {"data_count": data_count, "total_tokens": total_tokens},
                    "$set": {"updated_at": datetime.now()},
                },
            )
            logger.debug(f"更新集合统计: {collection_id}")

        except Exception as e:
            logger.error(f"更新集合统计失败: {e}")

    # 数据操作（支持多向量映射）

    def create_data(self, data: Data) -> bool:
        """创建数据条目（支持多向量映射）"""
        try:
            result = self._collections["data"].insert_one(data.model_dump())
            logger.debug(f"创建数据: {data.id}, 向量数: {len(data.vector_ids)}")
            return result.acknowledged

        except Exception as e:
            logger.error(f"创建数据失败: {e}")
            return False

    def get_data(self, data_id: str) -> Optional[Data]:
        """获取数据条目"""
        try:
            doc = self._collections["data"].find_one({"id": data_id})
            if doc:
                doc.pop("_id", None)
                return Data(**doc)
            return None

        except Exception as e:
            logger.error(f"获取数据失败: {e}")
            return None

    def get_data_by_vector_ids(self, vector_ids: List[str]) -> List[Data]:
        """根据向量ID列表获取数据（多向量映射核心功能）"""
        try:
            docs = self._collections["data"].find({"vector_ids": {"$in": vector_ids}})

            data_list = []
            for doc in docs:
                doc.pop("_id", None)
                data_list.append(Data(**doc))

            logger.debug(f"根据{len(vector_ids)}个向量ID找到{len(data_list)}个数据条目")
            return data_list

        except Exception as e:
            logger.error(f"根据向量ID获取数据失败: {e}")
            return []

    def search_data_by_content(
        self, query: str, collection_id: Optional[str] = None, limit: int = 20
    ) -> List[Data]:
        """基于内容的全文检索（BM25）"""
        try:
            search_condition = {"$text": {"$search": query}}

            if collection_id:
                search_condition["collection_id"] = collection_id

            docs = (
                self._collections["data"]
                .find(search_condition, {"score": {"$meta": "textScore"}})
                .sort([("score", {"$meta": "textScore"})])
                .limit(limit)
            )

            data_list = []
            for doc in docs:
                doc.pop("_id", None)
                bm25_score = doc.pop("score", 0.0)
                data = Data(**doc)
                data.metadata["bm25_score"] = bm25_score
                data_list.append(data)

            logger.debug(f"全文检索找到{len(data_list)}个结果")
            return data_list

        except Exception as e:
            logger.error(f"全文检索失败: {e}")
            return []

    # 对话历史操作

    def save_conversation_turn(self, turn: ConversationTurn) -> bool:
        """保存对话轮次"""
        try:
            result = self._collections["conversations"].insert_one(turn.model_dump())
            return result.acknowledged

        except Exception as e:
            logger.error(f"保存对话轮次失败: {e}")
            return False

    def get_conversation_history(
        self, session_id: str, limit: int = 10
    ) -> List[ConversationTurn]:
        """获取对话历史"""
        try:
            docs = (
                self._collections["conversations"]
                .find({"session_id": session_id})
                .sort("timestamp", -1)
                .limit(limit)
            )

            history = []
            for doc in docs:
                doc.pop("_id", None)
                history.append(ConversationTurn(**doc))

            return list(reversed(history))

        except Exception as e:
            logger.error(f"获取对话历史失败: {e}")
            return []

    # 导入服务支持方法

    def get_dataset_by_name(self, name: str) -> Optional[Dataset]:
        """根据名称获取数据集"""
        try:
            doc = self._collections["datasets"].find_one({"name": name})
            if doc:
                doc.pop("_id", None)
                return Dataset(**doc)
            return None
        except Exception as e:
            logger.error(f"根据名称获取数据集失败: {e}")
            return None

    def get_collections_by_dataset(self, dataset_id: str) -> List[Collection]:
        """获取数据集下的所有集合"""
        try:
            docs = self._collections["collections"].find({"dataset_id": dataset_id})
            collections = []
            for doc in docs:
                doc.pop("_id", None)
                collections.append(Collection(**doc))
            return collections
        except Exception as e:
            logger.error(f"获取数据集集合失败: {e}")
            return []

    def get_data_by_collection(self, collection_id: str) -> List[Data]:
        """获取集合下的所有数据"""
        try:
            docs = self._collections["data"].find({"collection_id": collection_id})
            data_list = []
            for doc in docs:
                doc.pop("_id", None)
                data_list.append(Data(**doc))
            return data_list
        except Exception as e:
            logger.error(f"获取集合数据失败: {e}")
            return []

    def get_pending_data_by_collection(self, collection_id: str) -> List[Data]:
        """获取集合下未处理的数据"""
        try:
            docs = self._collections["data"].find(
                {"collection_id": collection_id, "metadata.processed": False}
            )
            data_list = []
            for doc in docs:
                doc.pop("_id", None)
                data_list.append(Data(**doc))
            return data_list
        except Exception as e:
            logger.error(f"获取未处理数据失败: {e}")
            return []

    def get_all_pending_data(self) -> List[Data]:
        """获取系统中所有未处理的数据"""
        try:
            docs = self._collections["data"].find({"metadata.processed": False})
            data_list = []
            for doc in docs:
                doc.pop("_id", None)
                data_list.append(Data(**doc))
            return data_list
        except Exception as e:
            logger.error(f"获取所有未处理数据失败: {e}")
            return []

    def get_pending_data_count(self) -> int:
        """获取未处理数据总数"""
        try:
            count = self._collections["data"].count_documents(
                {"metadata.processed": False}
            )
            return count
        except Exception as e:
            logger.error(f"获取未处理数据计数失败: {e}")
            return 0

    def update_data(self, data_id: str, data: Data) -> bool:
        """更新数据"""
        try:
            result = self._collections["data"].replace_one(
                {"id": data_id}, data.model_dump()
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"更新数据失败: {e}")
            return False


# 全局实例
mongo_store = MongoMetadataStore()
