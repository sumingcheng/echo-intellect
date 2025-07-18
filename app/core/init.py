import logging
from app.chains.retrieval_chain import retrieval_chain

logger = logging.getLogger()


async def initialize_system() -> bool:
    """初始化系统"""
    try:
        logger.info("开始初始化RAG系统...")

        if not retrieval_chain.initialized:
            retrieval_chain.initialize()

        logger.info("RAG系统初始化完成")
        return True

    except Exception as e:
        logger.error(f"系统初始化失败: {e}")
        return False 