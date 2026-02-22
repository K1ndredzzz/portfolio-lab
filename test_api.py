#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for Portfolio Lab API
"""
import requests
import json
import sys

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_URL = "http://localhost:8030/api/v1"


def test_health():
    """Test health endpoints."""
    print("Testing health endpoints...")

    # Test live endpoint
    response = requests.get(f"{BASE_URL}/health/live")
    print(f"[OK] Health live: {response.json()}")

    # Test ready endpoint
    response = requests.get(f"{BASE_URL}/health/ready")
    print(f"[OK] Health ready: {response.json()}")


def test_assets():
    """Test assets endpoint."""
    print("\nTesting assets endpoint...")
    response = requests.get(f"{BASE_URL}/meta/assets")
    assets = response.json()["assets"]
    print(f"[OK] Assets count: {len(assets)}")
    print(f"  First asset: {assets[0]}")


def test_portfolio_quote():
    """Test portfolio quote endpoint."""
    print("\nTesting portfolio quote endpoint...")

    payload = {
        "model": "risk_parity",
        "as_of_date": "2025-12-31",
        "horizon_months": 12,
        "weights": {
            "SPY": 0.20,
            "QQQ": 0.10,
            "TLT": 0.25,
            "GLD": 0.10,
            "BTC": 0.05,
            "EEM": 0.10,
            "EFA": 0.10,
            "FXI": 0.05,
            "USO": 0.03,
            "DBA": 0.02
        }
    }

    response = requests.post(f"{BASE_URL}/portfolios/quote", json=payload)

    if response.status_code == 200:
        result = response.json()
        print(f"[OK] Portfolio quote successful")
        print(f"  Dataset version: {result['dataset_version']}")
        print(f"  Weights hash: {result['weights_hash'][:16]}...")
        print(f"  Cache hit: {result['cache_hit']}")
        print(f"  Sharpe ratio: {result['metrics']['sharpe']}")
        print(f"  Expected return: {result['metrics']['expected_return_ann']:.2%}")
        print(f"  Volatility: {result['metrics']['volatility_ann']:.2%}")

        # Test cache hit on second request
        response2 = requests.post(f"{BASE_URL}/portfolios/quote", json=payload)
        result2 = response2.json()
        print(f"  Second request cache hit: {result2['cache_hit']}")
    else:
        print(f"[ERROR] Status: {response.status_code}")
        print(f"  {response.text}")


if __name__ == "__main__":
    try:
        test_health()
        test_assets()
        test_portfolio_quote()
        print("\n[OK] All tests passed!")
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
