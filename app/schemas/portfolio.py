from pydantic import BaseModel, Field
from typing import Dict, List
from datetime import date
from enum import Enum
from app.schemas.risk import RiskMetrics


class ModelType(str, Enum):
    markowitz = "markowitz"
    black_litterman = "black_litterman"
    risk_parity = "risk_parity"
    min_variance = "min_variance"
    max_sharpe = "max_sharpe"


class PortfolioQuoteRequest(BaseModel):
    model: ModelType
    as_of_date: date
    horizon_months: int = Field(..., ge=12, le=60)
    weights: Dict[str, float] = Field(..., min_length=1)

    class Config:
        json_schema_extra = {
            "example": {
                "model": "risk_parity",
                "as_of_date": "2025-12-31",
                "horizon_months": 12,
                "weights": {
                    "SPY": 0.20,
                    "QQQ": 0.10,
                    "TLT": 0.25,
                    "GLD": 0.10,
                    "BTC": 0.05,
                    "EEM": 0.10,
                    "EFA": 0.10,
                    "FXI": 0.05,
                    "USO": 0.03,
                    "DBA": 0.02
                }
            }
        }


class PortfolioOptimizeRequest(BaseModel):
    model: ModelType = Field(..., description="Optimization strategy: risk_parity, max_sharpe, or min_variance")
    as_of_date: date = Field(..., description="Date for covariance matrix lookup")
    horizon_months: int = Field(..., ge=12, le=60, description="Investment horizon in months")
    tickers: List[str] = Field(..., min_length=2, description="Selected asset tickers (min 2)")

    class Config:
        json_schema_extra = {
            "example": {
                "model": "risk_parity",
                "as_of_date": "2025-12-31",
                "horizon_months": 36,
                "tickers": ["SPY", "QQQ", "TLT", "GLD", "BTC"]
            }
        }


class PortfolioOptimizeResponse(BaseModel):
    model: str
    tickers: List[str]
    weights: Dict[str, float]
    metrics: RiskMetrics
