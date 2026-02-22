#!/usr/bin/env python3
"""
GCP Compute Task: Stress Testing for Portfolios
Usage: python 40_compute_stress_tests.py --cov covariance_matrices.npz --portfolios portfolios.parquet --output stress_tests.parquet
"""

import argparse
import pandas as pd
import numpy as np
from datetime import datetime


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
    parser = argparse.ArgumentParser(description='Compute stress tests')
    parser.add_argument('--cov', default='data/covariance_matrices.npz', help='Covariance matrices file')
    parser.add_argument('--portfolios', default='data/portfolios.parquet', help='Portfolio weights file')
    parser.add_argument('--output', default='data/stress_tests.parquet', help='Output file')
    args = parser.parse_args()

    print(f"Loading covariance matrices from {args.cov}...")
    cov_data = np.load(args.cov, allow_pickle=True)
    tickers = cov_data['tickers'].tolist()

    print(f"Loading portfolios from {args.portfolios}...")
    portfolios_df = pd.read_parquet(args.portfolios)

    # Select latest snapshot for each model
    latest_portfolios = portfolios_df.sort_values('as_of_date').groupby('model').tail(1)

    print(f"\nRunning stress tests...")
    print(f"Scenarios: {list(STRESS_SCENARIOS.keys())}")

    all_results = []

    for _, portfolio in latest_portfolios.iterrows():
        model = portfolio['model']
        as_of_date = portfolio['as_of_date']

        # Extract weights
        weight_cols = [col for col in portfolio.index if col.startswith('weight_')]
        weights = portfolio[weight_cols].values

        print(f"\n  Model: {model}")
        print(f"  As of: {as_of_date}")

        for scenario_name, scenario in STRESS_SCENARIOS.items():
            result = apply_stress_scenario(weights, tickers, scenario)

            all_results.append({
                'model': model,
                'as_of_date': as_of_date,
                'scenario_name': scenario_name,
                'scenario_description': result['scenario_description'],
                'portfolio_return': result['portfolio_return']
            })

            print(f"    {scenario['description']}: {result['portfolio_return']:.2%}")

    print(f"\nTotal stress test results: {len(all_results)}")

    # Save to parquet
    results_df = pd.DataFrame(all_results)
    results_df.to_parquet(args.output, index=False, compression='snappy')
    print(f"Saved to {args.output}")

    # Summary statistics
    print(f"\nSummary by model:")
    summary = results_df.groupby('model')['portfolio_return'].agg(['mean', 'min', 'max'])
    print(summary)


if __name__ == "__main__":
    main()
