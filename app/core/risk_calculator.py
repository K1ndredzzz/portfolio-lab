"""
Real-time portfolio risk metrics calculator.
"""
import numpy as np
import pandas as pd
from typing import Dict
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
        """Load precomputed covariance matrices (already annualized *252)."""
        if self._cov_matrices is None:
            cov_file = self.data_dir / "covariance_matrices.npz"
            data = np.load(cov_file)
            self._dates = data['dates']
            self._tickers = data['tickers']
            self._cov_matrices = {date: data[date] for date in self._dates}
        return self._cov_matrices

    def _load_returns_data(self):
        """Load historical log returns — same source as the covariance/MC pipeline."""
        if self._returns_data is None:
            prices_file = self.data_dir / "clean_prices.parquet"
            prices_df = pd.read_parquet(prices_file)

            # Use the pre-computed log_return column (same as covariance script)
            prices_df = prices_df[prices_df['log_return'].notna()].copy()
            returns_df = prices_df.pivot(
                index='trade_date', columns='ticker', values='log_return'
            )
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

        The covariance matrix stored in covariance_matrices.npz is already
        annualized (multiplied by 252 during the rolling-covariance job).
        Therefore portfolio_variance = w' @ Cov_ann @ w is already an
        annualized variance — do NOT multiply by 252 again.
        """
        self._load_covariance_matrices()
        self._load_returns_data()

        # Closest covariance snapshot (already annualized)
        closest_date = self._get_closest_date(as_of_date)
        cov_matrix_ann = self._cov_matrices[closest_date]

        # Weight vector aligned to tickers
        weight_array = np.array([weights.get(t, 0.0) for t in self._tickers])
        weight_sum = weight_array.sum()
        if weight_sum > 0:
            weight_array = weight_array / weight_sum

        # ── Expected returns ─────────────────────────────────────────────────
        # log_return daily mean → annualize by *252  (matches MC pipeline)
        aligned = self._returns_data.reindex(columns=self._tickers).fillna(0.0)
        annual_log_returns = aligned.mean().values * 252      # shape: (n_tickers,)
        portfolio_return = float(np.dot(weight_array, annual_log_returns))

        # ── Volatility ───────────────────────────────────────────────────────
        # Cov already annualized → just sqrt, no extra *252
        portfolio_variance_ann = float(np.dot(weight_array, cov_matrix_ann @ weight_array))
        portfolio_volatility = float(np.sqrt(max(portfolio_variance_ann, 0.0)))

        # ── Sharpe ───────────────────────────────────────────────────────────
        sharpe = (
            (portfolio_return - risk_free_rate) / portfolio_volatility
            if portfolio_volatility > 1e-10 else 0.0
        )

        # ── Downside metrics (daily log returns) ─────────────────────────────
        daily_port = (aligned * weight_array).sum(axis=1)
        rf_daily = risk_free_rate / 252
        downside = daily_port[daily_port < rf_daily]
        downside_std = (
            float(downside.std() * np.sqrt(252)) if len(downside) > 1
            else portfolio_volatility
        )
        sortino = (
            (portfolio_return - risk_free_rate) / downside_std
            if downside_std > 1e-10 else 0.0
        )

        # ── VaR / CVaR ───────────────────────────────────────────────────────
        scale = np.sqrt(252)
        var_95 = float(np.percentile(daily_port, 5) * scale)
        var_99 = float(np.percentile(daily_port, 1) * scale)
        cvar_95 = float(daily_port[daily_port <= np.percentile(daily_port, 5)].mean() * scale)
        cvar_99 = float(daily_port[daily_port <= np.percentile(daily_port, 1)].mean() * scale)

        # ── Max Drawdown / Calmar ─────────────────────────────────────────────
        cum = (1 + daily_port).cumprod()
        drawdown = (cum - cum.expanding().max()) / cum.expanding().max()
        max_drawdown = float(drawdown.min())
        calmar = portfolio_return / abs(max_drawdown) if max_drawdown != 0 else 0.0

        return {
            "expected_return_ann": portfolio_return,
            "volatility_ann": portfolio_volatility,
            "sharpe": float(sharpe),
            "sortino": float(sortino),
            "var95": var_95,
            "var99": var_99,
            "cvar95": cvar_95,
            "cvar99": cvar_99,
            "max_drawdown": max_drawdown,
            "calmar": float(calmar),
        }


# Global instance
_calculator = None


def get_calculator() -> RiskCalculator:
    """Get or create global calculator instance."""
    global _calculator
    if _calculator is None:
        _calculator = RiskCalculator()
    return _calculator
