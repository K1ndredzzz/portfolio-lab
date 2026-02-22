#!/usr/bin/env python3
"""
GCP Compute Task: Monte Carlo Simulation with Weight Grid
Usage: python 30_compute_monte_carlo_grid.py --cov covariance_matrices.npz --returns clean_prices.parquet --output monte_carlo_grid.parquet --step 0.05
"""

import argparse
import pandas as pd
import numpy as np
import hashlib
import json
from datetime import datetime
from itertools import product


def compute_weights_hash(weights_dict: dict) -> str:
    """Compute deterministic hash for portfolio weights."""
    sorted_weights = {k: round(v, 6) for k, v in sorted(weights_dict.items())}
    weights_str = json.dumps(sorted_weights, sort_keys=True)
    return hashlib.sha256(weights_str.encode()).hexdigest()


def generate_weight_grid(n_assets: int, step: float = 0.05) -> np.ndarray:
    """
    Generate all possible weight combinations that sum to 1.0.

    Args:
        n_assets: Number of assets
        step: Weight increment (e.g., 0.05 for 5%)

    Returns:
        Array of shape (n_combinations, n_assets) with all valid weight combinations
    """
    # Generate all possible values for each asset (0.00, 0.05, 0.10, ..., 1.00)
    n_steps = int(1.0 / step) + 1
    possible_values = [i * step for i in range(n_steps)]

    # Generate all combinations
    all_combinations = []

    def generate_recursive(current_weights, remaining_weight, asset_idx):
        """Recursively generate weight combinations."""
        if asset_idx == n_assets - 1:
            # Last asset gets the remaining weight
            if 0 <= remaining_weight <= 1.0 + 1e-9:
                current_weights.append(round(remaining_weight, 6))
                all_combinations.append(current_weights.copy())
                current_weights.pop()
            return

        # Try all possible values for current asset
        for value in possible_values:
            if value <= remaining_weight + 1e-9:
                current_weights.append(value)
                generate_recursive(current_weights, remaining_weight - value, asset_idx + 1)
                current_weights.pop()

    generate_recursive([], 1.0, 0)

    return np.array(all_combinations)


def monte_carlo_simulation(weights: np.ndarray, expected_returns: np.ndarray,
                           cov_matrix: np.ndarray, horizon_months: int,
                           n_simulations: int = 10000, seed: int = None) -> dict:
    """Run Monte Carlo simulation for portfolio returns."""
    n_days = horizon_months * 21  # Approximate trading days per month

    # Portfolio expected return and volatility (daily)
    portfolio_return_daily = (weights @ expected_returns) / 252
    portfolio_vol_daily = np.sqrt(weights @ cov_matrix @ weights) / np.sqrt(252)

    # Generate random returns
    if seed is not None:
        np.random.seed(seed)
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
        'percentiles': dict(zip(percentiles, percentile_values))
    }


def main():
    parser = argparse.ArgumentParser(description='Compute Monte Carlo simulations with weight grid')
    parser.add_argument('--cov', default='data/covariance_matrices.npz', help='Covariance matrices file')
    parser.add_argument('--returns', default='data/clean_prices.parquet', help='Returns data file')
    parser.add_argument('--output', default='data/monte_carlo_grid.parquet', help='Output file')
    parser.add_argument('--n-sims', type=int, default=10000, help='Number of simulations per combination')
    parser.add_argument('--step', type=float, default=0.10, help='Weight step size (default: 0.10 = 10%)')
    parser.add_argument('--max-combinations', type=int, default=None, help='Max combinations to compute (for testing)')
    args = parser.parse_args()

    print(f"Loading covariance matrices from {args.cov}...")
    cov_data = np.load(args.cov, allow_pickle=True)
    tickers = cov_data['tickers'].tolist()
    dates = cov_data['dates'].tolist()
    n_assets = len(tickers)

    print(f"Loading returns from {args.returns}...")
    returns_df = pd.read_parquet(args.returns)
    returns_df = returns_df[returns_df['log_return'].notna()].copy()

    # Compute expected returns
    returns_wide = returns_df.pivot(index='trade_date', columns='ticker', values='log_return')
    returns_wide = returns_wide.sort_index()
    expected_returns_series = returns_wide.tail(252).mean() * 252
    expected_returns = expected_returns_series.reindex(tickers).values

    # Use latest covariance matrix
    latest_date = sorted(dates)[-1]
    cov_matrix = cov_data[latest_date]

    print(f"\nGenerating weight grid...")
    print(f"  Assets: {n_assets}")
    print(f"  Step size: {args.step} ({args.step*100:.0f}%)")

    weight_grid = generate_weight_grid(n_assets, args.step)
    n_combinations = len(weight_grid)

    print(f"  Total combinations: {n_combinations:,}")

    if args.max_combinations and n_combinations > args.max_combinations:
        print(f"  Limiting to first {args.max_combinations:,} combinations for testing")
        weight_grid = weight_grid[:args.max_combinations]
        n_combinations = args.max_combinations

    print(f"\nRunning Monte Carlo simulations...")
    print(f"  Simulations per combination: {args.n_sims:,}")
    print(f"  Total simulations: {n_combinations * args.n_sims:,}")

    all_results = []
    horizons = [12, 24, 36, 60]  # months

    # Progress tracking
    checkpoint_interval = max(1, n_combinations // 20)  # Report every 5%

    for idx, weights in enumerate(weight_grid):
        # Compute weights hash
        weights_dict = dict(zip(tickers, weights))
        weights_hash = compute_weights_hash(weights_dict)

        # Progress reporting
        if idx % checkpoint_interval == 0 or idx == n_combinations - 1:
            progress = (idx + 1) / n_combinations * 100
            print(f"  Progress: {idx+1:,}/{n_combinations:,} ({progress:.1f}%)")

        for horizon in horizons:
            # Run Monte Carlo simulation
            mc_result = monte_carlo_simulation(
                weights, expected_returns, cov_matrix,
                horizon, args.n_sims, seed=42 + idx  # Different seed for each combination
            )

            # Store distribution percentiles
            for percentile, value in mc_result['percentiles'].items():
                all_results.append({
                    'weights_hash': weights_hash,
                    'as_of_date': latest_date,
                    'horizon_months': horizon,
                    'percentile': float(percentile),
                    'return_value': value,
                    'stat_type': 'percentile'
                })

            # Store summary statistics
            all_results.append({
                'weights_hash': weights_hash,
                'as_of_date': latest_date,
                'horizon_months': horizon,
                'percentile': 50.0,  # Use median as placeholder
                'return_value': mc_result['mean_return'],
                'stat_type': 'mean'
            })
            all_results.append({
                'weights_hash': weights_hash,
                'as_of_date': latest_date,
                'horizon_months': horizon,
                'percentile': 50.0,  # Use median as placeholder
                'return_value': mc_result['std_return'],
                'stat_type': 'std'
            })

    print(f"\nTotal Monte Carlo results: {len(all_results):,}")

    # Save results
    results_df = pd.DataFrame(all_results)
    results_df.to_parquet(args.output, index=False, compression='snappy')
    print(f"Saved to {args.output}")

    # Save weight grid mapping
    weight_mapping_file = args.output.replace('.parquet', '_weights.parquet')
    weight_mapping = []
    for weights in weight_grid:
        weights_dict = dict(zip(tickers, weights))
        weights_hash = compute_weights_hash(weights_dict)
        row = {'weights_hash': weights_hash}
        row.update({f'weight_{ticker}': w for ticker, w in weights_dict.items()})
        weight_mapping.append(row)

    weight_mapping_df = pd.DataFrame(weight_mapping)
    weight_mapping_df.to_parquet(weight_mapping_file, index=False, compression='snappy')
    print(f"Saved weight mapping to {weight_mapping_file}")

    # Print statistics
    print(f"\nStatistics:")
    print(f"  Unique weight combinations: {len(weight_mapping_df):,}")
    print(f"  Horizons: {horizons}")
    print(f"  Total data points: {len(results_df):,}")
    print(f"  File size: {results_df.memory_usage(deep=True).sum() / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main()
