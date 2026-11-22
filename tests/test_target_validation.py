import pandas as pd
import target_validation as TV
import load_data as L

def test_outcome_categories_cover_every_row(raw):
    o = TV.classify_outcomes(raw)
    assert set(o.unique()) <= {"ON_TIME", "LATE", "CANCELLED", "UNDELIVERED", "UNKNOWN"} and len(o) == len(raw)

def test_label_reproduced_on_eligible_rows(raw):
    o = TV.classify_outcomes(raw); el = TV.eligible_mask(o)
    rule = (raw["Days for shipping (real)"] > raw["Days for shipment (scheduled)"]).astype(int)
    assert (rule[el] == raw.loc[el, L.TARGET]).all()

def test_cancelled_rows_are_not_in_the_lateness_model(raw):
    o = TV.classify_outcomes(raw)
    assert not TV.eligible_mask(o)[raw["Delivery Status"] == "Shipping canceled"].any()
    assert (raw.loc[o == "CANCELLED", L.TARGET] == 0).all()           # the label noise this separation removes

def test_missing_duration_is_undelivered_or_unknown():
    d = pd.DataFrame({"Days for shipping (real)": [None, 3, 1], "Days for shipment (scheduled)": [2, 2, 2], "Delivery Status": ["Advance shipping", "Late delivery", "Shipping on time"]})
    assert TV.classify_outcomes(d).tolist() == ["UNDELIVERED", "LATE", "ON_TIME"]

def test_report_written(raw, tmp_path):
    TV.target_report(raw, TV.classify_outcomes(raw), str(tmp_path))
    assert (tmp_path / "target_definition_report.txt").exists() and (tmp_path / "target_outcome_summary.csv").exists()
