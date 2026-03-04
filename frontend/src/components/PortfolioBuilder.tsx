import React, { useEffect, useRef } from 'react';
import { usePortfolioStore } from '../store';
import { getAssets, optimizePortfolio } from '../api';

type ModelType = 'risk_parity' | 'max_sharpe' | 'min_variance';

const MODEL_LABELS: Record<ModelType, string> = {
  risk_parity: 'Risk Parity',
  max_sharpe: 'Max Sharpe',
  min_variance: 'Min Variance',
};

const MODEL_DESCRIPTIONS: Record<ModelType, string> = {
  risk_parity: 'Each asset contributes equally to total portfolio risk.',
  max_sharpe: 'Maximize return per unit of risk (highest Sharpe ratio).',
  min_variance: 'Minimize portfolio volatility (lowest-risk combination).',
};

const PortfolioBuilder: React.FC = () => {
  const assets = usePortfolioStore((state) => state.assets);
  const setAssets = usePortfolioStore((state) => state.setAssets);
  const selectedTickers = usePortfolioStore((state) => state.selectedTickers);
  const toggleTicker = usePortfolioStore((state) => state.toggleTicker);
  const weights = usePortfolioStore((state) => state.weights);
  const model = usePortfolioStore((state) => state.model);
  const setModel = usePortfolioStore((state) => state.setModel);
  const horizon_months = usePortfolioStore((state) => state.horizon_months);
  const setHorizon = usePortfolioStore((state) => state.setHorizon);
  const as_of_date = usePortfolioStore((state) => state.as_of_date);
  const isOptimizing = usePortfolioStore((state) => state.isOptimizing);
  const optimizeError = usePortfolioStore((state) => state.optimizeError);
  const setIsOptimizing = usePortfolioStore((state) => state.setIsOptimizing);
  const setOptimizeError = usePortfolioStore((state) => state.setOptimizeError);
  const setWeights = usePortfolioStore((state) => state.setWeights);
  const setMetrics = usePortfolioStore((state) => state.setMetrics);

  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    getAssets().then(setAssets).catch(console.error);
  }, [setAssets]);

  const handleOptimize = async () => {
    if (selectedTickers.size < 2) {
      setOptimizeError('Please select at least 2 assets.');
      return;
    }

    // Cancel any in-flight request
    if (abortRef.current) abortRef.current.abort();
    abortRef.current = new AbortController();

    setIsOptimizing(true);
    setOptimizeError(null);

    try {
      const result = await optimizePortfolio(
        model as ModelType,
        as_of_date,
        horizon_months,
        Array.from(selectedTickers),
        abortRef.current.signal
      );
      setWeights(result.weights);
      setMetrics(result.metrics);
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        const detail = err?.response?.data?.detail ?? err.message ?? 'Optimization failed.';
        setOptimizeError(String(detail));
      }
    } finally {
      setIsOptimizing(false);
    }
  };

  const handleReset = () => {
    usePortfolioStore.getState().resetWeights();
    setOptimizeError(null);
  };

  const hasWeights = Object.keys(weights).length > 0;

  return (
    <div className="portfolio-builder">
      {/* ── Header ── */}
      <div className="builder-header">
        <h2>Portfolio Builder</h2>
        <div className="controls">
          <label htmlFor="model-select" className="sr-only">Optimization Strategy</label>
          <select
            id="model-select"
            value={model}
            onChange={(e) => setModel(e.target.value as ModelType)}
          >
            {(Object.keys(MODEL_LABELS) as ModelType[]).map((m) => (
              <option key={m} value={m}>{MODEL_LABELS[m]}</option>
            ))}
          </select>

          <label htmlFor="horizon-select" className="sr-only">Investment Horizon</label>
          <select
            id="horizon-select"
            value={horizon_months}
            onChange={(e) => setHorizon(Number(e.target.value))}
          >
            <option value={12}>12 Mo</option>
            <option value={24}>24 Mo</option>
            <option value={36}>36 Mo</option>
            <option value={60}>60 Mo</option>
          </select>
        </div>
      </div>

      {/* ── Strategy description ── */}
      <div className="strategy-hint">
        <span className="strategy-badge">{MODEL_LABELS[model as ModelType]}</span>
        {MODEL_DESCRIPTIONS[model as ModelType]}
      </div>

      {/* ── Action bar ── */}
      <div className="action-bar">
        <span className="selection-count">
          {selectedTickers.size} asset{selectedTickers.size !== 1 ? 's' : ''} selected
        </span>
        <button
          className="btn-optimize"
          onClick={handleOptimize}
          disabled={isOptimizing || selectedTickers.size < 2}
          aria-busy={isOptimizing}
        >
          {isOptimizing ? (
            <><span className="btn-spinner" />Optimizing…</>
          ) : (
            <>⚡ Optimize</>
          )}
        </button>
        {hasWeights && (
          <button className="btn-reset" onClick={handleReset}>Reset</button>
        )}
      </div>

      {/* ── Error banner ── */}
      {optimizeError && (
        <div className="error-banner" role="alert">
          ⚠ {optimizeError}
        </div>
      )}

      {/* ── Asset grid ── */}
      <div className="assets-grid">
        {assets.map((asset) => {
          const isSelected = selectedTickers.has(asset.ticker);
          const weight = weights[asset.ticker];
          const hasWeight = weight !== undefined;

          return (
            <div
              key={asset.ticker}
              className={`asset-card ${isSelected ? 'selected' : ''} ${hasWeight ? 'optimized' : ''}`}
              onClick={() => toggleTicker(asset.ticker)}
              role="checkbox"
              aria-checked={isSelected}
              tabIndex={0}
              onKeyDown={(e) => e.key === ' ' || e.key === 'Enter' ? toggleTicker(asset.ticker) : undefined}
            >
              <div className="asset-check">
                <div className={`checkbox ${isSelected ? 'checked' : ''}`}>
                  {isSelected && <svg viewBox="0 0 12 10" fill="none"><polyline points="1,5 4,8 11,1" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>}
                </div>
              </div>
              <div className="asset-info">
                <span className="ticker">{asset.ticker}</span>
                <span className="name">{asset.name}</span>
              </div>
              {hasWeight && (
                <div className="weight-badge">
                  <div
                    className="weight-fill"
                    style={{ width: `${(weight * 100).toFixed(1)}%` }}
                  />
                  <span className="weight-text">{(weight * 100).toFixed(1)}%</span>
                </div>
              )}
            </div>
          );
        })}
      </div>

      <style>{`
        .portfolio-builder {
          padding: 32px;
          height: 100%;
          display: flex;
          flex-direction: column;
          gap: 16px;
        }

        /* Header */
        .builder-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        .builder-header h2 {
          margin: 0;
          font-size: 20px;
          font-weight: 600;
          color: var(--text-primary);
        }
        .controls {
          display: flex;
          gap: 10px;
        }
        .sr-only {
          position: absolute; width: 1px; height: 1px;
          padding: 0; margin: -1px; overflow: hidden;
          clip: rect(0,0,0,0); border: 0;
        }
        .controls select {
          padding: 7px 14px;
          background: rgba(255,255,255,0.05);
          border: 1px solid var(--border-color);
          border-radius: 6px;
          font-size: 13px;
          color: var(--text-primary);
          cursor: pointer;
          transition: all 0.2s;
          outline: none;
        }
        .controls select:hover, .controls select:focus {
          border-color: var(--accent-blue);
          background: rgba(255,255,255,0.08);
        }
        .controls select option {
          background: var(--bg-panel);
          color: var(--text-primary);
        }

        /* Strategy hint */
        .strategy-hint {
          display: flex;
          align-items: center;
          gap: 10px;
          font-size: 13px;
          color: var(--text-secondary);
          padding: 10px 14px;
          background: rgba(59,130,246,0.06);
          border: 1px solid rgba(59,130,246,0.15);
          border-radius: 8px;
        }
        .strategy-badge {
          font-weight: 700;
          font-size: 11px;
          color: var(--accent-blue);
          text-transform: uppercase;
          letter-spacing: 0.8px;
          background: rgba(59,130,246,0.12);
          padding: 3px 8px;
          border-radius: 4px;
          white-space: nowrap;
        }

        /* Action bar */
        .action-bar {
          display: flex;
          align-items: center;
          gap: 12px;
        }
        .selection-count {
          font-size: 13px;
          color: var(--text-secondary);
          margin-right: auto;
        }
        .btn-optimize {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 9px 22px;
          background: linear-gradient(135deg, #3B82F6, #2563EB);
          color: white;
          border: none;
          border-radius: 8px;
          font-size: 14px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s;
          box-shadow: 0 0 20px rgba(59,130,246,0.25);
        }
        .btn-optimize:hover:not(:disabled) {
          background: linear-gradient(135deg, #2563EB, #1D4ED8);
          box-shadow: 0 0 28px rgba(59,130,246,0.45);
          transform: translateY(-1px);
        }
        .btn-optimize:disabled {
          opacity: 0.45;
          cursor: not-allowed;
          box-shadow: none;
          transform: none;
        }
        .btn-spinner {
          display: inline-block;
          width: 14px; height: 14px;
          border: 2px solid rgba(255,255,255,0.3);
          border-top-color: white;
          border-radius: 50%;
          animation: spin 0.7s linear infinite;
          flex-shrink: 0;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .btn-reset {
          padding: 9px 18px;
          background: transparent;
          border: 1px solid var(--border-color);
          border-radius: 8px;
          font-size: 13px;
          color: var(--text-secondary);
          cursor: pointer;
          transition: all 0.2s;
        }
        .btn-reset:hover {
          background: rgba(255,255,255,0.05);
          color: var(--text-primary);
        }

        /* Error banner */
        .error-banner {
          padding: 10px 16px;
          background: rgba(239,68,68,0.1);
          border: 1px solid rgba(239,68,68,0.25);
          border-radius: 8px;
          color: var(--danger);
          font-size: 13px;
        }

        /* Assets grid */
        .assets-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
          gap: 12px;
          overflow-y: auto;
          flex: 1;
          padding-right: 4px;
        }
        .assets-grid::-webkit-scrollbar { width: 5px; }
        .assets-grid::-webkit-scrollbar-track { background: rgba(255,255,255,0.02); border-radius: 4px; }
        .assets-grid::-webkit-scrollbar-thumb { background: var(--border-color); border-radius: 4px; }
        .assets-grid::-webkit-scrollbar-thumb:hover { background: #4B5563; }

        /* Asset card */
        .asset-card {
          position: relative;
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 14px 16px;
          border: 1px solid var(--border-color);
          border-radius: 10px;
          background: rgba(255,255,255,0.02);
          cursor: pointer;
          transition: all 0.18s ease;
          user-select: none;
          overflow: hidden;
        }
        .asset-card:hover {
          background: rgba(255,255,255,0.05);
          border-color: rgba(255,255,255,0.15);
        }
        .asset-card.selected {
          border-color: rgba(59,130,246,0.5);
          background: rgba(59,130,246,0.07);
        }
        .asset-card.optimized {
          border-color: rgba(16,185,129,0.4);
          background: rgba(16,185,129,0.05);
        }
        .asset-card.selected.optimized {
          border-color: rgba(16,185,129,0.55);
          background: rgba(16,185,129,0.08);
        }

        /* Checkbox */
        .asset-check { flex-shrink: 0; }
        .checkbox {
          width: 18px; height: 18px;
          border: 2px solid var(--border-color);
          border-radius: 4px;
          display: flex; align-items: center; justify-content: center;
          transition: all 0.15s;
          background: rgba(255,255,255,0.03);
        }
        .checkbox.checked {
          background: var(--accent-blue);
          border-color: var(--accent-blue);
          color: white;
        }
        .checkbox svg { width: 12px; height: 10px; }

        /* Asset info */
        .asset-info {
          display: flex;
          flex-direction: column;
          gap: 3px;
          flex: 1;
          min-width: 0;
        }
        .ticker {
          font-weight: 700;
          font-size: 15px;
          color: var(--text-primary);
          letter-spacing: 0.4px;
        }
        .name {
          font-size: 11px;
          color: var(--text-secondary);
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        /* Weight badge */
        .weight-badge {
          position: relative;
          display: flex;
          align-items: center;
          justify-content: flex-end;
          min-width: 58px;
          height: 28px;
          background: rgba(16,185,129,0.08);
          border: 1px solid rgba(16,185,129,0.25);
          border-radius: 6px;
          overflow: hidden;
          flex-shrink: 0;
        }
        .weight-fill {
          position: absolute;
          left: 0; top: 0; bottom: 0;
          background: rgba(16,185,129,0.18);
          transition: width 0.4s ease;
          min-width: 2px;
        }
        .weight-text {
          position: relative;
          font-size: 12px;
          font-weight: 700;
          color: var(--accent-green);
          font-family: monospace;
          padding: 0 8px;
          letter-spacing: 0.3px;
        }
      `}</style>
    </div>
  );
};

export default PortfolioBuilder;
