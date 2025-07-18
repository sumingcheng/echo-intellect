import logging
import uuid
from typing import List, Dict, Any, Optional
from pathlib import Path
import tiktoken
from datetime import datetime

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    TextLoader, 
    PyPDFLoader, 
    Docx2txtLoader,
    UnstructuredMarkdownLoader
)

from app.models.data_models import Dataset, Collection, Data, EmbeddingVector
from app.vectorstores.mongo_metadata import mongo_store
from app.vectorstores.milvus_store import milvus_store
from app.embeddings.embedding_models import embedding_manager

logger = logging.getLogger()


class DocumentProcessor:
    """文档处理器 - 实现dev.md要求的Dataset->Collection->Data三层架构"""
    
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=512,
            chunk_overlap=50,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        self.encoding = None
        self._initialize_tokenizer()
    
    def _initialize_tokenizer(self):
        """初始化分词器"""
        try:
            self.encoding = tiktoken.get_encoding("cl100k_base")
            logger.info("文档处理器分词器初始化成功")
        except Exception as e:
            logger.warning(f"分词器初始化失败: {e}")
    
    def _count_tokens(self, text: str) -> int:
        """计算token数量"""
        try:
            if self.encoding:
                return len(self.encoding.encode(text))
            else:
                return len(text) // 4  # 粗略估算
        except:
            return len(text) // 4
    
    def process_file(
        self,
        file_path: str,
        dataset_id: str,
        collection_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        处理单个文件，实现三层架构
        
        Args:
            file_path: 文件路径
            dataset_id: 目标数据集ID
            collection_name: 集合名称（可选，默认使用文件名）
        
        Returns:
            处理结果统计
        """
        try:
            # 1. 加载文档
            documents = self._load_document(file_path)
            if not documents:
                return {"error": "文档加载失败"}
            
            # 2. 创建或获取集合
            collection_id = self._create_collection(
                dataset_id=dataset_id,
                file_path=file_path,
                collection_name=collection_name
            )
            
            # 3. 处理文档内容
            processed_data = []
            total_tokens = 0
            
            for doc in documents:
                # 分块处理
                chunks = self._split_document(doc.page_content)
                
                for i, chunk_text in enumerate(chunks):
                    # 创建数据条目
                    data_id = str(uuid.uuid4())
                    tokens = self._count_tokens(chunk_text)
                    total_tokens += tokens
                    
                    # 生成多个向量（实现多向量映射）
                    vector_ids = self._generate_multiple_vectors(
                        data_id=data_id,
                        content=chunk_text
                    )
                    
                    # 创建Data对象
                    data = Data(
                        id=data_id,
                        collection_id=collection_id,
                        content=chunk_text,
                        title=f"第{i+1}段",
                        vector_ids=vector_ids,  # 多向量映射
                        metadata={
                            "source_file": file_path,
                            "chunk_index": i,
                            "file_metadata": doc.metadata
                        },
                        sequence=i,
                        tokens=tokens
                    )
                    
                    processed_data.append(data)
            
            # 4. 批量保存到MongoDB
            self._save_batch_data(processed_data)
            
            # 5. 更新统计信息
            self._update_statistics(
                dataset_id=dataset_id,
                collection_id=collection_id,
                data_count=len(processed_data),
                total_tokens=total_tokens
            )
            
            logger.info(f"文件处理完成: {file_path}, 生成{len(processed_data)}个数据条目")
            
            return {
                "collection_id": collection_id,
                "data_count": len(processed_data),
                "total_tokens": total_tokens,
                "vector_count": sum(len(data.vector_ids) for data in processed_data)
            }
            
        except Exception as e:
            logger.error(f"处理文件失败: {e}")
            return {"error": str(e)}
    
    def _load_document(self, file_path: str) -> List[Any]:
        """加载文档"""
        try:
            file_extension = Path(file_path).suffix.lower()
            
            if file_extension == '.txt':
                loader = TextLoader(file_path, encoding='utf-8')
            elif file_extension == '.pdf':
                loader = PyPDFLoader(file_path)
            elif file_extension in ['.docx', '.doc']:
                loader = Docx2txtLoader(file_path)
            elif file_extension == '.md':
                loader = UnstructuredMarkdownLoader(file_path)
            else:
                logger.error(f"不支持的文件格式: {file_extension}")
                return []
            
            documents = loader.load()
            logger.info(f"成功加载文档: {file_path}, 页数: {len(documents)}")
            return documents
            
        except Exception as e:
            logger.error(f"加载文档失败: {e}")
            return []
    
    def _split_document(self, content: str) -> List[str]:
        """分割文档"""
        try:
            chunks = self.text_splitter.split_text(content)
            logger.debug(f"文档分割完成，生成 {len(chunks)} 个分块")
            return chunks
        except Exception as e:
            logger.error(f"文档分割失败: {e}")
            return [content]  # 降级处理
    
    def _create_collection(
        self,
        dataset_id: str,
        file_path: str,
        collection_name: Optional[str] = None
    ) -> str:
        """创建或获取集合"""
        try:
            if not collection_name:
                collection_name = Path(file_path).stem
            
            collection = Collection(
                id=str(uuid.uuid4()),
                dataset_id=dataset_id,
                name=collection_name,
                description=f"从文件 {Path(file_path).name} 创建的集合",
                source_file=file_path,
                file_type=Path(file_path).suffix.lower()
            )
            
            # 保存到MongoDB
            mongo_store.create_collection(collection)
            
            logger.info(f"创建集合: {collection_name} (ID: {collection.id})")
            return collection.id
            
        except Exception as e:
            logger.error(f"创建集合失败: {e}")
            raise
    
    def _generate_multiple_vectors(
        self,
        data_id: str,
        content: str
    ) -> List[str]:
        """
        为一组数据生成多个向量（实现dev.md的多向量映射）
        
        Args:
            data_id: 数据ID
            content: 文本内容
        
        Returns:
            向量ID列表
        """
        try:
            vector_ids = []
            
            # 策略1：完整内容向量
            full_embedding = embedding_manager.embed_query(content)
            if full_embedding:
                vector_id = str(uuid.uuid4())
                vector = EmbeddingVector(
                    id=vector_id,
                    data_id=data_id,
                    vector=full_embedding,
                    dimension=len(full_embedding),
                    model=embedding_manager.model,
                    chunk_text=content,
                    chunk_index=0
                )
                
                # 保存向量到Milvus
                if milvus_store.insert_vectors([vector]):
                    vector_ids.append(vector_id)
            
            # 策略2：如果内容较长，生成子块向量
            if len(content) > 300:  # 内容较长时
                # 分成更小的子块
                sub_chunks = self.text_splitter.split_text(content)
                
                for i, sub_chunk in enumerate(sub_chunks[:2]):  # 最多2个子向量
                    if len(sub_chunk) > 50:  # 子块足够长
                        sub_embedding = embedding_manager.embed_query(sub_chunk)
                        if sub_embedding:
                            vector_id = str(uuid.uuid4())
                            vector = EmbeddingVector(
                                id=vector_id,
                                data_id=data_id,
                                vector=sub_embedding,
                                dimension=len(sub_embedding),
                                model=embedding_manager.model,
                                chunk_text=sub_chunk,
                                chunk_index=i + 1
                            )
                            
                            if milvus_store.insert_vectors([vector]):
                                vector_ids.append(vector_id)
            
            logger.debug(f"为数据 {data_id} 生成了 {len(vector_ids)} 个向量")
            return vector_ids
            
        except Exception as e:
            logger.error(f"生成多向量失败: {e}")
            return []
    
    def _save_batch_data(self, data_list: List[Data]):
        """批量保存数据到MongoDB"""
        try:
            for data in data_list:
                mongo_store.create_data(data)
            
            logger.info(f"批量保存 {len(data_list)} 个数据条目")
            
        except Exception as e:
            logger.error(f"批量保存数据失败: {e}")
            raise
    
    def _update_statistics(
        self,
        dataset_id: str,
        collection_id: str,
        data_count: int,
        total_tokens: int
    ):
        """更新统计信息"""
        try:
            # 更新集合统计
            mongo_store.update_collection_stats(
                collection_id=collection_id,
                data_count=data_count,
                total_tokens=total_tokens
            )
            
            # 更新数据集统计
            mongo_store.update_dataset_stats(
                dataset_id=dataset_id,
                data_count=data_count,
                total_tokens=total_tokens
            )
            
        except Exception as e:
            logger.error(f"更新统计信息失败: {e}")


# 全局实例
document_processor = DocumentProcessor() 