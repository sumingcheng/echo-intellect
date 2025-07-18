from fastapi import APIRouter

from app.api.query_routes import router as query_router
from app.api.health_routes import router as health_router
from app.api.import_endpoints import router as import_router

# 创建主路由器
router = APIRouter()

# 所有子路由列表
sub_routers = [
    query_router,
    health_router,
    import_router,
]

# 循环注册所有子路由
for sub_router in sub_routers:
    router.include_router(sub_router)
