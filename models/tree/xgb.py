# models/tree/xgb.py
import pandas as pd
from xgboost import XGBClassifier
from models.base import register_model

@register_model(name="xgb", desc="XGBoost Classifier")
class XGBModel:
    def __init__(self):
        self.clf = XGBClassifier(use_label_encoder=False, eval_metric="logloss")

    def fit(self, X: pd.DataFrame, y: pd.Series):
        return self.clf.fit(X, y)

    def predict(self, X: pd.DataFrame):
        return self.clf.predict(X)

    def predict_proba(self, X: pd.DataFrame):
        return self.clf.predict_proba(X)[:, 1]