#!/usr/bin/env python3
"""
GCP Compute Task: Monte Carlo Simulation for Portfolio Returns
Usage: python 30_compute_monte_carlo.py --cov covariance_matrices.npz --returns clean_prices.parquet --output monte_carlo.parquet
"""

import argparse
import pandas as pd
import numpy as np
from datetime import datetime


def monte_carlo_simulation(weights: np.ndarray, expected_returns: np.ndarray,
                           cov_matrix: np.ndarray, horizon_months: int,
                           n_simulations: int = 10000) -> dict:
    """Run Monte Carlo simulation for portfolio returns."""
    n_days = horizon_months * 21  # Approximate trading days per month

    # Portfolio expected return and volatility (daily)
    portfolio_return_daily = (weights @ expected_returns) / 252
    portfolio_vol_daily = np.sqrt(weights @ cov_matrix @ weights) / np.sqrt(252)

    # Generate random returns
    np.random.seed(42)
    random_returns = np.random.normal(
        portfolio_return_daily,
        portfolio_vol_daily,
        size=(n_simulations, n_days)
    )

    # Compute cumulative returns
    cumulative_returns = np.exp(np.cumsum(random_returns, axis=1))

    # Final returns
    final_returns = cumulative_returns[:, -1] - 1

    # Compute percentiles
    percentiles = [1, 5, 10, 25, 50, 75, 90, 95, 99]
    percentile_values = np.percentile(final_returns, percentiles)

    return {
        'mean_return': np.mean(final_returns),
        'median_return': np.median(final_returns),
        'std_return': np.std(final_returns),
        'min_return': np.min(final_returns),
        'max_return': np.max(final_returns),
        'percentiles': dict(zip(percentiles, percentile_values)),
        'final_returns': final_returns
    }


def main():
    parser = argparse.ArgumentParser(description='Compute Monte Carlo simulations')
    parser.add_argument('--cov', default='data/covariance_matrices.npz', help='Covariance matrices file')
    parser.add_argument('--returns', default='data/clean_prices.parquet', help='Returns data file')
    parser.add_argument('--portfolios', default='data/portfolios.parquet', help='Portfolio weights file')
    parser.add_argument('--output', default='data/monte_carlo.parquet', help='Output file')
    parser.add_argument('--n-sims', type=int, default=10000, help='Number of simulations')
    args = parser.parse_args()

    print(f"Loading covariance matrices from {args.cov}...")
    cov_data = np.load(args.cov, allow_pickle=True)
    tickers = cov_data['tickers'].tolist()
    dates = cov_data['dates'].tolist()

    print(f"Loading returns from {args.returns}...")
    returns_df = pd.read_parquet(args.returns)
    returns_df = returns_df[returns_df['log_return'].notna()].copy()

    # Compute expected returns
    returns_wide = returns_df.pivot(index='trade_date', columns='ticker', values='log_return')
    returns_wide = returns_wide.sort_index()
    expected_returns_series = returns_wide.tail(252).mean() * 252
    expected_returns = expected_returns_series.reindex(tickers).values

    print(f"Loading portfolios from {args.portfolios}...")
    portfolios_df = pd.read_parquet(args.portfolios)

    # Select latest snapshot for each model
    latest_portfolios = portfolios_df.sort_values('as_of_date').groupby('model').tail(1)

    print(f"\nRunning Monte Carlo simulations ({args.n_sims} paths)...")

    all_results = []
    horizons = [12, 24, 36, 60]  # months

    for _, portfolio in latest_portfolios.iterrows():
        model = portfolio['model']
        as_of_date = portfolio['as_of_date']

        # Extract weights
        weight_cols = [col for col in portfolio.index if col.startswith('weight_')]
        weights = portfolio[weight_cols].values

        # Get covariance matrix for this date
        cov_matrix = cov_data[as_of_date]

        print(f"\n  Model: {model}")
        print(f"  As of: {as_of_date}")
        print(f"  Weights: {dict(zip(tickers, weights))}")

        for horizon in horizons:
            print(f"    Horizon: {horizon} months...")

            mc_result = monte_carlo_simulation(
                weights, expected_returns, cov_matrix,
                horizon, args.n_sims
            )

            # Store distribution percentiles
            for percentile, value in mc_result['percentiles'].items():
                all_results.append({
                    'model': model,
                    'as_of_date': as_of_date,
                    'horizon_months': horizon,
                    'percentile': float(percentile),
                    'return_value': value,
                    'stat_type': 'percentile'
                })

            # Store summary statistics separately
            all_results.append({
                'model': model,
                'as_of_date': as_of_date,
                'horizon_months': horizon,
                'percentile': 50.0,  # Use median as placeholder
                'return_value': mc_result['mean_return'],
                'stat_type': 'mean'
            })
            all_results.append({
                'model': model,
                'as_of_date': as_of_date,
                'horizon_months': horizon,
                'percentile': 50.0,  # Use median as placeholder
                'return_value': mc_result['std_return'],
                'stat_type': 'std'
            })

            print(f"      Mean: {mc_result['mean_return']:.2%}")
            print(f"      Median: {mc_result['median_return']:.2%}")
            print(f"      5th percentile: {mc_result['percentiles'][5]:.2%}")
            print(f"      95th percentile: {mc_result['percentiles'][95]:.2%}")

    print(f"\nTotal Monte Carlo results: {len(all_results)}")

    # Save to parquet
    results_df = pd.DataFrame(all_results)
    results_df.to_parquet(args.output, index=False, compression='snappy')
    print(f"Saved to {args.output}")


if __name__ == "__main__":
    main()
