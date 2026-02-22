from fastapi import APIRouter
from app.api.v1.endpoints import portfolios, risk

api_router = APIRouter()

api_router.include_router(
    portfolios.router,
    prefix="/portfolios",
    tags=["portfolios"]
)

api_router.include_router(
    risk.router,
    prefix="/risk",
    tags=["risk"]
)
