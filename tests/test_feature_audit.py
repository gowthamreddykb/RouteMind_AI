import pandas as pd
import pytest
import feature_audit as FA
import load_data as L

@pytest.fixture(scope="module")
def audits(raw, tmp_path_factory):
    d = tmp_path_factory.mktemp("rep")
    return FA.build_audits(raw, str(d)), d

def test_all_29_candidates_have_a_decision(audits):
    (oc, dp, leak), _ = audits
    assert set(L.CANDIDATES) <= set(oc["Original column name"]) and set(L.CANDIDATES) <= set(dp["Original column name"])
    assert oc[oc["Original column name"].isin(L.CANDIDATES)]["Final decision"].isin(["Include", "Exclude", "Review"]).all()

def test_required_audit_columns(audits):
    (oc, _, _), _ = audits
    for c in ["Original column name", "Data type", "Missing count", "Missing percentage", "Prediction stage",
              "Available at prediction time", "Leakage risk", "Final decision", "Reason"]:
        assert c in oc.columns

def test_shipping_date_excluded_from_both_stages(audits):
    (oc, dp, _), _ = audits
    for a in (oc, dp):
        r = a[a["Original column name"] == "shipping date (DateOrders)"].iloc[0]
        assert r["Final decision"] == "Exclude" and r["Leakage risk"] == "High"

def test_shipping_date_is_derived_from_outcome(raw):
    import numpy as np
    od = pd.to_datetime(raw["order date (DateOrders)"], format="%m/%d/%Y %H:%M"); sd = pd.to_datetime(raw["shipping date (DateOrders)"], format="%m/%d/%Y %H:%M")
    gap = (sd - od).dt.total_seconds() / 86400
    assert np.corrcoef(gap, raw["Days for shipping (real)"])[0, 1] > 0.99

def test_guard_blocks_prohibited_columns():
    for bad in [L.TARGET, "Days for shipping (real)", "Delivery Status", "Order Id", "Customer Email", "shipping date (DateOrders)"]:
        with pytest.raises(ValueError, match="STOP"):
            FA.assert_no_prohibited(["Type", bad])
    assert FA.assert_no_prohibited(["Type", "Shipping Mode"])

def test_review_overrides_are_applied(raw, tmp_path):
    oc, _, _ = FA.build_audits(raw, str(tmp_path), overrides={"Latitude": ("Exclude", "test")})
    assert oc.loc[oc["Original column name"] == "Latitude", "Final decision"].iloc[0] == "Exclude"

def test_stage_reports_written(raw, tmp_path):
    oc, _, _ = FA.build_audits(raw, str(tmp_path)); st = FA.write_stage_reports(raw, oc, str(tmp_path))
    assert {"Feature Name", "Order Creation Availability", "Dispatch Availability", "Data Type", "Leakage Risk",
            "Missing Percentage", "Decision", "Reason"} <= set(st.columns)
    assert (tmp_path / "approved_feature_list.csv").exists() and (tmp_path / "feature_dictionary.csv").exists()
