import logging
from typing import List, Dict, Any
import tiktoken

from config.settings import app_config
from app.models.data_models import RerankResult

logger = logging.getLogger()


class TokenRelevanceFilter:
    """Token相关性过滤器"""
    
    def __init__(self):
        self.encoding = None
        self._initialize_tokenizer()
    
    def _initialize_tokenizer(self):
        """初始化分词器"""
        try:
            self.encoding = tiktoken.get_encoding("cl100k_base")
            logger.info("Token分词器初始化成功")
        except Exception as e:
            logger.warning(f"Token分词器初始化失败: {e}")
            self.encoding = None
    
    def filter_results(
        self,
        results: List[RerankResult],
        max_tokens: int = None,
        relevance_threshold: float = None,
        min_results: int = 1,
        preserve_diversity: bool = True
    ) -> List[RerankResult]:
        """过滤检索结果"""
        try:
            if not results:
                return []
            
            if max_tokens is None:
                max_tokens = app_config.max_tokens_limit
            if relevance_threshold is None:
                relevance_threshold = app_config.relevance_threshold
            
            logger.info(f"开始过滤，原始结果: {len(results)}，最大tokens: {max_tokens}，相关性阈值: {relevance_threshold}")
            
            relevance_filtered = self._filter_by_relevance(results, relevance_threshold, min_results)
            token_filtered = self._filter_by_tokens(relevance_filtered, max_tokens, min_results)
            
            if preserve_diversity and len(token_filtered) > min_results:
                final_results = self._preserve_diversity(token_filtered, max_tokens)
            else:
                final_results = token_filtered
            
            logger.info(f"过滤完成: {len(results)} -> {len(final_results)} 个结果")
            
            self._add_filter_metadata(final_results, len(results), max_tokens, relevance_threshold)
            
            return final_results
            
        except Exception as e:
            logger.error(f"结果过滤失败: {e}")
            return results[:min_results] if results else []
    
    def _filter_by_relevance(
        self, 
        results: List[RerankResult], 
        threshold: float,
        min_results: int
    ) -> List[RerankResult]:
        """根据相关性阈值过滤"""
        try:
            high_relevance = [r for r in results if r.final_score >= threshold]
            
            if len(high_relevance) < min_results:
                return results[:min_results]
            
            logger.debug(f"相关性过滤: {len(results)} -> {len(high_relevance)} 个结果")
            return high_relevance
            
        except Exception as e:
            logger.error(f"相关性过滤失败: {e}")
            return results
    
    def _filter_by_tokens(
        self, 
        results: List[RerankResult], 
        max_tokens: int,
        min_results: int
    ) -> List[RerankResult]:
        """根据token限制过滤"""
        try:
            if not results:
                return []
            
            for result in results:
                if result.tokens == 0:
                    result.tokens = self._count_tokens(result.content)
            
            filtered_results = []
            total_tokens = 0
            
            for result in results:
                if total_tokens + result.tokens <= max_tokens:
                    filtered_results.append(result)
                    total_tokens += result.tokens
                elif len(filtered_results) < min_results:
                    filtered_results.append(result)
                    total_tokens += result.tokens
                    logger.warning(f"为确保最少结果数，添加了超出token限制的结果")
                else:
                    break
            
            logger.debug(f"Token过滤: {len(results)} -> {len(filtered_results)} 个结果，总tokens: {total_tokens}")
            return filtered_results
            
        except Exception as e:
            logger.error(f"Token过滤失败: {e}")
            return results[:min_results]
    
    def _preserve_diversity(
        self, 
        results: List[RerankResult], 
        max_tokens: int
    ) -> List[RerankResult]:
        """保持结果多样性"""
        try:
            if len(results) <= 3:
                return results
            
            document_counts = {}
            diverse_results = []
            total_tokens = 0
            
            # 第一轮：每个文档最多选一个结果
            for result in results:
                doc_id = result.collection_id
                if doc_id not in document_counts:
                    if total_tokens + result.tokens <= max_tokens:
                        diverse_results.append(result)
                        document_counts[doc_id] = 1
                        total_tokens += result.tokens
                    else:
                        break
            
            # 第二轮：如果还有token空间，添加更多结果
            if total_tokens < max_tokens:
                for result in results:
                    if result not in diverse_results:
                        doc_id = result.collection_id
                        doc_count = document_counts.get(doc_id, 0)
                        
                        if doc_count < 2 and total_tokens + result.tokens <= max_tokens:
                            diverse_results.append(result)
                            document_counts[doc_id] = doc_count + 1
                            total_tokens += result.tokens
            
            diverse_results.sort(key=lambda x: results.index(x))
            
            logger.debug(f"多样性处理: {len(results)} -> {len(diverse_results)} 个结果")
            return diverse_results
            
        except Exception as e:
            logger.error(f"多样性处理失败: {e}")
            return results
    
    def _count_tokens(self, text: str) -> int:
        """计算文本的token数量"""
        try:
            if self.encoding:
                return len(self.encoding.encode(text))
            else:
                return len(text) // 4
        except Exception as e:
            logger.warning(f"Token计算失败: {e}")
            return len(text) // 4
    
    def _add_filter_metadata(
        self, 
        results: List[RerankResult], 
        original_count: int,
        max_tokens: int,
        relevance_threshold: float
    ):
        """为结果添加过滤元数据"""
        try:
            total_tokens = sum(r.tokens for r in results)
            
            filter_stats = {
                "original_count": original_count,
                "filtered_count": len(results),
                "total_tokens": total_tokens,
                "max_tokens_limit": max_tokens,
                "relevance_threshold": relevance_threshold,
                "filter_ratio": len(results) / original_count if original_count > 0 else 0
            }
            
            for result in results:
                result.metadata["filter_stats"] = filter_stats
                
        except Exception as e:
            logger.warning(f"添加过滤元数据失败: {e}")
    
    def adaptive_filter(
        self, 
        results: List[RerankResult],
        target_tokens: int,
        quality_priority: float = 0.7
    ) -> List[RerankResult]:
        """自适应过滤，平衡质量和数量"""
        try:
            if not results:
                return []
            
            for result in results:
                if result.tokens == 0:
                    result.tokens = self._count_tokens(result.content)
                
                quality_density = result.final_score / max(result.tokens, 1)
                result.metadata["quality_density"] = quality_density
            
            def adaptive_score(result):
                return (
                    quality_priority * result.final_score +
                    (1 - quality_priority) * result.metadata["quality_density"]
                )
            
            sorted_results = sorted(results, key=adaptive_score, reverse=True)
            
            selected_results = []
            total_tokens = 0
            
            for result in sorted_results:
                if total_tokens + result.tokens <= target_tokens:
                    selected_results.append(result)
                    total_tokens += result.tokens
                else:
                    break
            
            selected_results.sort(key=lambda x: results.index(x))
            
            logger.info(f"自适应过滤: {len(results)} -> {len(selected_results)} 个结果，使用tokens: {total_tokens}")
            return selected_results
            
        except Exception as e:
            logger.error(f"自适应过滤失败: {e}")
            return results[:3]
    
    def get_filter_statistics(self, results: List[RerankResult]) -> Dict[str, Any]:
        """获取过滤统计信息"""
        try:
            if not results:
                return {}
            
            scores = [r.final_score for r in results]
            tokens = [r.tokens for r in results]
            
            stats = {
                "result_count": len(results),
                "total_tokens": sum(tokens),
                "avg_tokens_per_result": sum(tokens) / len(tokens),
                "max_tokens_per_result": max(tokens),
                "min_tokens_per_result": min(tokens),
                "avg_relevance_score": sum(scores) / len(scores),
                "max_relevance_score": max(scores),
                "min_relevance_score": min(scores),
                "unique_documents": len(set(r.collection_id for r in results))
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"获取过滤统计失败: {e}")
            return {}


# 全局实例
token_relevance_filter = TokenRelevanceFilter() 