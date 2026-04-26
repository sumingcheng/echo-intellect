import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent

# 合并后的原始YAML，供 get_llm_channels 等读取复杂结构
_raw_yaml: dict[str, Any] = {}


def _load_yaml_config(path: Path) -> dict[str, Any]:
    """读取YAML配置，文件不存在就返回空配置。"""
    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}

    if not isinstance(data, dict):
        raise ValueError(f"配置文件必须是YAML对象: {path}")

    return data


def _set_env_defaults(config: dict[str, Any]) -> None:
    """YAML标量值写入env默认值，复杂类型（list/dict）跳过。"""
    for key, value in config.items():
        if value is None or isinstance(value, (list, dict)):
            continue

        env_key = key.upper()
        if isinstance(value, bool):
            env_value = "true" if value else "false"
        else:
            env_value = str(value)

        os.environ.setdefault(env_key, env_value)


def _load_runtime_config() -> None:
    """加载后端运行配置：环境变量/.env > config.local.yaml > config.yaml > 代码默认值。"""
    global _raw_yaml
    app_env = os.getenv("APP_ENV", "dev").lower()
    if app_env not in {"prod", "production"} and (ROOT_DIR / ".env").exists():
        load_dotenv(ROOT_DIR / ".env")

    yaml_config = _load_yaml_config(ROOT_DIR / "config.yaml")
    yaml_config.update(_load_yaml_config(ROOT_DIR / "config.local.yaml"))
    _raw_yaml = yaml_config
    _set_env_defaults(yaml_config)


_load_runtime_config()


# ── LLM Provider 配置 ──

class LLMProvider(BaseModel):
    """LLM 供应商配置（OpenAI / DeepSeek 等）"""
    id: str = Field(description="供应商标识，如 openai / deepseek")
    label: str = Field(description="前端显示名称，如 OpenAI")
    api_base: str = Field(description="API 端点")
    api_key: str = Field(description="API 密钥")


def get_llm_providers() -> list[LLMProvider]:
    """从 YAML 获取所有已配置的 LLM 供应商。"""
    raw = _raw_yaml.get("llm_providers", [])
    if not isinstance(raw, list):
        return []
    return [LLMProvider(**p) for p in raw if isinstance(p, dict)]


def get_default_llm() -> str:
    """返回默认模型 ID。"""
    return str(_raw_yaml.get("default_llm", ""))


class AppSettings(BaseSettings):
    # 应用基础配置
    app_env: str = Field(default="dev", env="APP_ENV", description="应用环境标识")
    app_port: int = Field(default=8000, env="APP_PORT", description="应用服务端口")
    debug: bool = Field(default=True, env="DEBUG", description="调试模式开关")
    log_level: str = Field(
        default="INFO",
        env="LOG_LEVEL",
        description="日志级别：DEBUG | INFO | WARNING | ERROR",
    )

    # 向量数据库配置
    qdrant_url: str = Field(
        default="http://127.0.0.1:6333",
        env="QDRANT_URL",
        description="Qdrant向量数据库连接地址",
    )
    qdrant_api_key: str = Field(
        default="", env="QDRANT_API_KEY", description="Qdrant API密钥"
    )
    qdrant_collection: str = Field(
        default="rag_knowledge",
        env="QDRANT_COLLECTION",
        description="Qdrant集合名称",
    )

    # MongoDB配置
    mongodb_uri: str = Field(
        default="mongodb://raguser:ragpassword@127.0.0.1:27017/rag_db?authSource=admin",
        env="MONGODB_URI",
        description="MongoDB连接字符串",
    )

    # Redis缓存配置
    redis_uri: str = Field(
        default="redis://:rag123456@127.0.0.1:6379/0",
        env="REDIS_URI",
        description="Redis连接URI",
    )

    # OpenAI Embedding配置
    openai_api_key: str = Field(
        default="", env="OPENAI_API_KEY", description="OpenAI API密钥"
    )
    openai_embedding_model: str = Field(
        default="text-embedding-3-small",
        env="OPENAI_EMBEDDING_MODEL",
        description="OpenAI嵌入模型名称",
    )
    openai_embedding_dimension: int = Field(
        default=1536,
        env="OPENAI_EMBEDDING_DIMENSION",
        description="OpenAI嵌入向量维度",
    )
    openai_transcription_model: str = Field(
        default="whisper-1",
        env="OPENAI_TRANSCRIPTION_MODEL",
        description="OpenAI语音转文字模型名称",
    )
    openai_tts_model: str = Field(
        default="tts-1",
        env="OPENAI_TTS_MODEL",
        description="OpenAI文字转语音模型名称",
    )
    openai_tts_voice: str = Field(
        default="alloy",
        env="OPENAI_TTS_VOICE",
        description="OpenAI文字转语音默认声音",
    )
    openai_tts_format: str = Field(
        default="mp3",
        env="OPENAI_TTS_FORMAT",
        description="OpenAI文字转语音默认音频格式",
    )

    # 重排服务配置（默认不启用）
    rerank_service: str = Field(
        default="http://127.0.0.1:6006",
        env="RERANK_SERVICE",
        description="重排模型服务端点（BGE Reranker）",
    )
    rerank_endpoint: str = Field(
        default="/v1/rerank", env="RERANK_ENDPOINT", description="重排服务API端点"
    )
    rerank_access_token: str = Field(
        default="123456", env="RERANK_ACCESS_TOKEN", description="重排服务访问令牌"
    )

    # 检索配置
    max_tokens_limit: int = Field(
        default=4000, env="MAX_TOKENS_LIMIT", description="最大token数量限制"
    )
    relevance_threshold: float = Field(
        default=0.6, env="RELEVANCE_THRESHOLD", description="相关性阈值（0-1之间）"
    )

    # LLM渠道配置已迁移到 llm_channels（YAML list），通过 get_llm_channels() 获取

    class Config:
        """Pydantic配置类"""

        env_file = ".env"  # 环境变量文件路径
        env_file_encoding = "utf-8"  # 文件编码

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """验证日志级别的有效性"""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v.upper()

    @field_validator("app_env")
    @classmethod
    def normalize_app_env(cls, v: str) -> str:
        """统一生产环境写法，避免 prod/production 双标准。"""
        value = v.lower()
        if value == "production":
            return "prod"
        return value

    @field_validator("relevance_threshold")
    @classmethod
    def validate_relevance_threshold(cls, v: float) -> float:
        """验证相关性阈值范围"""
        if not 0.0 <= v <= 1.0:
            raise ValueError("relevance_threshold must be between 0.0 and 1.0")
        return v

    @property
    def is_production(self) -> bool:
        """判断是否为生产环境"""
        return self.app_env == "prod"

    def __str__(self) -> str:
        """格式化输出配置信息，自动脱敏敏感数据"""
        sensitive_fields = {
            "mongodb_uri",
            "redis_uri",
            "openai_api_key",
            "qdrant_api_key",
        }

        config_lines = []
        config_lines.append("=" * 50)
        config_lines.append("  应用配置信息")
        config_lines.append("=" * 50)

        for field_name, field_value in self.model_dump().items():
            # 敏感字段脱敏处理
            if field_name in sensitive_fields:
                display_value = self._mask_sensitive_value(str(field_value))
            else:
                display_value = field_value
            config_lines.append(f"{field_name:20}: {display_value}")

        config_lines.append("=" * 50)
        return "\n".join(config_lines)

    @staticmethod
    def _mask_sensitive_value(
        value: str, show_chars: int = 4, max_mask: int = 8
    ) -> str:
        """
        脱敏敏感信息
        Args:
            value: 原始值
            show_chars: 显示末尾字符数
            max_mask: 最大遮罩字符数
        """
        if not value or len(value) <= show_chars:
            return "****"
        mask_length = min(len(value) - show_chars, max_mask)
        return "*" * mask_length + value[-show_chars:]


app_config = AppSettings()
