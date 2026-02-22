// API Types
export interface Asset {
  ticker: string;
  name: string;
  asset_class: string;
}

export interface PortfolioWeights {
  [ticker: string]: number;
}

export interface RiskMetrics {
  expected_return_ann: number;
  volatility_ann: number;
  sharpe: number;
  sortino: number;
  var95: number;
  var99: number;
  cvar95: number;
  cvar99: number;
  max_drawdown: number;
  calmar: number;
}

export interface PortfolioQuoteResponse {
  dataset_version: string;
  weights_hash: string;
  metrics: RiskMetrics;
  cache_hit: boolean;
}

export interface MonteCarloResponse {
  model: string;
  horizon_months: number;
  n_simulations: number;
  mean_return: number;
  std_return: number;
  distribution: { [key: string]: number };
  as_of_date: string;
}

export interface StressTestResult {
  scenario_name: string;
  scenario_description: string;
  portfolio_return: number;
  as_of_date: string;
}

export interface CovarianceResponse {
  as_of_date: string;
  tickers: string[];
  covariance_matrix: number[][];
  window_days: number;
}

// UI State Types
export interface PortfolioState {
  weights: PortfolioWeights;
  model: 'max_sharpe' | 'risk_parity' | 'min_variance';
  horizon_months: number;
  as_of_date: string;
}
