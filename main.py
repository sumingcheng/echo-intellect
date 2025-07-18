import uvicorn

from config.settings import app_config
from app.core.app import create_app
from app.api.routes import router

# 创建应用实例
app = create_app()

# 注册路由
app.include_router(router)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=app_config.app_port,
        reload=app_config.debug,
    )
