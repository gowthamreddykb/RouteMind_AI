"""model_training.py - Phases 8-9: Logistic Regression baseline and XGBoost fitting helpers."""
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, average_precision_score, log_loss, brier_score_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer
from xgboost import XGBClassifier
from feature_engineering import engineer_order_features, feature_lists
from data_preprocessing import build_preprocessor
from load_data import RANDOM_SEED

def features_step(extra_cols, hist_cols=()):
    """Pipeline step that turns RAW columns into model features (same code at training and inference)."""
    return FunctionTransformer(engineer_order_features, kw_args={"extra_cols": list(extra_cols), "hist_cols": list(hist_cols)}, validate=False)

def make_front(extra_cols, scale_numeric, hist_cols=()):
    """features -> preprocessing. Must be .fit() on TRAINING rows only."""
    num, cat = feature_lists(extra_cols, hist_cols)
    return Pipeline([("features", features_step(extra_cols, hist_cols)), ("prep", build_preprocessor(num, cat, scale_numeric))])

def quick_scores(y, p):
    return {"roc_auc": roc_auc_score(y, p), "pr_auc": average_precision_score(y, p),
            "log_loss": log_loss(y, p), "brier": brier_score_loss(y, p)}

def train_logistic(raw_tr, y_tr, raw_va, y_va, extra_cols, C_grid=(0.01, 0.1, 1.0), weights=(None, "balanced")):
    """Baseline. Grid over regularisation strength C and class weighting, chosen on VALIDATION ROC-AUC."""
    best, rows = None, []
    for cw in weights:
        for C in C_grid:
            pipe = Pipeline([("front", make_front(extra_cols, True)),
                             ("model", LogisticRegression(C=C, solver="lbfgs", max_iter=1000,
                                                          class_weight=cw, random_state=RANDOM_SEED))])
            pipe.fit(raw_tr, y_tr)
            s = quick_scores(y_va, pipe.predict_proba(raw_va)[:, 1])
            s_tr = quick_scores(y_tr, pipe.predict_proba(raw_tr)[:, 1])
            rows.append({"model": "LogisticRegression", "C": C, "class_weight": str(cw), "solver": "lbfgs", "penalty": "l2 (default)",
                         **{f"val_{k}": v for k, v in s.items()}, "train_roc_auc": s_tr["roc_auc"]})
            if best is None or s["roc_auc"] > best[0]:
                best = (s["roc_auc"], pipe)
    return best[1], pd.DataFrame(rows)

def make_xgb(params, seed=RANDOM_SEED, early_stopping_rounds=30):
    base = dict(objective="binary:logistic", eval_metric="logloss", tree_method="hist", random_state=seed,
                n_jobs=1, early_stopping_rounds=early_stopping_rounds)
    base.update(params)
    return XGBClassifier(**base)

def fit_xgb(params, Xtr, ytr, Xva, yva):
    """Fit with early stopping on the VALIDATION set (never the test set)."""
    m = make_xgb(params)
    m.fit(Xtr, ytr, eval_set=[(Xva, yva)], verbose=False)
    return m

DEFAULT_XGB = {}    # library defaults (n_estimators=100 etc.), early stopping still applied on validation
