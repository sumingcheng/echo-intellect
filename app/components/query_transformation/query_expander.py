import logging
from typing import List, Optional, Dict, Any
from langchain_deepseek import ChatDeepSeek
from langchain_core.messages import HumanMessage, SystemMessage

from config.settings import app_config

logger = logging.getLogger()


class QueryExpander:
    """查询扩展器 - 生成多个查询变体"""

    def __init__(self):
        self.llm: Optional[ChatDeepSeek] = None
        self.initialized = False

    def initialize(self):
        """初始化查询扩展器"""
        try:
            self.llm = ChatDeepSeek(
                api_key=app_config.llm_api_key,
                base_url=app_config.llm_api_base,
                model=app_config.llm_model,
                temperature=0.3,
                max_tokens=1024,
            )

            self.initialized = True
            logger.info("查询扩展器初始化成功")

        except Exception as e:
            logger.error(f"初始化查询扩展器失败: {e}")
            raise

    def expand_query(
        self, original_query: str, num_variants: int = 3
    ) -> Dict[str, Any]:
        """扩展查询生成多个变体"""
        try:
            if not self.initialized:
                logger.warning("查询扩展器未初始化，返回原始查询")
                return {
                    "original_query": original_query,
                    "expanded_queries": [],
                    "concat_query": original_query,
                }

            expanded_queries = []

            for i in range(num_variants):
                try:
                    expanded_query = self._generate_variant(original_query, i + 1)
                    if expanded_query and expanded_query != original_query:
                        expanded_queries.append(expanded_query)
                        logger.debug(f"扩展查询{i+1}: {expanded_query}")
                except Exception as e:
                    logger.warning(f"生成扩展查询{i+1}失败: {e}")

            concat_query = self._generate_concat_query(original_query, expanded_queries)

            result = {
                "original_query": original_query,
                "expanded_queries": expanded_queries,
                "concat_query": concat_query,
            }

            logger.info(f"查询扩展完成，生成了 {len(expanded_queries)} 个变体")
            return result

        except Exception as e:
            logger.error(f"查询扩展失败: {e}")
            return {
                "original_query": original_query,
                "expanded_queries": [],
                "concat_query": original_query,
            }

    def _generate_variant(self, query: str, variant_index: int) -> str:
        """生成查询变体"""
        try:
            system_prompt = """你是一个查询扩展专家。请为用户的查询生成一个语义相关但表达不同的变体查询。

要求：
1. 保持与原查询相同的核心意图
2. 使用不同的表达方式或关键词
3. 可以从不同角度表述同一问题
4. 确保变体查询有助于检索到更多相关信息
5. 只输出变体查询，不要添加解释

示例：
原查询：如何提高学习效率？
变体：怎样增强学习效果？"""

            user_prompt = f"原始查询：{query}\n\n请生成变体查询{variant_index}："

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]

            response = self.llm.invoke(messages)
            variant = response.content.strip()

            # 处理LLM可能返回的列表格式（取第一个有效项）
            if "\n" in variant:
                lines = variant.split("\n")
                for line in lines:
                    clean_line = line.strip()
                    if clean_line:
                        import re

                        clean_line = re.sub(r"^\d+\.\s*", "", clean_line)
                        if clean_line and len(clean_line) > 5:
                            variant = clean_line
                            break

            if self._is_valid_variant(query, variant):
                return variant
            else:
                logger.warning(f"生成的变体质量不佳: {variant}")
                return ""

        except Exception as e:
            logger.error(f"生成查询变体{variant_index}失败: {e}")
            return ""

    def _generate_concat_query(self, original: str, variants: List[str]) -> str:
        """生成合并查询"""
        try:
            if not variants:
                return original

            all_queries = [original] + variants

            system_prompt = """你是一个查询合并专家。请将多个相关查询合并成一个综合查询。

要求：
1. 合并所有查询的关键信息
2. 去除重复的概念和词汇
3. 保持查询的可读性和逻辑性
4. 确保合并后的查询涵盖原始查询的核心意图
5. 只输出合并后的查询，不要添加解释"""

            user_prompt = f"""需要合并的查询：
{chr(10).join([f"{i+1}. {q}" for i, q in enumerate(all_queries)])}

请生成一个合并查询："""

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]

            response = self.llm.invoke(messages)
            concat_query = response.content.strip()

            if concat_query and len(concat_query) > len(original):
                logger.debug(f"合并查询: {concat_query}")
                return concat_query
            else:
                return f"{original} {' '.join(variants)}"

        except Exception as e:
            logger.error(f"生成合并查询失败: {e}")
            return original

    def _is_valid_variant(self, original: str, variant: str) -> bool:
        """验证变体查询的质量"""
        try:
            if not variant or len(variant) < 5:
                return False

            if variant.lower() == original.lower():
                return False

            if len(variant) > len(original) * 3:
                return False

            original_words = set(original.lower().split())
            variant_words = set(variant.lower().split())
            overlap = len(original_words & variant_words)
            total_original = len(original_words)

            if overlap / total_original > 0.8 and len(variant_words) <= len(
                original_words
            ):
                return False

            return True

        except Exception as e:
            logger.error(f"验证变体查询失败: {e}")
            return False

    def generate_multi_angle_queries(self, query: str) -> List[str]:
        """生成多角度查询（快速版本）"""
        try:
            if not self.initialized:
                return [query]

            system_prompt = """请为给定查询生成3个不同角度的变体查询。每个变体应该：
1. 从不同角度表达相同的信息需求
2. 使用不同的关键词和表达方式
3. 保持与原查询的高相关性

请按以下格式输出：
1. [第一个变体]
2. [第二个变体]
3. [第三个变体]"""

            user_prompt = f"原始查询：{query}"

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]

            response = self.llm.invoke(messages)
            result_text = response.content.strip()

            variants = []
            for line in result_text.split("\n"):
                line = line.strip()
                if line and (
                    line.startswith(("1.", "2.", "3.")) or line.startswith("-")
                ):
                    variant = line.split(".", 1)[-1].strip()
                    if variant.startswith("[") and variant.endswith("]"):
                        variant = variant[1:-1]
                    if variant and variant != query:
                        variants.append(variant)

            logger.info(f"生成多角度查询: {len(variants)} 个变体")
            return variants[:3]

        except Exception as e:
            logger.error(f"生成多角度查询失败: {e}")
            return []


# 全局实例
query_expander = QueryExpander()
