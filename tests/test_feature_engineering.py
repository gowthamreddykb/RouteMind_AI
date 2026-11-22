import numpy as np
import pandas as pd
import pytest
import feature_engineering as FE
from conftest import records_from

def _rec(cleaned, date):
    r = records_from(cleaned, 1)[0]; r[FE.RAW_DATE] = date; return pd.DataFrame([r])

def test_calendar_features_correct(cleaned):
    f = FE.engineer_order_features(_rec(cleaned, "1/31/2018 22:56")).iloc[0]     # Wednesday
    assert (f.order_year, f.order_month, f.order_day, f.order_day_of_week, f.order_hour, f.is_weekend) == (2018, 1, 31, 2, 22, 0)

def test_weekend_flag(cleaned):
    assert FE.engineer_order_features(_rec(cleaned, "1/27/2018 10:00")).iloc[0].is_weekend == 1       # Saturday

def test_iso_dates_accepted(cleaned):
    assert FE.engineer_order_features(_rec(cleaned, "2018-01-31T22:56:00")).iloc[0].order_hour == 22

def test_invalid_date_becomes_nan_not_crash(cleaned):
    f = FE.engineer_order_features(_rec(cleaned, "not a date"))
    assert f[["order_year", "order_hour"]].isna().all().all()

def test_missing_field_raises(cleaned):
    with pytest.raises(KeyError):
        FE.engineer_order_features(_rec(cleaned, "1/1/2018 1:00").drop(columns=["Shipping Mode"]))

def test_no_duplicate_columns_and_renames(cleaned):
    f = FE.engineer_order_features(cleaned.head(100))
    assert f.columns.is_unique and "Sales" not in f.columns and "order_value" in f.columns and "scheduled_days" in f.columns

def test_row_and_batch_give_identical_features(cleaned):
    batch = FE.engineer_order_features(cleaned.head(20))
    one = FE.engineer_order_features(cleaned.head(20).iloc[[7]])
    pd.testing.assert_frame_equal(batch.iloc[[7]], one)

def test_training_and_inference_share_text_standardisation():
    s = pd.Series(["South of  USA", "EE. UU."]); out = FE.standardize_categories(pd.DataFrame({"Customer Country": s}), ["Customer Country"])
    assert out["Customer Country"].tolist() == ["South of USA", "United States"]

def test_features_match_listed_schema(cleaned):
    f = FE.engineer_order_features(cleaned.head(50)); num, cat = FE.feature_lists()
    assert list(f.columns) == num + cat

def test_missing_text_values_survive_standardisation():
    out = FE.standardize_categories(pd.DataFrame({"Market": ["Africa ", None, np.nan]}), ["Market"])
    assert out["Market"].iloc[0] == "Africa" and out["Market"].iloc[1:].isna().all()
