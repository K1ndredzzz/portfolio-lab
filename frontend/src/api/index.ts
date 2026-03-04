import axios from 'axios';
import type {
  Asset,
  PortfolioQuoteResponse,
  PortfolioOptimizeResponse,
  MonteCarloResponse,
  StressTestResult,
  CovarianceResponse,
  PortfolioWeights
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

// Warn if using HTTP in production
if (import.meta.env.PROD && API_BASE_URL.startsWith('http://')) {
  console.warn('WARNING: Using HTTP in production. Consider using HTTPS for secure data transmission.');
}

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, // 60 seconds for complex interpolation calculations
  headers: {
    'Content-Type': 'application/json',
  },
});

// Health Check
export const healthCheck = async () => {
  const response = await api.get('/health/live');
  return response.data;
};

// Get Assets
export const getAssets = async (): Promise<Asset[]> => {
  const response = await api.get('/meta/assets');
  return response.data.assets;
};

// Portfolio Quote
export const getPortfolioQuote = async (
  model: 'risk_parity' | 'max_sharpe' | 'min_variance',
  as_of_date: string,
  horizon_months: number,
  weights: PortfolioWeights,
  signal?: AbortSignal
): Promise<PortfolioQuoteResponse> => {
  const response = await api.post('/portfolios/quote', {
    model,
    as_of_date,
    horizon_months,
    weights,
  }, { signal });
  return response.data;
};

// Portfolio Optimize — compute optimal weights from selected tickers + strategy
export const optimizePortfolio = async (
  model: 'risk_parity' | 'max_sharpe' | 'min_variance',
  as_of_date: string,
  horizon_months: number,
  tickers: string[],
  signal?: AbortSignal
): Promise<PortfolioOptimizeResponse> => {
  const response = await api.post('/portfolios/optimize', {
    model,
    as_of_date,
    horizon_months,
    tickers,
  }, { signal });
  return response.data;
};

// Monte Carlo Simulation
export const getMonteCarlo = async (
  weights: PortfolioWeights,
  horizon_months: number,
  as_of_date: string,
  signal?: AbortSignal
): Promise<MonteCarloResponse> => {
  const response = await api.post('/risk/monte-carlo', {
    weights,
    horizon_months,
    as_of_date,
  }, { signal });
  return response.data;
};

// Stress Test
export const getStressTest = async (
  weights: PortfolioWeights,
  signal?: AbortSignal
): Promise<StressTestResult[]> => {
  const response = await api.post('/risk/stress', {
    weights,
  }, { signal });
  return response.data;
};

// Covariance Matrix
export const getCovariance = async (
  as_of_date: string
): Promise<CovarianceResponse> => {
  const response = await api.post('/risk/covariance', {
    as_of_date,
  });
  return response.data;
};

export default api;
