from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import date


class RiskMetrics(BaseModel):
    expected_return_ann: float
    volatility_ann: float
    sharpe: float
    sortino: float
    var95: float
    var99: float
    cvar95: float
    cvar99: float
    max_drawdown: float
    calmar: float


class PortfolioQuoteResponse(BaseModel):
    dataset_version: str
    weights_hash: str
    metrics: RiskMetrics
    cache_hit: bool

    class Config:
        json_schema_extra = {
            "example": {
                "dataset_version": "2026.02.21",
                "weights_hash": "2ea9fd4d5d84d6f9e8cf0e8e3347d2de",
                "metrics": {
                    "expected_return_ann": 0.094,
                    "volatility_ann": 0.127,
                    "sharpe": 0.63,
                    "sortino": 0.91,
                    "var95": -0.124,
                    "var99": -0.197,
                    "cvar95": -0.169,
                    "cvar99": -0.238,
                    "max_drawdown": -0.223,
                    "calmar": 0.42
                },
                "cache_hit": True
            }
        }


# Monte Carlo schemas
class MonteCarloRequest(BaseModel):
    weights: Dict[str, float] = Field(..., min_length=1, description="Portfolio weights")
    horizon_months: int = Field(..., ge=12, le=60, description="Investment horizon in months")
    as_of_date: str = Field(default="2025-12-31", description="Date for covariance snapshot")

    class Config:
        json_schema_extra = {
            "example": {
                "weights": {
                    "SPY": 0.3,
                    "TLT": 0.3,
                    "GLD": 0.2,
                    "BTC": 0.2
                },
                "horizon_months": 36,
                "as_of_date": "2025-12-31"
            }
        }


class MonteCarloResponse(BaseModel):
    model: str
    horizon_months: int
    n_simulations: int
    mean_return: float
    std_return: float
    distribution: Dict[str, float]
    as_of_date: str

    class Config:
        json_schema_extra = {
            "example": {
                "model": "risk_parity",
                "horizon_months": 36,
                "n_simulations": 10000,
                "mean_return": 0.3043,
                "std_return": 0.1124,
                "distribution": {
                    "p1": 0.0512,
                    "p5": 0.0923,
                    "p50": 0.2982,
                    "p95": 0.5364,
                    "p99": 0.6421
                },
                "as_of_date": "2025-12-31"
            }
        }


# Stress Test schemas
class StressTestRequest(BaseModel):
    weights: Dict[str, float] = Field(..., min_length=1, description="Portfolio weights")

    class Config:
        json_schema_extra = {
            "example": {
                "weights": {
                    "SPY": 0.3,
                    "TLT": 0.3,
                    "GLD": 0.2,
                    "BTC": 0.2
                }
            }
        }


class StressTestResponse(BaseModel):
    scenario_name: str
    scenario_description: str
    portfolio_return: float
    as_of_date: str

    class Config:
        json_schema_extra = {
            "example": {
                "scenario_name": "2008_financial_crisis",
                "scenario_description": "2008 Financial Crisis",
                "portfolio_return": -0.2914,
                "as_of_date": "2025-12-31"
            }
        }


# Covariance schemas
class CovarianceRequest(BaseModel):
    as_of_date: date = Field(..., description="Date for covariance matrix")

    class Config:
        json_schema_extra = {
            "example": {
                "as_of_date": "2025-12-31"
            }
        }


class CovarianceResponse(BaseModel):
    as_of_date: str
    tickers: List[str]
    covariance_matrix: List[List[float]]
    window_days: int

    class Config:
        json_schema_extra = {
            "example": {
                "as_of_date": "2025-12-31",
                "tickers": ["BTC", "DBA", "EEM", "EFA", "FXI", "GLD", "IWM", "QQQ", "SPY", "TLT", "USO"],
                "covariance_matrix": [[0.66, 0.01], [0.01, 0.03]],
                "window_days": 1260
            }
        }

