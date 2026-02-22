import React from 'react';
import { usePortfolioStore } from '../store';

const RiskDashboard: React.FC = () => {
  const metrics = usePortfolioStore((state) => state.metrics);
  const isLoadingMetrics = usePortfolioStore((state) => state.isLoadingMetrics);
  const metricsError = usePortfolioStore((state) => state.metricsError);

  if (isLoadingMetrics) {
    return (
      <div className="risk-dashboard loading" aria-busy="true" aria-label="Loading risk metrics">
        <div className="spinner">Loading...</div>
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
        <p>Configure your portfolio to see risk metrics</p>
      </div>
    );
  }

  const formatPercent = (value: number) => `${(value * 100).toFixed(2)}%`;
  const formatRatio = (value: number) => value.toFixed(2);

  const kpis = [
    {
      label: 'Expected Return',
      value: formatPercent(metrics.expected_return_ann),
      color: metrics.expected_return_ann > 0 ? '#28a745' : '#dc3545',
    },
    {
      label: 'Volatility',
      value: formatPercent(metrics.volatility_ann),
      color: '#6c757d',
    },
    {
      label: 'Sharpe Ratio',
      value: formatRatio(metrics.sharpe),
      color: metrics.sharpe > 1 ? '#28a745' : metrics.sharpe > 0.5 ? '#b7791f' : '#dc3545',
    },
    {
      label: 'Sortino Ratio',
      value: formatRatio(metrics.sortino),
      color: metrics.sortino > 1 ? '#28a745' : metrics.sortino > 0.5 ? '#b7791f' : '#dc3545',
    },
    {
      label: 'VaR (95%)',
      value: formatPercent(metrics.var95),
      color: '#dc3545',
    },
    {
      label: 'VaR (99%)',
      value: formatPercent(metrics.var99),
      color: '#dc3545',
    },
    {
      label: 'CVaR (95%)',
      value: formatPercent(metrics.cvar95),
      color: '#dc3545',
    },
    {
      label: 'CVaR (99%)',
      value: formatPercent(metrics.cvar99),
      color: '#dc3545',
    },
    {
      label: 'Max Drawdown',
      value: formatPercent(metrics.max_drawdown),
      color: '#dc3545',
    },
    {
      label: 'Calmar Ratio',
      value: formatRatio(metrics.calmar),
      color: metrics.calmar > 0.5 ? '#28a745' : '#b7791f',
    },
  ];

  return (
    <div className="risk-dashboard">
      <h2>Risk Metrics</h2>
      <div className="kpi-grid">
        {kpis.map((kpi) => (
          <div key={kpi.label} className="kpi-card">
            <div className="kpi-label">{kpi.label}</div>
            <div className="kpi-value" style={{ color: kpi.color }}>
              {kpi.value}
            </div>
          </div>
        ))}
      </div>

      <style>{`
        .risk-dashboard {
          padding: 20px;
          background: white;
          border-radius: 8px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .risk-dashboard.loading,
        .risk-dashboard.empty {
          display: flex;
          justify-content: center;
          align-items: center;
          min-height: 200px;
          color: #666;
        }

        .spinner {
          font-size: 18px;
        }

        .risk-dashboard h2 {
          margin: 0 0 20px 0;
          font-size: 24px;
        }

        .kpi-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
          gap: 16px;
        }

        .kpi-card {
          padding: 16px;
          border: 1px solid #e0e0e0;
          border-radius: 8px;
          background: #fafafa;
          transition: transform 0.2s, box-shadow 0.2s;
        }

        .kpi-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }

        .kpi-label {
          font-size: 12px;
          color: #666;
          margin-bottom: 8px;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .kpi-value {
          font-size: 24px;
          font-weight: bold;
        }
      `}</style>
    </div>
  );
};

export default RiskDashboard;
