import logging
from app.chains.retrieval_chain import retrieval_chain
from app.services.data_import_service import DataImportService

logger = logging.getLogger()

# 全局导入服务实例
import_service = DataImportService()


async def initialize_system() -> bool:
    """初始化系统"""
    try:
        logger.info("开始初始化RAG系统...")

        # 初始化检索链
        if not retrieval_chain.initialized:
            retrieval_chain.initialize()

        # 初始化数据导入服务
        success = await import_service.initialize()
        if not success:
            logger.error("导入服务初始化失败")
        else:
            logger.info("导入服务初始化成功")

        logger.info("RAG系统初始化完成")
        return True

    except Exception as e:
        logger.error(f"系统初始化失败: {e}")
        return False 