import logging
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from app.models.data_models import ConversationTurn
from app.vectorstores.mongo_metadata import mongo_store

logger = logging.getLogger()


class ConversationMemory:
    """对话历史记忆组件"""

    def __init__(self, max_history_length: int = 10, session_timeout_hours: int = 24):
        self.max_history_length = max_history_length
        self.session_timeout_hours = session_timeout_hours
        self._local_cache: Dict[str, List[ConversationTurn]] = {}

        logger.info(
            f"对话记忆组件初始化，最大历史长度: {max_history_length}, 会话超时: {session_timeout_hours}小时"
        )

    def add_conversation_turn(
        self,
        session_id: str,
        question: str,
        answer: str,
        retrieved_chunks: List = None,
        tokens_used: int = 0,
        relevance_score: float = 0.0,
        response_time: float = 0.0,
    ) -> str:
        """添加对话轮次"""
        try:
            turn_id = str(uuid.uuid4())

            turn = ConversationTurn(
                id=turn_id,
                session_id=session_id,
                question=question,
                answer=answer,
                retrieved_chunks=retrieved_chunks or [],
                timestamp=datetime.now(),
                tokens_used=tokens_used,
                relevance_score=relevance_score,
                response_time=response_time,
            )

            success = mongo_store.save_conversation_turn(turn)
            if not success:
                logger.warning(f"保存对话轮次到MongoDB失败: {turn_id}")

            self._update_local_cache(session_id, turn)

            logger.debug(f"添加对话轮次成功: {turn_id}")
            return turn_id

        except Exception as e:
            logger.error(f"添加对话轮次失败: {e}")
            return ""

    def get_conversation_history(
        self,
        session_id: str,
        limit: int = None,
        include_current_session_only: bool = True,
    ) -> List[ConversationTurn]:
        """获取对话历史"""
        try:
            if limit is None:
                limit = self.max_history_length

            # 先从本地缓存获取
            if session_id in self._local_cache:
                cached_history = self._local_cache[session_id]
                if cached_history:
                    latest_turn = cached_history[-1]
                    if self._is_session_valid(latest_turn.timestamp):
                        return cached_history[-limit:]

            # 从MongoDB获取
            history = mongo_store.get_conversation_history(session_id, limit)

            # 过滤过期会话
            if include_current_session_only:
                history = [
                    turn for turn in history if self._is_session_valid(turn.timestamp)
                ]

            self._local_cache[session_id] = history

            logger.debug(f"获取对话历史: session={session_id}, 数量={len(history)}")
            return history

        except Exception as e:
            logger.error(f"获取对话历史失败: {e}")
            return []

    def get_recent_context(
        self, session_id: str, max_turns: int = 3, max_tokens: int = 1000
    ) -> str:
        """获取最近的对话上下文"""
        try:
            history = self.get_conversation_history(session_id, max_turns)

            if not history:
                return ""

            context_parts = []
            total_tokens = 0

            for turn in reversed(history):
                turn_text = f"Q: {turn.question}\nA: {turn.answer}"
                turn_tokens = len(turn_text) // 4

                if total_tokens + turn_tokens > max_tokens:
                    break

                context_parts.insert(0, turn_text)
                total_tokens += turn_tokens

            context = "\n\n".join(context_parts)
            logger.debug(
                f"生成对话上下文: {len(context_parts)} 轮对话, ~{total_tokens} tokens"
            )

            return context

        except Exception as e:
            logger.error(f"获取对话上下文失败: {e}")
            return ""

    def clear_session_history(self, session_id: str) -> bool:
        """清除会话历史"""
        try:
            if session_id in self._local_cache:
                del self._local_cache[session_id]

            logger.info(f"清除会话历史: {session_id}")
            return True

        except Exception as e:
            logger.error(f"清除会话历史失败: {e}")
            return False

    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """获取会话摘要统计"""
        try:
            history = self.get_conversation_history(session_id, limit=100)

            if not history:
                return {}

            total_tokens = sum(turn.tokens_used for turn in history)
            avg_relevance = sum(turn.relevance_score for turn in history) / len(history)
            avg_response_time = sum(turn.response_time for turn in history) / len(
                history
            )

            first_turn = min(history, key=lambda x: x.timestamp)
            last_turn = max(history, key=lambda x: x.timestamp)

            summary = {
                "session_id": session_id,
                "total_turns": len(history),
                "total_tokens_used": total_tokens,
                "average_relevance_score": round(avg_relevance, 3),
                "average_response_time": round(avg_response_time, 3),
                "session_start": first_turn.timestamp.isoformat(),
                "session_last_activity": last_turn.timestamp.isoformat(),
                "session_duration_minutes": (
                    last_turn.timestamp - first_turn.timestamp
                ).total_seconds()
                / 60,
            }

            return summary

        except Exception as e:
            logger.error(f"获取会话摘要失败: {e}")
            return {}

    def _update_local_cache(self, session_id: str, turn: ConversationTurn):
        """更新本地缓存"""
        try:
            if session_id not in self._local_cache:
                self._local_cache[session_id] = []

            self._local_cache[session_id].append(turn)

            if len(self._local_cache[session_id]) > self.max_history_length:
                self._local_cache[session_id] = self._local_cache[session_id][
                    -self.max_history_length :
                ]

        except Exception as e:
            logger.error(f"更新本地缓存失败: {e}")

    def _is_session_valid(self, timestamp: datetime) -> bool:
        """检查会话是否有效"""
        try:
            timeout_threshold = datetime.now() - timedelta(
                hours=self.session_timeout_hours
            )
            return timestamp > timeout_threshold
        except Exception as e:
            logger.error(f"检查会话有效性失败: {e}")
            return True

    def cleanup_expired_sessions(self) -> int:
        """清理过期的会话缓存"""
        try:
            expired_sessions = []
            current_time = datetime.now()
            timeout_threshold = current_time - timedelta(
                hours=self.session_timeout_hours
            )

            for session_id, history in self._local_cache.items():
                if history:
                    latest_turn = max(history, key=lambda x: x.timestamp)
                    if latest_turn.timestamp < timeout_threshold:
                        expired_sessions.append(session_id)

            for session_id in expired_sessions:
                del self._local_cache[session_id]

            logger.info(f"清理了 {len(expired_sessions)} 个过期会话")
            return len(expired_sessions)

        except Exception as e:
            logger.error(f"清理过期会话失败: {e}")
            return 0


# 全局实例
conversation_memory = ConversationMemory()
