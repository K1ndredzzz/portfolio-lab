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
          padding: 32px;
          height: 100%;
          display: flex;
          flex-direction: column;
        }

        .builder-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 24px;
        }

        .builder-header h2 {
          margin: 0;
          font-size: 20px;
          font-weight: 600;
          color: var(--text-primary);
        }

        .controls {
          display: flex;
          gap: 12px;
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
          padding: 8px 16px;
          background-color: rgba(255, 255, 255, 0.05);
          border: 1px solid var(--border-color);
          border-radius: 6px;
          font-size: 14px;
          color: var(--text-primary);
          cursor: pointer;
          transition: all 0.2s;
          outline: none;
        }

        .controls select:hover, .controls select:focus {
          border-color: var(--accent-blue);
          background-color: rgba(255, 255, 255, 0.1);
        }

        .controls select option {
          background-color: var(--bg-panel);
          color: var(--text-primary);
        }

        .weight-summary {
          display: flex;
          gap: 12px;
          align-items: center;
          margin-bottom: 24px;
          padding: 16px;
          background: rgba(255, 255, 255, 0.02);
          border: 1px solid var(--border-color);
          border-radius: 8px;
        }

        .total-weight {
          font-size: 16px;
          font-weight: 600;
          padding: 6px 16px;
          border-radius: 6px;
          margin-right: auto;
        }

        .total-weight.ok {
          background: rgba(16, 185, 129, 0.1);
          color: var(--accent-green);
          border: 1px solid rgba(16, 185, 129, 0.2);
        }

        .total-weight.over {
          background: rgba(239, 68, 68, 0.1);
          color: var(--danger);
          border: 1px solid rgba(239, 68, 68, 0.2);
        }

        .total-weight.under {
          background: rgba(245, 158, 11, 0.1);
          color: var(--warning);
          border: 1px solid rgba(245, 158, 11, 0.2);
        }

        .weight-summary button {
          padding: 8px 20px;
          border: none;
          border-radius: 6px;
          font-size: 14px;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.2s;
        }

        .weight-summary button:first-of-type {
          background: var(--accent-blue);
          color: white;
        }

        .weight-summary button:first-of-type:hover:not(:disabled) {
          background: #2563EB;
          box-shadow: 0 0 15px rgba(59, 130, 246, 0.4);
        }

        .weight-summary button:last-of-type {
          background: transparent;
          border: 1px solid var(--border-color);
          color: var(--text-secondary);
        }

        .weight-summary button:last-of-type:hover {
          background: rgba(255, 255, 255, 0.05);
          color: var(--text-primary);
        }

        .weight-summary button:disabled {
          background: rgba(255, 255, 255, 0.1);
          color: var(--text-secondary);
          cursor: not-allowed;
          box-shadow: none;
        }

        .assets-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
          gap: 16px;
          overflow-y: auto;
          flex: 1;
          padding-right: 8px;
        }

        .assets-grid::-webkit-scrollbar {
          width: 6px;
        }

        .assets-grid::-webkit-scrollbar-track {
          background: rgba(255, 255, 255, 0.02);
          border-radius: 4px;
        }

        .assets-grid::-webkit-scrollbar-thumb {
          background: var(--border-color);
          border-radius: 4px;
        }

        .assets-grid::-webkit-scrollbar-thumb:hover {
          background: #4B5563;
        }

        .asset-card {
          padding: 20px;
          border: 1px solid var(--border-color);
          border-radius: 12px;
          background: rgba(255, 255, 255, 0.02);
          transition: all 0.2s ease;
        }

        .asset-card:hover {
          background: rgba(255, 255, 255, 0.04);
          border-color: rgba(255, 255, 255, 0.15);
        }

        .asset-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 16px;
        }

        .ticker {
          font-weight: 700;
          font-size: 16px;
          color: var(--text-primary);
          background: rgba(255, 255, 255, 0.1);
          padding: 4px 10px;
          border-radius: 4px;
          letter-spacing: 0.5px;
        }

        .name {
          font-size: 13px;
          color: var(--text-secondary);
          text-align: right;
          max-width: 60%;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .weight-control {
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .weight-control input[type="range"] {
          flex: 1;
          -webkit-appearance: none;
          height: 4px;
          background: rgba(255, 255, 255, 0.1);
          border-radius: 2px;
          outline: none;
        }

        .weight-control input[type="range"]::-webkit-slider-thumb {
          -webkit-appearance: none;
          appearance: none;
          width: 16px;
          height: 16px;
          border-radius: 50%;
          background: var(--accent-green);
          cursor: pointer;
          transition: all 0.2s;
          box-shadow: 0 0 10px rgba(16, 185, 129, 0.4);
        }

        .weight-control input[type="range"]::-webkit-slider-thumb:hover {
          transform: scale(1.2);
          box-shadow: 0 0 15px rgba(16, 185, 129, 0.6);
        }

        .weight-input {
          width: 64px;
          padding: 6px 8px;
          background: rgba(0, 0, 0, 0.2);
          border: 1px solid var(--border-color);
          border-radius: 6px;
          text-align: right;
          color: var(--text-primary);
          font-size: 14px;
          font-family: monospace;
          outline: none;
          transition: all 0.2s;
        }

        .weight-input:focus {
          border-color: var(--accent-green);
          box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.2);
        }

        .weight-control span {
          color: var(--text-secondary);
          font-weight: 600;
        }
      `}</style>
    </div>
  );
};

export default PortfolioBuilder;
