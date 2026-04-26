import logging
from typing import List

from app.models.data_models import RetrievalResult, Query
from app.llms.embeddings import embedding_manager
from app.rag.rrf import rrf_merger
from app.stores.mongo import mongo_store
from app.stores.qdrant import qdrant_store

logger = logging.getLogger()


class LexicalRetriever:
    """基于MongoDB全文索引的词法检索器。"""

    def search(self, query: str, top_k: int = 10) -> List[RetrievalResult]:
        """执行词法搜索。"""
        try:
            data_list = mongo_store.search_data_by_content(
                query=query,
                limit=top_k
            )

            results = []
            for i, data in enumerate(data_list):
                lexical_score = data.metadata.get("text_score", 1.0 / (i + 1))
                result = RetrievalResult(
                    data_id=data.id,
                    collection_id=data.collection_id,
                    content=data.content,
                    score=lexical_score,
                    source="lexical",
                    metadata={
                        "text_score": lexical_score,
                        "title": data.title
                    },
                    tokens=data.tokens
                )
                results.append(result)

            logger.debug(f"词法搜索返回 {len(results)} 个结果")
            return results

        except Exception as e:
            logger.error(f"词法搜索失败: {e}")
            return []


class EmbeddingRetriever:
    """嵌入向量检索器"""
    
    def __init__(self):
        self.initialized = False
    
    def initialize(self):
        """初始化检索器"""
        try:
            # 确保所有依赖都已初始化
            if not embedding_manager.embeddings:
                embedding_manager.initialize()
            
            if not qdrant_store.connected:
                dimension = embedding_manager.get_dimension()
                qdrant_store.connect(dimension)
            
            self.initialized = True
            logger.info("嵌入向量检索器初始化成功")
            
        except Exception as e:
            logger.error(f"初始化嵌入向量检索器失败: {e}")
            raise
    
    def search(self, query: str, top_k: int = 10) -> List[RetrievalResult]:
        """向量搜索"""
        try:
            if not self.initialized:
                logger.warning("向量检索器未初始化，返回空结果")
                return []
            
            # 生成查询向量
            query_vector = embedding_manager.embed_text(query)
            
            # 执行向量搜索
            results = qdrant_store.search_vectors(
                query_vector=query_vector,
                top_k=top_k,
                score_threshold=0.0
            )
            
            # 补充metadata信息（支持多向量映射）
            vector_ids = [result.metadata.get("vector_id") for result in results if result.metadata.get("vector_id")]
            data_list = mongo_store.get_data_by_vector_ids(vector_ids)
            
            # 创建data_id到data的映射
            data_map = {data.id: data for data in data_list}
            
            # 更新结果信息
            for result in results:
                # 从向量找到对应的数据
                matching_data = None
                for data in data_list:
                    if result.metadata.get("vector_id") in data.vector_ids:  # 检查向量ID是否在数据的vector_ids中
                        matching_data = data
                        break
                
                if matching_data:
                    result.data_id = matching_data.id
                    result.collection_id = matching_data.collection_id
                    result.content = matching_data.content
                    result.tokens = matching_data.tokens
                    result.metadata.update(matching_data.metadata)
            
            logger.debug(f"向量搜索返回 {len(results)} 个结果")
            return results
            
        except Exception as e:
            logger.error(f"向量搜索失败: {e}")
            return []


class HybridRetriever:
    """混合检索器（结合embedding和词法检索）"""
    
    def __init__(self):
        self.embedding_retriever = EmbeddingRetriever()
        self.lexical_retriever = LexicalRetriever()
        self.initialized = False
        self.connected = False
    
    def connect(self):
        """连接混合检索器"""
        try:
            # 连接各个组件
            self.embedding_retriever.initialize()

            self.connected = True
            self.initialized = True
            logger.info("混合检索器连接成功")
            
        except Exception as e:
            logger.error(f"连接混合检索器失败: {e}")
            raise
    
    def initialize(self):
        """初始化混合检索器（别名）"""
        return self.connect()
    
    def retrieve(
        self, 
        query: Query,
        embedding_weight: float = 0.6,
        lexical_weight: float = 0.4
    ) -> List[RetrievalResult]:
        """
        混合检索
        
        Args:
            query: 查询对象
            embedding_weight: 向量检索权重
            lexical_weight: 词法检索权重
        
        Returns:
            合并后的检索结果
        """
        try:
            if not self.initialized:
                logger.warning("混合检索器未初始化")
                return []
            
            # 执行embedding检索
            embedding_results = self.embedding_retriever.search(
                query.optimized_question or query.question,
                top_k=query.top_k
            )
            
            # 执行词法检索
            lexical_results = self.lexical_retriever.search(
                query.optimized_question or query.question,
                top_k=query.top_k
            )

            # 使用RRF合并结果
            merged_results = rrf_merger.merge_results(
                embedding_results=embedding_results,
                lexical_results=lexical_results,
                embedding_weight=embedding_weight,
                lexical_weight=lexical_weight
            )

            logger.info(
                f"混合检索完成: embedding({len(embedding_results)}) + "
                f"lexical({len(lexical_results)}) -> merged({len(merged_results)})"
            )
            return merged_results
            
        except Exception as e:
            logger.error(f"混合检索失败: {e}")
            return []
    
    def multi_query_retrieve(
        self, 
        queries: List[str],
        top_k: int = 10,
        merge_strategy: str = "rrf"
    ) -> List[RetrievalResult]:
        """
        多查询检索（支持查询扩展后的多个查询）
        
        Args:
            queries: 查询列表
            top_k: 每个查询返回的结果数
            merge_strategy: 合并策略（rrf/simple）
        
        Returns:
            合并后的检索结果
        """
        try:
            all_results = []
            
            for i, query_text in enumerate(queries):
                # 为每个查询执行混合检索
                query_obj = Query(
                    id=f"multi_{i}",
                    question=query_text,
                    top_k=top_k
                )
                
                results = self.retrieve(query_obj)
                
                # 为结果添加查询来源信息
                for result in results:
                    result.metadata["query_index"] = i
                    result.metadata["query_text"] = query_text
                
                all_results.append((results, 1.0 / len(queries), f"query_{i}"))
            
            # 使用RRF合并多个查询的结果
            if merge_strategy == "rrf" and len(all_results) > 1:
                merged_results = rrf_merger.merge_multiple_results(all_results)
            else:
                # 简单合并
                merged_results = []
                seen_chunks = set()
                for results, _, _ in all_results:
                    for result in results:
                        if result.data_id not in seen_chunks:
                            merged_results.append(result)
                            seen_chunks.add(result.data_id)
            
            logger.info(f"多查询检索完成，处理了 {len(queries)} 个查询，返回 {len(merged_results)} 个结果")
            return merged_results
            
        except Exception as e:
            logger.error(f"多查询检索失败: {e}")
            return []
    



# 全局实例
hybrid_retriever = HybridRetriever() 