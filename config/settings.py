import os
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from dotenv import load_dotenv
from typing import Literal

# 开发环境自动加载.env文件，生产环境使用系统环境变量
if os.getenv("ENVIRONMENT", "dev").lower() != "prod":
    load_dotenv()


class AppSettings(BaseSettings):
    # ==================== 应用基础配置 ====================
    app_env: str = Field(default="dev", env="APP_ENV", description="应用环境标识")
    app_port: int = Field(default=8000, env="APP_PORT", description="应用服务端口")
    debug: bool = Field(default=True, env="DEBUG", description="调试模式开关")
    log_level: str = Field(
        default="INFO",
        env="LOG_LEVEL",
        description="日志级别：DEBUG | INFO | WARNING | ERROR",
    )

    # ==================== 向量数据库配置 ====================
    milvus_uri: str = Field(
        default="http://localhost:19530",
        env="MILVUS_URI",
        description="Milvus向量数据库连接地址",
    )
    milvus_collection: str = Field(
        default="rag_knowledge", env="MILVUS_COLLECTION", description="Milvus集合名称"
    )

    # ==================== MongoDB配置 ====================
    mongodb_uri: str = Field(
        default="mongodb://raguser:ragpassword@localhost:27017/rag_db?authSource=admin",
        env="MONGODB_URI",
        description="MongoDB连接字符串",
    )

    # ==================== Redis缓存配置 ====================
    redis_uri: str = Field(
        default="redis://:rag123456@localhost:6379/0",
        env="REDIS_URI",
        description="Redis连接URI",
    )

    # ==================== 全文检索配置 ====================
    meilisearch_uri: str = Field(
        default="http://localhost:7700",
        env="MEILISEARCH_URI",
        description="Meilisearch服务地址",
    )
    meilisearch_api_key: str = Field(
        default="rag-meili-key-123456",
        env="MEILISEARCH_API_KEY",
        description="Meilisearch API密钥",
    )
    meilisearch_index: str = Field(
        default="rag_documents",
        env="MEILISEARCH_INDEX",
        description="Meilisearch索引名称",
    )

    # ==================== AI服务端点配置 ====================
    embedding_service: str = Field(
        default="http://localhost:11434",
        env="EMBEDDING_SERVICE",
        description="嵌入模型服务端点（Ollama）",
    )
    rerank_service: str = Field(
        default="http://localhost:11434",
        env="RERANK_SERVICE",
        description="重排模型服务端点（Ollama）",
    )

    # ==================== 检索配置 ====================
    max_tokens_limit: int = Field(
        default=4000, env="MAX_TOKENS_LIMIT", description="最大token数量限制"
    )
    relevance_threshold: float = Field(
        default=0.6, env="RELEVANCE_THRESHOLD", description="相关性阈值（0-1之间）"
    )

    # ==================== LLM配置 ====================
    llm_model: str = Field(
        default="deepseek", env="LLM_MODEL", description="LLM模型名称"
    )
    llm_api_base: str = Field(
        default="https://api.deepseek.com",
        env="LLM_API_BASE",
        description="LLM API基础URL",
    )
    llm_api_key: str = Field(
        default="your-api-key-here", env="LLM_API_KEY", description="LLM API密钥"
    )

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
        return self.environment == "production"

    def __str__(self) -> str:
        """格式化输出配置信息，自动脱敏敏感数据"""
        sensitive_fields = {
            "mongodb_uri",  # MongoDB连接字符串包含密码
            "redis_uri",  # Redis URI包含密码
            "meilisearch_api_key",  # Meilisearch API密钥
            "llm_api_key",  # LLM API密钥
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
