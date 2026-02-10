"""
XGBoost Hyperparameter Tuning for Small Datasets.

Provides dataset-size-aware hyperparameters with aggressive regularization
to prevent overfitting on 2000-5000 shot datasets.

Usage:
    from ml.tuning import get_small_dataset_params
    params = get_small_dataset_params(n_samples=2500)
    model = xgb.XGBRegressor(**params)
"""

from typing import Dict, Any


def get_small_dataset_params(n_samples: int) -> Dict[str, Any]:
    """
    Get XGBoost hyperparameters tuned for small datasets.

    Uses aggressive regularization to prevent overfitting on limited data.
    Parameters are tiered based on dataset size:
    - Very small (<1000): Maximum regularization
    - Small (<3000): Strong regularization
    - Medium (>=3000): Moderate regularization

    Args:
        n_samples: Number of training samples

    Returns:
        Dict of XGBoost hyperparameters including:
        - n_estimators: Number of boosting rounds
        - max_depth: Tree depth (lower = less overfitting)
        - learning_rate: Step size shrinkage
        - reg_lambda: L2 regularization (penalizes large weights)
        - reg_alpha: L1 regularization (feature selection)
        - subsample: Fraction of samples per tree
        - min_child_weight: Min sum of weights in child node
        - objective: Loss function
        - random_state: Random seed for reproducibility

    Example:
        >>> params = get_small_dataset_params(500)
        >>> params['max_depth']
        3
        >>> params['reg_lambda']
        3.0
    """
    # Base parameters (all tiers)
    params = {
        'objective': 'reg:squarederror',
        'random_state': 42,
    }

    if n_samples < 1000:
        # Very small dataset: maximum regularization
        params.update({
            'n_estimators': 50,
            'max_depth': 3,
            'learning_rate': 0.05,
            'reg_lambda': 3.0,      # High L2 regularization
            'reg_alpha': 1.5,       # High L1 regularization
            'subsample': 0.7,       # Aggressive row sampling
            'min_child_weight': 3,  # Prevent tiny leaf nodes
        })
    elif n_samples < 3000:
        # Small dataset: strong regularization
        params.update({
            'n_estimators': 75,
            'max_depth': 4,
            'learning_rate': 0.08,
            'reg_lambda': 2.0,
            'reg_alpha': 1.0,
            'subsample': 0.8,
            'min_child_weight': 2,
        })
    else:
        # Medium dataset: moderate regularization
        params.update({
            'n_estimators': 100,
            'max_depth': 5,
            'learning_rate': 0.1,
            'reg_lambda': 1.0,
            'reg_alpha': 0.5,
            'subsample': 0.8,
            'min_child_weight': 1,
        })

    return params
