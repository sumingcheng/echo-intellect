"""service 单测：模型兼容性检测逻辑 — 不依赖网络。"""
from app.rag.service import RetrievalChain


class TestIsReasoningModel:
    """推理模型只能用 temperature=1，检测必须准确。"""

    def test_o_series(self):
        for m in ["o1", "o1-mini", "o1-pro-2025-03-19", "o3-mini", "o4-mini-2025-04-16"]:
            assert RetrievalChain._is_reasoning_model(m), f"{m} should be reasoning"

    def test_gpt55(self):
        for m in ["gpt-5.5", "gpt-5.5-pro", "gpt-5.5-turbo-2026"]:
            assert RetrievalChain._is_reasoning_model(m), f"{m} should be reasoning"

    def test_gpt4_not_reasoning(self):
        for m in ["gpt-4o", "gpt-4o-mini", "gpt-4.1-mini", "gpt-4-turbo"]:
            assert not RetrievalChain._is_reasoning_model(m), f"{m} should NOT be reasoning"

    def test_gpt5_non55_not_reasoning(self):
        for m in ["gpt-5", "gpt-5.4-pro", "gpt-5.3-codex", "gpt-5.1"]:
            assert not RetrievalChain._is_reasoning_model(m), f"{m} should NOT be reasoning"


class TestNeedsCompletionTokens:
    """gpt-5.x 和 o 系列需要 max_completion_tokens 替代 max_tokens。"""

    def test_o_series(self):
        for m in ["o1", "o3-mini", "o4-mini-2025-04-16"]:
            assert RetrievalChain._needs_completion_tokens(m), f"{m} should need completion_tokens"

    def test_gpt5x(self):
        for m in ["gpt-5", "gpt-5.4-pro", "gpt-5.5"]:
            assert RetrievalChain._needs_completion_tokens(m), f"{m} should need completion_tokens"

    def test_gpt4_old_style(self):
        for m in ["gpt-4o", "gpt-4o-mini", "gpt-4.1-mini", "gpt-4-turbo", "gpt-3.5-turbo"]:
            assert not RetrievalChain._needs_completion_tokens(m), f"{m} should NOT need completion_tokens"
