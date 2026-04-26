from dataclasses import dataclass, field

from app.ingestion.service import DataImportService
from app.rag.service import RetrievalChain
from app.rag.service import retrieval_chain as default_retrieval_chain


@dataclass
class AppContainer:
    """集中管理运行时依赖，避免路由层到处 import 全局对象。"""

    retrieval_chain: RetrievalChain = field(default_factory=lambda: default_retrieval_chain)
    import_service: DataImportService = field(default_factory=DataImportService)


def create_container() -> AppContainer:
    """创建应用依赖容器。"""
    return AppContainer()
