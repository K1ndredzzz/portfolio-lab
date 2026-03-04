from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.portfolio import PortfolioQuoteRequest, PortfolioOptimizeRequest, PortfolioOptimizeResponse
from app.schemas.risk import PortfolioQuoteResponse, RiskMetrics
from app.cache.redis_client import redis_client, compute_weights_hash
from app.core.config import get_settings
from app.core.risk_calculator import get_calculator
from app.core.optimizer import optimize_risk_parity, optimize_min_variance, optimize_max_sharpe
import numpy as np

router = APIRouter()
settings = get_settings()


def normalize_weights(weights: dict) -> dict:
    """Normalize weights to sum to 1.0."""
    total = sum(weights.values())
    if abs(total - 1.0) > 0.01:  # Allow 1% tolerance
        return {k: v / total for k, v in weights.items()}
    return weights


@router.post("/quote", response_model=PortfolioQuoteResponse)
async def get_portfolio_quote(
    request: PortfolioQuoteRequest,
    db: Session = Depends(get_db)
):
    """
    Get risk metrics for a portfolio.

    This endpoint calculates risk metrics in real-time using historical data
    and covariance matrices. Results are cached in Redis for fast subsequent lookups.
    """
    # Normalize weights
    normalized_weights = normalize_weights(request.weights)

    # Compute weights hash
    weights_hash = compute_weights_hash(normalized_weights)

    # Try Redis cache first
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

    # Calculate metrics in real-time
    try:
        calculator = get_calculator()
        metrics = calculator.calculate_metrics(
            weights=normalized_weights,
            as_of_date=str(request.as_of_date),
            horizon_months=request.horizon_months,
            risk_free_rate=0.02
        )

        # Cache the result
        redis_client.set(cache_key, metrics)

        return PortfolioQuoteResponse(
            dataset_version=settings.DATASET_VERSION,
            weights_hash=weights_hash,
            metrics=RiskMetrics(**metrics),
            cache_hit=False
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate risk metrics: {str(e)}"
        )


@router.post("/optimize", response_model=PortfolioOptimizeResponse)
async def optimize_portfolio(
    request: PortfolioOptimizeRequest,
    db: Session = Depends(get_db)
):
    """
    Compute optimal portfolio weights for the selected assets using the chosen strategy.

    - **risk_parity**: Equal Risk Contribution — each asset contributes equally to total portfolio risk
    - **max_sharpe**: Maximize the Sharpe Ratio (return / volatility)
    - **min_variance**: Minimize portfolio variance (lowest-risk combination)

    Returns the computed weights and corresponding risk metrics.
    """
    try:
        calculator = get_calculator()

        # Load covariance data
        calculator._load_covariance_matrices()
        calculator._load_returns_data()

        # Validate tickers against available data
        available_tickers = list(calculator._tickers)
        unknown = [t for t in request.tickers if t not in available_tickers]
        if unknown:
            raise HTTPException(
                status_code=422,
                detail=f"Unknown tickers: {unknown}. Available: {available_tickers}"
            )

        if len(request.tickers) < 2:
            raise HTTPException(status_code=422, detail="At least 2 tickers are required.")

        # Get closest covariance matrix for the requested date
        closest_date = calculator._get_closest_date(str(request.as_of_date))
        full_cov = calculator._cov_matrices[closest_date]

        # Build sub-matrix for selected tickers only
        idx = [available_tickers.index(t) for t in request.tickers]
        cov_sub = full_cov[np.ix_(idx, idx)]

        # Compute expected returns for selected tickers
        returns_df = calculator._returns_data
        mean_returns_full = returns_df.mean().values  # aligned with _tickers
        mean_returns_sub = np.array([
            mean_returns_full[available_tickers.index(t)] * 252
            for t in request.tickers
        ])

        # Run optimization
        model_value = request.model.value
        if model_value == "risk_parity":
            weights = optimize_risk_parity(cov_sub, request.tickers)
        elif model_value == "min_variance":
            weights = optimize_min_variance(cov_sub, request.tickers)
        elif model_value == "max_sharpe":
            weights = optimize_max_sharpe(mean_returns_sub, cov_sub, request.tickers)
        else:
            raise HTTPException(
                status_code=422,
                detail=f"Unsupported optimization model: {model_value}. "
                       "Use 'risk_parity', 'max_sharpe', or 'min_variance'."
            )

        # Calculate risk metrics for the optimized weights
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
        raise HTTPException(
            status_code=500,
            detail=f"Optimization failed: {str(e)}"
        )
