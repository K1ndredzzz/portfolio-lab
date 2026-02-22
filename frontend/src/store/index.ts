import { create } from 'zustand';
import type { Asset, PortfolioWeights, RiskMetrics, MonteCarloResponse, StressTestResult } from '../types';

interface PortfolioStore {
  // Assets
  assets: Asset[];
  setAssets: (assets: Asset[]) => void;

  // Portfolio Configuration
  weights: PortfolioWeights;
  model: 'max_sharpe' | 'risk_parity' | 'min_variance';
  horizon_months: number;
  as_of_date: string;

  // Results
  metrics: RiskMetrics | null;
  monteCarlo: MonteCarloResponse | null;
  stressTests: StressTestResult[];

  // Loading States
  isLoadingMetrics: boolean;
  isLoadingMonteCarlo: boolean;
  isLoadingStress: boolean;

  // Error States
  metricsError: string | null;
  monteCarloError: string | null;
  stressError: string | null;

  // Actions
  setWeights: (weights: PortfolioWeights) => void;
  updateWeight: (ticker: string, weight: number) => void;
  setModel: (model: 'max_sharpe' | 'risk_parity' | 'min_variance') => void;
  setHorizon: (months: number) => void;
  setAsOfDate: (date: string) => void;
  setMetrics: (metrics: RiskMetrics | null) => void;
  setMonteCarlo: (data: MonteCarloResponse | null) => void;
  setStressTests: (tests: StressTestResult[]) => void;
  setLoadingMetrics: (loading: boolean) => void;
  setLoadingMonteCarlo: (loading: boolean) => void;
  setLoadingStress: (loading: boolean) => void;
  setMetricsError: (error: string | null) => void;
  setMonteCarloError: (error: string | null) => void;
  setStressError: (error: string | null) => void;
  resetWeights: () => void;
}

export const usePortfolioStore = create<PortfolioStore>((set) => ({
  // Initial State
  assets: [],
  weights: {},
  model: 'risk_parity',
  horizon_months: 36,
  as_of_date: '2025-12-31',
  metrics: null,
  monteCarlo: null,
  stressTests: [],
  isLoadingMetrics: false,
  isLoadingMonteCarlo: false,
  isLoadingStress: false,
  metricsError: null,
  monteCarloError: null,
  stressError: null,

  // Actions
  setAssets: (assets) => set({ assets }),

  setWeights: (weights) => set({ weights }),

  updateWeight: (ticker, weight) =>
    set((state) => ({
      weights: { ...state.weights, [ticker]: weight },
    })),

  setModel: (model) => set({ model }),

  setHorizon: (horizon_months) => set({ horizon_months }),

  setAsOfDate: (as_of_date) => set({ as_of_date }),

  setMetrics: (metrics) => set({ metrics }),

  setMonteCarlo: (monteCarlo) => set({ monteCarlo }),

  setStressTests: (stressTests) => set({ stressTests }),

  setLoadingMetrics: (isLoadingMetrics) => set({ isLoadingMetrics }),

  setLoadingMonteCarlo: (isLoadingMonteCarlo) => set({ isLoadingMonteCarlo }),

  setLoadingStress: (isLoadingStress) => set({ isLoadingStress }),

  setMetricsError: (metricsError) => set({ metricsError }),

  setMonteCarloError: (monteCarloError) => set({ monteCarloError }),

  setStressError: (stressError) => set({ stressError }),

  resetWeights: () => set({ weights: {} }),
}));
