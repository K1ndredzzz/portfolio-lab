#!/usr/bin/env python3
"""
GCP Compute Task: Stress Testing with Weight Grid
Usage: python 40_compute_stress_tests_grid.py --cov covariance_matrices.npz --output stress_tests_grid.parquet --step 0.05
"""

import argparse
import pandas as pd
import numpy as np
import hashlib
import json
from datetime import datetime


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


# Stress scenarios (asset-level shocks in %)
STRESS_SCENARIOS = {
    '2008_financial_crisis': {
        'description': '2008 Financial Crisis',
        'shocks': {
            'SPY': -0.37, 'QQQ': -0.42, 'IWM': -0.34,
            'TLT': 0.14, 'GLD': 0.05, 'BTC': -0.50,
            'EEM': -0.53, 'EFA': -0.43, 'FXI': -0.48,
            'USO': -0.54, 'DBA': -0.14
        }
    },
    '2020_covid_crash': {
        'description': '2020 COVID-19 Crash',
        'shocks': {
            'SPY': -0.34, 'QQQ': -0.30, 'IWM': -0.42,
            'TLT': 0.21, 'GLD': 0.08, 'BTC': -0.40,
            'EEM': -0.31, 'EFA': -0.35, 'FXI': -0.28,
            'USO': -0.66, 'DBA': -0.08
        }
    },
    '2022_rate_hikes': {
        'description': '2022 Rate Hikes',
        'shocks': {
            'SPY': -0.18, 'QQQ': -0.33, 'IWM': -0.21,
            'TLT': -0.31, 'GLD': -0.01, 'BTC': -0.64,
            'EEM': -0.20, 'EFA': -0.14, 'FXI': -0.22,
            'USO': 0.07, 'DBA': 0.16
        }
    }
}


def apply_stress_scenario(weights: np.ndarray, tickers: list, scenario: dict) -> dict:
    """Apply stress scenario to portfolio."""
    shocks = scenario['shocks']

    # Compute portfolio return under stress
    portfolio_return = 0.0
    for ticker, weight in zip(tickers, weights):
        shock = shocks.get(ticker, 0.0)
        portfolio_return += weight * shock

    return {
        'portfolio_return': portfolio_return,
        'scenario_description': scenario['description']
    }


def main():
    parser = argparse.ArgumentParser(description='Compute stress tests with weight grid')
    parser.add_argument('--cov', default='data/covariance_matrices.npz', help='Covariance matrices file')
    parser.add_argument('--output', default='data/stress_tests_grid.parquet', help='Output file')
    parser.add_argument('--step', type=float, default=0.10, help='Weight step size (default: 0.10 = 10%)')
    parser.add_argument('--max-combinations', type=int, default=None, help='Max combinations to compute (for testing)')
    args = parser.parse_args()

    print(f"Loading covariance matrices from {args.cov}...")
    cov_data = np.load(args.cov, allow_pickle=True)
    tickers = cov_data['tickers'].tolist()
    dates = cov_data['dates'].tolist()
    n_assets = len(tickers)

    # Use latest date
    latest_date = sorted(dates)[-1]

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

    print(f"\nRunning stress tests...")
    print(f"  Scenarios: {list(STRESS_SCENARIOS.keys())}")

    all_results = []

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

        for scenario_name, scenario in STRESS_SCENARIOS.items():
            result = apply_stress_scenario(weights, tickers, scenario)

            all_results.append({
                'weights_hash': weights_hash,
                'as_of_date': latest_date,
                'scenario_name': scenario_name,
                'scenario_description': result['scenario_description'],
                'portfolio_return': result['portfolio_return']
            })

    print(f"\nTotal stress test results: {len(all_results):,}")

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
    print(f"  Scenarios: {len(STRESS_SCENARIOS)}")
    print(f"  Total data points: {len(results_df):,}")
    print(f"  File size: {results_df.memory_usage(deep=True).sum() / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main()
