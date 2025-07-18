import logging
import time
import uuid
from typing import Dict, Any, List, Optional

from app.models.data_models import Query, ConversationTurn
from app.components.query_transformation.query_optimizer import query_optimizer
from app.components.query_transformation.query_expander import query_expander
from app.memory.conversation_memory import conversation_memory

logger = logging.getLogger()


class QueryProcessingChain:
    """查询处理链 - 整合查询优化和扩展"""

    def __init__(self):
        self.initialized = False

    def initialize(self) -> bool:
        """初始化查询处理链"""
        try:
            if not query_optimizer.initialized:
                query_optimizer.initialize()

            if not query_expander.initialized:
                query_expander.initialize()

            self.initialized = True
            logger.info("查询处理链初始化成功")
            return True

        except Exception as e:
            logger.error(f"查询处理链初始化失败: {e}")
            return False

    def process_query(
        self,
        question: str,
        session_id: str = None,
        max_tokens: int = 4000,
        relevance_threshold: float = 0.6,
        top_k: int = 10,
        enable_optimization: bool = True,
        enable_expansion: bool = True,
    ) -> Query:
        """处理用户查询"""
        try:
            start_time = time.time()

            if not self.initialized:
                logger.warning("查询处理链未初始化，执行基础处理")
                return self._create_basic_query(
                    question, max_tokens, relevance_threshold, top_k
                )

            query_id = str(uuid.uuid4())

            # 获取对话历史（如果有会话ID）
            conversation_history = []
            if session_id and enable_optimization:
                conversation_history = conversation_memory.get_conversation_history(
                    session_id
                )

            # 第一步：查询优化
            optimized_question = question
            if enable_optimization:
                try:
                    optimized_question = query_optimizer.optimize_query(
                        current_question=question,
                        conversation_history=conversation_history,
                        max_history=3,
                    )

                    logger.debug(
                        f"查询优化完成: '{question}' -> '{optimized_question}'"
                    )
                except Exception as e:
                    logger.warning(f"查询优化失败，使用原始问题: {e}")
                    optimized_question = question

            # 第二步：查询扩展
            expanded_queries = []
            concat_query = optimized_question

            if enable_expansion:
                try:
                    expansion_result = query_expander.expand_query(
                        original_query=optimized_question, num_variants=3
                    )

                    expanded_queries = expansion_result.get("expanded_queries", [])
                    concat_query = expansion_result.get(
                        "concat_query", optimized_question
                    )

                    logger.debug(f"查询扩展完成，生成 {len(expanded_queries)} 个变体")

                except Exception as e:
                    logger.warning(f"查询扩展失败: {e}")
                    expanded_queries = []
                    concat_query = optimized_question

            processed_query = Query(
                id=query_id,
                question=question,
                optimized_question=optimized_question,
                expanded_queries=expanded_queries,
                concat_query=concat_query,
                max_tokens=max_tokens,
                relevance_threshold=relevance_threshold,
                top_k=top_k,
            )

            processing_time = time.time() - start_time

            logger.info(f"查询处理完成 (ID: {query_id})，耗时: {processing_time:.3f}秒")

            return processed_query

        except Exception as e:
            logger.error(f"查询处理失败: {e}")
            return self._create_basic_query(
                question, max_tokens, relevance_threshold, top_k
            )

    def _create_basic_query(
        self, question: str, max_tokens: int, relevance_threshold: float, top_k: int
    ) -> Query:
        """创建基础查询对象（备用方案）"""
        return Query(
            id=str(uuid.uuid4()),
            question=question,
            optimized_question=question,
            expanded_queries=[],
            concat_query=question,
            max_tokens=max_tokens,
            relevance_threshold=relevance_threshold,
            top_k=top_k,
        )

    def process_batch_queries(
        self, questions: List[str], session_id: str = None, **kwargs
    ) -> List[Query]:
        """批量处理查询"""
        try:
            processed_queries = []

            for question in questions:
                processed_query = self.process_query(
                    question=question, session_id=session_id, **kwargs
                )
                processed_queries.append(processed_query)

            logger.info(f"批量处理完成，处理了 {len(questions)} 个查询")
            return processed_queries

        except Exception as e:
            logger.error(f"批量查询处理失败: {e}")
            return []

    def optimize_only(self, question: str, session_id: str = None) -> str:
        """仅执行查询优化"""
        try:
            if not self.initialized:
                return question

            conversation_history = []
            if session_id:
                conversation_history = conversation_memory.get_conversation_history(
                    session_id
                )

            optimized_question = query_optimizer.optimize_query(
                current_question=question, conversation_history=conversation_history
            )

            logger.debug(f"查询优化: '{question}' -> '{optimized_question}'")
            return optimized_question

        except Exception as e:
            logger.error(f"查询优化失败: {e}")
            return question

    def expand_only(
        self, question: str, strategies: List[str] = None
    ) -> Dict[str, Any]:
        """仅执行查询扩展"""
        try:
            if not self.initialized:
                return {
                    "original_query": question,
                    "expanded_queries": [],
                    "concat_query": question,
                }

            expansion_result = query_expander.expand_query(original_query=question)

            logger.debug(
                f"查询扩展: 生成 {len(expansion_result.get('expanded_queries', []))} 个变体"
            )
            return expansion_result

        except Exception as e:
            logger.error(f"查询扩展失败: {e}")
            return {
                "original_query": question,
                "expanded_queries": [],
                "concat_query": question,
            }

    def get_all_query_variants(self, processed_query: Query) -> List[str]:
        """获取所有查询变体（用于检索）"""
        try:
            all_queries = []

            if processed_query.optimized_question:
                all_queries.append(processed_query.optimized_question)

            if processed_query.expanded_queries:
                all_queries.extend(processed_query.expanded_queries)

            if (
                processed_query.concat_query
                and processed_query.concat_query not in all_queries
            ):
                all_queries.append(processed_query.concat_query)

            if not all_queries:
                all_queries.append(processed_query.question)

            logger.debug(f"获取查询变体: {len(all_queries)} 个")
            return all_queries

        except Exception as e:
            logger.error(f"获取查询变体失败: {e}")
            return [processed_query.question]


# 全局实例
query_processing_chain = QueryProcessingChain()
