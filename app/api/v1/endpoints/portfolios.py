from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.portfolio import PortfolioQuoteRequest
from app.schemas.risk import PortfolioQuoteResponse, RiskMetrics
from app.cache.redis_client import redis_client, compute_weights_hash
from app.core.config import get_settings
from app.core.risk_calculator import get_calculator

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
