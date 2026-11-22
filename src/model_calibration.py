"""model_calibration.py - Phase 11: leakage-safe probability calibration (validation data only)."""
import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss

def _logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p)).reshape(-1, 1)

class Calibrator:
    """method: 'none' | 'sigmoid' (Platt) | 'isotonic'. Output always stays inside [0, 1]."""
    def __init__(self, method="none"):
        self.method = method
    def fit(self, p, y):
        if self.method == "sigmoid":
            self.m_ = LogisticRegression(C=1e6, max_iter=1000).fit(_logit(p), y)
        elif self.method == "isotonic":
            self.m_ = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0).fit(p, y)
        return self
    def transform(self, p):
        p = np.asarray(p, dtype=float)
        if self.method == "sigmoid":
            return self.m_.predict_proba(_logit(p))[:, 1]
        if self.method == "isotonic":
            return np.clip(self.m_.predict(p), 0.0, 1.0)
        return p

def choose_calibration(p_val, y_val):
    """Compare methods WITHOUT touching test data: fit on the first (older) half of validation,
    score on the second (newer) half. Pick a method only if it clearly improves Brier score;
    then refit the chosen method on all of validation."""
    h = len(p_val) // 2
    rows = []
    for method in ["none", "sigmoid", "isotonic"]:
        c = Calibrator(method).fit(p_val[:h], y_val[:h])
        q = c.transform(p_val[h:])
        rows.append({"method": method, "brier_on_newer_half": brier_score_loss(y_val[h:], q),
                     "log_loss_on_newer_half": log_loss(y_val[h:], np.clip(q, 1e-6, 1 - 1e-6))})
    tab = pd.DataFrame(rows)
    raw = tab.loc[tab.method == "none", "brier_on_newer_half"].iloc[0]
    best = tab.sort_values("brier_on_newer_half").iloc[0]
    chosen = best.method if (best.method != "none" and raw - best.brier_on_newer_half > 1e-4) else "none"
    return Calibrator(chosen).fit(p_val, y_val), tab, chosen
