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

router = APIRouter()


@router.post("/monte-carlo", response_model=MonteCarloResponse)
async def get_monte_carlo_simulation(
    request: MonteCarloRequest,
    db: Session = Depends(get_db)
):
    """
    Get Monte Carlo simulation results for a portfolio.

    Returns distribution of potential returns over specified horizon.
    """
    try:
        # Load Monte Carlo data from parquet (temporary solution)
        mc_df = pd.read_parquet('data/monte_carlo.parquet')

        # Filter by model and horizon
        filtered = mc_df[
            (mc_df['model'] == request.model) &
            (mc_df['horizon_months'] == request.horizon_months)
        ]

        if filtered.empty:
            raise HTTPException(
                status_code=404,
                detail=f"No Monte Carlo data found for model={request.model}, horizon={request.horizon_months}"
            )

        # Extract percentiles
        percentile_data = filtered[filtered['stat_type'] == 'percentile']
        distribution = {
            f"p{int(row['percentile'])}": float(row['return_value'])
            for _, row in percentile_data.iterrows()
        }

        # Extract mean and std
        mean_row = filtered[filtered['stat_type'] == 'mean'].iloc[0]
        std_row = filtered[filtered['stat_type'] == 'std'].iloc[0]

        return MonteCarloResponse(
            model=request.model,
            horizon_months=request.horizon_months,
            n_simulations=10000,
            mean_return=float(mean_row['return_value']),
            std_return=float(std_row['return_value']),
            distribution=distribution,
            as_of_date=str(filtered.iloc[0]['as_of_date'])
        )

    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="Monte Carlo data not available. Please run computation tasks first."
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

    Returns portfolio performance under historical crisis scenarios.
    """
    try:
        # Load stress test data from parquet (temporary solution)
        stress_df = pd.read_parquet('data/stress_tests.parquet')

        # Filter by model
        filtered = stress_df[stress_df['model'] == request.model]

        if filtered.empty:
            raise HTTPException(
                status_code=404,
                detail=f"No stress test data found for model={request.model}"
            )

        # Convert to response format
        results = []
        for _, row in filtered.iterrows():
            results.append(StressTestResponse(
                scenario_name=row['scenario_name'],
                scenario_description=row['scenario_description'],
                portfolio_return=float(row['portfolio_return']),
                as_of_date=str(row['as_of_date'])
            ))

        return results

    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="Stress test data not available. Please run computation tasks first."
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
