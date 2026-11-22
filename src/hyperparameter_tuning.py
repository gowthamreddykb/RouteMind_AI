"""hyperparameter_tuning.py - Phase 9: randomized search for XGBoost using the VALIDATION period only.

Why not RandomizedSearchCV? Shuffled K-fold would mix future and past orders and split same-order rows.
A single chronological validation partition (already group-safe) is the leakage-safe choice here.
"""
import time
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss
from sklearn.model_selection import ParameterSampler
from model_training import fit_xgb
from load_data import RANDOM_SEED

def search_space(neg_pos_ratio, extra_spw=()):
    return {"n_estimators": [300, 600], "max_depth": [3, 4, 5, 6, 8], "learning_rate": [0.03, 0.05, 0.1],
            "min_child_weight": [1, 5, 10, 20], "subsample": [0.7, 0.85, 1.0], "colsample_bytree": [0.5, 0.7, 0.9],
            "gamma": [0, 0.1, 0.5, 1.0], "reg_alpha": [0, 0.1, 1.0], "reg_lambda": [1, 5, 10],
            "scale_pos_weight": [round(neg_pos_ratio, 4), 1.0] + list(extra_spw)}

def random_search(Xtr, ytr, Xva, yva, n_iter=12, seed=RANDOM_SEED, extra_spw=()):
    ratio = float((ytr == 0).sum() / (ytr == 1).sum())
    rows, best = [], None
    for i, params in enumerate(ParameterSampler(search_space(ratio, extra_spw), n_iter=n_iter, random_state=seed)):
        t = time.time()
        m = fit_xgb(params, Xtr, ytr, Xva, yva)
        p = m.predict_proba(Xva)[:, 1]
        r = {"trial": i, **params, "best_iteration": int(m.best_iteration),
             "val_roc_auc": roc_auc_score(yva, p), "val_pr_auc": average_precision_score(yva, p),
             "val_brier": brier_score_loss(yva, p), "seconds": round(time.time() - t, 1)}
        rows.append(r)
        print(f"  trial {i + 1}/{n_iter}: val AUC={r['val_roc_auc']:.4f} (best_iter={r['best_iteration']}, {r['seconds']}s)", flush=True)
        if best is None or r["val_roc_auc"] > best[0]:
            best = (r["val_roc_auc"], params, m)
    return best[1], best[2], pd.DataFrame(rows)
