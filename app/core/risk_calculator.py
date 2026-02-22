"""
Real-time portfolio risk metrics calculator.
"""
import numpy as np
import pandas as pd
from typing import Dict, Optional
from datetime import datetime
from pathlib import Path


class RiskCalculator:
    """Calculate portfolio risk metrics in real-time."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self._cov_matrices = None
        self._dates = None
        self._tickers = None
        self._returns_data = None

    def _load_covariance_matrices(self):
        """Load precomputed covariance matrices."""
        if self._cov_matrices is None:
            cov_file = self.data_dir / "covariance_matrices.npz"
            data = np.load(cov_file)
            self._dates = data['dates']
            self._tickers = data['tickers']
            self._cov_matrices = {date: data[date] for date in self._dates}
        return self._cov_matrices

    def _load_returns_data(self):
        """Load historical returns for downside risk calculations."""
        if self._returns_data is None:
            prices_file = self.data_dir / "clean_prices.parquet"
            prices_df = pd.read_parquet(prices_file)

            # Pivot from long format to wide format
            prices_wide = prices_df.pivot(index='trade_date', columns='ticker', values='close')

            # Calculate returns
            returns_df = prices_wide.pct_change().dropna()
            self._returns_data = returns_df
        return self._returns_data

    def _get_closest_date(self, target_date: str) -> str:
        """Find the closest available date in covariance matrices."""
        self._load_covariance_matrices()
        target = pd.to_datetime(target_date)
        dates_dt = pd.to_datetime(self._dates)
        idx = np.argmin(np.abs(dates_dt - target))
        return self._dates[idx]

    def calculate_metrics(
        self,
        weights: Dict[str, float],
        as_of_date: str,
        horizon_months: int = 12,
        risk_free_rate: float = 0.02
    ) -> Dict[str, float]:
        """
        Calculate portfolio risk metrics.

        Args:
            weights: Dict of {ticker: weight}, weights should sum to 1.0
            as_of_date: Date for covariance matrix (YYYY-MM-DD)
            horizon_months: Investment horizon in months
            risk_free_rate: Annual risk-free rate (default 2%)

        Returns:
            Dict of risk metrics
        """
        # Load data
        self._load_covariance_matrices()
        self._load_returns_data()

        # Get closest available date
        closest_date = self._get_closest_date(as_of_date)
        cov_matrix = self._cov_matrices[closest_date]

        # Convert weights dict to array (aligned with tickers)
        weight_array = np.array([weights.get(ticker, 0.0) for ticker in self._tickers])

        # Normalize weights
        weight_sum = weight_array.sum()
        if weight_sum > 0:
            weight_array = weight_array / weight_sum

        # Calculate expected returns (using historical mean)
        returns_df = self._returns_data
        mean_returns = returns_df.mean().values

        # Portfolio expected return (annualized)
        portfolio_return = np.dot(weight_array, mean_returns) * 252

        # Portfolio volatility (annualized)
        portfolio_variance = np.dot(weight_array, np.dot(cov_matrix, weight_array))
        portfolio_volatility = np.sqrt(portfolio_variance * 252)

        # Sharpe Ratio
        sharpe = (portfolio_return - risk_free_rate) / portfolio_volatility if portfolio_volatility > 0 else 0.0

        # Calculate downside metrics
        portfolio_returns = (returns_df * weight_array).sum(axis=1)

        # Sortino Ratio (downside deviation)
        downside_returns = portfolio_returns[portfolio_returns < 0]
        downside_std = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else portfolio_volatility
        sortino = (portfolio_return - risk_free_rate) / downside_std if downside_std > 0 else 0.0

        # VaR and CVaR (95% and 99%)
        var_95 = np.percentile(portfolio_returns, 5) * np.sqrt(252)
        var_99 = np.percentile(portfolio_returns, 1) * np.sqrt(252)

        cvar_95 = portfolio_returns[portfolio_returns <= np.percentile(portfolio_returns, 5)].mean() * np.sqrt(252)
        cvar_99 = portfolio_returns[portfolio_returns <= np.percentile(portfolio_returns, 1)].mean() * np.sqrt(252)

        # Max Drawdown
        cumulative_returns = (1 + portfolio_returns).cumprod()
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown = drawdown.min()

        # Calmar Ratio
        calmar = portfolio_return / abs(max_drawdown) if max_drawdown != 0 else 0.0

        return {
            "expected_return_ann": float(portfolio_return),
            "volatility_ann": float(portfolio_volatility),
            "sharpe": float(sharpe),
            "sortino": float(sortino),
            "var95": float(var_95),
            "var99": float(var_99),
            "cvar95": float(cvar_95),
            "cvar99": float(cvar_99),
            "max_drawdown": float(max_drawdown),
            "calmar": float(calmar)
        }


# Global instance
_calculator = None

def get_calculator() -> RiskCalculator:
    """Get or create global calculator instance."""
    global _calculator
    if _calculator is None:
        _calculator = RiskCalculator()
    return _calculator
