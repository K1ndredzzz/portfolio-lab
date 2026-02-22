"""
Interpolation service for Monte Carlo and Stress Test lookup tables.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from pathlib import Path


class WeightInterpolator:
    """Interpolate Monte Carlo and Stress Test results from lookup tables."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self._mc_data = None
        self._mc_weights = None
        self._stress_data = None
        self._stress_weights = None

    def _load_monte_carlo_data(self):
        """Load Monte Carlo lookup table."""
        if self._mc_data is None:
            mc_file = self.data_dir / "monte_carlo_grid.parquet"
            weights_file = self.data_dir / "monte_carlo_grid_weights.parquet"

            # Try test files if main files don't exist
            if not mc_file.exists():
                mc_file = self.data_dir / "monte_carlo_grid_test.parquet"
                weights_file = self.data_dir / "monte_carlo_grid_test_weights.parquet"

            self._mc_data = pd.read_parquet(mc_file)
            self._mc_weights = pd.read_parquet(weights_file)

    def _load_stress_data(self):
        """Load Stress Test lookup table."""
        if self._stress_data is None:
            stress_file = self.data_dir / "stress_tests_grid.parquet"
            weights_file = self.data_dir / "stress_tests_grid_weights.parquet"

            # Try test files if main files don't exist
            if not stress_file.exists():
                stress_file = self.data_dir / "stress_tests_grid_test.parquet"
                weights_file = self.data_dir / "stress_tests_grid_test_weights.parquet"

            self._stress_data = pd.read_parquet(stress_file)
            self._stress_weights = pd.read_parquet(weights_file)

    def _find_nearest_weights(
        self,
        target_weights: Dict[str, float],
        weights_df: pd.DataFrame,
        k: int = 4
    ) -> List[Tuple[str, float, Dict[str, float]]]:
        """
        Find k nearest weight combinations using Euclidean distance.

        Args:
            target_weights: Target portfolio weights {ticker: weight}
            weights_df: DataFrame with weight combinations
            k: Number of nearest neighbors to return

        Returns:
            List of (weights_hash, distance, weights_dict) tuples
        """
        # Ensure weights are normalized
        total = sum(target_weights.values())
        if abs(total - 1.0) > 0.01:
            target_weights = {k: v / total for k, v in target_weights.items()}

        # Convert target weights to array
        tickers = sorted(target_weights.keys())
        target_array = np.array([target_weights.get(t, 0.0) for t in tickers])

        # Convert lookup table weights to array
        weight_cols = [f'weight_{t}' for t in tickers]
        weights_array = weights_df[weight_cols].values

        # Compute Euclidean distances
        distances = np.sqrt(((weights_array - target_array) ** 2).sum(axis=1))

        # Find k nearest
        nearest_indices = np.argsort(distances)[:k]

        results = []
        for idx in nearest_indices:
            weights_hash = weights_df.iloc[idx]['weights_hash']
            distance = distances[idx]
            weights_dict = {
                t: weights_df.iloc[idx][f'weight_{t}']
                for t in tickers
            }
            results.append((weights_hash, distance, weights_dict))

        return results

    def interpolate_monte_carlo(
        self,
        target_weights: Dict[str, float],
        horizon_months: int
    ) -> Dict:
        """
        Interpolate Monte Carlo results for target weights.

        Args:
            target_weights: Target portfolio weights
            horizon_months: Investment horizon in months

        Returns:
            Dict with interpolated Monte Carlo results
        """
        self._load_monte_carlo_data()

        # Find nearest weight combinations
        nearest = self._find_nearest_weights(target_weights, self._mc_weights, k=4)

        # If exact match found (distance < 0.001), return it directly
        if nearest[0][1] < 0.001:
            weights_hash = nearest[0][0]
            mc_subset = self._mc_data[
                (self._mc_data['weights_hash'] == weights_hash) &
                (self._mc_data['horizon_months'] == horizon_months)
            ]

            # Extract results
            percentile_data = mc_subset[mc_subset['stat_type'] == 'percentile']
            mean_data = mc_subset[mc_subset['stat_type'] == 'mean']
            std_data = mc_subset[mc_subset['stat_type'] == 'std']

            distribution = {
                f"p{int(row['percentile'])}": float(row['return_value'])
                for _, row in percentile_data.iterrows()
            }

            return {
                'mean_return': float(mean_data.iloc[0]['return_value']) if len(mean_data) > 0 else 0.0,
                'std_return': float(std_data.iloc[0]['return_value']) if len(std_data) > 0 else 0.0,
                'distribution': distribution,
                'interpolated': False,
                'nearest_distance': nearest[0][1]
            }

        # Interpolate using inverse distance weighting
        weights_hashes = [n[0] for n in nearest]
        distances = np.array([n[1] for n in nearest])

        # Inverse distance weights (avoid division by zero)
        inv_distances = 1.0 / (distances + 1e-10)
        interp_weights = inv_distances / inv_distances.sum()

        # Get data for all nearest neighbors
        mc_subset = self._mc_data[
            (self._mc_data['weights_hash'].isin(weights_hashes)) &
            (self._mc_data['horizon_months'] == horizon_months)
        ]

        # Interpolate each statistic
        result = {
            'mean_return': 0.0,
            'std_return': 0.0,
            'distribution': {},
            'interpolated': True,
            'nearest_distance': nearest[0][1]
        }

        # Interpolate mean and std
        for stat_type in ['mean', 'std']:
            stat_data = mc_subset[mc_subset['stat_type'] == stat_type]
            for i, (weights_hash, _, _) in enumerate(nearest):
                value = stat_data[stat_data['weights_hash'] == weights_hash]['return_value'].values
                if len(value) > 0:
                    result[f'{stat_type}_return'] += interp_weights[i] * value[0]

        # Interpolate distribution percentiles
        percentile_data = mc_subset[mc_subset['stat_type'] == 'percentile']
        percentiles = percentile_data['percentile'].unique()

        for percentile in percentiles:
            interp_value = 0.0
            for i, (weights_hash, _, _) in enumerate(nearest):
                value = percentile_data[
                    (percentile_data['weights_hash'] == weights_hash) &
                    (percentile_data['percentile'] == percentile)
                ]['return_value'].values
                if len(value) > 0:
                    interp_value += interp_weights[i] * value[0]
            result['distribution'][f'p{int(percentile)}'] = interp_value

        return result

    def interpolate_stress_test(
        self,
        target_weights: Dict[str, float]
    ) -> List[Dict]:
        """
        Interpolate Stress Test results for target weights.

        Args:
            target_weights: Target portfolio weights

        Returns:
            List of stress test results for each scenario
        """
        self._load_stress_data()

        # Find nearest weight combinations
        nearest = self._find_nearest_weights(target_weights, self._stress_weights, k=4)

        # If exact match found, return it directly
        if nearest[0][1] < 0.001:
            weights_hash = nearest[0][0]
            stress_subset = self._stress_data[
                self._stress_data['weights_hash'] == weights_hash
            ]

            return [
                {
                    'scenario_name': row['scenario_name'],
                    'scenario_description': row['scenario_description'],
                    'portfolio_return': float(row['portfolio_return']),
                    'interpolated': False
                }
                for _, row in stress_subset.iterrows()
            ]

        # Interpolate using inverse distance weighting
        weights_hashes = [n[0] for n in nearest]
        distances = np.array([n[1] for n in nearest])

        inv_distances = 1.0 / (distances + 1e-10)
        interp_weights = inv_distances / inv_distances.sum()

        # Get data for all nearest neighbors
        stress_subset = self._stress_data[
            self._stress_data['weights_hash'].isin(weights_hashes)
        ]

        # Interpolate for each scenario
        scenarios = stress_subset['scenario_name'].unique()
        results = []

        for scenario in scenarios:
            scenario_data = stress_subset[stress_subset['scenario_name'] == scenario]
            interp_return = 0.0

            for i, (weights_hash, _, _) in enumerate(nearest):
                value = scenario_data[
                    scenario_data['weights_hash'] == weights_hash
                ]['portfolio_return'].values
                if len(value) > 0:
                    interp_return += interp_weights[i] * value[0]

            # Get scenario description from first match
            description = scenario_data.iloc[0]['scenario_description']

            results.append({
                'scenario_name': scenario,
                'scenario_description': description,
                'portfolio_return': float(interp_return),
                'interpolated': True
            })

        return results


# Global instance
_interpolator = None


def get_interpolator() -> WeightInterpolator:
    """Get or create global interpolator instance."""
    global _interpolator
    if _interpolator is None:
        _interpolator = WeightInterpolator()
    return _interpolator
