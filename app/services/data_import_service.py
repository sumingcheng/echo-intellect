import os
import time
import logging
from typing import List, Dict, Optional, Tuple
from pathlib import Path

from app.models.data_models import Dataset, Collection, Data
from app.vectorstores.mongo_metadata import MongoMetadataStore
from app.vectorstores.milvus_store import MilvusVectorStore
from app.document_loaders.document_processor import DocumentProcessor
from app.embeddings.embedding_models import embedding_manager

logger = logging.getLogger(__name__)


class DataImportService:
    """数据导入服务 - 支持批量处理、断点续传和接口调用"""

    def __init__(self):
        self.mongo_store = MongoMetadataStore()
        self.milvus_store = MilvusVectorStore()
        self.processor = DocumentProcessor()
        self.batch_size = 10  # 向量化批次大小

    async def initialize(self):
        """初始化所有组件"""
        try:
            logger.info("🔧 初始化数据导入服务...")

            # 初始化各组件（根据实际情况调整async/sync）
            self.mongo_store.connect()

            # 初始化嵌入模型
            if embedding_manager.embeddings is None:
                success = embedding_manager.initialize()
                if not success:
                    raise Exception("嵌入模型初始化失败")

            # 获取正确的向量维度
            dimension = embedding_manager.get_dimension()
            self.milvus_store.connect(dimension=dimension)

            logger.info("✅ 数据导入服务初始化成功")

            # 检查并处理未完成的数据
            await self._check_and_process_pending_data()

            return True

        except Exception as e:
            logger.error(f"❌ 初始化失败: {e}")
            return False

    async def import_directory(
        self, data_dir: str = "./data", dataset_name: str = "文档知识库"
    ) -> Dict:
        """导入指定目录下的所有txt文件"""
        result = {
            "success": False,
            "dataset_id": None,
            "files_processed": 0,
            "data_created": 0,
            "vectors_created": 0,
            "error": None,
        }

        try:
            # 创建或获取数据集
            dataset = await self._get_or_create_dataset(dataset_name)
            result["dataset_id"] = dataset.id

            # 扫描文件
            txt_files = list(Path(data_dir).glob("*.txt"))
            if not txt_files:
                result["error"] = f"在 {data_dir} 目录下未找到txt文件"
                return result

            logger.info(f"📂 找到 {len(txt_files)} 个txt文件")

            total_data = 0
            total_vectors = 0

            # 处理每个文件
            for file_path in txt_files:
                logger.info(f"🔄 处理文件: {file_path.name}")

                file_result = await self._import_single_file(file_path, dataset.id)

                if file_result["success"]:
                    total_data += file_result["data_created"]
                    total_vectors += file_result["vectors_created"]
                    result["files_processed"] += 1
                else:
                    logger.error(f"❌ 文件处理失败: {file_result['error']}")

            result["data_created"] = total_data
            result["vectors_created"] = total_vectors
            result["success"] = True

            logger.info("🎉 目录导入完成！")

        except Exception as e:
            logger.error(f"❌ 目录导入失败: {e}")
            result["error"] = str(e)

        return result

    async def _import_single_file(self, file_path: Path, dataset_id: str) -> Dict:
        """导入单个文件 - 支持断点续传"""
        result = {
            "success": False,
            "data_created": 0,
            "vectors_created": 0,
            "error": None,
        }

        try:
            # 创建集合
            collection_name = file_path.stem
            collection = await self._get_or_create_collection(
                collection_name, dataset_id
            )

            # 检查是否已有未完成的数据
            pending_data = await self._get_pending_data(collection.id)

            if pending_data:
                logger.info(f"🔄 发现 {len(pending_data)} 条未处理数据，继续处理...")
                await self._process_pending_data(pending_data)
                result["vectors_created"] = len(pending_data) * 2  # 主向量+子向量

            # 读取文件内容
            content = await self._read_file_with_encoding(file_path)
            if not content:
                result["error"] = f"无法读取文件: {file_path}"
                return result

            # 切分文档
            chunks = await self._split_document(content)
            logger.info(f"📏 文档切分为 {len(chunks)} 个数据块")

            # 第一阶段：批量存储到MongoDB（标记为未处理）
            data_list = await self._batch_store_chunks(chunks, collection.id)
            result["data_created"] = len(data_list)

            # 第二阶段：批量向量化处理
            vectors_created = await self._batch_vectorize_data(data_list)
            result["vectors_created"] = vectors_created

            result["success"] = True

        except Exception as e:
            logger.error(f"❌ 文件导入失败: {e}")
            result["error"] = str(e)

        return result

    async def _read_file_with_encoding(self, file_path: Path) -> Optional[str]:
        """尝试多种编码读取文件"""
        encodings = ["utf-8", "gbk", "gb2312", "utf-16", "big5"]

        for encoding in encodings:
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    content = f.read()
                    logger.info(f"✅ 使用 {encoding} 编码成功读取文件")
                    return content
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logger.error(f"❌ 读取文件错误: {e}")
                return None

        logger.error("❌ 尝试所有编码都失败")
        return None

    async def _split_document(self, content: str) -> List[str]:
        """智能文档切分 - 优化版本，确保1024字符且保持句子完整性"""
        target_chunk_size = 1024  # 目标块大小
        min_chunk_size = 800      # 最小块大小
        max_chunk_size = 1200     # 最大块大小
        overlap_size = 100        # 重叠大小
        
        # 优化的分割优先级：段落 > 章节 > 句号+换行 > 感叹号+换行 > 问号+换行 > 句号 > 感叹号 > 问号 > 换行
        split_patterns = [
            "\n\n\n",     # 段落分隔（3个换行）
            "\n\n",       # 段落分隔（2个换行）
            "。\n",       # 句号+换行
            "！\n",       # 感叹号+换行
            "？\n",       # 问号+换行
            "；\n",       # 分号+换行
            "。",         # 句号
            "！",         # 感叹号
            "？",         # 问号
            "；",         # 分号
            "：",         # 冒号
            "\n",         # 换行
        ]
        
        chunks = []
        start = 0
        
        logger.info(f"📄 开始切分文档，总长度: {len(content)} 字符")
        
        while start < len(content):
            # 初始目标结束位置
            target_end = start + target_chunk_size
            
            # 如果剩余内容小于最小块大小，直接作为最后一块
            if len(content) - start <= min_chunk_size:
                remaining = content[start:].strip()
                if remaining:
                    chunks.append(remaining)
                    logger.debug(f"✅ 最后一块: {len(remaining)} 字符")
                break
            
            # 如果剩余内容不足目标大小，直接取完
            if target_end >= len(content):
                remaining = content[start:].strip()
                if remaining:
                    chunks.append(remaining)
                    logger.debug(f"✅ 剩余内容块: {len(remaining)} 字符")
                break
            
            # 寻找最佳切分点
            best_split_pos = target_end
            best_pattern = None
            
            # 在目标位置前后寻找合适的切分点
            search_start = max(start + min_chunk_size, target_end - 200)  # 向前最多搜索200字符
            search_end = min(len(content), target_end + 200)              # 向后最多搜索200字符
            
            for pattern in split_patterns:
                # 向后搜索（优先）
                forward_pos = content.find(pattern, target_end, search_end)
                if forward_pos != -1:
                    split_pos = forward_pos + len(pattern)
                    if split_pos - start <= max_chunk_size:  # 不超过最大大小
                        best_split_pos = split_pos
                        best_pattern = pattern
                        break
                
                # 向前搜索
                backward_pos = content.rfind(pattern, search_start, target_end)
                if backward_pos != -1:
                    split_pos = backward_pos + len(pattern)
                    if split_pos - start >= min_chunk_size:  # 不小于最小大小
                        best_split_pos = split_pos
                        best_pattern = pattern
                        break
            
            # 提取当前块
            chunk = content[start:best_split_pos].strip()
            if chunk:
                chunks.append(chunk)
                logger.debug(f"✅ 切分块: {len(chunk)} 字符，分割符: {repr(best_pattern) if best_pattern else '强制切分'}")
                
                # 验证块大小
                if len(chunk) < min_chunk_size:
                    logger.warning(f"⚠️ 块过小: {len(chunk)} < {min_chunk_size}")
                elif len(chunk) > max_chunk_size:
                    logger.warning(f"⚠️ 块过大: {len(chunk)} > {max_chunk_size}")
            
            # 计算下一个起始位置（考虑重叠）
            next_start = max(best_split_pos - overlap_size, start + min_chunk_size)
            
            # 避免无限循环
            if next_start <= start:
                next_start = start + min_chunk_size
            
            start = next_start
        
        # 统计信息
        if chunks:
            sizes = [len(chunk) for chunk in chunks]
            avg_size = sum(sizes) / len(sizes)
            logger.info(f"📊 切分完成: {len(chunks)} 块, 平均大小: {avg_size:.0f} 字符")
            logger.info(f"📊 大小范围: {min(sizes)}-{max(sizes)} 字符")
            
            # 检查过小的块
            small_chunks = [i for i, size in enumerate(sizes) if size < min_chunk_size]
            if small_chunks:
                logger.warning(f"⚠️ 发现 {len(small_chunks)} 个过小的块: {small_chunks}")
        
        return chunks

    async def _batch_store_chunks(
        self, chunks: List[str], collection_id: str
    ) -> List[Data]:
        """批量存储数据块到MongoDB（标记为未处理）"""
        data_list = []

        for i, chunk in enumerate(chunks):
            data_id = self._generate_data_id()

            data = Data(
                id=data_id,
                collection_id=collection_id,
                content=chunk,
                vector_ids=[],  # 暂时为空
                metadata={
                    "chunk_index": i,
                    "char_count": len(chunk),
                    "processed": False,  # 标记为未处理
                },
            )

            # 存储到MongoDB
            try:
                self.mongo_store.create_data(data)
                data_list.append(data)

                if (i + 1) % 50 == 0:
                    logger.info(f"📝 已存储 {i + 1}/{len(chunks)} 个数据块")

            except Exception as e:
                error_msg = str(e)
                if "E11000" in error_msg and "duplicate key" in error_msg:
                    # 重复键错误，立即停止
                    logger.error(f"❌ 检测到重复键错误，立即停止导入: {error_msg}")
                    raise Exception(f"数据导入失败：检测到重复数据，请清理数据库后重试")
                else:
                    # 其他错误也停止
                    logger.error(f"❌ 数据存储失败，立即停止: {error_msg}")
                    raise Exception(f"数据存储失败: {error_msg}")

        logger.info(f"✅ 完成存储 {len(data_list)} 个数据块到MongoDB")
        return data_list

    async def _batch_vectorize_data(self, data_list: List[Data]) -> int:
        """批量向量化处理"""
        total_vectors = 0
        total_batches = (
            len(data_list) + self.batch_size - 1
        ) // self.batch_size  # 向上取整

        # 按批次处理
        for i in range(0, len(data_list), self.batch_size):
            batch_num = i // self.batch_size + 1
            batch = data_list[i : i + self.batch_size]

            try:
                # 批量生成向量
                batch_vectors = await self._generate_batch_vectors(batch)

                # 批量存储到Milvus
                await self._store_batch_vectors(batch_vectors)

                # 更新MongoDB状态
                await self._update_batch_status(batch, batch_vectors)

                total_vectors += len(batch_vectors)

                # 计算并显示进度百分比
                progress_percent = (batch_num / total_batches) * 100
                logger.info(
                    f"🔗 批次 {batch_num}/{total_batches} 完成 | 进度: {progress_percent:.1f}% | 累计向量: {total_vectors}"
                )

            except Exception as e:
                logger.error(
                    f"❌ 批次 {batch_num}/{total_batches} 处理失败，立即停止: {e}"
                )
                # 立即停止，不再处理后续批次
                raise Exception(f"批量向量化失败: {e}")

        return total_vectors

    async def _generate_batch_vectors(self, data_batch: List[Data]) -> List[Dict]:
        """批量生成向量"""
        vectors = []

        for data in data_batch:
            # 生成主向量
            main_vector_id = self._generate_vector_id()
            main_embedding = embedding_manager.embed_text(data.content)

            vectors.append(
                {
                    "id": main_vector_id,
                    "data_id": data.id,
                    "embedding": main_embedding,
                    "vector_type": "main",
                }
            )

            # 生成子向量（前512字符）
            if len(data.content) > 512:
                sub_content = data.content[:512]
                sub_vector_id = self._generate_vector_id()
                sub_embedding = embedding_manager.embed_text(sub_content)

                vectors.append(
                    {
                        "id": sub_vector_id,
                        "data_id": data.id,
                        "embedding": sub_embedding,
                        "vector_type": "sub",
                    }
                )

        return vectors

    async def _store_batch_vectors(self, vectors: List[Dict]):
        """批量存储向量到Milvus"""
        if not vectors:
            return

        from app.models.data_models import EmbeddingVector

        # 转换为EmbeddingVector对象
        embedding_vectors = []
        for vec in vectors:
            embedding_vector = EmbeddingVector(
                id=vec["id"],
                data_id=vec["data_id"],
                vector=vec["embedding"],
                model="bge-m3:latest",  # 使用默认模型名称
            )
            embedding_vectors.append(embedding_vector)

        # 批量插入
        try:
            self.milvus_store.insert_vectors(embedding_vectors)
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ 向量存储失败，立即停止: {error_msg}")
            raise Exception(f"向量存储失败: {error_msg}")

    async def _update_batch_status(self, data_batch: List[Data], vectors: List[Dict]):
        """批量更新数据状态"""
        for data in data_batch:
            # 获取该数据的向量ID
            data_vectors = [v["id"] for v in vectors if v["data_id"] == data.id]

            # 更新数据
            data.vector_ids = data_vectors
            data.metadata["processed"] = True
            data.metadata["vector_count"] = len(data_vectors)

            self.mongo_store.update_data(data.id, data)

    async def _get_pending_data(self, collection_id: str) -> List[Data]:
        """获取未处理的数据"""
        return self.mongo_store.get_pending_data_by_collection(collection_id)

    async def _process_pending_data(self, pending_data: List[Data]):
        """处理未完成的数据"""
        logger.info(f"🔄 继续处理 {len(pending_data)} 条未完成数据")
        await self._batch_vectorize_data(pending_data)

    async def _get_or_create_dataset(self, name: str) -> Dataset:
        """获取或创建数据集"""
        # 检查是否存在
        existing = self.mongo_store.get_dataset_by_name(name)
        if existing:
            return existing

        # 创建新数据集
        dataset_id = self._generate_dataset_id()
        dataset = Dataset(
            id=dataset_id,
            name=name,
            description=f"自动创建的数据集: {name}",
            collection_ids=[],
            metadata={"created_at": time.time()},
        )

        try:
            self.mongo_store.create_dataset(dataset)
            logger.info(f"✅ 创建数据集: {name} (ID: {dataset_id})")
            return dataset
        except Exception as e:
            error_msg = str(e)
            if "E11000" in error_msg and "duplicate key" in error_msg:
                logger.error(f"❌ 数据集ID重复，立即停止: {error_msg}")
                raise Exception(f"数据集创建失败：ID重复，请重试")
            else:
                logger.error(f"❌ 数据集创建失败: {error_msg}")
                raise Exception(f"数据集创建失败: {error_msg}")

    async def _get_or_create_collection(self, name: str, dataset_id: str) -> Collection:
        """获取或创建集合"""
        collection_id = self._generate_collection_id()
        collection = Collection(
            id=collection_id,
            dataset_id=dataset_id,
            name=name,
            description=f"从文件创建: {name}",
            data_ids=[],
            metadata={"created_at": time.time()},
        )

        try:
            self.mongo_store.create_collection(collection)
            logger.info(f"✅ 创建集合: {name} (ID: {collection_id})")
            return collection
        except Exception as e:
            error_msg = str(e)
            if "E11000" in error_msg and "duplicate key" in error_msg:
                logger.error(f"❌ 集合ID重复，立即停止: {error_msg}")
                raise Exception(f"集合创建失败：ID重复，请重试")
            else:
                logger.error(f"❌ 集合创建失败: {error_msg}")
                raise Exception(f"集合创建失败: {error_msg}")

    def _generate_dataset_id(self) -> str:
        """生成数据集ID: 1 + 时间戳(6位) + 计数器(3位)"""
        timestamp = str(int(time.time()))[-6:]
        counter = "001"  # 简化版，实际可以用Redis计数器
        return f"1{timestamp}{counter}"

    def _generate_collection_id(self) -> str:
        """生成集合ID: 2 + 时间戳(6位) + 计数器(3位)"""
        timestamp = str(int(time.time()))[-6:]
        counter = "001"
        return f"2{timestamp}{counter}"

    def _generate_data_id(self) -> str:
        """生成数据ID: 3 + 时间戳(6位) + 计数器(5位)"""
        timestamp = str(int(time.time()))[-6:]
        counter = str(int(time.time() * 1000000))[-5:]  # 微秒作为计数器
        return f"3{timestamp}{counter}"

    def _generate_vector_id(self) -> str:
        """生成向量ID: 4 + 时间戳(6位) + 计数器(5位)"""
        timestamp = str(int(time.time()))[-6:]
        counter = str(int(time.time() * 1000000))[-5:]
        return f"4{timestamp}{counter}"

    async def get_import_status(self, dataset_id: str) -> Dict:
        """获取导入状态"""
        dataset = self.mongo_store.get_dataset(dataset_id)
        if not dataset:
            return {"error": "数据集不存在"}

        # 统计信息
        collections = self.mongo_store.get_collections_by_dataset(dataset_id)
        total_data = 0
        processed_data = 0

        for collection in collections:
            data_list = self.mongo_store.get_data_by_collection(collection.id)
            total_data += len(data_list)
            processed_data += sum(
                1 for d in data_list if d.metadata.get("processed", False)
            )

        return {
            "dataset_id": dataset_id,
            "dataset_name": dataset.name,
            "total_collections": len(collections),
            "total_data": total_data,
            "processed_data": processed_data,
            "pending_data": total_data - processed_data,
            "progress": f"{processed_data}/{total_data}" if total_data > 0 else "0/0",
        }

    async def _check_and_process_pending_data(self):
        """检查并处理启动时未完成的数据"""
        try:
            logger.info("🔍 检查系统中未处理的数据...")

            # 获取未处理数据计数
            pending_count = self.mongo_store.get_pending_data_count()

            if pending_count == 0:
                logger.info("✅ 没有未处理的数据，系统状态正常")
                return

            logger.info(f"🔄 发现 {pending_count} 条未处理数据，开始断点续传处理...")

            # 获取所有未处理数据
            pending_data = self.mongo_store.get_all_pending_data()

            if not pending_data:
                logger.warning("⚠️ 计数显示有未处理数据，但查询结果为空")
                return

            # 按集合分组处理
            collection_groups = {}
            for data in pending_data:
                collection_id = data.collection_id
                if collection_id not in collection_groups:
                    collection_groups[collection_id] = []
                collection_groups[collection_id].append(data)

            total_processed = 0
            total_vectors = 0

            # 逐个集合处理
            for collection_id, data_list in collection_groups.items():
                logger.info(f"📂 处理集合 {collection_id}: {len(data_list)} 条数据")

                try:
                    # 批量向量化处理
                    vectors_created = await self._batch_vectorize_data(data_list)
                    total_processed += len(data_list)
                    total_vectors += vectors_created

                    logger.info(
                        f"✅ 集合 {collection_id} 处理完成: {len(data_list)} 数据, {vectors_created} 向量"
                    )

                except Exception as e:
                    logger.error(f"❌ 集合 {collection_id} 处理失败: {e}")
                    # 记录错误但继续处理其他集合
                    continue

            logger.info(f"🎉 断点续传处理完成!")
            logger.info(
                f"📊 处理统计: {total_processed} 条数据, {total_vectors} 个向量"
            )

        except Exception as e:
            logger.error(f"❌ 检查未处理数据失败: {e}")
            # 不抛出异常，避免影响系统启动
