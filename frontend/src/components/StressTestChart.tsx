import React, { useEffect, useRef } from 'react';
import Plot from 'react-plotly.js';
import { usePortfolioStore } from '../store';
import { getStressTest } from '../api';

const StressTestChart: React.FC = () => {
  const model = usePortfolioStore((state) => state.model);
  const stressTests = usePortfolioStore((state) => state.stressTests);
  const setStressTests = usePortfolioStore((state) => state.setStressTests);
  const isLoadingStress = usePortfolioStore((state) => state.isLoadingStress);
  const setLoadingStress = usePortfolioStore((state) => state.setLoadingStress);
  const stressError = usePortfolioStore((state) => state.stressError);
  const setStressError = usePortfolioStore((state) => state.setStressError);

  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    let isMounted = true;

    const fetchStressTests = async () => {
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
        const data = await getStressTest(model, abortControllerRef.current.signal);
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
  }, [model]);

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
        color: stressTests.map((t) => (t.portfolio_return < 0 ? '#dc3545' : '#28a745')),
      },
      text: stressTests.map((t) => `${(t.portfolio_return * 100).toFixed(2)}%`),
      textposition: 'outside',
    },
  ];

  const layout = {
    title: 'Stress Test Results',
    xaxis: {
      title: 'Crisis Scenario',
    },
    yaxis: {
      title: 'Portfolio Return (%)',
      tickformat: '.1f',
      zeroline: true,
      zerolinecolor: '#666',
      zerolinewidth: 2,
    },
    hovermode: 'closest',
    showlegend: false,
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
        config={{ responsive: true }}
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
          padding: 20px;
          background: white;
          border-radius: 8px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .stress-test-chart.loading,
        .stress-test-chart.empty {
          display: flex;
          justify-content: center;
          align-items: center;
          min-height: 400px;
          color: #666;
        }

        .chart-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 20px;
        }

        .chart-header h2 {
          margin: 0;
          font-size: 24px;
        }

        .summary {
          display: flex;
          gap: 20px;
        }

        .stat {
          display: flex;
          flex-direction: column;
          align-items: flex-end;
        }

        .stat .label {
          font-size: 12px;
          color: #666;
        }

        .stat .value {
          font-size: 18px;
          font-weight: bold;
          color: #007bff;
        }

        .stat .value.worst {
          color: #dc3545;
        }

        .scenarios-detail {
          margin-top: 20px;
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
          gap: 16px;
        }

        .scenario-card {
          padding: 16px;
          border: 1px solid #e0e0e0;
          border-radius: 8px;
          background: #fafafa;
        }

        .scenario-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 8px;
        }

        .scenario-header h4 {
          margin: 0;
          font-size: 16px;
        }

        .return {
          font-size: 20px;
          font-weight: bold;
        }

        .return.negative {
          color: #dc3545;
        }

        .return.positive {
          color: #28a745;
        }

        .scenario-date {
          font-size: 12px;
          color: #666;
        }
      `}</style>
    </div>
  );
};

export default StressTestChart;
