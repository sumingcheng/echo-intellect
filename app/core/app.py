from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from config.settings import app_config
from config.log import setup_logger
from app.core.init import initialize_system


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    await initialize_system()
    yield
    # 关闭时执行（如果需要的话）


def create_app() -> FastAPI:
    """创建FastAPI应用实例"""
    # 初始化日志
    logger = setup_logger(
        name="echo-intellect",
        log_file="logs/app.log" if not app_config.is_production else None,
        level=getattr(__import__('logging'), app_config.log_level),
    )
    
    logger.info("Echo Intellect RAG 系统启动中...")
    
    # 创建FastAPI应用
    app = FastAPI(
        title="Echo Intellect",
        description="智能问答系统（RAG）",
        version="1.0.0",
        lifespan=lifespan,
    )
    
    # 添加CORS中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    return app 