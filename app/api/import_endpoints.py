from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Optional
import logging

from app.core.init import import_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/import", tags=["数据导入"])


@router.post("/start", summary="启动数据导入")
async def start_import(
    background_tasks: BackgroundTasks,
    data_dir: str = "./data",
    dataset_name: str = "文档知识库",
) -> Dict:
    """启动数据导入任务"""
    try:
        logger.info(f"启动数据导入任务: {data_dir} -> {dataset_name}")

        background_tasks.add_task(_execute_import, data_dir, dataset_name)

        return {
            "success": True,
            "message": "数据导入任务已启动",
            "data_dir": data_dir,
            "dataset_name": dataset_name,
        }

    except Exception as e:
        logger.error(f"启动导入任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动导入任务失败: {e}")


@router.post("/import-sync", summary="同步执行数据导入")
async def import_sync(
    data_dir: str = "./data", dataset_name: str = "文档知识库"
) -> Dict:
    """同步执行数据导入（等待完成）"""
    try:
        logger.info(f"同步执行数据导入: {data_dir} -> {dataset_name}")

        result = await import_service.import_directory(data_dir, dataset_name)

        if result["success"]:
            logger.info("数据导入完成")
        else:
            logger.error(f"数据导入失败: {result.get('error')}")

        return result

    except Exception as e:
        logger.error(f"数据导入失败: {e}")
        raise HTTPException(status_code=500, detail=f"数据导入失败: {e}")


@router.get("/status", summary="获取导入状态")
async def get_import_status() -> Dict:
    """获取数据导入状态"""
    try:
        return {
            "service_initialized": import_service.mongo_store.client is not None,
            "milvus_connected": import_service.milvus_store.connected,
            "embedding_available": import_service.processor is not None,
        }
    except Exception as e:
        logger.error(f"获取导入状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取状态失败: {e}")


async def _execute_import(data_dir: str, dataset_name: str):
    """后台执行导入任务"""
    try:
        logger.info(f"后台导入任务开始: {data_dir}")

        result = await import_service.import_directory(data_dir, dataset_name)

        if result["success"]:
            logger.info(
                f"后台导入任务完成: 处理{result['files_processed']}个文件, "
                f"创建{result['data_created']}个数据条目, "
                f"生成{result['vectors_created']}个向量"
            )
        else:
            logger.error(f"后台导入任务失败: {result.get('error')}")

    except Exception as e:
        logger.error(f"后台导入任务异常: {e}")
