from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import numpy as np
import pandas as pd
from sklearn.covariance import LedoitWolf

from app.db.session import get_db
from app.schemas.portfolio import PortfolioQuoteRequest, PortfolioOptimizeRequest, PortfolioOptimizeResponse
from app.schemas.risk import PortfolioQuoteResponse, RiskMetrics
from app.cache.redis_client import redis_client, compute_weights_hash
from app.core.config import get_settings
from app.core.risk_calculator import get_calculator
from app.core.optimizer import optimize_risk_parity, optimize_min_variance, optimize_max_sharpe

router = APIRouter()
settings = get_settings()
DATA_DIR = Path("data")


def normalize_weights(weights: dict) -> dict:
    """Normalize weights to sum to 1.0."""
    total = sum(weights.values())
    if abs(total - 1.0) > 0.01:
        return {k: v / total for k, v in weights.items()}
    return weights


@router.post("/quote", response_model=PortfolioQuoteResponse)
async def get_portfolio_quote(
    request: PortfolioQuoteRequest,
    db: Session = Depends(get_db)
):
    """Get risk metrics for a portfolio."""
    normalized_weights = normalize_weights(request.weights)
    weights_hash = compute_weights_hash(normalized_weights)

    cache_key = redis_client.build_key(
        dataset_version=settings.DATASET_VERSION,
        model=request.model.value,
        as_of_date=str(request.as_of_date),
        horizon_months=request.horizon_months,
        weights_hash=weights_hash
    )

    cached_result = redis_client.get(cache_key)
    if cached_result:
        return PortfolioQuoteResponse(
            dataset_version=settings.DATASET_VERSION,
            weights_hash=weights_hash,
            metrics=RiskMetrics(**cached_result),
            cache_hit=True
        )

    try:
        calculator = get_calculator()
        metrics = calculator.calculate_metrics(
            weights=normalized_weights,
            as_of_date=str(request.as_of_date),
            horizon_months=request.horizon_months,
            risk_free_rate=0.02
        )
        redis_client.set(cache_key, metrics)

        return PortfolioQuoteResponse(
            dataset_version=settings.DATASET_VERSION,
            weights_hash=weights_hash,
            metrics=RiskMetrics(**metrics),
            cache_hit=False
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate risk metrics: {str(e)}")


@router.post("/optimize", response_model=PortfolioOptimizeResponse)
async def optimize_portfolio(
    request: PortfolioOptimizeRequest,
    db: Session = Depends(get_db)
):
    """
    Compute optimal portfolio weights for the selected assets.

    - **risk_parity**: Equal Risk Contribution
    - **max_sharpe**: Maximize Sharpe Ratio
    - **min_variance**: Minimize portfolio variance
    """
    try:
        # ©¤©¤ Load returns ©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤
        prices_df = pd.read_parquet(DATA_DIR / "clean_prices.parquet")
        prices_df = prices_df[prices_df["log_return"].notna()].copy()
        returns_wide = prices_df.pivot(
            index="trade_date", columns="ticker", values="log_return"
        ).sort_index()

        available_tickers = sorted(returns_wide.columns.tolist())

        # Validate tickers
        unknown = [t for t in request.tickers if t not in available_tickers]
        if unknown:
            raise HTTPException(
                status_code=422,
                detail=f"Unknown tickers: {unknown}. Available: {available_tickers}"
            )
        if len(request.tickers) < 2:
            raise HTTPException(status_code=422, detail="At least 2 tickers are required.")

        # ©¤©¤ Window returns to horizon ©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤
        n_days = int(request.horizon_months * 21)
        returns_sub = returns_wide[request.tickers].tail(n_days).fillna(0.0)

        # ©¤©¤ Ledoit-Wolf covariance (annualised) ©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤
        lw = LedoitWolf()
        cov_daily = lw.fit(returns_sub.values).covariance_
        cov_ann = cov_daily * 252

        # ©¤©¤ Annualised expected returns ©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤
        mean_returns_ann = returns_sub.mean().values * 252

        # ©¤©¤ Run optimization ©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤
        model_value = request.model.value
        if model_value == "risk_parity":
            weights = optimize_risk_parity(cov_ann, request.tickers)
        elif model_value == "min_variance":
            weights = optimize_min_variance(cov_ann, request.tickers)
        elif model_value == "max_sharpe":
            weights = optimize_max_sharpe(mean_returns_ann, cov_ann, request.tickers)
        else:
            raise HTTPException(
                status_code=422,
                detail=f"Unsupported model: {model_value}. Use 'risk_parity', 'max_sharpe', or 'min_variance'."
            )

        # ©¤©¤ Risk metrics for optimized weights ©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤
        calculator = get_calculator()
        metrics = calculator.calculate_metrics(
            weights=weights,
            as_of_date=str(request.as_of_date),
            horizon_months=request.horizon_months,
            risk_free_rate=0.02
        )

        return PortfolioOptimizeResponse(
            model=model_value,
            tickers=request.tickers,
            weights=weights,
            metrics=RiskMetrics(**metrics)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")
