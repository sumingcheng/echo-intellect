import logging
from typing import List, Dict, Any, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage

from app.models.data_models import RerankResult

logger = logging.getLogger()

# 基础 RAG 系统提示词
_BASIC_SYSTEM = """\
You are Echo Intellect, a personal knowledge assistant with access to the user's private knowledge base.

## Behavior

1. When <context> contains relevant information, ground your answer strictly in it.
   - Synthesize across multiple sources when they complement each other.
   - If sources conflict, present both views and note the discrepancy.
   - Never fabricate details not present in the provided context.

2. When <context> is empty or irrelevant to the question, answer from your general knowledge.
   - Do NOT apologize or say "I couldn't find anything."
   - Simply provide a helpful, accurate answer.

3. Always respond in the same language the user writes in.

4. Be concise by default. Elaborate only when the question demands depth.

{context_section}\
"""

# 对话式 RAG 系统提示词
_CONVERSATIONAL_SYSTEM = """\
You are Echo Intellect, a personal knowledge assistant with access to the user's private knowledge base.

## Conversation History

{conversation_history}

## Behavior

1. Maintain coherence with the conversation history above.
2. When <context> contains relevant information, ground your answer strictly in it.
   - Synthesize across multiple sources when they complement each other.
   - If sources conflict, present both views and note the discrepancy.
   - Never fabricate details not present in the provided context.
3. When <context> is empty or irrelevant, answer from general knowledge without apology.
4. Always respond in the same language the user writes in.
5. Be concise by default. Elaborate only when the question demands depth.

{context_section}\
"""


class RAGPromptTemplates:
    """RAG 提示词管理"""

    def __init__(self):
        self.templates: Dict[str, ChatPromptTemplate] = {}
        self._init_templates()
        logger.info("RAG 提示词初始化完成")

    def _init_templates(self):
        self.templates = {
            "basic_rag": ChatPromptTemplate.from_messages([
                ("system", _BASIC_SYSTEM),
                ("human", "{question}"),
            ]),
            "conversational_rag": ChatPromptTemplate.from_messages([
                ("system", _CONVERSATIONAL_SYSTEM),
                ("human", "{question}"),
            ]),
        }

    def get_template(self, name: str = "basic_rag") -> ChatPromptTemplate:
        t = self.templates.get(name)
        if t is None:
            logger.warning("模板 '%s' 不存在，回退到 basic_rag", name)
            return self.templates["basic_rag"]
        return t

    @staticmethod
    def format_context(results: List[RerankResult]) -> str:
        """将检索结果格式化为 XML 结构化上下文"""
        if not results:
            return ""

        parts = []
        for i, r in enumerate(results, 1):
            source = r.metadata.get("source", "")
            src_attr = f' source="{source}"' if source else ""
            parts.append(
                f'<source id="{i}" relevance="{r.final_score:.3f}"{src_attr}>\n'
                f'{r.content}\n'
                f'</source>'
            )
        return "\n\n".join(parts)

    @staticmethod
    def format_conversation_history(history: str) -> str:
        if not history:
            return "(Start of conversation)"
        return history

    def create_rag_prompt(
        self,
        question: str,
        context_results: List[RerankResult],
        template_name: str = "basic_rag",
        conversation_history: str = None,
        additional_context: Dict[str, Any] = None,
    ) -> Dict[str, str]:
        """构建完整的 RAG prompt，返回 {system, human} 字典"""
        try:
            template = self.get_template(template_name)

            context_xml = self.format_context(context_results)
            if context_xml:
                context_section = (
                    "\n## Retrieved Context\n\n"
                    f"{context_xml}\n"
                )
            else:
                context_section = ""

            template_vars: Dict[str, Any] = {
                "question": question,
                "context_section": context_section,
            }

            if template_name == "conversational_rag":
                template_vars["conversation_history"] = (
                    self.format_conversation_history(conversation_history)
                )

            if additional_context:
                template_vars.update(additional_context)

            formatted = template.format_messages(**template_vars)

            result: Dict[str, str] = {}
            for msg in formatted:
                if isinstance(msg, SystemMessage):
                    result["system"] = msg.content
                elif isinstance(msg, HumanMessage):
                    result["human"] = msg.content

            return result

        except Exception as e:
            logger.error("创建 RAG prompt 失败: %s", e)
            return {"system": "You are a helpful assistant.", "human": question}

    def get_available_templates(self) -> List[str]:
        return list(self.templates.keys())


# 全局实例
rag_prompts = RAGPromptTemplates()
