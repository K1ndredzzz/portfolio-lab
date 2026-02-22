from pydantic import BaseModel, Field
from typing import Dict
from datetime import date
from enum import Enum


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
