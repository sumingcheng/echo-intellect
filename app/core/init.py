import logging

from app.core.container import AppContainer

logger = logging.getLogger()


async def initialize_system(container: AppContainer) -> bool:
    """初始化系统"""
    try:
        logger.info("开始初始化RAG系统...")

        # 初始化检索链
        if not container.retrieval_chain.initialized:
            container.retrieval_chain.initialize()

        # 初始化数据导入服务
        success = await container.import_service.initialize()
        if not success:
            logger.error("导入服务初始化失败")
        else:
            logger.info("导入服务初始化成功")

        logger.info("RAG系统初始化完成")
        return True

    except Exception as e:
        logger.error(f"系统初始化失败: {e}")
        return False 