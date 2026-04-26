import logging
import time
import uuid
from pathlib import Path
from typing import Any

from app.ingestion.chunker import TextChunk, TokenAwareChunker
from app.ingestion.indexer import EmbeddingIndexer
from app.ingestion.readers import FileReader
from app.llms.embeddings import embedding_manager
from app.models.data_models import Collection, Data, Dataset
from app.stores.mongo import MongoMetadataStore
from app.stores.qdrant import QdrantVectorStore

logger = logging.getLogger(__name__)


class DataImportService:
    """导入编排服务，只负责把读取、切块、入库、索引串起来。"""

    def __init__(self):
        self.mongo_store = MongoMetadataStore()
        self.qdrant_store = QdrantVectorStore()
        self.reader = FileReader()
        self.chunker = TokenAwareChunker()
        self.indexer = EmbeddingIndexer(self.qdrant_store)

    @property
    def embedding_available(self) -> bool:
        """导入链路是否已有可用向量模型。"""
        return embedding_manager.embeddings is not None

    async def initialize(self) -> bool:
        """初始化导入依赖。"""
        try:
            logger.info("初始化数据导入服务...")
            self.mongo_store.connect()

            if embedding_manager.embeddings is None:
                if not embedding_manager.initialize():
                    raise RuntimeError("嵌入模型初始化失败")

            self.qdrant_store.connect(dimension=embedding_manager.get_dimension())
            await self._process_pending_data()
            logger.info("数据导入服务初始化成功")
            return True

        except Exception as e:
            logger.error("数据导入服务初始化失败: %s", e)
            return False

    async def import_directory(
        self,
        data_dir: str = "./data",
        dataset_name: str = "文档知识库",
    ) -> dict[str, Any]:
        """导入指定目录下的所有txt文件。"""
        result = {
            "success": False,
            "dataset_id": None,
            "files_processed": 0,
            "data_created": 0,
            "vectors_created": 0,
            "error": None,
        }

        try:
            dataset = self._get_or_create_dataset(dataset_name)
            result["dataset_id"] = dataset.id

            documents = self.reader.read_directory(data_dir)
            if not documents:
                result["error"] = f"在 {data_dir} 目录下未找到txt文件"
                return result

            for document in documents:
                file_result = self._import_document(document.path, document.content, dataset)
                if file_result["success"]:
                    result["files_processed"] += 1
                    result["data_created"] += file_result["data_created"]
                    result["vectors_created"] += file_result["vectors_created"]
                else:
                    logger.error("文件导入失败: %s", file_result["error"])

            result["success"] = True
            return result

        except Exception as e:
            logger.error("目录导入失败: %s", e)
            result["error"] = str(e)
            return result

    def import_file(
        self,
        file_path: Path,
        dataset_name: str = "文档知识库",
    ) -> dict[str, Any]:
        """导入单个文件到知识库，供上传接口调用。"""
        result = {
            "success": False,
            "dataset_id": None,
            "file_name": file_path.name,
            "data_created": 0,
            "vectors_created": 0,
            "error": None,
        }
        try:
            content = self.reader.read_file(file_path)
            if not content:
                result["error"] = f"无法读取文件: {file_path.name}"
                return result

            dataset = self._get_or_create_dataset(dataset_name)
            result["dataset_id"] = dataset.id

            file_result = self._import_document(file_path, content, dataset)
            result["success"] = file_result["success"]
            result["data_created"] = file_result["data_created"]
            result["vectors_created"] = file_result["vectors_created"]
            return result

        except Exception as e:
            logger.error("文件导入失败: %s, error=%s", file_path.name, e)
            result["error"] = str(e)
            return result

    async def get_import_status(self, dataset_id: str) -> dict[str, Any]:
        """获取数据集导入状态。"""
        dataset = self.mongo_store.get_dataset(dataset_id)
        if not dataset:
            return {"error": "数据集不存在"}

        collections = self.mongo_store.get_collections_by_dataset(dataset_id)
        total_data = 0
        processed_data = 0

        for collection in collections:
            data_list = self.mongo_store.get_data_by_collection(collection.id)
            total_data += len(data_list)
            processed_data += sum(
                1 for data in data_list if data.metadata.get("processed", False)
            )

        return {
            "dataset_id": dataset_id,
            "dataset_name": dataset.name,
            "total_collections": len(collections),
            "total_data": total_data,
            "processed_data": processed_data,
            "pending_data": total_data - processed_data,
            "progress": f"{processed_data}/{total_data}" if total_data else "0/0",
        }

    def _import_document(
        self,
        file_path: Path,
        content: str,
        dataset: Dataset,
    ) -> dict[str, Any]:
        chunks = self.chunker.split(content)
        collection = self._get_or_create_collection(file_path, dataset.id)

        existing_data = self.mongo_store.get_data_by_collection(collection.id)
        if existing_data:
            logger.info("文件已导入，跳过重复导入: %s", file_path.name)
            return {
                "success": True,
                "data_created": 0,
                "vectors_created": 0,
            }

        data_list = self._store_chunks(chunks, collection)
        vector_map = self.indexer.index_data(data_list)
        self._mark_indexed(data_list, vector_map)
        self._update_stats(dataset.id, collection.id, data_list)

        return {
            "success": True,
            "data_created": len(data_list),
            "vectors_created": sum(len(ids) for ids in vector_map.values()),
        }

    def _get_or_create_dataset(self, name: str) -> Dataset:
        existing = self.mongo_store.get_dataset_by_name(name)
        if existing:
            return existing

        dataset = Dataset(
            id=str(uuid.uuid4()),
            name=name,
            description=f"自动创建的数据集: {name}",
        )
        if not self.mongo_store.create_dataset(dataset):
            raise RuntimeError(f"数据集创建失败: {name}")

        return dataset

    def _get_or_create_collection(self, file_path: Path, dataset_id: str) -> Collection:
        existing = self._find_collection(dataset_id, file_path.stem)
        if existing:
            return existing

        collection = Collection(
            id=str(uuid.uuid4()),
            dataset_id=dataset_id,
            name=file_path.stem,
            description=f"从文件创建: {file_path.name}",
            source_file=str(file_path),
            file_type=file_path.suffix.lower(),
            metadata={"created_at": time.time()},
        )
        if not self.mongo_store.create_collection(collection):
            raise RuntimeError(f"集合创建失败: {file_path.name}")

        return collection

    def _find_collection(self, dataset_id: str, name: str) -> Collection | None:
        for collection in self.mongo_store.get_collections_by_dataset(dataset_id):
            if collection.name == name:
                return collection
        return None

    def _store_chunks(
        self,
        chunks: list[TextChunk],
        collection: Collection,
    ) -> list[Data]:
        data_list = []
        for chunk in chunks:
            data = Data(
                id=str(uuid.uuid4()),
                collection_id=collection.id,
                content=chunk.content,
                title=f"{collection.name}#{chunk.index + 1}",
                metadata={
                    "chunk_index": chunk.index,
                    "processed": False,
                    "token_count": chunk.tokens,
                    "source_file": collection.source_file,
                },
                sequence=chunk.index,
                tokens=chunk.tokens,
            )
            if not self.mongo_store.create_data(data):
                raise RuntimeError(f"数据块创建失败: {collection.name}#{chunk.index}")
            data_list.append(data)

        return data_list

    def _mark_indexed(
        self,
        data_list: list[Data],
        vector_map: dict[str, list[str]],
    ) -> None:
        for data in data_list:
            data.vector_ids = vector_map.get(data.id, [])
            data.metadata["processed"] = True
            data.metadata["vector_count"] = len(data.vector_ids)
            self.mongo_store.update_data(data.id, data)

    def _update_stats(
        self,
        dataset_id: str,
        collection_id: str,
        data_list: list[Data],
    ) -> None:
        data_count = len(data_list)
        total_tokens = sum(data.tokens for data in data_list)
        self.mongo_store.update_collection_stats(collection_id, data_count, total_tokens)
        self.mongo_store.update_dataset_stats(dataset_id, data_count, total_tokens)

    async def _process_pending_data(self) -> None:
        pending_data = self.mongo_store.get_all_pending_data()
        if not pending_data:
            logger.info("没有未处理的数据")
            return

        logger.info("处理未完成数据: %s", len(pending_data))
        vector_map = self.indexer.index_data(pending_data)
        self._mark_indexed(pending_data, vector_map)
