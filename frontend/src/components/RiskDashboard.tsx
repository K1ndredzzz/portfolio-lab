import React from 'react';
import { usePortfolioStore } from '../store';

const RiskDashboard: React.FC = () => {
  const metrics = usePortfolioStore((state) => state.metrics);
  const isLoadingMetrics = usePortfolioStore((state) => state.isLoadingMetrics);
  const metricsError = usePortfolioStore((state) => state.metricsError);

  if (isLoadingMetrics) {
    return (
      <div className="risk-dashboard loading" aria-busy="true" aria-label="Loading risk metrics">
        <div className="spinner"></div>
      </div>
    );
  }

  if (metricsError) {
    return (
      <div className="risk-dashboard error" role="alert">
        <p>Error loading metrics: {metricsError}</p>
      </div>
    );
  }

  if (!metrics) {
    return (
      <div className="risk-dashboard empty" role="status">
        <div className="empty-state">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21.21 15.89A10 10 0 1 1 8 2.83"></path>
            <path d="M22 12A10 10 0 0 0 12 2v10z"></path>
          </svg>
          <p>Configure your portfolio to see risk metrics</p>
        </div>
      </div>
    );
  }

  const formatPercent = (value: number) => `${(value * 100).toFixed(2)}%`;
  const formatRatio = (value: number) => value.toFixed(2);

  const kpis = [
    {
      label: 'Expected Return',
      sublabel: 'Annualized',
      value: formatPercent(metrics.expected_return_ann),
      color: metrics.expected_return_ann > 0 ? 'var(--accent-green)' : 'var(--danger)',
    },
    {
      label: 'Volatility',
      sublabel: 'Annualized',
      value: formatPercent(metrics.volatility_ann),
      color: 'var(--text-primary)',
    },
    {
      label: 'Sharpe Ratio',
      sublabel: 'Ann. Return / Ann. Vol',
      value: formatRatio(metrics.sharpe),
      color: metrics.sharpe > 1 ? 'var(--accent-green)' : metrics.sharpe > 0.5 ? 'var(--warning)' : 'var(--danger)',
    },
    {
      label: 'Sortino Ratio',
      sublabel: 'Ann. Excess / Downside',
      value: formatRatio(metrics.sortino),
      color: metrics.sortino > 1 ? 'var(--accent-green)' : metrics.sortino > 0.5 ? 'var(--warning)' : 'var(--danger)',
    },
    {
      label: 'VaR (95%)',
      sublabel: 'Annualized',
      value: formatPercent(metrics.var95),
      color: 'var(--danger)',
    },
    {
      label: 'VaR (99%)',
      sublabel: 'Annualized',
      value: formatPercent(metrics.var99),
      color: 'var(--danger)',
    },
    {
      label: 'CVaR (95%)',
      sublabel: 'Annualized',
      value: formatPercent(metrics.cvar95),
      color: 'var(--danger)',
    },
    {
      label: 'CVaR (99%)',
      sublabel: 'Annualized',
      value: formatPercent(metrics.cvar99),
      color: 'var(--danger)',
    },
    {
      label: 'Max Drawdown',
      sublabel: 'Full History',
      value: formatPercent(metrics.max_drawdown),
      color: 'var(--danger)',
    },
    {
      label: 'Calmar Ratio',
      sublabel: 'Ann. Return / |Max DD|',
      value: formatRatio(metrics.calmar),
      color: metrics.calmar > 0.5 ? 'var(--accent-green)' : 'var(--warning)',
    },
  ];

  return (
    <div className="risk-dashboard">
      <div className="dashboard-header">
        <h2>Risk Metrics</h2>
      </div>
      <div className="kpi-grid">
        {kpis.map((kpi) => (
          <div key={kpi.label} className="kpi-card">
            <div className="kpi-label">{kpi.label}</div>
            <div className="kpi-value" style={{ color: kpi.color, textShadow: `0 0 20px ${kpi.color}22` }}>
              {kpi.value}
            </div>
            {kpi.sublabel && (
              <div className="kpi-sublabel">{kpi.sublabel}</div>
            )}
          </div>
        ))}
      </div>
      <div className="metrics-note">
        Computed from daily log-returns (5-yr rolling window, Ledoit-Wolf shrinkage).
        VaR &amp; CVaR are annualized via √252 scaling of daily percentiles.
      </div>

      <style>{`
        .risk-dashboard {
          padding: 32px;
          height: 100%;
          display: flex;
          flex-direction: column;
        }

        .dashboard-header {
          margin-bottom: 24px;
        }

        .risk-dashboard h2 {
          margin: 0;
          font-size: 20px;
          font-weight: 600;
          color: var(--text-primary);
        }

        .risk-dashboard.loading,
        .risk-dashboard.empty,
        .risk-dashboard.error {
          display: flex;
          justify-content: center;
          align-items: center;
          min-height: 100%;
          flex: 1;
        }

        .empty-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 16px;
          color: var(--text-secondary);
        }

        .empty-state svg {
          opacity: 0.5;
        }

        .error {
          color: var(--danger);
          background: rgba(239, 68, 68, 0.1);
          padding: 16px;
          border-radius: 8px;
          border: 1px solid rgba(239, 68, 68, 0.2);
        }

        .kpi-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
          gap: 16px;
          flex: 1;
        }

        .kpi-card {
          padding: 20px;
          border: 1px solid var(--border-color);
          border-radius: 12px;
          background: rgba(255, 255, 255, 0.02);
          transition: all 0.2s ease;
          display: flex;
          flex-direction: column;
          justify-content: center;
        }

        .kpi-card:hover {
          transform: translateY(-2px);
          background: rgba(255, 255, 255, 0.04);
          border-color: rgba(255, 255, 255, 0.2);
          box-shadow: 0 8px 20px rgba(0, 0, 0, 0.2);
        }

        .kpi-label {
          font-size: 11px;
          color: var(--text-secondary);
          margin-bottom: 8px;
          text-transform: uppercase;
          letter-spacing: 1px;
          font-weight: 600;
        }

        .kpi-value {
          font-size: 28px;
          font-weight: 700;
          letter-spacing: -0.5px;
          line-height: 1.2;
        }

        .kpi-sublabel {
          font-size: 10px;
          color: var(--text-secondary);
          margin-top: 4px;
          opacity: 0.7;
          letter-spacing: 0.3px;
        }

        .metrics-note {
          margin-top: 16px;
          padding: 10px 14px;
          font-size: 11px;
          color: var(--text-secondary);
          background: rgba(255,255,255,0.02);
          border: 1px solid var(--border-color);
          border-radius: 8px;
          line-height: 1.6;
          opacity: 0.8;
        }
      `}</style>
    </div>
  );
};

export default RiskDashboard;
