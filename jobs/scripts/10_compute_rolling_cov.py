#!/usr/bin/env python3
"""
GCP Compute Task: Rolling Covariance Matrix Calculation
Usage: python 10_compute_rolling_cov.py --input clean_prices.parquet --output covariance_matrices.npz
"""

import argparse
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.covariance import LedoitWolf

WINDOW_DAYS = 1260  # 5 years of trading days
SNAPSHOT_FREQ = 'ME'  # Monthly snapshots


def compute_rolling_covariance(returns_df: pd.DataFrame, window_days: int) -> dict:
    """Compute rolling covariance matrices with shrinkage."""
    print(f"Computing rolling covariance with {window_days}-day window...")

    # Pivot to wide format (dates x tickers)
    returns_wide = returns_df.pivot(index='trade_date', columns='ticker', values='log_return')
    returns_wide = returns_wide.sort_index()

    print(f"Returns shape: {returns_wide.shape}")
    print(f"Date range: {returns_wide.index.min()} to {returns_wide.index.max()}")

    # Generate monthly snapshot dates
    snapshot_dates = pd.date_range(
        start=returns_wide.index.min() + pd.Timedelta(days=window_days),
        end=returns_wide.index.max(),
        freq=SNAPSHOT_FREQ
    )

    covariance_matrices = {}
    tickers = returns_wide.columns.tolist()

    for snapshot_date in snapshot_dates:
        # Get window data
        window_end = returns_wide.index.asof(snapshot_date)
        if pd.isna(window_end):
            continue

        window_start_idx = returns_wide.index.get_loc(window_end) - window_days + 1
        if window_start_idx < 0:
            continue

        window_data = returns_wide.iloc[window_start_idx:window_start_idx + window_days]

        # Check for missing data
        if window_data.isnull().any().any():
            print(f"  Warning: Missing data in window ending {snapshot_date}, skipping")
            continue

        # Compute shrinkage covariance
        lw = LedoitWolf()
        cov_matrix = lw.fit(window_data.values).covariance_

        # Annualize (252 trading days)
        cov_matrix_ann = cov_matrix * 252

        date_key = snapshot_date.strftime('%Y-%m-%d')
        covariance_matrices[date_key] = cov_matrix_ann

        if len(covariance_matrices) % 12 == 0:
            print(f"  Processed {len(covariance_matrices)} snapshots (latest: {date_key})")

    print(f"\nTotal snapshots: {len(covariance_matrices)}")
    return {'matrices': covariance_matrices, 'tickers': tickers}


def main():
    parser = argparse.ArgumentParser(description='Compute rolling covariance matrices')
    parser.add_argument('--input', default='data/clean_prices.parquet', help='Input parquet file')
    parser.add_argument('--output', default='data/covariance_matrices.npz', help='Output npz file')
    args = parser.parse_args()

    print(f"Loading data from {args.input}...")
    df = pd.read_parquet(args.input)

    # Filter to only include rows with log_return
    df = df[df['log_return'].notna()].copy()
    print(f"Loaded {len(df)} return records")

    result = compute_rolling_covariance(df, WINDOW_DAYS)

    # Save to npz format
    print(f"\nSaving to {args.output}...")
    np.savez_compressed(
        args.output,
        tickers=result['tickers'],
        dates=list(result['matrices'].keys()),
        **{date: matrix for date, matrix in result['matrices'].items()}
    )

    print(f"Saved {len(result['matrices'])} covariance matrices")
    print(f"Matrix shape: {list(result['matrices'].values())[0].shape}")
    print(f"Tickers: {result['tickers']}")


if __name__ == "__main__":
    main()
