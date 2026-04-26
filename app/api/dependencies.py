from fastapi import Request

from app.core.container import AppContainer


def get_container(request: Request) -> AppContainer:
    """从 FastAPI 应用状态获取运行时依赖。"""
    return request.app.state.container
