import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import app_config
from config.log import setup_logger
from app.api.routes import router


def create_app() -> FastAPI:
    """创建FastAPI应用实例"""
    # 初始化日志
    logger = setup_logger(
        name="echo-intellect",
        log_file="logs/app.log" if not app_config.is_production else None,
        level=getattr(__import__('logging'), app_config.log_level),
    )
    
    logger.info("🚀 Echo Intellect RAG 系统启动中...")
    
    # 创建FastAPI应用
    app = FastAPI(
        title="Echo Intellect",
        description="智能问答系统（RAG）",
        version="1.0.0",
    )
    
    # 添加CORS中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 注册路由
    app.include_router(router)
    
    return app


# 创建应用实例
app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=app_config.app_port,
        reload=app_config.debug,
    )
