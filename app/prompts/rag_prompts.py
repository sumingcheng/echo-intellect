import logging
from typing import List, Dict, Any, Optional
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage

from app.models.data_models import RerankResult

logger = logging.getLogger()


class RAGPromptTemplates:
    """RAG提示模板管理器"""
    
    def __init__(self):
        self.templates = {}
        self._initialize_templates()
        logger.info("RAG提示模板管理器初始化完成")
    
    def _initialize_templates(self):
        """初始化所有提示模板"""
        self.templates = {
            "basic_rag": self._create_basic_rag_template(),
            "conversational_rag": self._create_conversational_rag_template()
        }
    
    def _create_basic_rag_template(self) -> ChatPromptTemplate:
        """基础RAG模板"""
        system_prompt = """你是一个专业的知识问答助手。请根据提供的上下文信息来回答用户的问题。

回答要求：
1. 优先使用提供的上下文信息
2. 如果上下文不包含相关信息，请说明无法从提供的信息中找到答案
3. 保持回答准确、简洁、有用
4. 可以进行合理的推理，但要基于提供的信息
5. 如果问题需要实时信息或个人意见，请说明这些限制

上下文信息：
{context}

请基于以上信息回答用户的问题。"""

        human_prompt = "问题：{question}"
        
        return ChatPromptTemplate.from_messages([
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ])
    
    def _create_conversational_rag_template(self) -> ChatPromptTemplate:
        """对话式RAG模板（包含历史对话）"""
        system_prompt = """你是一个智能对话助手。请根据提供的上下文信息和对话历史来回答用户的问题。

回答要求：
1. 考虑对话历史，保持对话的连贯性
2. 优先使用提供的上下文信息
3. 如果当前问题与之前的对话相关，要体现这种关联
4. 保持友好、自然的对话语调
5. 如果信息不足，可以询问用户更多细节

对话历史：
{conversation_history}

当前上下文信息：
{context}

请基于对话历史和上下文信息回答用户的当前问题。"""

        human_prompt = "当前问题：{question}"
        
        return ChatPromptTemplate.from_messages([
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ])
    

    
    def get_template(self, template_name: str = "basic_rag") -> ChatPromptTemplate:
        """获取指定的提示模板"""
        template = self.templates.get(template_name)
        if template is None:
            logger.warning(f"模板 '{template_name}' 不存在，返回基础模板")
            return self.templates["basic_rag"]
        return template
    
    def format_context(self, results: List[RerankResult]) -> str:
        """格式化检索结果为上下文"""
        try:
            if not results:
                return "暂无相关信息。"
            
            context_parts = []
            for i, result in enumerate(results, 1):
                # 构建上下文条目
                context_entry = f"[信息 {i}]\n内容：{result.content}"
                
                # 添加相关性得分（如果需要）
                if result.final_score > 0:
                    context_entry += f"\n相关性：{result.final_score:.2f}"
                
                # 添加来源信息（如果有）
                if result.metadata.get("source"):
                    context_entry += f"\n来源：{result.metadata['source']}"
                
                context_parts.append(context_entry)
            
            context = "\n\n".join(context_parts)
            logger.debug(f"格式化上下文完成，包含 {len(results)} 条信息")
            
            return context
            
        except Exception as e:
            logger.error(f"格式化上下文失败: {e}")
            return "上下文信息处理出错。"
    
    def format_conversation_history(self, conversation_history: str) -> str:
        """格式化对话历史"""
        try:
            if not conversation_history:
                return "这是对话的开始。"
            
            return conversation_history
            
        except Exception as e:
            logger.error(f"格式化对话历史失败: {e}")
            return "对话历史处理出错。"
    
    def create_rag_prompt(
        self,
        question: str,
        context_results: List[RerankResult],
        template_name: str = "basic_rag",
        conversation_history: str = None,
        additional_context: Dict[str, Any] = None
    ) -> Dict[str, str]:
        """
        创建完整的RAG提示
        
        Args:
            question: 用户问题
            context_results: 检索结果
            template_name: 模板名称
            conversation_history: 对话历史
            additional_context: 额外上下文信息
        
        Returns:
            格式化后的提示字典
        """
        try:
            # 获取模板
            template = self.get_template(template_name)
            
            # 格式化上下文
            context = self.format_context(context_results)
            
            # 准备变量
            template_vars = {
                "question": question,
                "context": context
            }
            
            # 如果是对话式模板，添加对话历史
            if template_name == "conversational_rag" and conversation_history:
                template_vars["conversation_history"] = self.format_conversation_history(conversation_history)
            elif template_name == "conversational_rag":
                template_vars["conversation_history"] = "这是对话的开始。"
            
            # 添加额外上下文
            if additional_context:
                template_vars.update(additional_context)
            
            # 格式化提示
            formatted_messages = template.format_messages(**template_vars)
            
            # 转换为字典格式
            result = {}
            for message in formatted_messages:
                if isinstance(message, SystemMessage):
                    result["system"] = message.content
                elif isinstance(message, HumanMessage):
                    result["human"] = message.content
            
            logger.debug(f"创建RAG提示成功，模板: {template_name}")
            return result
            
        except Exception as e:
            logger.error(f"创建RAG提示失败: {e}")
            return {
                "system": "你是一个有用的助手。",
                "human": question
            }
    
    def get_available_templates(self) -> List[str]:
        """获取可用的模板列表"""
        return list(self.templates.keys())
    
    def add_custom_template(self, name: str, template: ChatPromptTemplate) -> bool:
        """添加自定义模板"""
        try:
            self.templates[name] = template
            logger.info(f"添加自定义模板: {name}")
            return True
        except Exception as e:
            logger.error(f"添加自定义模板失败: {e}")
            return False
    
    def create_streaming_prompt(
        self,
        question: str,
        context_results: List[RerankResult],
        template_name: str = "basic_rag"
    ) -> str:
        """创建流式输出的提示（单一字符串格式）"""
        try:
            prompt_dict = self.create_rag_prompt(question, context_results, template_name)
            
            # 合并系统提示和用户提示
            system_part = prompt_dict.get("system", "")
            human_part = prompt_dict.get("human", "")
            
            full_prompt = f"{system_part}\n\n{human_part}"
            
            return full_prompt
            
        except Exception as e:
            logger.error(f"创建流式提示失败: {e}")
            return f"请回答以下问题：{question}"


# 全局实例
rag_prompts = RAGPromptTemplates() 