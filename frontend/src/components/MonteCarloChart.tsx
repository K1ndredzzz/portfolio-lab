import React, { useEffect, useRef } from 'react';
import Plot from 'react-plotly.js';
import { usePortfolioStore } from '../store';
import { getMonteCarlo } from '../api';

const MonteCarloChart: React.FC = () => {
  const weights = usePortfolioStore((state) => state.weights);
  const horizon_months = usePortfolioStore((state) => state.horizon_months);
  const monteCarlo = usePortfolioStore((state) => state.monteCarlo);
  const setMonteCarlo = usePortfolioStore((state) => state.setMonteCarlo);
  const isLoadingMonteCarlo = usePortfolioStore((state) => state.isLoadingMonteCarlo);
  const setLoadingMonteCarlo = usePortfolioStore((state) => state.setLoadingMonteCarlo);
  const monteCarloError = usePortfolioStore((state) => state.monteCarloError);
  const setMonteCarloError = usePortfolioStore((state) => state.setMonteCarloError);

  const abortControllerRef = useRef<AbortController | null>(null);

  // Serialize weights for dependency tracking
  const weightsKey = JSON.stringify(weights);

  useEffect(() => {
    let isMounted = true;

    const fetchMonteCarlo = async () => {
      // Skip if no weights configured
      if (Object.keys(weights).length === 0) return;

      // Cancel previous request
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      abortControllerRef.current = new AbortController();

      if (isMounted) {
        setLoadingMonteCarlo(true);
        setMonteCarloError(null);
      }

      try {
        const data = await getMonteCarlo(weights, horizon_months, abortControllerRef.current.signal);
        if (isMounted) {
          setMonteCarlo(data);
        }
      } catch (error: any) {
        if (error.name !== 'AbortError' && isMounted) {
          console.error('Failed to fetch Monte Carlo data:', error);
          setMonteCarloError(error.message || 'Failed to fetch Monte Carlo data');
          setMonteCarlo(null);
        }
      } finally {
        if (isMounted) {
          setLoadingMonteCarlo(false);
        }
      }
    };

    fetchMonteCarlo();

    return () => {
      isMounted = false;
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [weightsKey, horizon_months]);

  if (isLoadingMonteCarlo) {
    return (
      <div className="monte-carlo-chart loading" aria-busy="true" aria-label="Loading Monte Carlo simulation">
        <div className="spinner">Loading Monte Carlo simulation...</div>
      </div>
    );
  }

  if (monteCarloError) {
    return (
      <div className="monte-carlo-chart error" role="alert">
        <p>Error: {monteCarloError}</p>
      </div>
    );
  }

  if (!monteCarlo) {
    return (
      <div className="monte-carlo-chart empty" role="status">
        <p>No Monte Carlo data available</p>
      </div>
    );
  }

  // Extract percentiles for visualization
  const percentiles = Object.entries(monteCarlo.distribution)
    .filter(([key]) => key.startsWith('p'))
    .map(([key, value]) => ({
      percentile: parseInt(key.substring(1)),
      value: value * 100,
    }))
    .sort((a, b) => a.percentile - b.percentile);

  const data = [
    {
      x: percentiles.map((p) => p.percentile),
      y: percentiles.map((p) => p.value),
      type: 'scatter',
      mode: 'lines+markers',
      name: 'Return Distribution',
      line: { color: '#007bff', width: 3 },
      marker: { size: 8 },
      fill: 'tozeroy',
      fillcolor: 'rgba(0, 123, 255, 0.1)',
    },
  ];

  const layout = {
    title: `Monte Carlo Simulation (${horizon_months} months, ${monteCarlo.n_simulations.toLocaleString()} paths)`,
    xaxis: {
      title: 'Percentile',
      ticksuffix: 'th',
    },
    yaxis: {
      title: 'Return (%)',
      tickformat: '.1f',
    },
    hovermode: 'closest',
    showlegend: false,
    annotations: [
      {
        x: 5,
        y: monteCarlo.distribution.p5 * 100,
        text: `5th: ${(monteCarlo.distribution.p5 * 100).toFixed(1)}%`,
        showarrow: true,
        arrowhead: 2,
        ax: -40,
        ay: -40,
      },
      {
        x: 50,
        y: monteCarlo.distribution.p50 * 100,
        text: `Median: ${(monteCarlo.distribution.p50 * 100).toFixed(1)}%`,
        showarrow: true,
        arrowhead: 2,
        ax: 0,
        ay: -50,
      },
      {
        x: 95,
        y: monteCarlo.distribution.p95 * 100,
        text: `95th: ${(monteCarlo.distribution.p95 * 100).toFixed(1)}%`,
        showarrow: true,
        arrowhead: 2,
        ax: 40,
        ay: -40,
      },
    ],
  };

  return (
    <div className="monte-carlo-chart">
      <div className="chart-header">
        <h2>Monte Carlo Simulation</h2>
        <div className="stats">
          <div className="stat">
            <span className="label">Mean:</span>
            <span className="value">{(monteCarlo.mean_return * 100).toFixed(2)}%</span>
          </div>
          <div className="stat">
            <span className="label">Std Dev:</span>
            <span className="value">{(monteCarlo.std_return * 100).toFixed(2)}%</span>
          </div>
        </div>
      </div>

      <Plot
        data={data as any}
        layout={layout as any}
        config={{ responsive: true }}
        style={{ width: '100%', height: '500px' }}
      />

      <style>{`
        .monte-carlo-chart {
          padding: 20px;
          background: white;
          border-radius: 8px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .monte-carlo-chart.loading,
        .monte-carlo-chart.empty {
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

        .stats {
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
      `}</style>
    </div>
  );
};

export default MonteCarloChart;
