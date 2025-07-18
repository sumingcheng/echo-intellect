import logging
from typing import List, Optional, Dict, Any
from langchain_deepseek import ChatDeepSeek
from langchain_core.messages import HumanMessage, SystemMessage

from config.settings import app_config
from app.models.data_models import ConversationTurn

logger = logging.getLogger()


class QueryOptimizer:
    """查询优化器 - 处理指代消除和上下文补全"""
    
    def __init__(self):
        self.llm: Optional[ChatDeepSeek] = None
        self.initialized = False
    
    def initialize(self):
        """初始化查询优化器"""
        try:
            self.llm = ChatDeepSeek(
                api_key=app_config.llm_api_key,
                base_url=app_config.llm_api_base,
                model=app_config.llm_model,
                temperature=0.1,
                max_tokens=512
            )
            
            self.initialized = True
            logger.info("查询优化器初始化成功")
            
        except Exception as e:
            logger.error(f"初始化查询优化器失败: {e}")
            raise
    
    def optimize_query(
        self, 
        current_question: str,
        conversation_history: List[ConversationTurn] = None,
        max_history: int = 3
    ) -> str:
        """优化查询 - 结合指代消除和上下文补全"""
        try:
            if not self.initialized:
                logger.warning("查询优化器未初始化，返回原始问题")
                return current_question
            
            if not conversation_history:
                return current_question
            
            context = self._build_context(conversation_history, max_history)
            
            system_prompt = self._get_optimization_prompt()
            user_prompt = self._build_user_prompt(current_question, context)
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = self.llm.invoke(messages)
            optimized_question = response.content.strip()
            
            if not optimized_question or len(optimized_question) < 10:
                logger.warning("查询优化结果异常，返回原始问题")
                return current_question
            
            logger.info(f"查询优化完成: '{current_question}' -> '{optimized_question}'")
            return optimized_question
            
        except Exception as e:
            logger.error(f"查询优化失败: {e}")
            return current_question
    
    def _build_context(
        self, 
        history: List[ConversationTurn], 
        max_history: int
    ) -> str:
        """构建对话上下文"""
        try:
            recent_history = history[-max_history:] if len(history) > max_history else history
            
            context_parts = []
            for i, turn in enumerate(recent_history, 1):
                context_parts.append(f"Q{i}: {turn.question}")
                context_parts.append(f"A{i}: {turn.answer}")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"构建对话上下文失败: {e}")
            return ""
    
    def _get_optimization_prompt(self) -> str:
        """获取优化提示词"""
        return """你是一个专业的查询优化助手。你的任务是根据对话历史，优化当前的用户问题，使其更加清晰、完整和独立。

优化原则：
1. 指代消除：将"它"、"这个"、"那个"等指代词替换为具体的实体名称
2. 上下文补全：根据对话历史补充缺失的关键信息
3. 保持原意：确保优化后的问题与原问题意图完全一致
4. 独立理解：优化后的问题应该能够独立理解，不依赖对话历史

注意事项：
- 只输出优化后的问题，不要添加任何解释
- 如果原问题已经很清晰完整，可以直接返回原问题
- 不要改变问题的核心意图和要求"""
    
    def _build_user_prompt(self, current_question: str, context: str) -> str:
        """构建用户提示词"""
        if not context:
            return f"请优化以下问题：\n\n{current_question}"
        
        return f"""对话历史：
{context}

当前问题：
{current_question}

请根据对话历史优化当前问题，使其更加清晰、完整和独立："""
    
    def resolve_coreferences(self, question: str, context: str) -> str:
        """专门处理指代消解"""
        try:
            if not self.initialized:
                return question
            
            coreference_words = ["它", "这个", "那个", "这", "那", "此", "该"]
            has_coreference = any(word in question for word in coreference_words)
            
            if not has_coreference:
                return question
            
            system_prompt = """你是一个指代消解专家。请根据上下文，将问题中的指代词（如"它"、"这个"、"那个"等）替换为具体的实体名称。

要求：
1. 仅处理指代词，不改变问题的其他部分
2. 确保替换后的问题语义清晰、语法正确
3. 如果无法确定指代对象，保持原样
4. 只输出处理后的问题"""
            
            user_prompt = f"""上下文：
{context}

问题：
{question}

请将问题中的指代词替换为具体实体："""
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = self.llm.invoke(messages)
            resolved_question = response.content.strip()
            
            if resolved_question and len(resolved_question) >= len(question) * 0.8:
                logger.debug(f"指代消解: '{question}' -> '{resolved_question}'")
                return resolved_question
            else:
                return question
                
        except Exception as e:
            logger.error(f"指代消解失败: {e}")
            return question
    
    def complete_context(self, question: str, context: str) -> str:
        """专门处理上下文补全"""
        try:
            if not self.initialized or not context:
                return question
            
            system_prompt = """你是一个上下文补全专家。根据对话历史，为当前问题补充必要的背景信息，使其能够独立理解。

要求：
1. 补充关键的主题、实体或背景信息
2. 保持问题的原始意图不变
3. 补充的信息应该自然融入问题中
4. 如果问题已经足够完整，保持原样
5. 只输出补全后的问题"""
            
            user_prompt = f"""对话历史：
{context}

当前问题：
{question}

请为当前问题补充必要的上下文信息："""
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = self.llm.invoke(messages)
            completed_question = response.content.strip()
            
            if completed_question and len(completed_question) >= len(question):
                logger.debug(f"上下文补全: '{question}' -> '{completed_question}'")
                return completed_question
            else:
                return question
                
        except Exception as e:
            logger.error(f"上下文补全失败: {e}")
            return question


# 全局实例
query_optimizer = QueryOptimizer() 