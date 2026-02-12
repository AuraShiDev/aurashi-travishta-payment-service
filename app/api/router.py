from fastapi import APIRouter
from app.api.health.routes import health_router
from app.api.payments.routes import payments_router
api_router = APIRouter()

api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(payments_router, prefix="/payments", tags=["payments"])
