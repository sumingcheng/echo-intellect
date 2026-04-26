"""settings 单测：YAML 加载、provider 解析、校验器。"""
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from config.settings import (
    _load_yaml_config,
    _set_env_defaults,
    AppSettings,
    LLMProvider,
)


class TestLoadYamlConfig:
    def test_missing_file_returns_empty(self, tmp_path):
        assert _load_yaml_config(tmp_path / "nope.yaml") == {}

    def test_valid_yaml(self, tmp_path):
        f = tmp_path / "test.yaml"
        f.write_text("app_port: 9000\ndebug: true\n")
        cfg = _load_yaml_config(f)
        assert cfg["app_port"] == 9000
        assert cfg["debug"] is True

    def test_non_dict_raises(self, tmp_path):
        f = tmp_path / "bad.yaml"
        f.write_text("- item1\n- item2\n")
        import pytest
        with pytest.raises(ValueError, match="YAML对象"):
            _load_yaml_config(f)


class TestSetEnvDefaults:
    def test_scalar_written(self):
        env_key = "_TEST_SET_ENV_SCALAR"
        os.environ.pop(env_key, None)
        _set_env_defaults({"_test_set_env_scalar": "hello"})
        assert os.environ.get(env_key) == "hello"
        os.environ.pop(env_key, None)

    def test_bool_converted(self):
        env_key = "_TEST_SET_ENV_BOOL"
        os.environ.pop(env_key, None)
        _set_env_defaults({"_test_set_env_bool": True})
        assert os.environ.get(env_key) == "true"
        os.environ.pop(env_key, None)

    def test_dict_skipped(self):
        _set_env_defaults({"_test_dict_skip": {"nested": 1}})
        assert "_TEST_DICT_SKIP" not in os.environ

    def test_none_skipped(self):
        _set_env_defaults({"_test_none_skip": None})
        assert "_TEST_NONE_SKIP" not in os.environ

    def test_existing_env_not_overwritten(self):
        key = "_TEST_NO_OVERWRITE"
        os.environ[key] = "original"
        _set_env_defaults({"_test_no_overwrite": "new_val"})
        assert os.environ[key] == "original"
        os.environ.pop(key, None)


class TestAppSettingsValidators:
    def test_log_level_uppercased(self):
        s = AppSettings(log_level="debug")
        assert s.log_level == "DEBUG"

    def test_invalid_log_level_rejected(self):
        import pytest
        with pytest.raises(Exception):
            AppSettings(log_level="TRACE")

    def test_production_normalized(self):
        s = AppSettings(app_env="production")
        assert s.app_env == "prod"
        assert s.is_production

    def test_relevance_threshold_range(self):
        import pytest
        with pytest.raises(Exception):
            AppSettings(relevance_threshold=1.5)
        with pytest.raises(Exception):
            AppSettings(relevance_threshold=-0.1)


class TestSensitiveMask:
    def test_short_value(self):
        assert AppSettings._mask_sensitive_value("ab") == "****"

    def test_normal_value(self):
        masked = AppSettings._mask_sensitive_value("sk-1234567890abcdef")
        assert masked.endswith("cdef")
        assert "1234567890" not in masked


class TestLLMProvider:
    def test_valid_provider(self):
        p = LLMProvider(
            id="openai",
            label="OpenAI",
            api_base="https://api.openai.com/v1",
            api_key="sk-test",
        )
        assert p.id == "openai"
