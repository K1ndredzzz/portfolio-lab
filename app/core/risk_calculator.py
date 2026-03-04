"""
Real-time portfolio risk metrics calculator.

Computation logic:
- Covariance is computed live via Ledoit-Wolf on the windowed log-return data
  (window = horizon_months trading days =~ horizon_months * 21).
- Expected return = mean(daily log_return) * 252, over the same window.
- VaR / CVaR use the *parametric (normal) method* based on annualized mu/sigma.
  Do NOT scale daily percentiles by sqrt(252) - that is statistically wrong.
- Max Drawdown is computed over the COMMON available history, not the window.
- Sortino uses downside deviation from the windowed daily returns.
"""
import logging
import numpy as np
import pandas as pd
from typing import Dict
from pathlib import Path
from scipy.stats import norm as norm_dist
from sklearn.covariance import LedoitWolf

logger = logging.getLogger(__name__)


class RiskCalculator:
    """Calculate portfolio risk metrics in real-time."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self._tickers = None        # canonical ticker order
        self._returns_data = None   # all daily log returns (wide DataFrame)

    def _load_returns_data(self) -> pd.DataFrame:
        """
        Load historical daily log returns from clean_prices.parquet.
        log_return = ln(close / prev_close) - already decimal form.
        """
        if self._returns_data is None:
            prices_file = self.data_dir / "clean_prices.parquet"
            prices_df = pd.read_parquet(prices_file)
            prices_df = prices_df[prices_df["log_return"].notna()].copy()
            wide = prices_df.pivot(
                index="trade_date", columns="ticker", values="log_return"
            ).sort_index()
            self._returns_data = wide

            logger.info(
                "Loaded returns: shape=%s  date_range=%s -> %s  freq=DAILY",
                wide.shape,
                wide.index.min(),
                wide.index.max(),
            )
        return self._returns_data

    def _get_tickers(self) -> list:
        """Return sorted ticker list (canonical order for weight arrays)."""
        if self._tickers is None:
            self._load_returns_data()
            self._tickers = sorted(self._returns_data.columns.tolist())
        return self._tickers

    def calculate_metrics(
        self,
        weights: Dict[str, float],
        as_of_date: str,          # kept for API compatibility; not used for slicing
        horizon_months: int = 36,
        risk_free_rate: float = 0.02,
    ) -> Dict[str, float]:
        """
        Calculate portfolio risk metrics.

        Parameters
        ----------
        weights : dict  {ticker: weight}  - will be normalised internally.
        as_of_date : str   YYYY-MM-DD   (for future use / logging).
        horizon_months : int   Number of months for the estimation window.
        risk_free_rate : float   Annual risk-free rate (default 2 %).

        Returns
        -------
        dict of float risk metrics.
        """
        all_returns = self._load_returns_data()
        tickers = self._get_tickers()

        # -- weight vector (aligned to canonical ticker order) -----------------
        w_raw = np.array([weights.get(t, 0.0) for t in tickers])
        w_sum = w_raw.sum()
        if w_sum < 1e-12:
            raise ValueError("All weights are zero.")
        w = w_raw / w_sum

        # -- Align returns DataFrame to canonical ticker order -----------------
        aligned_all = all_returns.reindex(columns=tickers).fillna(0.0)

        # -- Slice to estimation window (Phase 3) -----------------------------
        #   Approx trading days: 252 per year -> 21 per month
        n_days_window = int(horizon_months * 21)
        aligned_window = aligned_all.tail(n_days_window)

        logger.info(
            "Window: horizon=%d mo  n_days=%d  actual_rows=%d  "
            "date_range=%s -> %s",
            horizon_months,
            n_days_window,
            len(aligned_window),
            aligned_window.index.min() if len(aligned_window) else "N/A",
            aligned_window.index.max() if len(aligned_window) else "N/A",
        )

        # -- Covariance via Ledoit-Wolf on the windowed data (Phase 3) ---------
        if len(aligned_window) > len(tickers) + 5:
            lw = LedoitWolf()
            cov_daily = lw.fit(aligned_window.values).covariance_
        else:
            # Degenerate window - fall back to sample covariance
            cov_daily = np.cov(aligned_window.values, rowvar=False)
        cov_ann = cov_daily * 252   # annualise

        # -- Expected return - windowed, annualised (Phase 3) -----------------
        mean_daily = aligned_window.mean().values      # shape: (n_tickers,)
        expected_ann = mean_daily * 252                # annualise
        portfolio_return = float(w @ expected_ann)

        # -- Volatility - from windowed covariance (Phase 3) ------------------
        portfolio_variance_ann = float(w @ cov_ann @ w)
        portfolio_volatility = float(np.sqrt(max(portfolio_variance_ann, 0.0)))

        logger.info(
            "Metrics | mu=%.4f  sigma=%.4f  rf=%.4f",
            portfolio_return,
            portfolio_volatility,
            risk_free_rate,
        )

        # -- Sharpe (annualised) -----------------------------------------------
        sharpe = (
            (portfolio_return - risk_free_rate) / portfolio_volatility
            if portfolio_volatility > 1e-10 else 0.0
        )

        # -- Sortino (windowed daily returns) ---------------------------------
        daily_port = (aligned_window * w).sum(axis=1)
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

        # -- Parametric VaR / CVaR (Phase 1 & 7) ------------------------------
        #
        # Use parametric normal method with annualised sigma.
        # Force Expected Return (mu) = 0 to measure pure volatility-driven downside.
        #
        z_05 = norm_dist.ppf(0.05)   # =~ -1.6449
        z_01 = norm_dist.ppf(0.01)   # =~ -2.3263

        var_95 = float(0.0 + z_05 * portfolio_volatility)
        var_99 = float(0.0 + z_01 * portfolio_volatility)

        # CVaR = mu - sigma * phi(z_alpha)/alpha
        cvar_95 = float(0.0 - portfolio_volatility * norm_dist.pdf(z_05) / 0.05)
        cvar_99 = float(0.0 - portfolio_volatility * norm_dist.pdf(z_01) / 0.01)

        # -- Max Drawdown - COMMON HISTORY (Phase 2, 3, 6) --------------------
        #
        # Only use the common date range where ALL selected assets have data,
        # avoiding artificial 0.0% returns padding that damps historical drawdowns.
        #
        # Active tickers (weight > 0)
        active_tickers = [t for t, wt in zip(tickers, w_raw) if wt > 1e-12]
        if not active_tickers:
            active_tickers = tickers
        
        # Drop rows where any active ticker is NA to get the common history
        common_returns = all_returns[active_tickers].dropna()
        if len(common_returns) > 0:
            active_min_date = common_returns.index.min()
            if active_min_date > pd.Timestamp("2008-01-01"):
                logger.warning(
                    "Max Drawdown: Common history begins %s, missing 2008 crisis data!", 
                    active_min_date
                )
        
        # Normalise weights for the active subset
        w_active = np.array([weights.get(t, 0.0) for t in active_tickers])
        w_active = w_active / w_active.sum()

        daily_port_full = (common_returns * w_active).sum(axis=1)
        cum_full = np.exp(daily_port_full.cumsum())
        drawdown_full = cum_full / cum_full.cummax() - 1
        max_drawdown = float(drawdown_full.min()) if len(drawdown_full) > 0 else 0.0

        calmar = (
            portfolio_return / abs(max_drawdown) if abs(max_drawdown) > 1e-10 else 0.0
        )

        return {
            "expected_return_ann": portfolio_return,
            "volatility_ann":      portfolio_volatility,
            "sharpe":              float(sharpe),
            "sortino":             float(sortino),
            "var95":               var_95,
            "var99":               var_99,
            "cvar95":              cvar_95,
            "cvar99":              cvar_99,
            "max_drawdown":        max_drawdown,
            "calmar":              float(calmar),
        }


# -- Singleton ------------------------------------------------------------------
_calculator: "RiskCalculator | None" = None


def get_calculator() -> RiskCalculator:
    """Get (or create) the global RiskCalculator instance."""
    global _calculator
    if _calculator is None:
        _calculator = RiskCalculator()
    return _calculator
