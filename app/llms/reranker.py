import logging
import httpx
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from config.settings import app_config
from app.models.data_models import RetrievalResult, RerankResult

logger = logging.getLogger()


@dataclass
class RerankRequest:
    """重排请求数据结构"""
    query: str
    passages: List[str]


class BGEReranker:
    """BGE重排模型客户端"""
    
    def __init__(
        self,
        base_url: str = None,
        endpoint: str = None,
        access_token: str = None,
        timeout: int = 60
    ):
        self.base_url = base_url or app_config.rerank_service
        self.endpoint = endpoint or app_config.rerank_endpoint
        self.access_token = access_token or app_config.rerank_access_token
        self.timeout = timeout
        self.client = httpx.Client(timeout=timeout)
        
        self.api_url = f"{self.base_url.rstrip('/')}{self.endpoint}"
        
        logger.info(f"初始化BGE重排模型: {self.api_url}")
    
    def rerank(self, query: str, passages: List[str], top_k: int = None) -> List[float]:
        """对文档段落进行重排，返回相关性得分"""
        try:
            if not passages:
                return []
            
            request_data = {
                "model": "bge-reranker-base",
                "query": query,
                "documents": passages,
            }
            
            if top_k:
                request_data["top_k"] = min(top_k, len(passages))
            
            headers = {"Content-Type": "application/json"}
            
            if self.access_token:
                headers["Authorization"] = f"Bearer {self.access_token}"
            
            response = self.client.post(
                self.api_url,
                json=request_data,
                headers=headers
            )
            response.raise_for_status()
            
            result = response.json()
            scores = [0.0] * len(passages)
            
            if "results" in result:
                for item in result["results"]:
                    index = item.get("index", 0)
                    score = item.get("relevance_score", item.get("score", 0.0))
                    if 0 <= index < len(scores):
                        scores[index] = float(score)
            elif "data" in result:
                for item in result["data"]:
                    index = item.get("index", 0)
                    score = item.get("relevance_score", item.get("score", 0.0))
                    if 0 <= index < len(scores):
                        scores[index] = float(score)
            
            logger.debug(f"重排完成，处理了 {len(passages)} 个文档")
            return scores
            
        except Exception as e:
            logger.error(f"BGE重排失败: {e}")
            return [0.5] * len(passages)
    
    def batch_rerank(self, query: str, passages: List[str], batch_size: int = 10) -> List[float]:
        """批量重排处理"""
        try:
            if len(passages) <= batch_size:
                return self.rerank(query, passages)
            
            all_scores = []
            
            for i in range(0, len(passages), batch_size):
                batch = passages[i:i + batch_size]
                batch_scores = self.rerank(query, batch)
                all_scores.extend(batch_scores)
            
            return all_scores
            
        except Exception as e:
            logger.error(f"批量重排失败: {e}")
            return [0.5] * len(passages)
    
    def health_check(self) -> bool:
        """健康检查"""
        try:
            test_response = self.client.post(
                self.api_url,
                json={
                    "model": "bge-reranker-base",
                    "query": "health check",
                    "documents": ["test document"],
                },
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.access_token}" if self.access_token else ""
                }
            )
            test_response.raise_for_status()
            return True
            
        except Exception as e:
            logger.error(f"BGE重排服务健康检查失败: {e}")
            return False
    
    def close(self):
        """关闭客户端连接"""
        if self.client:
            self.client.close()
            logger.info("BGE重排模型客户端连接已关闭")


class CustomReranker:
    """自定义重排器"""
    
    def __init__(self):
        self.reranker: Optional[BGEReranker] = None
        self.initialized = False
    
    def initialize(self) -> bool:
        """初始化重排器"""
        try:
            self.reranker = BGEReranker()
            
            if not self.reranker.health_check():
                raise Exception("重排服务健康检查失败")
            
            self.initialized = True
            logger.info("重排器初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"初始化重排器失败: {e}")
            return False
    
    def rerank_results(
        self, 
        query: str, 
        results: List[RetrievalResult],
        score_weight: float = 0.7
    ) -> List[RerankResult]:
        """对检索结果进行重排"""
        try:
            if not self.initialized or not self.reranker:
                logger.warning("重排器未初始化，跳过重排")
                return self._convert_to_rerank_results(results)
            
            if not results:
                return []
            
            passages = [result.content for result in results]
            rerank_scores = self.reranker.batch_rerank(query, passages)
            
            rerank_results = []
            for i, (result, rerank_score) in enumerate(zip(results, rerank_scores)):
                final_score = (
                    (1 - score_weight) * result.score + 
                    score_weight * rerank_score
                )
                
                rerank_result = RerankResult(
                    data_id=result.data_id,
                    collection_id=result.collection_id,
                    content=result.content,
                    original_score=result.score,
                    rerank_score=rerank_score,
                    final_score=final_score,
                    metadata=result.metadata,
                    tokens=result.tokens
                )
                rerank_results.append(rerank_result)
            
            rerank_results.sort(key=lambda x: x.final_score, reverse=True)
            
            logger.info(f"重排完成，处理了 {len(results)} 个结果")
            return rerank_results
            
        except Exception as e:
            logger.error(f"重排结果失败: {e}")
            return self._convert_to_rerank_results(results)
    
    def _convert_to_rerank_results(self, results: List[RetrievalResult]) -> List[RerankResult]:
        """将检索结果转换为重排结果"""
        rerank_results = []
        
        for result in results:
            rerank_result = RerankResult(
                data_id=result.data_id,
                collection_id=result.collection_id,
                content=result.content,
                original_score=result.score,
                rerank_score=result.score,
                final_score=result.score,
                metadata=result.metadata,
                tokens=result.tokens
            )
            rerank_results.append(rerank_result)
        
        return rerank_results
    
    def rerank(
        self, 
        query: str, 
        passages: List[str], 
        top_k: int = None
    ) -> List[Dict[str, Any]]:
        """简化的重排方法"""
        try:
            if not self.initialized or not self.reranker:
                logger.warning("重排器未初始化，返回原始结果")
                results = []
                for i, passage in enumerate(passages):
                    results.append({
                        "index": i,
                        "text": passage,
                        "score": 0.5
                    })
                return results[:top_k] if top_k else results
            
            scores = self.reranker.batch_rerank(query, passages)
            
            results = []
            for i, (passage, score) in enumerate(zip(passages, scores)):
                results.append({
                    "index": i,
                    "text": passage,
                    "score": score
                })
            
            results.sort(key=lambda x: x["score"], reverse=True)
            
            return results[:top_k] if top_k else results
            
        except Exception as e:
            logger.error(f"重排失败: {e}")
            results = []
            for i, passage in enumerate(passages):
                results.append({
                    "index": i,
                    "text": passage,
                    "score": 0.5
                })
            return results[:top_k] if top_k else results
    
    def filter_by_threshold(
        self, 
        results: List[RerankResult], 
        threshold: float = None
    ) -> List[RerankResult]:
        """根据阈值过滤重排结果"""
        if threshold is None:
            threshold = app_config.relevance_threshold
        
        filtered_results = [
            result for result in results 
            if result.final_score >= threshold
        ]
        
        logger.debug(f"阈值过滤: {len(results)} -> {len(filtered_results)} 个结果")
        return filtered_results
    
    def close(self):
        """关闭连接"""
        if self.reranker:
            self.reranker.close()


# 全局实例
custom_reranker = CustomReranker() 