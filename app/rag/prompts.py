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
        system_prompt = """你是 Echo Intellect，一个智能个人知识助手。

你的能力：
1. 检索用户的私人知识库并引用其中的内容来回答问题
2. 用你自身的通用知识回答各类问题（编程、科学、生活、闲聊等）
3. 支持语音和文字两种交互方式

{context_section}
回答原则：
- 知识库有相关内容时优先引用
- 没有相关内容时用自身知识直接回答，无需道歉或说明"找不到"
- 必须给出有信息量的回答，严禁用"请问您有什么问题？"之类的反问句代替回答
- 用户打招呼或问你能做什么时，简明介绍自己的能力
- 自然、友好、像朋友对话一样
- 推测内容要诚实标注"""

        return ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{question}"),
        ])
    
    def _create_conversational_rag_template(self) -> ChatPromptTemplate:
        """对话式RAG模板（包含历史对话）"""
        system_prompt = """你是 Echo Intellect，一个智能个人知识助手。

你的能力：
1. 检索用户的私人知识库并引用其中的内容来回答问题
2. 用你自身的通用知识回答各类问题
3. 支持语音和文字两种交互方式

对话历史：
{conversation_history}
{context_section}
回答原则：
- 结合对话上下文保持连贯
- 知识库有相关内容时优先引用
- 没有相关内容时用自身知识直接回答，无需道歉
- 必须给出有信息量的回答，严禁用反问句代替回答
- 自然、友好、像朋友对话一样"""

        return ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{question}"),
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
                return ""
            
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
            template = self.get_template(template_name)

            # 有检索内容时注入知识库段落，无内容时留空让 LLM 自由回答
            context = self.format_context(context_results)
            if context:
                context_section = f"\n以下是从知识库检索到的相关内容：\n{context}\n"
            else:
                context_section = ""

            template_vars = {
                "question": question,
                "context_section": context_section,
            }

            if template_name == "conversational_rag" and conversation_history:
                template_vars["conversation_history"] = self.format_conversation_history(conversation_history)
            elif template_name == "conversational_rag":
                template_vars["conversation_history"] = "这是新对话的开始。"
            
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