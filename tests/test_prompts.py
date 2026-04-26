"""prompts 单测：模板变量替换、上下文格式化 — 不依赖外部服务。"""
from app.rag.prompts import RAGPromptTemplates
from app.models.data_models import RerankResult


def _make_result(content: str, score: float = 0.8, source: str = "") -> RerankResult:
    """快速构造 RerankResult。"""
    return RerankResult(
        data_id="test-data-id",
        collection_id="test-collection-id",
        content=content,
        original_score=score,
        rerank_score=score,
        final_score=score,
        metadata={"source": source} if source else {},
    )


class TestTemplateVariableSubstitution:
    """之前踩过 {question} 字面量未被替换的坑，必须回归。"""

    def setup_method(self):
        self.prompts = RAGPromptTemplates()

    def test_basic_template_substitutes_question(self):
        result = self.prompts.create_rag_prompt(
            question="你好，你可以做什么？",
            context_results=[],
            template_name="basic_rag",
        )
        assert "{question}" not in result["human"]
        assert "你好" in result["human"]

    def test_basic_template_substitutes_context(self):
        results = [_make_result("Python 是一门语言", source="wiki")]
        result = self.prompts.create_rag_prompt(
            question="什么是 Python？",
            context_results=results,
            template_name="basic_rag",
        )
        assert "{context_section}" not in result["system"]
        assert "Python 是一门语言" in result["system"]

    def test_conversational_template_substitutes_all(self):
        result = self.prompts.create_rag_prompt(
            question="继续说",
            context_results=[],
            template_name="conversational_rag",
            conversation_history="用户: 你好\n助手: 你好呀",
        )
        assert "{question}" not in result["human"]
        assert "{conversation_history}" not in result["system"]
        assert "你好呀" in result["system"]

    def test_empty_context_no_knowledge_section(self):
        result = self.prompts.create_rag_prompt(
            question="今天天气怎么样？",
            context_results=[],
        )
        assert "从知识库检索" not in result["system"]


class TestFormatContext:
    def setup_method(self):
        self.prompts = RAGPromptTemplates()

    def test_empty_results(self):
        assert self.prompts.format_context([]) == ""

    def test_single_result(self):
        ctx = self.prompts.format_context([_make_result("段落A", 0.9, "doc.pdf")])
        assert "段落A" in ctx
        assert "doc.pdf" in ctx
        assert "0.900" in ctx

    def test_multiple_results_numbered(self):
        results = [_make_result(f"段落{i}") for i in range(3)]
        ctx = self.prompts.format_context(results)
        assert '<source id="1"' in ctx
        assert '<source id="3"' in ctx


class TestGetTemplate:
    def setup_method(self):
        self.prompts = RAGPromptTemplates()

    def test_known_template(self):
        t = self.prompts.get_template("basic_rag")
        assert t is not None

    def test_unknown_falls_back(self):
        t = self.prompts.get_template("nonexistent")
        assert t is self.prompts.templates["basic_rag"]

    def test_available_templates(self):
        names = self.prompts.get_available_templates()
        assert "basic_rag" in names
        assert "conversational_rag" in names
