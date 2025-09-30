# models/linear/logistic.py
import pandas as pd
from sklearn.linear_model import LogisticRegression
from models.base import register_model

@register_model(name="logit", desc="Logistic Regression classifier", task="classification")
class LogitModel:
    def __init__(self):
        self.clf = LogisticRegression(max_iter=200)

    def fit(self, X: pd.DataFrame, y: pd.Series):
        return self.clf.fit(X, y)

    def predict(self, X: pd.DataFrame):
        return self.clf.predict(X)

    def predict_proba(self, X: pd.DataFrame):
        return self.clf.predict_proba(X)
