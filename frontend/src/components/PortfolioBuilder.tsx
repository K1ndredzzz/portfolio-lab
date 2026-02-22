import React, { useEffect, useState, useCallback, useRef } from 'react';
import { usePortfolioStore } from '../store';
import { getAssets, getPortfolioQuote } from '../api';
import { debounce } from 'lodash';
import type { PortfolioWeights } from '../types';

type ModelType = 'risk_parity' | 'max_sharpe' | 'min_variance';

const PortfolioBuilder: React.FC = () => {
  const assets = usePortfolioStore((state) => state.assets);
  const setAssets = usePortfolioStore((state) => state.setAssets);
  const weights = usePortfolioStore((state) => state.weights);
  const updateWeight = usePortfolioStore((state) => state.updateWeight);
  const model = usePortfolioStore((state) => state.model);
  const setModel = usePortfolioStore((state) => state.setModel);
  const horizon_months = usePortfolioStore((state) => state.horizon_months);
  const setHorizon = usePortfolioStore((state) => state.setHorizon);
  const as_of_date = usePortfolioStore((state) => state.as_of_date);
  const setMetrics = usePortfolioStore((state) => state.setMetrics);
  const setLoadingMetrics = usePortfolioStore((state) => state.setLoadingMetrics);
  const setMetricsError = usePortfolioStore((state) => state.setMetricsError);

  const [totalWeight, setTotalWeight] = useState(0);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Serialize weights for dependency tracking
  const weightsKey = JSON.stringify(weights);

  useEffect(() => {
    // Load assets on mount
    getAssets().then(setAssets).catch(console.error);
  }, [setAssets]);

  useEffect(() => {
    // Calculate total weight
    const total = Object.values(weights).reduce((sum, w) => sum + w, 0);
    setTotalWeight(total);
  }, [weights]);

  // Stable debounced API call with cancellation
  const fetchMetricsRef = useRef(
    debounce(async (
      currentModel: string,
      currentDate: string,
      currentHorizon: number,
      currentWeights: PortfolioWeights,
      controller: AbortController
    ) => {
      setLoadingMetrics(true);
      setMetricsError(null);

      try {
        const response = await getPortfolioQuote(
          currentModel as ModelType,
          currentDate,
          currentHorizon,
          currentWeights,
          controller.signal
        );
        setMetrics(response.metrics);
      } catch (error: any) {
        if (error.name !== 'AbortError') {
          console.error('Failed to fetch metrics:', error);
          setMetricsError(error.message || 'Failed to fetch metrics');
          setMetrics(null);
        }
      } finally {
        setLoadingMetrics(false);
      }
    }, 500)
  );

  useEffect(() => {
    if (totalWeight === 0) return;

    // Cancel previous request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    abortControllerRef.current = new AbortController();
    fetchMetricsRef.current(model, as_of_date, horizon_months, weights, abortControllerRef.current);

    return () => {
      fetchMetricsRef.current.cancel();
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [totalWeight, model, as_of_date, horizon_months, weightsKey]);

  const handleWeightChange = (ticker: string, value: number) => {
    updateWeight(ticker, Math.max(0, Math.min(100, value)) / 100);
  };

  const normalizeWeights = useCallback(() => {
    if (totalWeight === 0) return;
    const normalized: { [key: string]: number } = {};
    Object.entries(weights).forEach(([ticker, weight]) => {
      normalized[ticker] = weight / totalWeight;
    });
    usePortfolioStore.getState().setWeights(normalized);
  }, [totalWeight, weights]);

  const resetWeights = useCallback(() => {
    usePortfolioStore.getState().setWeights({});
  }, []);

  return (
    <div className="portfolio-builder">
      <div className="builder-header">
        <h2>Portfolio Builder</h2>
        <div className="controls">
          <label htmlFor="model-select" className="sr-only">Optimization Model</label>
          <select
            id="model-select"
            value={model}
            onChange={(e) => setModel(e.target.value as ModelType)}
          >
            <option value="risk_parity">Risk Parity</option>
            <option value="max_sharpe">Max Sharpe</option>
            <option value="min_variance">Min Variance</option>
          </select>

          <label htmlFor="horizon-select" className="sr-only">Investment Horizon</label>
          <select
            id="horizon-select"
            value={horizon_months}
            onChange={(e) => setHorizon(Number(e.target.value))}
          >
            <option value={12}>12 Months</option>
            <option value={24}>24 Months</option>
            <option value={36}>36 Months</option>
            <option value={60}>60 Months</option>
          </select>
        </div>
      </div>

      <div className="weight-summary">
        <div
          aria-live="polite"
          className={`total-weight ${totalWeight > 1.01 ? 'over' : totalWeight < 0.99 ? 'under' : 'ok'}`}
        >
          Total: {(totalWeight * 100).toFixed(1)}%
        </div>
        <button onClick={normalizeWeights} disabled={totalWeight === 0}>
          Normalize
        </button>
        <button onClick={resetWeights}>Reset</button>
      </div>

      <div className="assets-grid">
        {assets.map((asset) => (
          <div key={asset.ticker} className="asset-card">
            <div className="asset-header">
              <span className="ticker">{asset.ticker}</span>
              <span className="name">{asset.name}</span>
            </div>
            <div className="weight-control">
              <input
                type="range"
                min="0"
                max="100"
                step="1"
                aria-label={`Weight for ${asset.name}`}
                value={(weights[asset.ticker] || 0) * 100}
                onChange={(e) => handleWeightChange(asset.ticker, Number(e.target.value))}
              />
              <input
                type="number"
                min="0"
                max="100"
                step="0.1"
                aria-label={`Weight percentage for ${asset.name}`}
                value={((weights[asset.ticker] || 0) * 100).toFixed(1)}
                onChange={(e) => handleWeightChange(asset.ticker, Number(e.target.value))}
                className="weight-input"
              />
              <span>%</span>
            </div>
          </div>
        ))}
      </div>

      <style>{`
        .portfolio-builder {
          padding: 20px;
          background: white;
          border-radius: 8px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .builder-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 20px;
        }

        .builder-header h2 {
          margin: 0;
          font-size: 24px;
        }

        .controls {
          display: flex;
          gap: 10px;
        }

        .sr-only {
          position: absolute;
          width: 1px;
          height: 1px;
          padding: 0;
          margin: -1px;
          overflow: hidden;
          clip: rect(0, 0, 0, 0);
          border: 0;
        }

        .controls select {
          padding: 8px 12px;
          border: 1px solid #ddd;
          border-radius: 4px;
          font-size: 14px;
        }

        .weight-summary {
          display: flex;
          gap: 10px;
          align-items: center;
          margin-bottom: 20px;
          padding: 12px;
          background: #f5f5f5;
          border-radius: 4px;
        }

        .total-weight {
          font-size: 18px;
          font-weight: bold;
          padding: 4px 12px;
          border-radius: 4px;
        }

        .total-weight.ok {
          background: #d4edda;
          color: #155724;
        }

        .total-weight.over {
          background: #f8d7da;
          color: #721c24;
        }

        .total-weight.under {
          background: #fff3cd;
          color: #856404;
        }

        .weight-summary button {
          padding: 8px 16px;
          border: none;
          border-radius: 4px;
          background: #007bff;
          color: white;
          cursor: pointer;
          font-size: 14px;
        }

        .weight-summary button:hover {
          background: #0056b3;
        }

        .weight-summary button:disabled {
          background: #ccc;
          cursor: not-allowed;
        }

        .assets-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
          gap: 16px;
        }

        .asset-card {
          padding: 16px;
          border: 1px solid #ddd;
          border-radius: 4px;
          background: #fafafa;
        }

        .asset-header {
          display: flex;
          justify-content: space-between;
          margin-bottom: 12px;
        }

        .ticker {
          font-weight: bold;
          font-size: 16px;
        }

        .name {
          font-size: 12px;
          color: #666;
        }

        .weight-control {
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .weight-control input[type="range"] {
          flex: 1;
        }

        .weight-input {
          width: 60px;
          padding: 4px 8px;
          border: 1px solid #ddd;
          border-radius: 4px;
          text-align: right;
        }
      `}</style>
    </div>
  );
};

export default PortfolioBuilder;
