# models/linear/logistic.py
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from models.base import BaseModel

class LogitModel(BaseModel):
    def __init__(self, C=1.0, penalty="l2", max_iter=1000):
        self.clf = LogisticRegression(C=C, penalty=penalty, max_iter=max_iter)

    def fit(self, X: pd.DataFrame, y: pd.Series):
        self.clf.fit(X, y)
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        return self.clf.predict_proba(X)[:, 1]  # probability of "up"
