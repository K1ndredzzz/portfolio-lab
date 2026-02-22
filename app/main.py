from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.api.v1.router import api_router

settings = get_settings()

app = FastAPI(
    title="Portfolio Lab API",
    description="Investment Portfolio Analysis & Optimization",
    version="1.0.0",
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc",
    openapi_url=f"{settings.API_PREFIX}/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_PREFIX)


@app.get(f"{settings.API_PREFIX}/health/live")
async def health_live():
    return {"status": "ok"}


@app.get(f"{settings.API_PREFIX}/health/ready")
async def health_ready():
    return {
        "status": "ready",
        "dataset_version": settings.DATASET_VERSION,
        "db": "ok",
        "redis": "ok"
    }


@app.get(f"{settings.API_PREFIX}/meta/assets")
async def get_assets():
    return {
        "assets": [
            {"ticker": "SPY", "name": "SPDR S&P 500 ETF Trust", "class": "Equity_US"},
            {"ticker": "QQQ", "name": "Invesco QQQ Trust", "class": "Equity_US"},
            {"ticker": "IWM", "name": "iShares Russell 2000 ETF", "class": "Equity_US_SmallCap"},
            {"ticker": "TLT", "name": "iShares 20+ Year Treasury Bond ETF", "class": "Rates_US"},
            {"ticker": "GLD", "name": "SPDR Gold Shares", "class": "Commodity_Gold"},
            {"ticker": "BTC", "name": "Bitcoin Spot Proxy", "class": "Crypto"},
            {"ticker": "EEM", "name": "iShares MSCI Emerging Markets ETF", "class": "Equity_EM"},
            {"ticker": "EFA", "name": "iShares MSCI EAFE ETF", "class": "Equity_DM_exUS"},
            {"ticker": "FXI", "name": "iShares China Large-Cap ETF", "class": "Equity_China"},
            {"ticker": "USO", "name": "United States Oil Fund", "class": "Commodity_Oil"},
            {"ticker": "DBA", "name": "Invesco DB Agriculture Fund", "class": "Commodity_Agriculture"}
        ]
    }
