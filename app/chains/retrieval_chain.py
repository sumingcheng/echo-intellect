import logging
import time
import uuid
from typing import Dict, Any, List, Optional
from langchain_deepseek import ChatDeepSeek
from langchain_core.messages import SystemMessage, HumanMessage

from config.settings import app_config
from app.models.data_models import Query, RerankResult
from app.chains.query_processing_chain import query_processing_chain
from app.components.retrievers.parallel_retriever import parallel_retriever
from app.components.rerankers.custom_reranker import custom_reranker
from app.components.filters.token_relevance_filter import token_relevance_filter
from app.prompts.rag_prompts import rag_prompts
from app.memory.conversation_memory import conversation_memory
from app.vectorstores.mongo_metadata import mongo_store

logger = logging.getLogger()


class RetrievalChain:
    """检索链 - 完整的RAG流程"""

    def __init__(self):
        self.llm: Optional[ChatDeepSeek] = None
        self.initialized = False

    def initialize(self) -> bool:
        """初始化检索链"""
        try:
            self.llm = ChatDeepSeek(
                api_key=app_config.llm_api_key,
                base_url=app_config.llm_api_base,
                model=app_config.llm_model,
                temperature=0.7,
                max_tokens=2048,
            )

            if not query_processing_chain.initialized:
                query_processing_chain.initialize()

            if not custom_reranker.initialized:
                custom_reranker.initialize()

            if not mongo_store.client:
                mongo_store.connect()

            self.initialized = True
            logger.info("检索链初始化成功")
            return True

        except Exception as e:
            logger.error(f"检索链初始化失败: {e}")
            return False

    def run(
        self,
        question: str,
        session_id: str = None,
        template_name: str = "basic_rag",
        max_tokens: int = None,
        relevance_threshold: float = None,
        enable_rerank: bool = True,
        enable_optimization: bool = True,
        enable_expansion: bool = True,
    ) -> Dict[str, Any]:
        """运行完整的RAG检索链"""
        try:
            start_time = time.time()

            if not self.initialized:
                logger.error("检索链未初始化")
                return self._create_error_response("系统未初始化，请稍后再试")

            if max_tokens is None:
                max_tokens = app_config.max_tokens_limit
            if relevance_threshold is None:
                relevance_threshold = app_config.relevance_threshold

            logger.info(f"开始RAG检索流程: {question[:50]}...")

            # 第一步：查询处理
            processed_query = query_processing_chain.process_query(
                question=question,
                session_id=session_id,
                max_tokens=max_tokens,
                relevance_threshold=relevance_threshold,
                enable_optimization=enable_optimization,
                enable_expansion=enable_expansion,
            )

            # 第二步：并行检索
            all_query_variants = query_processing_chain.get_all_query_variants(
                processed_query
            )

            retrieval_results = parallel_retriever.parallel_retrieve(
                queries=all_query_variants,
                base_query=processed_query,
                merge_strategy="rrf",
            )

            if not retrieval_results:
                logger.warning("检索未返回任何结果")
                return self._create_no_results_response(question, processed_query)

            # 第三步：重排（可选）
            reranked_results = retrieval_results
            if enable_rerank:
                reranked_results = custom_reranker.rerank_results(
                    query=processed_query.optimized_question
                    or processed_query.question,
                    results=retrieval_results,
                )
            else:
                reranked_results = self._convert_to_rerank_results(retrieval_results)

            # 第四步：结果过滤
            filtered_results = token_relevance_filter.filter_results(
                results=reranked_results,
                max_tokens=max_tokens,
                relevance_threshold=relevance_threshold,
                min_results=1,
                preserve_diversity=True,
            )

            if not filtered_results:
                logger.warning("过滤后无剩余结果")
                return self._create_no_results_response(question, processed_query)

            # 第五步：获取对话历史（如果是对话式模板）
            conversation_history = ""
            if template_name == "conversational_rag" and session_id:
                conversation_history = conversation_memory.get_recent_context(
                    session_id=session_id, max_turns=3, max_tokens=800
                )

            # 第六步：生成回答
            answer = self._generate_answer(
                question=question,
                context_results=filtered_results,
                template_name=template_name,
                conversation_history=conversation_history,
            )

            # 第七步：保存对话（如果有会话ID）
            processing_time = time.time() - start_time
            tokens_used = sum(r.tokens for r in filtered_results)
            avg_relevance = sum(r.final_score for r in filtered_results) / len(
                filtered_results
            )

            if session_id:
                conversation_memory.add_conversation_turn(
                    session_id=session_id,
                    question=question,
                    answer=answer,
                    retrieved_chunks=filtered_results,
                    tokens_used=tokens_used,
                    relevance_score=avg_relevance,
                    response_time=processing_time,
                )

            # 构建返回结果
            response = {
                "question": question,
                "answer": answer,
                "query_id": processed_query.id,
                "session_id": session_id,
                "processing_time": round(processing_time, 3),
                "tokens_used": tokens_used,
                "relevance_score": round(avg_relevance, 3),
                "retrieved_chunks_count": len(filtered_results),
                "metadata": {
                    "processed_query": processed_query.model_dump(),
                    "retrieval_stats": {
                        "initial_results": len(retrieval_results),
                        "reranked_results": len(reranked_results),
                        "filtered_results": len(filtered_results),
                        "rerank_enabled": enable_rerank,
                    },
                    "template_used": template_name,
                    "processing_enabled": {
                        "optimization": enable_optimization,
                        "expansion": enable_expansion,
                        "rerank": enable_rerank,
                    },
                },
            }

            logger.info(
                f"RAG检索完成，耗时: {processing_time:.3f}秒，token使用: {tokens_used}"
            )
            return response

        except Exception as e:
            logger.error(f"RAG检索流程失败: {e}")
            return self._create_error_response(f"检索过程中发生错误: {str(e)}")

    def _generate_answer(
        self,
        question: str,
        context_results: List[RerankResult],
        template_name: str = "basic_rag",
        conversation_history: str = "",
    ) -> str:
        """生成答案"""
        try:
            prompt_dict = rag_prompts.create_rag_prompt(
                question=question,
                context_results=context_results,
                template_name=template_name,
                conversation_history=conversation_history,
            )

            messages = []
            if "system" in prompt_dict:
                messages.append(SystemMessage(content=prompt_dict["system"]))
            if "human" in prompt_dict:
                messages.append(HumanMessage(content=prompt_dict["human"]))

            response = self.llm.invoke(messages)
            answer = response.content.strip()

            if not answer:
                logger.warning("LLM返回空答案")
                return "抱歉，我无法基于提供的信息回答您的问题。"

            logger.debug("答案生成成功")
            return answer

        except Exception as e:
            logger.error(f"生成答案失败: {e}")
            return "抱歉，在生成答案时遇到了问题，请稍后再试。"

    def _convert_to_rerank_results(self, results: List) -> List[RerankResult]:
        """将检索结果转换为重排结果格式"""
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
                tokens=result.tokens,
            )
            rerank_results.append(rerank_result)
        return rerank_results

    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """创建错误响应"""
        return {
            "question": "",
            "answer": error_message,
            "query_id": "",
            "session_id": None,
            "processing_time": 0.0,
            "tokens_used": 0,
            "relevance_score": 0.0,
            "retrieved_chunks_count": 0,
            "error": True,
            "metadata": {},
        }

    def _create_no_results_response(
        self, question: str, query: Query
    ) -> Dict[str, Any]:
        """创建无结果响应"""
        return {
            "question": question,
            "answer": "抱歉，我没有找到与您问题相关的信息。请尝试换个方式提问或提供更多详细信息。",
            "query_id": query.id,
            "session_id": None,
            "processing_time": 0.0,
            "tokens_used": 0,
            "relevance_score": 0.0,
            "retrieved_chunks_count": 0,
            "no_results": True,
            "metadata": {"processed_query": query.model_dump()},
        }


# 全局实例
retrieval_chain = RetrievalChain()
