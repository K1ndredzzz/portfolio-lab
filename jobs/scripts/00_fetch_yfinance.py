#!/usr/bin/env python3
"""
GCP Compute Task: Fetch Historical Prices from yfinance
Usage: python 00_fetch_yfinance.py --output raw_prices.parquet
"""

import argparse
from datetime import datetime
import pandas as pd
import yfinance as yf
import time


ASSET_UNIVERSE = [
    "SPY", "QQQ", "IWM", "TLT", "GLD", "BTC-USD",
    "EEM", "EFA", "FXI", "USO", "DBA"
]

START_DATE = "2000-01-01"
END_DATE = "2025-12-31"


def fetch_single_ticker(ticker: str, start: str, end: str, retries: int = 3) -> pd.DataFrame:
    """Fetch data for a single ticker with retry logic."""
    for attempt in range(retries):
        try:
            print(f"Fetching {ticker} (attempt {attempt + 1}/{retries})...")
            ticker_obj = yf.Ticker(ticker)
            data = ticker_obj.history(start=start, end=end, auto_adjust=True)

            if data.empty:
                print(f"  Warning: No data for {ticker}")
                return pd.DataFrame()

            # Reset index to get date as column
            data = data.reset_index()
            data['ticker'] = ticker.replace('-USD', '')  # BTC-USD -> BTC
            data = data.rename(columns={
                'Date': 'trade_date',
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            })

            print(f"  Success: {len(data)} records for {ticker}")
            return data[['ticker', 'trade_date', 'open', 'high', 'low', 'close', 'volume']]

        except Exception as e:
            print(f"  Error fetching {ticker}: {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                print(f"  Failed to fetch {ticker} after {retries} attempts")
                return pd.DataFrame()


def fetch_prices(tickers: list[str], start: str, end: str) -> pd.DataFrame:
    """Fetch historical prices for given tickers."""
    print(f"Fetching data for {len(tickers)} assets from {start} to {end}...")

    all_data = []
    for ticker in tickers:
        df = fetch_single_ticker(ticker, start, end)
        if not df.empty:
            all_data.append(df)
        time.sleep(1)  # Rate limiting

    if not all_data:
        print("ERROR: No data fetched for any ticker!")
        return pd.DataFrame()

    combined = pd.concat(all_data, ignore_index=True)
    print(f"\nTotal fetched: {len(combined)} records across {len(all_data)} tickers")
    return combined


def main():
    parser = argparse.ArgumentParser(description='Fetch historical prices')
    parser.add_argument('--output', default='raw_prices.parquet', help='Output file path')
    args = parser.parse_args()

    df = fetch_prices(ASSET_UNIVERSE, START_DATE, END_DATE)

    if df.empty:
        print("ERROR: No data to save!")
        return

    df.to_parquet(args.output, index=False, compression='snappy')
    print(f"\nSaved to {args.output}")
    print(f"Shape: {df.shape}")
    print(f"Date range: {df['trade_date'].min()} to {df['trade_date'].max()}")
    print(f"Tickers: {sorted(df['ticker'].unique())}")


if __name__ == "__main__":
    main()
