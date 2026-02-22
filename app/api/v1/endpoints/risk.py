#!/usr/bin/env python3
"""
Risk Analysis API Endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Dict
import pandas as pd
import numpy as np
from datetime import date

from app.db.session import get_db
from app.schemas.risk import (
    MonteCarloRequest,
    MonteCarloResponse,
    StressTestRequest,
    StressTestResponse,
    CovarianceRequest,
    CovarianceResponse
)
from app.services.interpolation_service import get_interpolator

router = APIRouter()


@router.post("/monte-carlo", response_model=MonteCarloResponse)
async def get_monte_carlo_simulation(
    request: MonteCarloRequest,
    db: Session = Depends(get_db)
):
    """
    Get Monte Carlo simulation results for a portfolio.

    Uses interpolation from precomputed lookup table for fast response.
    """
    try:
        interpolator = get_interpolator()
        result = interpolator.interpolate_monte_carlo(
            request.weights,
            request.horizon_months
        )

        return MonteCarloResponse(
            model="custom",  # User's custom weights
            horizon_months=request.horizon_months,
            n_simulations=10000,
            mean_return=result['mean_return'],
            std_return=result['std_return'],
            distribution=result['distribution'],
            as_of_date="2025-12-31"
        )

    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="Monte Carlo lookup table not available. Please run computation tasks first."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stress", response_model=List[StressTestResponse])
async def get_stress_test_results(
    request: StressTestRequest,
    db: Session = Depends(get_db)
):
    """
    Get stress test results for a portfolio.

    Uses interpolation from precomputed lookup table for fast response.
    """
    try:
        interpolator = get_interpolator()
        results = interpolator.interpolate_stress_test(request.weights)

        return [
            StressTestResponse(
                scenario_name=r['scenario_name'],
                scenario_description=r['scenario_description'],
                portfolio_return=r['portfolio_return'],
                as_of_date="2025-12-31"
            )
            for r in results
        ]

    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="Stress test lookup table not available. Please run computation tasks first."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/covariance", response_model=CovarianceResponse)
async def get_covariance_matrix(
    request: CovarianceRequest,
    db: Session = Depends(get_db)
):
    """
    Get covariance matrix for specified date.

    Returns annualized covariance matrix and asset order.
    """
    try:
        # Load covariance data from npz (temporary solution)
        cov_data = np.load('data/covariance_matrices.npz', allow_pickle=True)
        tickers = cov_data['tickers'].tolist()
        dates = cov_data['dates'].tolist()

        # Find closest date
        request_date = str(request.as_of_date)
        if request_date not in dates:
            # Find nearest date
            dates_sorted = sorted(dates)
            closest_date = min(dates_sorted, key=lambda d: abs(
                pd.to_datetime(d) - pd.to_datetime(request_date)
            ))
        else:
            closest_date = request_date

        # Get covariance matrix
        cov_matrix = cov_data[closest_date]

        return CovarianceResponse(
            as_of_date=closest_date,
            tickers=tickers,
            covariance_matrix=cov_matrix.tolist(),
            window_days=1260
        )

    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="Covariance data not available. Please run computation tasks first."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
