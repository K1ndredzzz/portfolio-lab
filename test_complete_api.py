#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Complete API Test Suite for Portfolio Lab
"""
import requests
import json
import sys

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_URL = "http://localhost:8030/api/v1"


def print_section(title):
    """Print section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def test_health_endpoints():
    """Test health check endpoints."""
    print_section("Health Endpoints")

    # Test live endpoint
    response = requests.get(f"{BASE_URL}/health/live")
    print(f"[{'OK' if response.status_code == 200 else 'FAIL'}] GET /health/live: {response.json()}")

    # Test ready endpoint
    response = requests.get(f"{BASE_URL}/health/ready")
    print(f"[{'OK' if response.status_code == 200 else 'FAIL'}] GET /health/ready: {response.json()}")


def test_meta_endpoints():
    """Test metadata endpoints."""
    print_section("Metadata Endpoints")

    response = requests.get(f"{BASE_URL}/meta/assets")
    if response.status_code == 200:
        assets = response.json()["assets"]
        print(f"[OK] GET /meta/assets: {len(assets)} assets")
        print(f"     Assets: {', '.join([a['ticker'] for a in assets[:5]])}...")
    else:
        print(f"[FAIL] GET /meta/assets: {response.status_code}")


def test_portfolio_quote():
    """Test portfolio quote endpoint."""
    print_section("Portfolio Quote")

    payload = {
        "model": "risk_parity",
        "as_of_date": "2025-12-31",
        "horizon_months": 12,
        "weights": {
            "SPY": 0.20, "QQQ": 0.10, "TLT": 0.25,
            "GLD": 0.10, "BTC": 0.05, "EEM": 0.10,
            "EFA": 0.10, "FXI": 0.05, "USO": 0.03, "DBA": 0.02
        }
    }

    response = requests.post(f"{BASE_URL}/portfolios/quote", json=payload)

    if response.status_code == 200:
        result = response.json()
        print(f"[OK] POST /portfolios/quote")
        print(f"     Sharpe: {result['metrics']['sharpe']:.2f}")
        print(f"     Return: {result['metrics']['expected_return_ann']:.2%}")
        print(f"     Volatility: {result['metrics']['volatility_ann']:.2%}")
        print(f"     Cache hit: {result['cache_hit']}")
    else:
        print(f"[FAIL] POST /portfolios/quote: {response.status_code}")


def test_monte_carlo():
    """Test Monte Carlo endpoint."""
    print_section("Monte Carlo Simulation")

    models = ["max_sharpe", "risk_parity", "min_variance"]

    for model in models:
        payload = {"model": model, "horizon_months": 36}
        response = requests.post(f"{BASE_URL}/risk/monte-carlo", json=payload)

        if response.status_code == 200:
            result = response.json()
            print(f"[OK] {model:15s} | Mean: {result['mean_return']:>7.2%} | "
                  f"5th: {result['distribution'].get('p5', 0):>7.2%} | "
                  f"95th: {result['distribution'].get('p95', 0):>7.2%}")
        else:
            print(f"[FAIL] {model}: {response.status_code}")


def test_stress_tests():
    """Test stress test endpoint."""
    print_section("Stress Tests")

    models = ["max_sharpe", "risk_parity", "min_variance"]

    for model in models:
        payload = {"model": model}
        response = requests.post(f"{BASE_URL}/risk/stress", json=payload)

        if response.status_code == 200:
            results = response.json()
            returns = {r['scenario_name']: r['portfolio_return'] for r in results}
            print(f"[OK] {model:15s} | 2008: {returns.get('2008_financial_crisis', 0):>7.2%} | "
                  f"2020: {returns.get('2020_covid_crash', 0):>7.2%} | "
                  f"2022: {returns.get('2022_rate_hikes', 0):>7.2%}")
        else:
            print(f"[FAIL] {model}: {response.status_code}")


def test_covariance():
    """Test covariance matrix endpoint."""
    print_section("Covariance Matrix")

    payload = {"as_of_date": "2025-12-31"}
    response = requests.post(f"{BASE_URL}/risk/covariance", json=payload)

    if response.status_code == 200:
        result = response.json()
        print(f"[OK] POST /risk/covariance")
        print(f"     Date: {result['as_of_date']}")
        print(f"     Window: {result['window_days']} days")
        print(f"     Assets: {len(result['tickers'])}")
        print(f"     Matrix: {len(result['covariance_matrix'])}x{len(result['covariance_matrix'][0])}")
    else:
        print(f"[FAIL] POST /risk/covariance: {response.status_code}")


def run_all_tests():
    """Run all API tests."""
    print("\n" + "="*60)
    print("  Portfolio Lab API Test Suite")
    print("="*60)

    try:
        test_health_endpoints()
        test_meta_endpoints()
        test_portfolio_quote()
        test_monte_carlo()
        test_stress_tests()
        test_covariance()

        print("\n" + "="*60)
        print("  ✅ All tests completed successfully!")
        print("="*60 + "\n")

    except Exception as e:
        print(f"\n[ERROR] Test suite failed: {e}\n")
        raise


if __name__ == "__main__":
    run_all_tests()
