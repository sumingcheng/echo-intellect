import logging
from dataclasses import dataclass

import tiktoken

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TextChunk:
    """准备入库和向量化的文本块。"""

    content: str
    index: int
    tokens: int


class TokenAwareChunker:
    """按token预算切块，避免字符长度假装等于模型成本。"""

    def __init__(
        self,
        target_tokens: int = 700,
        max_tokens: int = 900,
        overlap_tokens: int = 80,
    ):
        self.target_tokens = target_tokens
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.encoding = tiktoken.get_encoding("cl100k_base")

    def split(self, content: str) -> list[TextChunk]:
        """将文本切成稳定的token块。"""
        paragraphs = [part.strip() for part in content.splitlines() if part.strip()]
        if not paragraphs:
            return []

        chunks: list[str] = []
        current_parts: list[str] = []
        current_tokens = 0

        for paragraph in paragraphs:
            paragraph_tokens = self.count_tokens(paragraph)
            if paragraph_tokens > self.max_tokens:
                self._flush_current(chunks, current_parts)
                current_parts = []
                current_tokens = 0
                chunks.extend(self._split_large_text(paragraph))
                continue

            if current_parts and current_tokens + paragraph_tokens > self.target_tokens:
                self._flush_current(chunks, current_parts)
                current_parts, current_tokens = self._build_overlap(current_parts)

            current_parts.append(paragraph)
            current_tokens += paragraph_tokens

        self._flush_current(chunks, current_parts)

        result = [
            TextChunk(content=chunk, index=index, tokens=self.count_tokens(chunk))
            for index, chunk in enumerate(chunks)
            if chunk
        ]
        logger.info("文档切分完成: %s chunks", len(result))
        return result

    def count_tokens(self, text: str) -> int:
        """计算文本token数。"""
        return len(self.encoding.encode(text))

    def _split_large_text(self, text: str) -> list[str]:
        """大段落按token硬切，保证不超过上限。"""
        token_ids = self.encoding.encode(text)
        chunks = []
        step = max(self.max_tokens - self.overlap_tokens, 1)

        for start in range(0, len(token_ids), step):
            part = self.encoding.decode(token_ids[start : start + self.max_tokens])
            if part.strip():
                chunks.append(part.strip())

        return chunks

    def _build_overlap(self, parts: list[str]) -> tuple[list[str], int]:
        """保留上一块尾部，减少上下文断裂。"""
        overlap_parts: list[str] = []
        overlap_tokens = 0

        for part in reversed(parts):
            part_tokens = self.count_tokens(part)
            if overlap_tokens + part_tokens > self.overlap_tokens:
                break

            overlap_parts.insert(0, part)
            overlap_tokens += part_tokens

        return overlap_parts, overlap_tokens

    @staticmethod
    def _flush_current(chunks: list[str], parts: list[str]) -> None:
        if parts:
            chunks.append("\n".join(parts).strip())
