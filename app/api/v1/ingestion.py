import logging
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile

from app.api.dependencies import get_container
from app.core.container import AppContainer
from app.ingestion.readers import SUPPORTED_EXTENSIONS

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/import", tags=["数据导入"])

# ── 内存任务追踪（轻量方案，重启丢失可接受） ──

_jobs: Dict[str, dict] = {}


def _create_job(file_name: str, file_size: int) -> dict:
    job = {
        "id": str(uuid.uuid4()),
        "file_name": file_name,
        "file_size": file_size,
        "status": "pending",
        "progress": 0,
        "data_created": 0,
        "vectors_created": 0,
        "error": None,
        "created_at": datetime.now().isoformat(),
        "finished_at": None,
    }
    _jobs[job["id"]] = job
    return job


# ── 上传并导入 ──

@router.post("/upload", summary="上传文件到知识库")
async def upload_file(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    container: AppContainer = Depends(get_container),
) -> dict:
    """接收用户上传的文件，后台处理入库。"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名为空")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的格式 {suffix}，仅支持: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件内容为空")

    # 落盘临时文件
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(content)
    tmp.close()

    job = _create_job(file.filename, len(content))
    logger.info("文件上传: %s (%d bytes), job=%s", file.filename, len(content), job["id"])

    background_tasks.add_task(
        _process_upload,
        container.import_service,
        Path(tmp.name),
        file.filename,
        job["id"],
    )

    return {"job_id": job["id"], "file_name": file.filename, "status": "pending"}


async def _process_upload(
    import_service,
    tmp_path: Path,
    original_name: str,
    job_id: str,
):
    """后台执行文件导入。"""
    job = _jobs[job_id]
    job["status"] = "processing"
    job["progress"] = 10

    try:
        # 用原始文件名创建一个带正确名称的软链接，让 collection.name 正确
        named_path = tmp_path.parent / original_name
        if not named_path.exists():
            named_path.symlink_to(tmp_path)

        result = import_service.import_file(named_path)

        if result["success"]:
            job["status"] = "completed"
            job["progress"] = 100
            job["data_created"] = result["data_created"]
            job["vectors_created"] = result["vectors_created"]
            logger.info("文件导入完成: %s, chunks=%d, vectors=%d",
                        original_name, result["data_created"], result["vectors_created"])
        else:
            job["status"] = "failed"
            job["error"] = result.get("error", "未知错误")
            logger.error("文件导入失败: %s, error=%s", original_name, job["error"])

    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)
        logger.error("文件处理异常: %s, error=%s", original_name, e)

    finally:
        job["finished_at"] = datetime.now().isoformat()
        # 清理临时文件
        try:
            tmp_path.unlink(missing_ok=True)
            named_path = tmp_path.parent / original_name
            if named_path.is_symlink():
                named_path.unlink()
        except Exception:
            pass


# ── 任务状态 ──

@router.get("/jobs", summary="获取所有导入任务状态")
async def list_jobs() -> dict:
    """返回所有文件导入任务的状态列表。"""
    jobs = sorted(_jobs.values(), key=lambda j: j["created_at"], reverse=True)
    return {"jobs": jobs}


@router.get("/jobs/{job_id}", summary="获取单个任务状态")
async def get_job(job_id: str) -> dict:
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    return job


# ── 知识库文件列表（持久化） ──

@router.get("/files", summary="获取知识库中的所有文件")
async def list_files(
    container: AppContainer = Depends(get_container),
) -> dict:
    """从 MongoDB 读取已入库的文件列表，不受服务重启影响。"""
    try:
        collections = container.import_service.mongo_store.get_all_collections()
        files = [
            {
                "id": c.id,
                "name": c.name,
                "file_type": c.file_type or "",
                "data_count": c.data_count,
                "total_tokens": c.total_tokens,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in collections
        ]
        return {"files": files}
    except Exception as e:
        logger.error("获取知识库文件列表失败: %s", e)
        return {"files": []}


# ── 支持格式 ──

@router.get("/formats", summary="获取支持的文件格式")
async def get_formats() -> dict:
    return {"formats": sorted(SUPPORTED_EXTENSIONS)}
