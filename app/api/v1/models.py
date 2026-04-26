import logging
import re
import time

from fastapi import APIRouter
from openai import AsyncOpenAI

from config.settings import get_llm_providers, get_default_llm, LLMProvider

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/models", tags=["模型"])

# ── 过滤：排除明确非 chat 的模型 ──

_EXCLUDE_PREFIXES = (
    "text-embedding", "tts-", "whisper-", "dall-e", "gpt-image",
    "sora-", "omni-moderation", "gpt-audio", "gpt-realtime",
    "babbage-", "davinci-", "chatgpt-image",
)


def _is_chat_model(model_id: str) -> bool:
    return not any(model_id.startswith(p) for p in _EXCLUDE_PREFIXES)


# ── 分组 ──

_GROUP_ORDER = [
    "o4", "o3", "o1",
    "gpt-5.5", "gpt-5.4", "gpt-5.3", "gpt-5.2", "gpt-5.1", "gpt-5",
    "gpt-4o", "gpt-4.1", "gpt-4", "gpt-3.5-turbo",
]

_GROUP_LABELS = {
    "gpt-3.5-turbo": "GPT-3.5 Turbo",
    "gpt-4": "GPT-4", "gpt-4.1": "GPT-4.1", "gpt-4o": "GPT-4o",
    "gpt-5": "GPT-5", "gpt-5.1": "GPT-5.1", "gpt-5.2": "GPT-5.2",
    "gpt-5.3": "GPT-5.3", "gpt-5.4": "GPT-5.4", "gpt-5.5": "GPT-5.5",
    "o1": "O1", "o3": "O3", "o4": "O4",
}


def _model_group(model_id: str) -> str:
    """提取模型族：gpt-5.4-pro-2026-03-05 → gpt-5.4"""
    if model_id.startswith("gpt-3.5"):
        return "gpt-3.5-turbo"
    m = re.match(r"^(gpt-\d+o)", model_id)
    if m:
        return m.group(1)
    m = re.match(r"^(gpt-\d+\.\d+)", model_id)
    if m:
        return m.group(1)
    m = re.match(r"^(gpt-\d+)", model_id)
    if m:
        return m.group(1)
    m = re.match(r"^(o\d+)", model_id)
    if m:
        return m.group(1)
    return model_id


def _group_sort_key(key: str) -> int:
    try:
        return _GROUP_ORDER.index(key)
    except ValueError:
        return len(_GROUP_ORDER)


# ── 缓存 ──

_cache_models: list[dict] = []
_cache_ts: float = 0
_CACHE_TTL = 300

_model_provider_map: dict[str, str] = {}


def get_provider_for_model(model_id: str) -> str | None:
    """根据模型 ID 查找所属 provider。"""
    return _model_provider_map.get(model_id)


async def _fetch_provider_models(provider: LLMProvider) -> list[dict]:
    """从单个 provider 拉取并过滤 chat 模型。"""
    try:
        client = AsyncOpenAI(api_key=provider.api_key, base_url=provider.api_base)
        resp = await client.models.list()
        models = []
        for m in resp.data:
            if _is_chat_model(m.id):
                models.append({"id": m.id, "provider": provider.id})
                _model_provider_map[m.id] = provider.id
        return models
    except Exception as e:
        logger.error("获取 %s 模型列表失败: %s", provider.id, e)
        return []


async def _get_all_models() -> list[dict]:
    """汇总所有 provider 的模型列表，带缓存。"""
    global _cache_models, _cache_ts

    now = time.time()
    if _cache_models and now - _cache_ts < _CACHE_TTL:
        return _cache_models

    result: list[dict] = []
    for provider in get_llm_providers():
        result.extend(await _fetch_provider_models(provider))

    result.sort(key=lambda m: m["id"])
    _cache_models = result
    _cache_ts = time.time()
    return result


@router.get("", summary="获取可用模型列表（分组）")
async def list_models():
    models = await _get_all_models()

    groups_map: dict[str, list[str]] = {}
    for m in models:
        key = _model_group(m["id"])
        groups_map.setdefault(key, []).append(m["id"])

    sorted_keys = sorted(groups_map.keys(), key=_group_sort_key)
    groups = [
        {
            "key": key,
            "label": _GROUP_LABELS.get(key, key),
            "models": groups_map[key],
        }
        for key in sorted_keys
    ]

    return {"groups": groups, "default": get_default_llm()}
