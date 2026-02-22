#!/usr/bin/env python3
"""
Load computed results into PostgreSQL
Usage: python 50_load_postgres.py
"""

import argparse
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from datetime import datetime, date
import os
import json


def get_db_connection():
    """Create database connection."""
    db_url = os.getenv('POSTGRES_DSN', 'postgresql://portfolio:portfolio@localhost:8031/portfolio_lab')
    engine = create_engine(db_url)
    return engine


def get_or_create_dataset(conn, version_tag: str = 'v1.0') -> str:
    """Get or create dataset version and return dataset_id."""
    # Check if version exists
    result = conn.execute(
        text("SELECT dataset_id FROM portfolio_lab.dataset_versions WHERE version_tag = :version_tag"),
        {"version_tag": version_tag}
    )
    row = result.fetchone()

    if row:
        dataset_id = str(row[0])
        print(f"Using existing dataset version {version_tag} (ID: {dataset_id})")
        return dataset_id

    # Create new dataset version
    print(f"Creating new dataset version {version_tag}...")
    result = conn.execute(
        text("""
            INSERT INTO portfolio_lab.dataset_versions
            (version_tag, date_start, date_end, is_active, notes)
            VALUES (:version_tag, :date_start, :date_end, true, :notes)
            RETURNING dataset_id
        """),
        {
            "version_tag": version_tag,
            "date_start": date(2000, 1, 1),
            "date_end": date(2025, 12, 31),
            "notes": "Initial dataset with mock data and computed results"
        }
    )
    dataset_id = str(result.fetchone()[0])
    conn.commit()
    print(f"Created dataset version {version_tag} (ID: {dataset_id})")
    return dataset_id


def load_covariance_snapshots(conn, dataset_id: str, cov_file: str):
    """Load covariance matrix snapshots."""
    print(f"\nLoading covariance matrices from {cov_file}...")
    cov_data = np.load(cov_file, allow_pickle=True)
    tickers = cov_data['tickers'].tolist()
    dates = cov_data['dates'].tolist()

    # Clear existing data
    conn.execute(
        text("DELETE FROM portfolio_lab.covariance_snapshots WHERE dataset_id = :dataset_id"),
        {"dataset_id": dataset_id}
    )

    # Insert new data
    for snapshot_date in dates:
        cov_matrix = cov_data[snapshot_date]
        cov_list = cov_matrix.tolist()

        conn.execute(
            text("""
                INSERT INTO portfolio_lab.covariance_snapshots
                (dataset_id, as_of_date, tickers, covariance_matrix)
                VALUES (:dataset_id, :as_of_date, CAST(:tickers AS jsonb), CAST(:covariance_matrix AS jsonb))
            """),
            {
                "dataset_id": dataset_id,
                "as_of_date": snapshot_date,
                "tickers": json.dumps(tickers),
                "covariance_matrix": json.dumps(cov_list)
            }
        )

    conn.commit()
    print(f"Loaded {len(dates)} covariance snapshots")


def load_monte_carlo(conn, dataset_id: str, mc_file: str):
    """Load Monte Carlo simulation results."""
    print(f"\nLoading Monte Carlo results from {mc_file}...")
    df = pd.read_parquet(mc_file)

    # Clear existing data
    conn.execute(
        text("DELETE FROM portfolio_lab.monte_carlo_distributions WHERE dataset_id = :dataset_id"),
        {"dataset_id": dataset_id}
    )

    # Group by model and horizon
    grouped = df.groupby(['model', 'as_of_date', 'horizon_months'])

    for (model, as_of_date, horizon), group in grouped:
        # Extract percentiles
        percentile_data = group[group['stat_type'] == 'percentile']
        distribution = {
            f"p{int(row['percentile'])}": float(row['return_value'])
            for _, row in percentile_data.iterrows()
        }

        # Extract mean and std
        mean_row = group[group['stat_type'] == 'mean'].iloc[0]
        std_row = group[group['stat_type'] == 'std'].iloc[0]

        conn.execute(
            text("""
                INSERT INTO portfolio_lab.monte_carlo_distributions
                (dataset_id, model, as_of_date, horizon_months, n_simulations,
                 mean_return, std_return, distribution)
                VALUES (:dataset_id, :model, :as_of_date, :horizon_months,
                        :n_simulations, :mean_return, :std_return, CAST(:distribution AS jsonb))
            """),
            {
                "dataset_id": dataset_id,
                "model": model,
                "as_of_date": as_of_date,
                "horizon_months": int(horizon),
                "n_simulations": 10000,
                "mean_return": float(mean_row['return_value']),
                "std_return": float(std_row['return_value']),
                "distribution": json.dumps(distribution)
            }
        )

    conn.commit()
    print(f"Loaded {len(grouped)} Monte Carlo records")


def load_stress_tests(conn, dataset_id: str, stress_file: str):
    """Load stress test results."""
    print(f"\nLoading stress tests from {stress_file}...")
    df = pd.read_parquet(stress_file)

    # Clear existing data
    conn.execute(
        text("DELETE FROM portfolio_lab.stress_results WHERE dataset_id = :dataset_id"),
        {"dataset_id": dataset_id}
    )

    # Insert new data
    for _, row in df.iterrows():
        conn.execute(
            text("""
                INSERT INTO portfolio_lab.stress_results
                (dataset_id, model, as_of_date, scenario_name, portfolio_return)
                VALUES (:dataset_id, :model, :as_of_date, :scenario_name, :portfolio_return)
            """),
            {
                "dataset_id": dataset_id,
                "model": row['model'],
                "as_of_date": row['as_of_date'],
                "scenario_name": row['scenario_name'],
                "portfolio_return": float(row['portfolio_return'])
            }
        )

    conn.commit()
    print(f"Loaded {len(df)} stress test records")


def main():
    parser = argparse.ArgumentParser(description='Load computed results into PostgreSQL')
    parser.add_argument('--monte-carlo', default='data/monte_carlo.parquet')
    parser.add_argument('--stress-tests', default='data/stress_tests.parquet')
    parser.add_argument('--covariance', default='data/covariance_matrices.npz')
    parser.add_argument('--version', default='v1.0', help='Dataset version tag')
    args = parser.parse_args()

    print("Connecting to PostgreSQL...")
    engine = get_db_connection()

    with engine.connect() as conn:
        # Get or create dataset version
        dataset_id = get_or_create_dataset(conn, args.version)

        # Load all data
        load_covariance_snapshots(conn, dataset_id, args.covariance)
        load_monte_carlo(conn, dataset_id, args.monte_carlo)
        load_stress_tests(conn, dataset_id, args.stress_tests)

    print("\n✅ All data loaded successfully!")


if __name__ == "__main__":
    main()
