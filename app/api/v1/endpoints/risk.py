#!/usr/bin/env python3
"""
Risk Analysis API Endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
import numpy as np
import logging

from app.db.session import get_db
from app.schemas.risk import (
    MonteCarloRequest,
    MonteCarloResponse,
    StressTestRequest,
    StressTestResponse,
    CovarianceRequest,
    CovarianceResponse
)
from app.core.risk_calculator import get_calculator
from app.services.interpolation_service import get_interpolator

logger = logging.getLogger(__name__)

router = APIRouter()

# Crisis period end dates used as the as_of_date label for each stress scenario
SCENARIO_DATES = {
    '2008_financial_crisis': '2009-02-28',   # trough of GFC drawdown
    '2020_covid_crash':      '2020-03-23',   # COVID market bottom
    '2022_rate_hikes':       '2022-12-31',   # end of 2022 bear market
}

# Fixed historical asset-level shocks (same as batch job 40_compute_stress_tests.py)
STRESS_SCENARIOS = {
    '2008_financial_crisis': {
        'description': '2008 Financial Crisis',
        'shocks': {
            'SPY': -0.37, 'QQQ': -0.42, 'IWM': -0.34,
            'TLT': 0.14,  'GLD': 0.05,  'BTC': -0.50,
            'EEM': -0.53, 'EFA': -0.43, 'FXI': -0.48,
            'USO': -0.54, 'DBA': -0.14,
        },
    },
    '2020_covid_crash': {
        'description': '2020 COVID-19 Crash',
        'shocks': {
            'SPY': -0.34, 'QQQ': -0.30, 'IWM': -0.42,
            'TLT': 0.21,  'GLD': 0.08,  'BTC': -0.40,
            'EEM': -0.31, 'EFA': -0.35, 'FXI': -0.28,
            'USO': -0.66, 'DBA': -0.08,
        },
    },
    '2022_rate_hikes': {
        'description': '2022 Rate Hikes',
        'shocks': {
            'SPY': -0.18, 'QQQ': -0.33, 'IWM': -0.21,
            'TLT': -0.31, 'GLD': -0.01, 'BTC': -0.64,
            'EEM': -0.20, 'EFA': -0.14, 'FXI': -0.22,
            'USO': 0.07,  'DBA': 0.16,
        },
    },
}


@router.post("/monte-carlo", response_model=MonteCarloResponse)
async def get_monte_carlo_simulation(
    request: MonteCarloRequest,
    db: Session = Depends(get_db)
):
    """
    Live Monte Carlo simulation.

    Uses the same annualized mu and sigma from risk_calculator so that
    the MC distribution is strictly consistent with the Risk Metrics cards.

    Steps:
    1. Compute portfolio annualized_return and annualized_vol via risk_calculator.
    2. Convert to daily parameters.
    3. Simulate `n_days = horizon_months * 21` paths.
    4. Return cumulative-return distribution.
    """
    try:
        calc = get_calculator()

        # ── Step 1: live annualized parameters (same pipeline as Risk Metrics) ──
        metrics = calc.calculate_metrics(
            weights=request.weights,
            as_of_date=request.as_of_date,
            horizon_months=request.horizon_months,
        )

        annual_return = metrics["expected_return_ann"]   # e.g. 0.124  (12.4%)
        annual_vol    = metrics["volatility_ann"]         # e.g. 0.152  (15.2%)

        logger.info(
            "MC inputs | as_of=%s horizon=%d mo | ann_return=%.4f ann_vol=%.4f",
            request.as_of_date, request.horizon_months, annual_return, annual_vol
        )

        # ── Step 2: daily parameters ──────────────────────────────────────────
        n_days = request.horizon_months * 21          # approx trading days
        daily_mu  = annual_return / 252               # daily log-return mean
        daily_sig = annual_vol    / np.sqrt(252)      # daily log-return std

        # ── Step 3: simulate ──────────────────────────────────────────────────
        N_SIM = 10_000
        rng = np.random.default_rng(seed=42)
        daily_returns = rng.normal(daily_mu, daily_sig, size=(N_SIM, n_days))
        # Cumulative return over horizon (log → arithmetic)
        final_log_returns  = daily_returns.sum(axis=1)
        final_returns      = np.expm1(final_log_returns)   # e^x - 1

        # ── Step 4: distribution ──────────────────────────────────────────────
        pcts = [1, 5, 10, 25, 50, 75, 90, 95, 99]
        distribution = {
            f"p{p}": float(np.percentile(final_returns, p))
            for p in pcts
        }

        return MonteCarloResponse(
            model="custom",
            horizon_months=request.horizon_months,
            n_simulations=N_SIM,
            mean_return=float(np.mean(final_returns)),
            std_return=float(np.std(final_returns)),
            distribution=distribution,
            as_of_date=request.as_of_date,
        )

    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=f"Data not available: {e}")
    except Exception as e:
        logger.exception("Monte Carlo failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stress", response_model=List[StressTestResponse])
async def get_stress_test_results(
    request: StressTestRequest,
    db: Session = Depends(get_db)
):
    """
    Stress test using fixed historical asset-level shocks.

    The crisis shocks are applied to the provided weights regardless of
    the user's selected lookback period. Stress tests always represent
    the peak-to-trough drawdown of each historical crisis scenario.
    """
    try:
        results = []
        for scenario_name, scenario in STRESS_SCENARIOS.items():
            portfolio_return = sum(
                request.weights.get(ticker, 0.0) * shock
                for ticker, shock in scenario['shocks'].items()
            )
            results.append(StressTestResponse(
                scenario_name=scenario_name,
                scenario_description=scenario['description'],
                portfolio_return=float(portfolio_return),
                as_of_date=SCENARIO_DATES[scenario_name],
            ))

        return results

    except Exception as e:
        logger.exception("Stress test failed")
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
        import numpy as np
        import pandas as pd

        cov_data = np.load('data/covariance_matrices.npz', allow_pickle=True)
        tickers = cov_data['tickers'].tolist()
        dates   = cov_data['dates'].tolist()

        request_date = str(request.as_of_date)
        if request_date not in dates:
            closest = min(dates, key=lambda d: abs(
                pd.to_datetime(d) - pd.to_datetime(request_date)
            ))
        else:
            closest = request_date

        cov_matrix = cov_data[closest]

        return CovarianceResponse(
            as_of_date=closest,
            tickers=tickers,
            covariance_matrix=cov_matrix.tolist(),
            window_days=1260,
        )

    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Covariance data not available.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
