import os, sys
import pytest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(ROOT_DIR, "src")
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import load_data as L
import data_cleaning as DC
import data_splitting as DS
import feature_engineering as FE
import model_training as MT

@pytest.fixture(scope="session")
def raw():
    return L.load_dataset(L.RAW_CSV)

@pytest.fixture(scope="session")
def cleaned(raw):
    return DC.clean_data(raw)[0]

@pytest.fixture(scope="session")
def split(cleaned):
    return DS.group_chronological_split(cleaned)

@pytest.fixture(scope="session")
def parts(cleaned, split):
    return {s: cleaned[split == s].reset_index(drop=True) for s in ["train", "val", "test"]}

@pytest.fixture(scope="session")
def small_model(parts):
    """Small, fast model trained on a train subsample (for logic tests; the production model is tested separately)."""
    from sklearn.pipeline import Pipeline
    tr = parts["train"].sample(15000, random_state=1); va = parts["val"].sample(5000, random_state=1)
    front = MT.make_front((), False)
    Xtr = front.fit_transform(tr); Xva = front.transform(va)
    m = MT.fit_xgb({"n_estimators": 60, "max_depth": 4, "learning_rate": 0.1}, Xtr, tr[L.TARGET].values, Xva, va[L.TARGET].values)
    return Pipeline([("front", front), ("model", m)]), front

def records_from(df, n=3, extra=()):
    cols = FE.BASE_RAW_FIELDS + list(extra)
    out = []
    for _, r in df.head(n).iterrows():
        d = {c: (r[c].item() if hasattr(r[c], "item") else r[c]) for c in cols}
        d[FE.RAW_DATE] = r[FE.RAW_DATE].strftime("%m/%d/%Y %H:%M")
        out.append(d)
    return out

@pytest.fixture(scope="session")
def production():
    import joblib
    path = os.path.join(L.MODELS, "order_creation", "best_model.joblib")
    if not os.path.exists(path):
        pytest.skip("production model not trained yet (run src/main.py first)")
    return joblib.load(path)
