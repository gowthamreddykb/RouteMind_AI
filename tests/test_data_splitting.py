import pytest
import data_splitting as DS
import load_data as L
import feature_engineering as FE

def test_no_order_overlap(cleaned, split):
    ids = {s: set(cleaned.loc[split == s, "Order Id"]) for s in ["train", "val", "test"]}
    assert not (ids["train"] & ids["val"]) and not (ids["train"] & ids["test"]) and not (ids["val"] & ids["test"])

def test_chronological_order(parts):
    assert parts["train"][FE.RAW_DATE].max() <= parts["val"][FE.RAW_DATE].min()
    assert parts["val"][FE.RAW_DATE].max() <= parts["test"][FE.RAW_DATE].min()

def test_proportions_close_to_70_15_15(cleaned, split):
    frac = split.value_counts(normalize=True)
    assert abs(frac["train"] - 0.70) < 0.01 and abs(frac["val"] - 0.15) < 0.01 and abs(frac["test"] - 0.15) < 0.01

def test_every_row_assigned_and_both_classes(cleaned, split):
    assert split.notna().all()
    for s in ["train", "val", "test"]:
        assert cleaned.loc[split == s, L.TARGET].nunique() == 2

def test_validate_split_detects_overlap(cleaned, split):
    bad = split.copy()
    oid = cleaned.loc[split == "test", "Order Id"].iloc[0]
    bad[(cleaned["Order Id"] == oid).idxmax()] = "train"       # move one row of a test order into train
    with pytest.raises(RuntimeError, match="FAIL"):
        DS.validate_split(cleaned, bad)

def test_summary_counts(cleaned, split):
    s = DS.split_summary(cleaned, split)
    assert s.rows.sum() == len(cleaned)
