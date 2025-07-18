import logging
import asyncio
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from app.models.data_models import Query, RetrievalResult
from app.components.retrievers.hybrid_retriever import hybrid_retriever
from app.components.mergers.rrf_merger import rrf_merger

logger = logging.getLogger()


class ParallelRetriever:
    """并行检索器 - 支持多查询并行执行"""
    
    def __init__(self, max_workers: int = 3):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        logger.info(f"并行检索器初始化，最大工作线程: {max_workers}")
    
    def parallel_retrieve(
        self,
        queries: List[str],
        base_query: Query,
        merge_strategy: str = "rrf"
    ) -> List[RetrievalResult]:
        """
        并行执行多个查询的检索
        
        Args:
            queries: 查询列表（包含原始查询和扩展查询）
            base_query: 基础查询配置
            merge_strategy: 合并策略
        
        Returns:
            合并后的检索结果
        """
        try:
            if not queries:
                return []
            
            start_time = time.time()
            logger.info(f"开始并行检索，查询数量: {len(queries)}")
            
            # 为每个查询创建Query对象
            query_objects = []
            for i, query_text in enumerate(queries):
                query_obj = Query(
                    id=f"{base_query.id}_parallel_{i}",
                    question=query_text,
                    optimized_question=query_text,
                    max_tokens=base_query.max_tokens,
                    relevance_threshold=base_query.relevance_threshold,
                    top_k=base_query.top_k
                )
                query_objects.append(query_obj)
            
            # 并行执行检索
            future_to_query = {}
            for i, query_obj in enumerate(query_objects):
                future = self.executor.submit(self._single_retrieve, query_obj, i)
                future_to_query[future] = (query_obj, i)
            
            # 收集结果
            all_results = []
            for future in as_completed(future_to_query):
                query_obj, query_index = future_to_query[future]
                try:
                    results = future.result(timeout=30)  # 30秒超时
                    
                    # 为结果添加查询信息
                    for result in results:
                        result.metadata.update({
                            "query_index": query_index,
                            "query_text": query_obj.question,
                            "parallel_retrieve": True
                        })
                    
                    all_results.append((results, 1.0 / len(queries), f"query_{query_index}"))
                    logger.debug(f"查询 {query_index} 完成，返回 {len(results)} 个结果")
                    
                except Exception as e:
                    logger.error(f"查询 {query_index} 执行失败: {e}")
                    # 添加空结果，避免影响其他查询
                    all_results.append(([], 0.0, f"query_{query_index}_failed"))
            
            # 合并结果
            if merge_strategy == "rrf" and len(all_results) > 1:
                merged_results = rrf_merger.merge_multiple_results(all_results)
            else:
                merged_results = self._simple_merge(all_results)
            
            elapsed_time = time.time() - start_time
            logger.info(f"并行检索完成，耗时: {elapsed_time:.2f}秒，最终结果: {len(merged_results)} 个")
            
            return merged_results
            
        except Exception as e:
            logger.error(f"并行检索失败: {e}")
            return []
    
    def _single_retrieve(self, query: Query, query_index: int) -> List[RetrievalResult]:
        """单个查询的检索执行"""
        try:
            logger.debug(f"执行查询 {query_index}: {query.question}")
            
            # 确保混合检索器已初始化
            if not hybrid_retriever.initialized:
                hybrid_retriever.initialize()
            
            # 执行检索
            results = hybrid_retriever.retrieve(query)
            
            logger.debug(f"查询 {query_index} 检索完成，结果数: {len(results)}")
            return results
            
        except Exception as e:
            logger.error(f"单个查询检索失败 (query_{query_index}): {e}")
            return []
    
    def _simple_merge(self, all_results: List[tuple]) -> List[RetrievalResult]:
        """简单合并策略（备用方案）"""
        try:
            merged_results = []
            seen_chunks = set()
            
            # 按查询顺序合并，避免重复
            for results, weight, source in all_results:
                for result in results:
                    if result.data_id not in seen_chunks:
                        merged_results.append(result)
                        seen_chunks.add(result.data_id)
            
            # 按原始得分排序
            merged_results.sort(key=lambda x: x.score, reverse=True)
            
            logger.debug(f"简单合并完成，合并了 {len(all_results)} 个查询结果")
            return merged_results
            
        except Exception as e:
            logger.error(f"简单合并失败: {e}")
            return []
    
    async def async_parallel_retrieve(
        self,
        queries: List[str],
        base_query: Query,
        merge_strategy: str = "rrf"
    ) -> List[RetrievalResult]:
        """
        异步并行检索（未来扩展用）
        
        Args:
            queries: 查询列表
            base_query: 基础查询配置
            merge_strategy: 合并策略
        
        Returns:
            合并后的检索结果
        """
        try:
            if not queries:
                return []
            
            start_time = time.time()
            logger.info(f"开始异步并行检索，查询数量: {len(queries)}")
            
            # 创建异步任务
            tasks = []
            for i, query_text in enumerate(queries):
                query_obj = Query(
                    id=f"{base_query.id}_async_{i}",
                    question=query_text,
                    optimized_question=query_text,
                    max_tokens=base_query.max_tokens,
                    relevance_threshold=base_query.relevance_threshold,
                    top_k=base_query.top_k
                )
                task = asyncio.create_task(self._async_single_retrieve(query_obj, i))
                tasks.append(task)
            
            # 等待所有任务完成
            results_list = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理结果
            all_results = []
            for i, results in enumerate(results_list):
                if isinstance(results, Exception):
                    logger.error(f"异步查询 {i} 失败: {results}")
                    all_results.append(([], 0.0, f"query_{i}_failed"))
                else:
                    # 为结果添加查询信息
                    for result in results:
                        result.metadata.update({
                            "query_index": i,
                            "query_text": queries[i],
                            "async_retrieve": True
                        })
                    all_results.append((results, 1.0 / len(queries), f"query_{i}"))
            
            # 合并结果
            if merge_strategy == "rrf" and len(all_results) > 1:
                merged_results = rrf_merger.merge_multiple_results(all_results)
            else:
                merged_results = self._simple_merge(all_results)
            
            elapsed_time = time.time() - start_time
            logger.info(f"异步并行检索完成，耗时: {elapsed_time:.2f}秒，最终结果: {len(merged_results)} 个")
            
            return merged_results
            
        except Exception as e:
            logger.error(f"异步并行检索失败: {e}")
            return []
    
    async def _async_single_retrieve(self, query: Query, query_index: int) -> List[RetrievalResult]:
        """异步单个查询检索"""
        try:
            logger.debug(f"执行异步查询 {query_index}: {query.question}")
            
            # 在异步环境中运行同步函数
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                self.executor, 
                self._single_retrieve, 
                query, 
                query_index
            )
            
            return results
            
        except Exception as e:
            logger.error(f"异步单个查询检索失败 (query_{query_index}): {e}")
            return []
    
    def batch_retrieve_with_strategies(
        self,
        query_groups: Dict[str, List[str]],
        base_query: Query
    ) -> Dict[str, List[RetrievalResult]]:
        """
        按策略分组的批量检索
        
        Args:
            query_groups: 按策略分组的查询字典 {"strategy": [queries]}
            base_query: 基础查询配置
        
        Returns:
            按策略分组的结果字典
        """
        try:
            results_by_strategy = {}
            
            for strategy, queries in query_groups.items():
                if not queries:
                    continue
                
                logger.info(f"执行策略 '{strategy}' 的并行检索，查询数: {len(queries)}")
                
                # 为每个策略执行并行检索
                strategy_results = self.parallel_retrieve(
                    queries=queries,
                    base_query=base_query,
                    merge_strategy="rrf"
                )
                
                # 为结果添加策略标记
                for result in strategy_results:
                    result.metadata["expansion_strategy"] = strategy
                
                results_by_strategy[strategy] = strategy_results
                logger.info(f"策略 '{strategy}' 完成，结果数: {len(strategy_results)}")
            
            return results_by_strategy
            
        except Exception as e:
            logger.error(f"批量策略检索失败: {e}")
            return {}
    

    
    def shutdown(self):
        """关闭并行检索器"""
        try:
            self.executor.shutdown(wait=True)
            logger.info("并行检索器已关闭")
        except Exception as e:
            logger.error(f"关闭并行检索器失败: {e}")
    
    def __del__(self):
        """析构函数，确保资源清理"""
        try:
            if hasattr(self, 'executor') and not self.executor._shutdown:
                self.executor.shutdown(wait=False)
        except Exception:
            pass


# 全局实例
parallel_retriever = ParallelRetriever() 