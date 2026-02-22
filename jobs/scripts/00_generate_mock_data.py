#!/usr/bin/env python3
"""
Generate mock historical price data for testing
Usage: python 00_generate_mock_data.py --output raw_prices.parquet
"""

import argparse
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

ASSET_UNIVERSE = [
    "SPY", "QQQ", "IWM", "TLT", "GLD", "BTC",
    "EEM", "EFA", "FXI", "USO", "DBA"
]

# Mock parameters (annual returns and volatilities)
ASSET_PARAMS = {
    "SPY": (0.10, 0.15),   # 10% return, 15% vol
    "QQQ": (0.12, 0.20),   # 12% return, 20% vol
    "IWM": (0.09, 0.18),
    "TLT": (0.04, 0.12),
    "GLD": (0.06, 0.16),
    "BTC": (0.50, 0.80),   # High return, high vol
    "EEM": (0.08, 0.22),
    "EFA": (0.07, 0.17),
    "FXI": (0.06, 0.25),
    "USO": (0.02, 0.30),
    "DBA": (0.03, 0.18)
}


def generate_mock_prices(ticker: str, start_date: str, end_date: str, initial_price: float = 100.0) -> pd.DataFrame:
    """Generate mock price data using geometric Brownian motion."""
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)

    dates = pd.date_range(start, end, freq='B')  # Business days
    n_days = len(dates)

    mu, sigma = ASSET_PARAMS[ticker]
    dt = 1/252  # Daily time step

    # Generate returns
    returns = np.random.normal(mu * dt, sigma * np.sqrt(dt), n_days)
    prices = initial_price * np.exp(np.cumsum(returns))

    # Generate OHLCV data
    df = pd.DataFrame({
        'ticker': ticker,
        'trade_date': dates,
        'close': prices
    })

    # Generate open, high, low from close
    df['open'] = df['close'] * (1 + np.random.normal(0, 0.005, n_days))
    df['high'] = df[['open', 'close']].max(axis=1) * (1 + np.abs(np.random.normal(0, 0.01, n_days)))
    df['low'] = df[['open', 'close']].min(axis=1) * (1 - np.abs(np.random.normal(0, 0.01, n_days)))
    df['volume'] = np.random.lognormal(15, 1, n_days).astype(int)

    return df[['ticker', 'trade_date', 'open', 'high', 'low', 'close', 'volume']]


def main():
    parser = argparse.ArgumentParser(description='Generate mock historical prices')
    parser.add_argument('--output', default='raw_prices.parquet', help='Output file path')
    parser.add_argument('--start', default='2000-01-01', help='Start date')
    parser.add_argument('--end', default='2025-12-31', help='End date')
    args = parser.parse_args()

    print(f"Generating mock data for {len(ASSET_UNIVERSE)} assets...")
    print(f"Date range: {args.start} to {args.end}")

    np.random.seed(42)  # For reproducibility

    all_data = []
    for ticker in ASSET_UNIVERSE:
        print(f"  Generating {ticker}...")
        df = generate_mock_prices(ticker, args.start, args.end)
        all_data.append(df)

    combined = pd.concat(all_data, ignore_index=True)

    combined.to_parquet(args.output, index=False, compression='snappy')
    print(f"\nSaved to {args.output}")
    print(f"Shape: {combined.shape}")
    print(f"Date range: {combined['trade_date'].min()} to {combined['trade_date'].max()}")
    print(f"Tickers: {sorted(combined['ticker'].unique())}")
    print(f"Sample data:")
    print(combined.head(10))


if __name__ == "__main__":
    main()
