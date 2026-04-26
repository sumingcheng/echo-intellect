from fastapi import APIRouter

from app.api.v1.chat import router as chat_router
from app.api.v1.health import router as health_router
from app.api.v1.ingestion import router as import_router
from app.api.v1.models import router as models_router
from app.api.v1.query import router as query_router
from app.api.v1.speech import router as speech_router

router = APIRouter(prefix="/api/v1")

for sub_router in (chat_router, query_router, health_router, import_router, speech_router, models_router):
    router.include_router(sub_router)
