#!/usr/bin/env python3
"""
GCP Compute Task: Portfolio Optimization (Markowitz, Black-Litterman, Risk Parity)
Usage: python 20_compute_markowitz_bl_rp.py --cov covariance_matrices.npz --returns clean_prices.parquet --output portfolios.parquet
"""

import argparse
import pandas as pd
import numpy as np
from scipy.optimize import minimize
from datetime import datetime


def compute_expected_returns(returns_df: pd.DataFrame, lookback_days: int = 252) -> pd.Series:
    """Compute annualized expected returns."""
    returns_wide = returns_df.pivot(index='trade_date', columns='ticker', values='log_return')
    returns_wide = returns_wide.sort_index()

    # Use last lookback_days for expected returns
    recent_returns = returns_wide.tail(lookback_days)
    expected_returns = recent_returns.mean() * 252  # Annualize

    return expected_returns


def markowitz_optimization(expected_returns: np.ndarray, cov_matrix: np.ndarray,
                          target_return: float = None) -> dict:
    """Markowitz mean-variance optimization."""
    n_assets = len(expected_returns)

    # Objective: minimize portfolio variance
    def portfolio_variance(weights):
        return weights @ cov_matrix @ weights

    # Constraints
    constraints = [
        {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}  # Weights sum to 1
    ]

    if target_return is not None:
        constraints.append({
            'type': 'eq',
            'fun': lambda w: w @ expected_returns - target_return
        })

    # Bounds: 0 <= weight <= 1 (long-only)
    bounds = tuple((0, 1) for _ in range(n_assets))

    # Initial guess: equal weights
    x0 = np.ones(n_assets) / n_assets

    result = minimize(
        portfolio_variance,
        x0,
        method='SLSQP',
        bounds=bounds,
        constraints=constraints
    )

    if result.success:
        weights = result.x
        portfolio_return = weights @ expected_returns
        portfolio_vol = np.sqrt(weights @ cov_matrix @ weights)
        sharpe = portfolio_return / portfolio_vol if portfolio_vol > 0 else 0

        return {
            'weights': weights,
            'expected_return': portfolio_return,
            'volatility': portfolio_vol,
            'sharpe': sharpe,
            'success': True
        }
    else:
        return {'success': False}


def risk_parity_optimization(cov_matrix: np.ndarray) -> dict:
    """Risk parity optimization (equal risk contribution)."""
    n_assets = cov_matrix.shape[0]

    def risk_parity_objective(weights):
        portfolio_vol = np.sqrt(weights @ cov_matrix @ weights)
        marginal_contrib = cov_matrix @ weights
        risk_contrib = weights * marginal_contrib / portfolio_vol

        # Minimize variance of risk contributions
        target_risk = portfolio_vol / n_assets
        return np.sum((risk_contrib - target_risk) ** 2)

    constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1}]
    bounds = tuple((0, 1) for _ in range(n_assets))
    x0 = np.ones(n_assets) / n_assets

    result = minimize(
        risk_parity_objective,
        x0,
        method='SLSQP',
        bounds=bounds,
        constraints=constraints
    )

    if result.success:
        weights = result.x
        return {
            'weights': weights,
            'success': True
        }
    else:
        return {'success': False}


def compute_efficient_frontier(expected_returns: np.ndarray, cov_matrix: np.ndarray,
                               n_points: int = 50) -> list:
    """Compute efficient frontier points."""
    min_return = expected_returns.min()
    max_return = expected_returns.max()

    target_returns = np.linspace(min_return, max_return, n_points)
    frontier_points = []

    for target_return in target_returns:
        result = markowitz_optimization(expected_returns, cov_matrix, target_return)
        if result['success']:
            frontier_points.append({
                'target_return': target_return,
                'expected_return': result['expected_return'],
                'volatility': result['volatility'],
                'sharpe': result['sharpe'],
                'weights': result['weights']
            })

    return frontier_points


def main():
    parser = argparse.ArgumentParser(description='Compute portfolio optimizations')
    parser.add_argument('--cov', default='data/covariance_matrices.npz', help='Covariance matrices file')
    parser.add_argument('--returns', default='data/clean_prices.parquet', help='Returns data file')
    parser.add_argument('--output', default='data/portfolios.parquet', help='Output file')
    args = parser.parse_args()

    print(f"Loading covariance matrices from {args.cov}...")
    cov_data = np.load(args.cov, allow_pickle=True)
    tickers = cov_data['tickers'].tolist()
    dates = cov_data['dates'].tolist()

    print(f"Loading returns from {args.returns}...")
    returns_df = pd.read_parquet(args.returns)
    returns_df = returns_df[returns_df['log_return'].notna()].copy()

    print(f"\nComputing expected returns...")
    expected_returns_series = compute_expected_returns(returns_df)
    expected_returns = expected_returns_series.reindex(tickers).values

    print(f"Expected returns (annualized):")
    for ticker, ret in zip(tickers, expected_returns):
        print(f"  {ticker}: {ret:.2%}")

    all_results = []

    print(f"\nProcessing {len(dates)} snapshots...")
    for i, date in enumerate(dates):
        cov_matrix = cov_data[date]

        # Min Variance
        min_var = markowitz_optimization(expected_returns, cov_matrix, target_return=None)
        if min_var['success']:
            all_results.append({
                'as_of_date': date,
                'model': 'min_variance',
                **{f'weight_{ticker}': w for ticker, w in zip(tickers, min_var['weights'])},
                'expected_return': min_var['expected_return'],
                'volatility': min_var['volatility'],
                'sharpe': min_var['sharpe']
            })

        # Max Sharpe
        # Find optimal by trying different target returns
        best_sharpe = -np.inf
        best_result = None
        for target_ret in np.linspace(expected_returns.min(), expected_returns.max(), 20):
            result = markowitz_optimization(expected_returns, cov_matrix, target_ret)
            if result['success'] and result['sharpe'] > best_sharpe:
                best_sharpe = result['sharpe']
                best_result = result

        if best_result:
            all_results.append({
                'as_of_date': date,
                'model': 'max_sharpe',
                **{f'weight_{ticker}': w for ticker, w in zip(tickers, best_result['weights'])},
                'expected_return': best_result['expected_return'],
                'volatility': best_result['volatility'],
                'sharpe': best_result['sharpe']
            })

        # Risk Parity
        rp = risk_parity_optimization(cov_matrix)
        if rp['success']:
            rp_return = rp['weights'] @ expected_returns
            rp_vol = np.sqrt(rp['weights'] @ cov_matrix @ rp['weights'])
            rp_sharpe = rp_return / rp_vol if rp_vol > 0 else 0

            all_results.append({
                'as_of_date': date,
                'model': 'risk_parity',
                **{f'weight_{ticker}': w for ticker, w in zip(tickers, rp['weights'])},
                'expected_return': rp_return,
                'volatility': rp_vol,
                'sharpe': rp_sharpe
            })

        if (i + 1) % 50 == 0:
            print(f"  Processed {i + 1}/{len(dates)} snapshots")

    print(f"\nTotal portfolio results: {len(all_results)}")

    # Save to parquet
    results_df = pd.DataFrame(all_results)
    results_df.to_parquet(args.output, index=False, compression='snappy')
    print(f"Saved to {args.output}")

    # Summary statistics
    print(f"\nSummary by model:")
    summary = results_df.groupby('model').agg({
        'expected_return': ['mean', 'std'],
        'volatility': ['mean', 'std'],
        'sharpe': ['mean', 'std']
    })
    print(summary)


if __name__ == "__main__":
    main()
