from __future__ import annotations
from typing import Tuple, Dict, Any
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier

class RegimeClassifier:
    def __init__(self):
        self.model = GradientBoostingClassifier()
        self.cols: list[str] = []

    def fit(self, X: pd.DataFrame, y: pd.Series):
        self.cols = list(X.columns)
        self.model.fit(X.values, y.values)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        return self.model.predict_proba(X[self.cols].values)

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return self.model.predict(X[self.cols].values)
