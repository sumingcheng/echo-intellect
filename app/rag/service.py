import logging
import re
import time
import uuid
from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from config.settings import app_config, get_llm_providers, get_default_llm
from app.models.data_models import Query, RerankResult
from app.llms.reranker import custom_reranker
from app.rag.query_processor import query_processing_chain
from app.rag.parallel_retriever import parallel_retriever
from app.rag.filter import token_relevance_filter
from app.rag.prompts import rag_prompts
from app.rag.memory import conversation_memory
from app.stores.mongo import mongo_store

logger = logging.getLogger()


class RetrievalChain:
    """检索链 - 完整的RAG流程"""

    def __init__(self):
        self._llm_cache: Dict[str, ChatOpenAI] = {}
        self.initialized = False

    def _resolve_model_id(self, model: Optional[str] = None) -> str:
        """解析实际模型ID：参数 > default_llm。"""
        if model:
            return model
        default = get_default_llm()
        if default:
            return default
        raise ValueError("未配置默认LLM模型")

    def _find_provider(self, model_id: str):
        """查找模型所属 provider。优先用动态映射，兜底用第一个 provider。"""
        from app.api.v1.models import get_provider_for_model
        providers = get_llm_providers()
        if not providers:
            raise ValueError("未配置任何LLM供应商")

        provider_id = get_provider_for_model(model_id)
        if provider_id:
            match = next((p for p in providers if p.id == provider_id), None)
            if match:
                return match

        return providers[0]

    @staticmethod
    def _is_reasoning_model(model_id: str) -> bool:
        """推理模型只支持 temperature=1（o 系列 + gpt-5.5）。"""
        return bool(re.match(r"^o\d+", model_id)) or model_id.startswith("gpt-5.5")

    @staticmethod
    def _needs_completion_tokens(model_id: str) -> bool:
        """gpt-5.x 和 o 系列要求 max_completion_tokens 替代 max_tokens。"""
        if re.match(r"^o\d+", model_id):
            return True
        m = re.match(r"^gpt-(\d+)", model_id)
        return bool(m) and int(m.group(1)) >= 5

    def _get_llm(self, model: Optional[str] = None) -> ChatOpenAI:
        """按模型ID获取或创建LLM客户端（带缓存）。"""
        model_id = self._resolve_model_id(model)
        if model_id in self._llm_cache:
            return self._llm_cache[model_id]

        provider = self._find_provider(model_id)

        kwargs: Dict[str, Any] = {
            "api_key": provider.api_key,
            "base_url": provider.api_base,
            "model": model_id,
            "temperature": 1 if self._is_reasoning_model(model_id) else 0.7,
        }

        if self._needs_completion_tokens(model_id):
            kwargs["model_kwargs"] = {"max_completion_tokens": 2048}
        else:
            kwargs["max_tokens"] = 2048

        logger.info("创建LLM客户端: model=%s, reasoning=%s, new_tokens=%s",
                     model_id, self._is_reasoning_model(model_id),
                     self._needs_completion_tokens(model_id))

        llm = ChatOpenAI(**kwargs)
        self._llm_cache[model_id] = llm
        return llm

    def initialize(self) -> bool:
        """初始化检索链"""
        try:
            providers = get_llm_providers()
            if not providers:
                logger.error("未配置任何LLM供应商")
                return False

            self._get_llm()

            if not query_processing_chain.initialized:
                query_processing_chain.initialize()

            if not mongo_store.client:
                mongo_store.connect()

            self.initialized = True
            logger.info("检索链初始化成功，供应商: %s", [p.id for p in providers])
            return True

        except Exception as e:
            logger.error(f"检索链初始化失败: {e}")
            return False

    def run(
        self,
        question: str,
        session_id: str = None,
        model: str = None,
        template_name: str = "basic_rag",
        max_tokens: int = None,
        relevance_threshold: float = None,
        enable_rerank: bool = False,
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

            # 第三步 & 第四步：重排 + 过滤（仅在有检索结果时执行）
            filtered_results = []
            reranked_results = []

            if retrieval_results:
                if enable_rerank:
                    if not custom_reranker.initialized and not custom_reranker.initialize():
                        logger.warning("重排器初始化失败，使用原始检索分数")
                        reranked_results = self._convert_to_rerank_results(
                            retrieval_results
                        )
                    else:
                        reranked_results = custom_reranker.rerank_results(
                            query=processed_query.optimized_question
                            or processed_query.question,
                            results=retrieval_results,
                        )
                else:
                    reranked_results = self._convert_to_rerank_results(retrieval_results)

                filtered_results = token_relevance_filter.filter_results(
                    results=reranked_results,
                    max_tokens=max_tokens,
                    relevance_threshold=relevance_threshold,
                    min_results=1,
                    preserve_diversity=True,
                )

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
                model=model,
            )

            # 第七步：保存对话（如果有会话ID）
            processing_time = time.time() - start_time
            tokens_used = sum(r.tokens for r in filtered_results) if filtered_results else 0
            avg_relevance = (
                sum(r.final_score for r in filtered_results) / len(filtered_results)
                if filtered_results
                else 0.0
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

    def run_stream(
        self,
        question: str,
        session_id: str = None,
        model: str = None,
        template_name: str = "basic_rag",
        max_tokens: int = None,
        relevance_threshold: float = None,
        enable_rerank: bool = False,
        enable_optimization: bool = True,
        enable_expansion: bool = True,
    ):
        """流式 RAG：检索 → 逐 token yield 答案内容。"""
        import json as _json

        if not self.initialized:
            yield f"data: {_json.dumps({'error': '系统未初始化'})}\n\n"
            return

        start_time = time.time()
        if max_tokens is None:
            max_tokens = app_config.max_tokens_limit
        if relevance_threshold is None:
            relevance_threshold = app_config.relevance_threshold

        processed_query = query_processing_chain.process_query(
            question=question, session_id=session_id,
            max_tokens=max_tokens, relevance_threshold=relevance_threshold,
            enable_optimization=enable_optimization, enable_expansion=enable_expansion,
        )

        all_query_variants = query_processing_chain.get_all_query_variants(processed_query)
        retrieval_results = parallel_retriever.parallel_retrieve(
            queries=all_query_variants, base_query=processed_query, merge_strategy="rrf",
        )

        filtered_results = []
        if retrieval_results:
            if enable_rerank and custom_reranker.initialized:
                reranked = custom_reranker.rerank_results(
                    query=processed_query.optimized_question or processed_query.question,
                    results=retrieval_results,
                )
            else:
                reranked = self._convert_to_rerank_results(retrieval_results)

            filtered_results = token_relevance_filter.filter_results(
                results=reranked, max_tokens=max_tokens,
                relevance_threshold=relevance_threshold,
                min_results=1, preserve_diversity=True,
            )

        conversation_history = ""
        if template_name == "conversational_rag" and session_id:
            conversation_history = conversation_memory.get_recent_context(
                session_id=session_id, max_turns=3, max_tokens=800,
            )

        full_answer = []
        for token in self.stream_answer(
            question=question, context_results=filtered_results,
            template_name=template_name,
            conversation_history=conversation_history, model=model,
        ):
            full_answer.append(token)
            yield f"data: {_json.dumps({'token': token})}\n\n"

        answer = "".join(full_answer)
        processing_time = time.time() - start_time
        tokens_used = sum(r.tokens for r in filtered_results) if filtered_results else 0

        if session_id:
            avg_relevance = (
                sum(r.final_score for r in filtered_results) / len(filtered_results)
                if filtered_results else 0.0
            )
            conversation_memory.add_conversation_turn(
                session_id=session_id, question=question, answer=answer,
                retrieved_chunks=filtered_results, tokens_used=tokens_used,
                relevance_score=avg_relevance, response_time=processing_time,
            )

        done_payload = {
            "done": True,
            "query_id": processed_query.id,
            "session_id": session_id,
            "processing_time": round(processing_time, 3),
            "tokens_used": tokens_used,
            "retrieved_chunks_count": len(filtered_results),
            "references": [
                {
                    "content": r.content[:300],
                    "score": round(r.final_score, 3),
                    "collection_id": r.collection_id,
                }
                for r in filtered_results
            ],
        }
        yield f"data: {_json.dumps(done_payload)}\n\n"

    def _build_messages(
        self,
        question: str,
        context_results: List[RerankResult],
        template_name: str = "basic_rag",
        conversation_history: str = "",
    ) -> list:
        """构造 LLM 消息列表，供同步和流式共用。"""
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
        return messages

    def _generate_answer(
        self,
        question: str,
        context_results: List[RerankResult],
        template_name: str = "basic_rag",
        conversation_history: str = "",
        model: str = None,
    ) -> str:
        """同步生成答案"""
        try:
            messages = self._build_messages(
                question, context_results, template_name, conversation_history,
            )
            llm = self._get_llm(model)
            response = llm.invoke(messages)
            answer = response.content.strip()

            if not answer:
                logger.warning("LLM返回空答案")
                return "抱歉，我无法基于提供的信息回答您的问题。"

            logger.debug("答案生成成功")
            return answer

        except Exception as e:
            logger.error(f"生成答案失败: {e}")
            return "抱歉，在生成答案时遇到了问题，请稍后再试。"

    def stream_answer(
        self,
        question: str,
        context_results: List[RerankResult],
        template_name: str = "basic_rag",
        conversation_history: str = "",
        model: str = None,
    ):
        """流式生成答案，yield 每个 token 文本片段。"""
        messages = self._build_messages(
            question, context_results, template_name, conversation_history,
        )
        llm = self._get_llm(model)
        for chunk in llm.stream(messages):
            if chunk.content:
                yield chunk.content

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
