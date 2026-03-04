"""
Portfolio optimization algorithms: Risk Parity, Max Sharpe, Min Variance.
"""
import numpy as np
from scipy.optimize import minimize
from typing import Dict, List, Optional


def optimize_risk_parity(
    cov_matrix: np.ndarray,
    tickers: List[str],
) -> Dict[str, float]:
    """
    Risk Parity (Equal Risk Contribution) optimization.
    Minimizes the variance of risk contributions across assets.
    """
    n = len(tickers)

    def objective(weights: np.ndarray) -> float:
        port_vol = np.sqrt(weights @ cov_matrix @ weights)
        if port_vol == 0:
            return 1e10
        marginal = cov_matrix @ weights
        risk_contrib = weights * marginal / port_vol
        target = port_vol / n
        return float(np.sum((risk_contrib - target) ** 2))

    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
    bounds = tuple((1e-6, 1.0) for _ in range(n))
    x0 = np.ones(n) / n

    result = minimize(objective, x0, method="SLSQP", bounds=bounds, constraints=constraints,
                      options={"ftol": 1e-12, "maxiter": 1000})

    weights = result.x if result.success else x0
    weights = np.maximum(weights, 0)
    weights /= weights.sum()
    return {ticker: float(w) for ticker, w in zip(tickers, weights)}


def optimize_min_variance(
    cov_matrix: np.ndarray,
    tickers: List[str],
) -> Dict[str, float]:
    """
    Minimum Variance optimization.
    Minimizes portfolio variance with no target-return constraint.
    """
    n = len(tickers)

    def objective(weights: np.ndarray) -> float:
        return float(weights @ cov_matrix @ weights)

    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
    bounds = tuple((0.0, 1.0) for _ in range(n))
    x0 = np.ones(n) / n

    result = minimize(objective, x0, method="SLSQP", bounds=bounds, constraints=constraints,
                      options={"ftol": 1e-12, "maxiter": 1000})

    weights = result.x if result.success else x0
    weights = np.maximum(weights, 0)
    weights /= weights.sum()
    return {ticker: float(w) for ticker, w in zip(tickers, weights)}


def optimize_max_sharpe(
    expected_returns: np.ndarray,
    cov_matrix: np.ndarray,
    tickers: List[str],
    risk_free_rate: float = 0.02,
) -> Dict[str, float]:
    """
    Maximum Sharpe Ratio optimization.
    Maximizes (portfolio_return - risk_free_rate) / portfolio_volatility.
    """
    n = len(tickers)

    def neg_sharpe(weights: np.ndarray) -> float:
        port_return = float(weights @ expected_returns)
        port_vol = float(np.sqrt(weights @ cov_matrix @ weights))
        if port_vol < 1e-10:
            return 1e10
        return -(port_return - risk_free_rate) / port_vol

    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
    bounds = tuple((0.0, 1.0) for _ in range(n))
    x0 = np.ones(n) / n

    result = minimize(neg_sharpe, x0, method="SLSQP", bounds=bounds, constraints=constraints,
                      options={"ftol": 1e-12, "maxiter": 1000})

    weights = result.x if result.success else x0
    weights = np.maximum(weights, 0)
    weights /= weights.sum()
    return {ticker: float(w) for ticker, w in zip(tickers, weights)}
