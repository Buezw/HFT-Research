# models/base.py
from abc import ABC, abstractmethod
import numpy as np
import pandas as pd

class BaseModel(ABC):
    """
    All models in HFTSim should inherit from this interface.
    This ensures a consistent API across linear, tree, ML, DL, and RL models.
    """

    @abstractmethod
    def fit(self, X: pd.DataFrame, y: pd.Series):
        """
        Train the model on historical data.
        X : pd.DataFrame of features
        y : pd.Series of labels (e.g., direction or returns)
        """
        pass

    @abstractmethod
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """
        Return predicted probabilities (if applicable).
        Example: probability of upward move in [0,1].
        If the model does not support probability, raise NotImplementedError.
        """
        pass

    def predict(self, X: pd.DataFrame, thr: float = 0.5) -> np.ndarray:
        """
        Return discrete predictions (0/1 or -1/1 depending on convention).
        By default: classify as 1 if proba >= thr, else 0.
        """
        proba = self.predict_proba(X)
        return (proba >= thr).astype(int)
