"""models API 纯逻辑单测：过滤、分组、排序 — 不依赖网络。"""
from app.api.v1.models import _is_chat_model, _model_group, _group_sort_key


# ── 过滤 ──

class TestIsChatModel:
    def test_gpt_models_pass(self):
        for m in ["gpt-4o", "gpt-4o-mini", "gpt-5.5-pro", "gpt-3.5-turbo-0125"]:
            assert _is_chat_model(m), f"{m} should be chat model"

    def test_o_series_pass(self):
        for m in ["o1", "o3-mini", "o4-mini-2025-04-16"]:
            assert _is_chat_model(m), f"{m} should be chat model"

    def test_embedding_excluded(self):
        assert not _is_chat_model("text-embedding-3-small")
        assert not _is_chat_model("text-embedding-ada-002")

    def test_tts_excluded(self):
        assert not _is_chat_model("tts-1")
        assert not _is_chat_model("tts-1-hd")

    def test_whisper_excluded(self):
        assert not _is_chat_model("whisper-1")

    def test_image_excluded(self):
        assert not _is_chat_model("dall-e-3")
        assert not _is_chat_model("gpt-image-1")
        assert not _is_chat_model("chatgpt-image")

    def test_other_excluded(self):
        assert not _is_chat_model("sora-2026")
        assert not _is_chat_model("omni-moderation-latest")
        assert not _is_chat_model("babbage-002")
        assert not _is_chat_model("davinci-002")


# ── 分组 ──

class TestModelGroup:
    def test_gpt35(self):
        assert _model_group("gpt-3.5-turbo") == "gpt-3.5-turbo"
        assert _model_group("gpt-3.5-turbo-0125") == "gpt-3.5-turbo"
        assert _model_group("gpt-3.5-turbo-instruct") == "gpt-3.5-turbo"

    def test_gpt4(self):
        assert _model_group("gpt-4") == "gpt-4"
        assert _model_group("gpt-4-turbo") == "gpt-4"
        assert _model_group("gpt-4-0613") == "gpt-4"

    def test_gpt4o(self):
        assert _model_group("gpt-4o") == "gpt-4o"
        assert _model_group("gpt-4o-mini") == "gpt-4o"
        assert _model_group("gpt-4o-mini-2024-07-18") == "gpt-4o"
        assert _model_group("gpt-4o-audio-preview") == "gpt-4o"

    def test_gpt41(self):
        assert _model_group("gpt-4.1") == "gpt-4.1"
        assert _model_group("gpt-4.1-mini") == "gpt-4.1"
        assert _model_group("gpt-4.1-nano-2025-04-14") == "gpt-4.1"

    def test_gpt5x(self):
        assert _model_group("gpt-5") == "gpt-5"
        assert _model_group("gpt-5-codex") == "gpt-5"
        assert _model_group("gpt-5.4-pro-2026-03-05") == "gpt-5.4"
        assert _model_group("gpt-5.5") == "gpt-5.5"
        assert _model_group("gpt-5.5-pro") == "gpt-5.5"

    def test_o_series(self):
        assert _model_group("o1") == "o1"
        assert _model_group("o1-pro-2025-03-19") == "o1"
        assert _model_group("o3-mini") == "o3"
        assert _model_group("o4-mini-2025-04-16") == "o4"

    def test_unknown_passthrough(self):
        assert _model_group("some-custom-model") == "some-custom-model"


# ── 排序 ──

class TestGroupSortKey:
    def test_known_groups_ordered(self):
        keys = ["gpt-3.5-turbo", "o4", "gpt-5.5", "gpt-4o", "o1"]
        sorted_keys = sorted(keys, key=_group_sort_key)
        assert sorted_keys == ["o4", "o1", "gpt-5.5", "gpt-4o", "gpt-3.5-turbo"]

    def test_unknown_group_goes_last(self):
        keys = ["o4", "unknown-model", "gpt-4"]
        sorted_keys = sorted(keys, key=_group_sort_key)
        assert sorted_keys[-1] == "unknown-model"
