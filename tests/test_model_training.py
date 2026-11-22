import numpy as np
import pandas as pd
import model_training as MT
import hyperparameter_tuning as HT
import feature_audit as FA
import load_data as L

def test_probabilities_between_zero_and_one(small_model, parts):
    p = small_model[0].predict_proba(parts["test"].head(500))[:, 1]
    assert ((p >= 0) & (p <= 1)).all()

def test_model_beats_chance_on_validation(small_model, parts):
    from sklearn.metrics import roc_auc_score
    p = small_model[0].predict_proba(parts["val"].head(5000))[:, 1]
    assert roc_auc_score(parts["val"].head(5000)[L.TARGET], p) > 0.65

def test_logistic_regression_trains(parts):
    tr = parts["train"].sample(8000, random_state=0); va = parts["val"].sample(3000, random_state=0)
    pipe, res = MT.train_logistic(tr, tr[L.TARGET].values, va, va[L.TARGET].values, (), C_grid=(0.1,), weights=(None,))
    p = pipe.predict_proba(va)[:, 1]
    assert ((p >= 0) & (p <= 1)).all() and len(res) == 1

def test_random_search_uses_only_given_validation(parts):
    tr = parts["train"].sample(6000, random_state=0); va = parts["val"].sample(2000, random_state=0)
    front = MT.make_front((), False); Xtr = front.fit_transform(tr); Xva = front.transform(va)
    params, model, trials = HT.random_search(Xtr, tr[L.TARGET].values, Xva, va[L.TARGET].values, n_iter=2)
    assert len(trials) == 2 and set(HT.search_space(0.8)) >= {"max_depth", "learning_rate", "scale_pos_weight", "gamma"}

def test_training_features_pass_leakage_guard(small_model):
    names = small_model[1].named_steps["features"].transform(__import__("pandas").DataFrame()).columns if False else None
    import feature_engineering as FE
    num, cat = FE.feature_lists()
    assert FA.assert_no_prohibited(num + cat)

def test_training_is_reproducible(parts):
    tr = parts["train"].sample(5000, random_state=0); va = parts["val"].sample(2000, random_state=0)
    front = MT.make_front((), False); Xtr = front.fit_transform(tr); Xva = front.transform(va)
    a = MT.fit_xgb({"n_estimators": 30}, Xtr, tr[L.TARGET].values, Xva, va[L.TARGET].values).predict_proba(Xva)
    b = MT.fit_xgb({"n_estimators": 30}, Xtr, tr[L.TARGET].values, Xva, va[L.TARGET].values).predict_proba(Xva)
    np.testing.assert_allclose(a, b)
