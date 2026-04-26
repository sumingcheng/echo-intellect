import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import fitz

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf"}


@dataclass(frozen=True)
class SourceDocument:
    """导入入口读到的原始文档。"""
    path: Path
    content: str


class FileReader:
    """读取本地文件，支持 txt / md / pdf。"""

    def __init__(self, encodings: Iterable[str] | None = None):
        self.encodings = list(
            encodings or ["utf-8", "gbk", "gb2312", "utf-16", "big5"]
        )

    def read_file(self, file_path: Path) -> str | None:
        """根据后缀分发到对应解析器。"""
        suffix = file_path.suffix.lower()
        if suffix == ".pdf":
            return self._read_pdf(file_path)
        if suffix in (".txt", ".md"):
            return self._read_text(file_path)
        logger.warning("不支持的文件格式: %s", suffix)
        return None

    def read_directory(self, data_dir: str) -> list[SourceDocument]:
        """读取目录下所有支持格式的文件。"""
        documents = []
        for ext in sorted(SUPPORTED_EXTENSIONS):
            for file_path in sorted(Path(data_dir).glob(f"*{ext}")):
                content = self.read_file(file_path)
                if content:
                    documents.append(SourceDocument(path=file_path, content=content))
        return documents

    def _read_text(self, file_path: Path) -> str | None:
        """按常见编码读取文本文件。"""
        for encoding in self.encodings:
            try:
                content = file_path.read_text(encoding=encoding)
                logger.info("使用 %s 编码读取: %s", encoding, file_path.name)
                return content
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logger.error("读取文件失败: %s, error=%s", file_path, e)
                return None
        logger.error("所有编码均失败: %s", file_path)
        return None

    def _read_pdf(self, file_path: Path) -> str | None:
        """用 PyMuPDF 提取 PDF 全文。"""
        try:
            doc = fitz.open(str(file_path))
            pages = [page.get_text() for page in doc]
            doc.close()
            text = "\n\n".join(pages).strip()
            if not text:
                logger.warning("PDF 无可提取文本: %s", file_path.name)
                return None
            logger.info("PDF 读取完成: %s (%d 页)", file_path.name, len(pages))
            return text
        except Exception as e:
            logger.error("PDF 读取失败: %s, error=%s", file_path, e)
            return None
