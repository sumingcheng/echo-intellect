import logging
from typing import List, Dict, Any, Tuple
from collections import defaultdict

from app.models.data_models import RetrievalResult

logger = logging.getLogger()


class RRFMerger:
    """RRF（Reciprocal Rank Fusion）结果合并器"""
    
    def __init__(self, k: int = 60):
        """
        初始化RRF合并器
        Args:
            k: RRF参数，通常设置为60
        """
        self.k = k
        logger.info(f"初始化RRF合并器，参数k={k}")
    
    def _merge_multiple_vectors(self, results: List[RetrievalResult]) -> List[RetrievalResult]:
        """
        合并多个向量对应同一组原数据的情况
        实现dev.md要求：如果多个向量对应同一组原数据，进行合并，向量得分取最高得分
        
        Args:
            results: 检索结果列表
        
        Returns:
            合并后的结果列表
        """
        try:
            data_groups = defaultdict(list)
            
            # 按data_id分组
            for result in results:
                data_id = result.data_id if hasattr(result, 'data_id') else result.metadata.get('data_id', '')
                if data_id:  # 只处理有效的data_id
                    data_groups[data_id].append(result)
            
            # 合并同一data_id的多个向量结果
            merged_results = []
            for data_id, group_results in data_groups.items():
                if len(group_results) == 1:
                    # 只有一个向量，直接使用
                    merged_results.append(group_results[0])
                else:
                    # 多个向量，取最高得分
                    best_result = max(group_results, key=lambda x: x.score)
                    
                    # 合并metadata信息
                    merged_metadata = best_result.metadata.copy()
                    merged_metadata['vector_count'] = len(group_results)
                    merged_metadata['all_scores'] = [r.score for r in group_results]
                    
                    # 创建合并后的结果
                    merged_result = RetrievalResult(
                                        data_id=best_result.data_id,
                collection_id=best_result.collection_id,
                        content=best_result.content,
                        score=best_result.score,  # 使用最高得分
                        source=best_result.source,
                        metadata=merged_metadata,
                        tokens=best_result.tokens
                    )
                    merged_results.append(merged_result)
                    
                    logger.debug(f"合并数据 {data_id} 的 {len(group_results)} 个向量，最高得分: {best_result.score}")
            
            logger.debug(f"多向量合并：{len(results)} -> {len(merged_results)} 个结果")
            return merged_results
            
        except Exception as e:
            logger.error(f"多向量合并失败: {e}")
            return results  # 失败时返回原结果

    def merge_results(
        self, 
        embedding_results: List[RetrievalResult],
        bm25_results: List[RetrievalResult],
        embedding_weight: float = 0.6,
        bm25_weight: float = 0.4
    ) -> List[RetrievalResult]:
        """
        使用RRF算法合并embedding和BM25检索结果
        实现dev.md要求的多向量合并逻辑
        
        Args:
            embedding_results: 向量检索结果
            bm25_results: BM25检索结果
            embedding_weight: 向量检索权重
            bm25_weight: BM25检索权重
        
        Returns:
            合并后的检索结果列表
        """
        try:
            # 1. 先处理多向量合并（dev.md要求：多个向量对应同一组原数据时合并，得分取最高）
            merged_embedding = self._merge_multiple_vectors(embedding_results)
            merged_bm25 = self._merge_multiple_vectors(bm25_results)
            
            # 2. 记录各结果的排名
            data_scores = defaultdict(lambda: {"embedding_rank": None, "bm25_rank": None, "metadata": {}})
            
            # 处理合并后的embedding结果
            for rank, result in enumerate(merged_embedding, 1):
                data_id = result.data_id if hasattr(result, 'data_id') else result.metadata.get('data_id', '')
                if data_id:  # 只处理有效的data_id
                    data_scores[data_id]["embedding_rank"] = rank
                data_scores[data_id]["content"] = result.content
                data_scores[data_id]["data_id"] = data_id
                data_scores[data_id]["metadata"].update(result.metadata)
                data_scores[data_id]["tokens"] = result.tokens
                data_scores[data_id]["embedding_score"] = result.score
            
            # 处理合并后的BM25结果
            for rank, result in enumerate(merged_bm25, 1):
                data_id = result.data_id if hasattr(result, 'data_id') else result.metadata.get('data_id', '')
                if data_id:  # 只处理有效的data_id
                    data_scores[data_id]["bm25_rank"] = rank
                if "content" not in data_scores[data_id]:
                    data_scores[data_id]["content"] = result.content
                    data_scores[data_id]["data_id"] = data_id
                    data_scores[data_id]["tokens"] = result.tokens
                data_scores[data_id]["metadata"].update(result.metadata)
                data_scores[data_id]["bm25_score"] = result.score
            
            # 计算RRF得分
            merged_results = []
            for data_id, data in data_scores.items():
                rrf_score = 0.0
                
                # 计算embedding RRF得分
                if data["embedding_rank"] is not None:
                    embedding_rrf = embedding_weight / (self.k + data["embedding_rank"])
                    rrf_score += embedding_rrf
                
                # 计算BM25 RRF得分
                if data["bm25_rank"] is not None:
                    bm25_rrf = bm25_weight / (self.k + data["bm25_rank"])
                    rrf_score += bm25_rrf
                
                # 构建合并结果
                merged_result = RetrievalResult(
                                data_id=data_id,
            collection_id=data.get("collection_id", ""),
                    content=data.get("content", ""),
                    score=rrf_score,
                    source="rrf_merged",
                    metadata={
                        **data.get("metadata", {}),
                        "data_id": data_id,
                        "embedding_rank": data["embedding_rank"],
                        "bm25_rank": data["bm25_rank"],
                        "embedding_score": data.get("embedding_score"),
                        "bm25_score": data.get("bm25_score"),
                        "rrf_score": rrf_score
                    },
                    tokens=data.get("tokens", 0)
                )
                merged_results.append(merged_result)
            
            # 按RRF得分排序
            merged_results.sort(key=lambda x: x.score, reverse=True)
            
            logger.info(f"RRF合并完成: embedding({len(merged_embedding)}) + bm25({len(merged_bm25)}) -> merged({len(merged_results)})")
            return merged_results
            
        except Exception as e:
            logger.error(f"RRF合并失败: {e}")
            # 失败时返回简单拼接的结果
            return self._simple_merge(embedding_results, bm25_results)
    
    def merge_multiple_results(
        self, 
        result_lists: List[Tuple[List[RetrievalResult], float, str]]
    ) -> List[RetrievalResult]:
        """
        合并多个检索结果列表
        
        Args:
            result_lists: 列表，每个元素为(结果列表, 权重, 来源名称)
        
        Returns:
            合并后的检索结果列表
        """
        try:
            data_scores = defaultdict(lambda: {"ranks": {}, "metadata": {}, "total_weight": 0.0})
            
            # 处理每个结果列表
            for results, weight, source in result_lists:
                for rank, result in enumerate(results, 1):
                    data_id = result.data_id
                    data_scores[data_id]["ranks"][source] = rank
                    data_scores[data_id]["content"] = result.content
                    data_scores[data_id]["collection_id"] = result.collection_id
                    data_scores[data_id]["metadata"].update(result.metadata)
                    data_scores[data_id]["tokens"] = result.tokens
                    data_scores[data_id]["total_weight"] += weight
            
            # 计算多路RRF得分
            merged_results = []
            for data_id, data in data_scores.items():
                rrf_score = 0.0
                
                # 对每个来源计算RRF贡献
                for source, rank in data["ranks"].items():
                    # 获取对应的权重
                    source_weight = next(w for r, w, s in result_lists if s == source)
                    rrf_contribution = source_weight / (self.k + rank)
                    rrf_score += rrf_contribution
                
                # 构建合并结果
                merged_result = RetrievalResult(
                    data_id=data_id,
                    collection_id=data.get("collection_id", ""),
                    content=data.get("content", ""),
                    score=rrf_score,
                    source="multi_rrf_merged",
                    metadata={
                        **data.get("metadata", {}),
                        "source_ranks": data["ranks"],
                        "total_weight": data["total_weight"]
                    },
                    tokens=data.get("tokens", 0)
                )
                merged_results.append(merged_result)
            
            # 按得分排序
            merged_results.sort(key=lambda x: x.score, reverse=True)
            
            logger.debug(f"多路RRF合并完成，输入{len(result_lists)}个列表，输出{len(merged_results)}个结果")
            return merged_results
            
        except Exception as e:
            logger.error(f"多路RRF合并失败: {e}")
            return []
    
    def _simple_merge(
        self, 
        embedding_results: List[RetrievalResult], 
        bm25_results: List[RetrievalResult]
    ) -> List[RetrievalResult]:
        """简单合并（备用方案）"""
        try:
            # 使用data_id去重
            seen_data = set()
            merged_results = []
            
            # 先添加embedding结果
            for result in embedding_results:
                if result.data_id not in seen_data:
                    merged_results.append(result)
                    seen_data.add(result.data_id)
            
            # 再添加BM25结果（跳过重复的）
            for result in bm25_results:
                if result.data_id not in seen_data:
                    merged_results.append(result)
                    seen_data.add(result.data_id)
            
            logger.info(f"简单合并完成: {len(merged_results)} 个结果")
            return merged_results
            
        except Exception as e:
            logger.error(f"简单合并失败: {e}")
            return embedding_results + bm25_results


# 全局实例
rrf_merger = RRFMerger() 