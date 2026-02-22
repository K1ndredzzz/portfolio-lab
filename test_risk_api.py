#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for Risk Analysis API endpoints
"""
import requests
import json
import sys

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_URL = "http://localhost:8030/api/v1"


def test_monte_carlo():
    """Test Monte Carlo simulation endpoint."""
    print("\n=== Testing Monte Carlo Simulation ===")

    payload = {
        "model": "risk_parity",
        "horizon_months": 36
    }

    response = requests.post(f"{BASE_URL}/risk/monte-carlo", json=payload)

    if response.status_code == 200:
        result = response.json()
        print(f"[OK] Monte Carlo simulation successful")
        print(f"  Model: {result['model']}")
        print(f"  Horizon: {result['horizon_months']} months")
        print(f"  Simulations: {result['n_simulations']}")
        print(f"  Mean return: {result['mean_return']:.2%}")
        print(f"  Std return: {result['std_return']:.2%}")
        print(f"  Distribution:")
        for key in ['p5', 'p50', 'p95']:
            if key in result['distribution']:
                print(f"    {key}: {result['distribution'][key]:.2%}")
    else:
        print(f"[ERROR] Status: {response.status_code}")
        print(f"  {response.text}")


def test_stress_tests():
    """Test stress test endpoint."""
    print("\n=== Testing Stress Tests ===")

    payload = {
        "model": "min_variance"
    }

    response = requests.post(f"{BASE_URL}/risk/stress", json=payload)

    if response.status_code == 200:
        results = response.json()
        print(f"[OK] Stress test successful")
        print(f"  Scenarios: {len(results)}")
        for result in results:
            print(f"  {result['scenario_description']}: {result['portfolio_return']:.2%}")
    else:
        print(f"[ERROR] Status: {response.status_code}")
        print(f"  {response.text}")


def test_covariance():
    """Test covariance matrix endpoint."""
    print("\n=== Testing Covariance Matrix ===")

    payload = {
        "as_of_date": "2025-12-31"
    }

    response = requests.post(f"{BASE_URL}/risk/covariance", json=payload)

    if response.status_code == 200:
        result = response.json()
        print(f"[OK] Covariance matrix retrieved")
        print(f"  As of date: {result['as_of_date']}")
        print(f"  Window: {result['window_days']} days")
        print(f"  Assets: {len(result['tickers'])}")
        print(f"  Tickers: {', '.join(result['tickers'][:5])}...")
        print(f"  Matrix shape: {len(result['covariance_matrix'])}x{len(result['covariance_matrix'][0])}")
    else:
        print(f"[ERROR] Status: {response.status_code}")
        print(f"  {response.text}")


def test_all_models_monte_carlo():
    """Test Monte Carlo for all models."""
    print("\n=== Testing All Models (Monte Carlo) ===")

    models = ["max_sharpe", "risk_parity", "min_variance"]
    horizon = 60

    for model in models:
        payload = {
            "model": model,
            "horizon_months": horizon
        }

        response = requests.post(f"{BASE_URL}/risk/monte-carlo", json=payload)

        if response.status_code == 200:
            result = response.json()
            print(f"[OK] {model}: Mean={result['mean_return']:.2%}, "
                  f"5th={result['distribution'].get('p5', 0):.2%}, "
                  f"95th={result['distribution'].get('p95', 0):.2%}")
        else:
            print(f"[ERROR] {model}: {response.status_code}")


if __name__ == "__main__":
    try:
        test_monte_carlo()
        test_stress_tests()
        test_covariance()
        test_all_models_monte_carlo()
        print("\n[OK] All risk API tests completed!")
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
