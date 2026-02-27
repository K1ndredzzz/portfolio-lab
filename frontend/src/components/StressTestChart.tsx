import React, { useEffect, useRef } from 'react';
import Plot from 'react-plotly.js';
import { usePortfolioStore } from '../store';
import { getStressTest } from '../api';

const StressTestChart: React.FC = () => {
  const weights = usePortfolioStore((state) => state.weights);
  const stressTests = usePortfolioStore((state) => state.stressTests);
  const setStressTests = usePortfolioStore((state) => state.setStressTests);
  const isLoadingStress = usePortfolioStore((state) => state.isLoadingStress);
  const setLoadingStress = usePortfolioStore((state) => state.setLoadingStress);
  const stressError = usePortfolioStore((state) => state.stressError);
  const setStressError = usePortfolioStore((state) => state.setStressError);

  const abortControllerRef = useRef<AbortController | null>(null);

  // Serialize weights for dependency tracking
  const weightsKey = JSON.stringify(weights);

  useEffect(() => {
    let isMounted = true;

    const fetchStressTests = async () => {
      // Skip if no weights configured
      if (Object.keys(weights).length === 0) return;

      // Cancel previous request
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      abortControllerRef.current = new AbortController();

      if (isMounted) {
        setLoadingStress(true);
        setStressError(null);
      }

      try {
        const data = await getStressTest(weights, abortControllerRef.current.signal);
        if (isMounted) {
          setStressTests(data);
        }
      } catch (error: any) {
        if (error.name !== 'AbortError' && isMounted) {
          console.error('Failed to fetch stress test data:', error);
          setStressError(error.message || 'Failed to fetch stress test data');
          setStressTests([]);
        }
      } finally {
        if (isMounted) {
          setLoadingStress(false);
        }
      }
    };

    fetchStressTests();

    return () => {
      isMounted = false;
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [weightsKey]);

  if (isLoadingStress) {
    return (
      <div className="stress-test-chart loading" aria-busy="true" aria-label="Loading stress test results">
        <div className="spinner">Loading stress test results...</div>
      </div>
    );
  }

  if (stressError) {
    return (
      <div className="stress-test-chart error" role="alert">
        <p>Error: {stressError}</p>
      </div>
    );
  }

  if (stressTests.length === 0) {
    return (
      <div className="stress-test-chart empty" role="status">
        <p>No stress test data available</p>
      </div>
    );
  }

  const data = [
    {
      x: stressTests.map((t) => t.scenario_description),
      y: stressTests.map((t) => t.portfolio_return * 100),
      type: 'bar',
      marker: {
        color: stressTests.map((t) => (t.portfolio_return < 0 ? '#EF4444' : '#10B981')),
        line: {
          color: stressTests.map((t) => (t.portfolio_return < 0 ? '#B91C1C' : '#059669')),
          width: 1,
        }
      },
      text: stressTests.map((t) => `${(t.portfolio_return * 100).toFixed(2)}%`),
      textposition: 'outside',
      textfont: {
        color: '#F3F4F6'
      }
    },
  ];

  const layout = {
    title: {
      text: 'Stress Test Results',
      font: { color: '#F3F4F6', family: 'Inter, sans-serif' }
    },
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: {
      color: '#9CA3AF',
      family: 'Inter, sans-serif'
    },
    xaxis: {
      title: 'Crisis Scenario',
      gridcolor: '#374151',
      tickangle: -45,
    },
    yaxis: {
      title: 'Portfolio Return (%)',
      tickformat: '.1f',
      gridcolor: '#374151',
      zeroline: true,
      zerolinecolor: '#9CA3AF',
      zerolinewidth: 2,
    },
    hovermode: 'closest',
    showlegend: false,
    margin: { t: 60, r: 20, l: 60, b: 100 }
  };

  return (
    <div className="stress-test-chart">
      <div className="chart-header">
        <h2>Stress Test Analysis</h2>
        <div className="summary">
          <div className="stat">
            <span className="label">Worst Case:</span>
            <span className="value worst">
              {(Math.min(...stressTests.map((t) => t.portfolio_return)) * 100).toFixed(2)}%
            </span>
          </div>
          <div className="stat">
            <span className="label">Average:</span>
            <span className="value">
              {(
                (stressTests.reduce((sum, t) => sum + t.portfolio_return, 0) / stressTests.length) *
                100
              ).toFixed(2)}%
            </span>
          </div>
        </div>
      </div>

      <Plot
        data={data as any}
        layout={layout as any}
        config={{ responsive: true, displayModeBar: false }}
        style={{ width: '100%', height: '400px' }}
      />

      <div className="scenarios-detail">
        {stressTests.map((test) => (
          <div key={test.scenario_name} className="scenario-card">
            <div className="scenario-header">
              <h4>{test.scenario_description}</h4>
              <span className={`return ${test.portfolio_return < 0 ? 'negative' : 'positive'}`}>
                {(test.portfolio_return * 100).toFixed(2)}%
              </span>
            </div>
            <div className="scenario-date">As of: {test.as_of_date}</div>
          </div>
        ))}
      </div>

      <style>{`
        .stress-test-chart {
          padding: 32px;
          height: 100%;
          display: flex;
          flex-direction: column;
        }

        .stress-test-chart.loading,
        .stress-test-chart.empty {
          display: flex;
          justify-content: center;
          align-items: center;
          min-height: 400px;
          color: var(--text-secondary);
        }

        .chart-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 24px;
        }

        .chart-header h2 {
          margin: 0;
          font-size: 20px;
          font-weight: 600;
          color: var(--text-primary);
        }

        .summary {
          display: flex;
          gap: 24px;
        }

        .stat {
          display: flex;
          flex-direction: column;
          align-items: flex-end;
          background: rgba(255, 255, 255, 0.03);
          padding: 8px 16px;
          border-radius: 8px;
          border: 1px solid var(--border-color);
        }

        .stat .label {
          font-size: 11px;
          color: var(--text-secondary);
          text-transform: uppercase;
          letter-spacing: 0.5px;
          margin-bottom: 4px;
        }

        .stat .value {
          font-size: 18px;
          font-weight: 700;
          color: var(--text-primary);
        }

        .stat .value.worst {
          color: var(--danger);
        }

        .scenarios-detail {
          margin-top: 32px;
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
          gap: 16px;
        }

        .scenario-card {
          padding: 16px;
          border: 1px solid var(--border-color);
          border-radius: 8px;
          background: rgba(255, 255, 255, 0.02);
          transition: all 0.2s;
        }

        .scenario-card:hover {
          background: rgba(255, 255, 255, 0.04);
          border-color: rgba(255, 255, 255, 0.15);
        }

        .scenario-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 12px;
        }

        .scenario-header h4 {
          margin: 0;
          font-size: fourteenpx;
          color: var(--text-primary);
          line-height: 1.4;
          font-weight: 500;
        }

        .return {
          font-size: 16px;
          font-weight: 700;
          padding: 4px 8px;
          border-radius: 4px;
          background: rgba(0, 0, 0, 0.2);
        }

        .return.negative {
          color: var(--danger);
          border: 1px solid rgba(239, 68, 68, 0.2);
        }

        .return.positive {
          color: var(--accent-green);
          border: 1px solid rgba(16, 185, 129, 0.2);
        }

        .scenario-date {
          font-size: 12px;
          color: var(--text-secondary);
        }
      `}</style>
    </div>
  );
};

export default StressTestChart;
