"""
Unit tests for MAPIE prediction intervals and XGBoost tuning.

Tests cover:
- get_small_dataset_params() for 3 size tiers
- DistancePredictor.predict_with_intervals() with graceful degradation
- Integration contract verification (keys expected by local_coach.py)
"""

import unittest
from unittest.mock import patch, MagicMock, Mock
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestGetSmallDatasetParams(unittest.TestCase):
    """Test dataset-size-aware hyperparameter tuning."""

    def test_very_small_dataset(self):
        """Very small datasets (<1000) get maximum regularization."""
        from ml.tuning import get_small_dataset_params

        params = get_small_dataset_params(500)

        self.assertEqual(params['max_depth'], 3)
        self.assertEqual(params['reg_lambda'], 3.0)
        self.assertEqual(params['reg_alpha'], 1.5)
        self.assertEqual(params['subsample'], 0.7)
        self.assertEqual(params['n_estimators'], 50)
        self.assertEqual(params['learning_rate'], 0.05)
        self.assertEqual(params['min_child_weight'], 3)

    def test_small_dataset(self):
        """Small datasets (<3000) get strong regularization."""
        from ml.tuning import get_small_dataset_params

        params = get_small_dataset_params(2000)

        self.assertEqual(params['max_depth'], 4)
        self.assertEqual(params['reg_lambda'], 2.0)
        self.assertEqual(params['reg_alpha'], 1.0)
        self.assertEqual(params['subsample'], 0.8)
        self.assertEqual(params['n_estimators'], 75)
        self.assertEqual(params['learning_rate'], 0.08)
        self.assertEqual(params['min_child_weight'], 2)

    def test_medium_dataset(self):
        """Medium datasets (>=3000) get moderate regularization."""
        from ml.tuning import get_small_dataset_params

        params = get_small_dataset_params(5000)

        self.assertEqual(params['max_depth'], 5)
        self.assertEqual(params['reg_lambda'], 1.0)
        self.assertEqual(params['reg_alpha'], 0.5)
        self.assertEqual(params['subsample'], 0.8)
        self.assertEqual(params['n_estimators'], 100)
        self.assertEqual(params['learning_rate'], 0.1)
        self.assertEqual(params['min_child_weight'], 1)

    def test_boundary_1000(self):
        """Boundary case: n=1000 should fall into small tier."""
        from ml.tuning import get_small_dataset_params

        params = get_small_dataset_params(1000)

        # Should use small tier (not very_small)
        self.assertEqual(params['max_depth'], 4)
        self.assertEqual(params['reg_lambda'], 2.0)

    def test_boundary_3000(self):
        """Boundary case: n=3000 should fall into medium tier."""
        from ml.tuning import get_small_dataset_params

        params = get_small_dataset_params(3000)

        # Should use medium tier (not small)
        self.assertEqual(params['max_depth'], 5)
        self.assertEqual(params['reg_lambda'], 1.0)

    def test_all_have_required_keys(self):
        """All tiers return complete parameter sets."""
        from ml.tuning import get_small_dataset_params

        required_keys = {
            'n_estimators',
            'max_depth',
            'learning_rate',
            'reg_lambda',
            'reg_alpha',
            'subsample',
            'objective',
            'random_state',
            'min_child_weight',
        }

        for n_samples in [500, 2000, 5000]:
            params = get_small_dataset_params(n_samples)
            self.assertEqual(set(params.keys()), required_keys,
                           f"Missing keys for n={n_samples}")


class TestDistancePredictorIntervals(unittest.TestCase):
    """Test DistancePredictor.predict_with_intervals()."""

    def test_predict_with_intervals_no_mapie(self):
        """Graceful fallback when MAPIE not available."""
        import ml.train_models
        import numpy as np

        # Mock HAS_MAPIE to False
        original_has_mapie = ml.train_models.HAS_MAPIE
        try:
            ml.train_models.HAS_MAPIE = False

            from ml.train_models import DistancePredictor

            predictor = DistancePredictor()

            # Mock the model and feature names
            predictor.model = Mock()
            predictor.model.predict = Mock(return_value=np.array([250.0]))
            predictor._feature_names = ['ball_speed', 'launch_angle', 'back_spin',
                                       'club_speed', 'attack_angle', 'dynamic_loft']
            predictor.mapie_model = None

            result = predictor.predict_with_intervals(
                ball_speed=165,
                launch_angle=12,
                back_spin=2500,
            )

            # Should return point estimate only
            self.assertFalse(result['has_intervals'])
            self.assertIn('predicted_value', result)
            self.assertIsInstance(result['predicted_value'], float)
            self.assertIn('message', result)
            self.assertIn('MAPIE', result['message'])
        finally:
            ml.train_models.HAS_MAPIE = original_has_mapie

    def test_predict_with_intervals_returns_dict_keys(self):
        """When MAPIE available, verify return dict structure."""
        import ml.train_models
        import numpy as np

        original_has_mapie = ml.train_models.HAS_MAPIE
        try:
            ml.train_models.HAS_MAPIE = True

            from ml.train_models import DistancePredictor

            predictor = DistancePredictor()

            # Mock base model
            predictor.model = Mock()
            predictor._feature_names = ['ball_speed', 'launch_angle', 'back_spin',
                                       'club_speed', 'attack_angle', 'dynamic_loft']

            # Mock MAPIE model
            mock_mapie = Mock()
            mock_mapie.predict = Mock(return_value=(
                np.array([250.0]),  # y_pred
                np.array([[[245.0], [255.0]]])  # y_pis (lower, upper)
            ))
            predictor.mapie_model = mock_mapie

            result = predictor.predict_with_intervals(
                ball_speed=165,
                launch_angle=12,
                back_spin=2500,
            )

            # Verify all expected keys present
            self.assertIn('predicted_value', result)
            self.assertIn('lower_bound', result)
            self.assertIn('upper_bound', result)
            self.assertIn('confidence_level', result)
            self.assertIn('interval_width', result)
            self.assertIn('has_intervals', result)
            self.assertTrue(result['has_intervals'])
        finally:
            ml.train_models.HAS_MAPIE = original_has_mapie

    def test_predict_with_intervals_bounds_ordering(self):
        """Lower bound < predicted value < upper bound."""
        import ml.train_models
        import numpy as np

        original_has_mapie = ml.train_models.HAS_MAPIE
        try:
            ml.train_models.HAS_MAPIE = True

            from ml.train_models import DistancePredictor

            predictor = DistancePredictor()

            # Mock base model
            predictor.model = Mock()
            predictor._feature_names = ['ball_speed', 'launch_angle', 'back_spin',
                                       'club_speed', 'attack_angle', 'dynamic_loft']

            # Mock MAPIE model with realistic intervals
            mock_mapie = Mock()
            mock_mapie.predict = Mock(return_value=(
                np.array([250.0]),  # y_pred
                np.array([[[240.0], [260.0]]])  # y_pis
            ))
            predictor.mapie_model = mock_mapie

            result = predictor.predict_with_intervals(
                ball_speed=165,
                launch_angle=12,
                back_spin=2500,
            )

            # Verify ordering
            self.assertLess(result['lower_bound'], result['predicted_value'])
            self.assertLess(result['predicted_value'], result['upper_bound'])

            # Verify interval width calculation
            expected_width = result['upper_bound'] - result['lower_bound']
            self.assertAlmostEqual(result['interval_width'], expected_width, places=2)
        finally:
            ml.train_models.HAS_MAPIE = original_has_mapie

    def test_train_uses_tuned_params(self):
        """Verify train() calls get_small_dataset_params."""
        with patch('ml.train_models.get_small_dataset_params') as mock_get_params:
            with patch('ml.train_models.HAS_ML_DEPS', True):
                with patch('ml.train_models.xgb') as mock_xgb:
                    from ml.train_models import train_distance_model
                    import pandas as pd

                    # Mock get_small_dataset_params
                    mock_get_params.return_value = {
                        'n_estimators': 50,
                        'max_depth': 3,
                        'learning_rate': 0.05,
                        'reg_lambda': 3.0,
                        'reg_alpha': 1.5,
                        'subsample': 0.7,
                        'min_child_weight': 3,
                        'objective': 'reg:squarederror',
                        'random_state': 42,
                    }

                    # Mock XGBoost
                    mock_model = Mock()
                    mock_model.predict = Mock(return_value=[250.0] * 20)
                    mock_model.feature_importances_ = [0.2] * 6
                    mock_xgb.XGBRegressor = Mock(return_value=mock_model)

                    # Create minimal training data
                    df = pd.DataFrame({
                        'ball_speed': [165.0] * 100,
                        'launch_angle': [12.0] * 100,
                        'back_spin': [2500.0] * 100,
                        'club_speed': [110.0] * 100,
                        'attack_angle': [0.0] * 100,
                        'dynamic_loft': [13.0] * 100,
                        'carry': [250.0] * 100,
                    })

                    try:
                        train_distance_model(df)
                    except Exception:
                        # May fail due to mocking, but we just want to verify the call
                        pass

                    # Verify get_small_dataset_params was called
                    mock_get_params.assert_called()

    def test_predict_with_intervals_contract(self):
        """
        Integration contract test: verify keys match local_coach.py expectations.

        This test defines the contract between DistancePredictor and LocalCoach.
        If keys change here, local_coach.py will break.
        """
        import ml.train_models
        import numpy as np

        original_has_mapie = ml.train_models.HAS_MAPIE
        try:
            ml.train_models.HAS_MAPIE = True

            from ml.train_models import DistancePredictor

            predictor = DistancePredictor()

            # Mock models
            predictor.model = Mock()
            predictor._feature_names = ['ball_speed', 'launch_angle', 'back_spin',
                                       'club_speed', 'attack_angle', 'dynamic_loft']

            mock_mapie = Mock()
            mock_mapie.predict = Mock(return_value=(
                np.array([250.0]),
                np.array([[[245.0], [255.0]]])
            ))
            predictor.mapie_model = mock_mapie

            result = predictor.predict_with_intervals(
                ball_speed=165,
                launch_angle=12,
                back_spin=2500,
            )

            # Contract: These exact keys MUST be present
            expected_keys = {
                'predicted_value',
                'lower_bound',
                'upper_bound',
                'confidence_level',
                'interval_width',
                'has_intervals',
            }

            self.assertEqual(set(result.keys()), expected_keys,
                           "Contract violation: keys changed. Update local_coach.py!")

            # Contract: Types must be correct
            self.assertIsInstance(result['predicted_value'], float)
            self.assertIsInstance(result['lower_bound'], float)
            self.assertIsInstance(result['upper_bound'], float)
            self.assertIsInstance(result['confidence_level'], float)
            self.assertIsInstance(result['interval_width'], float)
            self.assertIsInstance(result['has_intervals'], bool)
        finally:
            ml.train_models.HAS_MAPIE = original_has_mapie

    def test_predict_with_intervals_no_model_trained(self):
        """Fallback when model not trained with intervals."""
        import ml.train_models
        import numpy as np

        original_has_mapie = ml.train_models.HAS_MAPIE
        try:
            ml.train_models.HAS_MAPIE = True

            from ml.train_models import DistancePredictor

            predictor = DistancePredictor()

            # Mock base model but no MAPIE model
            predictor.model = Mock()
            predictor.model.predict = Mock(return_value=np.array([250.0]))
            predictor._feature_names = ['ball_speed', 'launch_angle', 'back_spin',
                                       'club_speed', 'attack_angle', 'dynamic_loft']
            predictor.mapie_model = None

            result = predictor.predict_with_intervals(
                ball_speed=165,
                launch_angle=12,
                back_spin=2500,
            )

            # Should fall back to point estimate
            self.assertFalse(result['has_intervals'])
            self.assertIn('predicted_value', result)
            self.assertIn('message', result)
            self.assertIn('not trained with intervals', result['message'])
        finally:
            ml.train_models.HAS_MAPIE = original_has_mapie


if __name__ == '__main__':
    unittest.main()
