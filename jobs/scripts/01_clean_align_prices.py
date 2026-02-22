#!/usr/bin/env python3
"""
GCP Compute Task: Clean and Align Historical Prices
Usage: python 01_clean_align_prices.py --input raw_prices.parquet --output clean_prices.parquet
"""

import argparse
import pandas as pd
import numpy as np


def clean_and_align(df: pd.DataFrame) -> pd.DataFrame:
    """Clean missing values and align to trading calendar."""
    print(f"Input shape: {df.shape}")

    # Sort by ticker and date
    df = df.sort_values(['ticker', 'trade_date']).reset_index(drop=True)

    # Forward fill missing values within each ticker
    df['close'] = df.groupby('ticker')['close'].ffill()

    # Drop rows with remaining NaN
    df = df.dropna(subset=['close'])

    # Calculate daily returns
    df['return'] = df.groupby('ticker')['close'].pct_change()
    df['log_return'] = np.log(df['close'] / df.groupby('ticker')['close'].shift(1))

    # Quality flags
    df['is_outlier'] = (df['return'].abs() > 0.5)  # 50% daily move

    print(f"Output shape: {df.shape}")
    print(f"Outliers detected: {df['is_outlier'].sum()}")

    return df


def main():
    parser = argparse.ArgumentParser(description='Clean and align prices')
    parser.add_argument('--input', required=True, help='Input parquet file')
    parser.add_argument('--output', default='clean_prices.parquet', help='Output file path')
    args = parser.parse_args()

    df = pd.read_parquet(args.input)
    df_clean = clean_and_align(df)

    df_clean.to_parquet(args.output, index=False, compression='snappy')
    print(f"Saved to {args.output}")


if __name__ == "__main__":
    main()
