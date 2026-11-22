import numpy as np
import pandas as pd
import model_training as MT
import feature_engineering as FE
import load_data as L

def test_imputer_and_scaler_fitted_on_training_only(parts):
    front = MT.make_front((), True).fit(parts["train"])
    prep = front.named_steps["prep"]
    feats_tr = FE.engineer_order_features(parts["train"]); feats_all = FE.engineer_order_features(
        pd.concat([parts["train"], parts["val"], parts["test"]]))
    num = FE.feature_lists()[0]
    np.testing.assert_allclose(prep.named_transformers_["num"].named_steps["imputer"].statistics_, feats_tr[num].median().values)
    np.testing.assert_allclose(prep.named_transformers_["num"].named_steps["scaler"].mean_, feats_tr[num].mean().values, rtol=1e-6)
    assert not np.allclose(feats_tr["order_year"].mean(), feats_all["order_year"].mean())   # proves train != full data

def test_unknown_categories_do_not_break(small_model, parts):
    front = small_model[1]; r = parts["test"].head(5).copy(); r["Customer City"] = "Atlantis"; r["Product Name"] = "Moon Rock"
    X = front.transform(r)
    assert X.shape[0] == 5 and np.isfinite(X.toarray()).all()

def test_same_schema_across_partitions(small_model, parts):
    front = small_model[1]
    shapes = {s: front.transform(parts[s].head(200)).shape[1] for s in parts}
    assert len(set(shapes.values())) == 1

def test_missing_values_are_imputed(small_model, parts):
    r = parts["test"].head(10).copy(); r["Order Item Quantity"] = np.nan; r["Market"] = np.nan
    assert np.isfinite(small_model[1].transform(r).toarray()).all()

def test_rare_categories_pooled(small_model):
    n = small_model[1].named_steps["prep"].get_feature_names_out().shape[0]
    assert n < 1000        # high-cardinality columns did not explode the matrix
