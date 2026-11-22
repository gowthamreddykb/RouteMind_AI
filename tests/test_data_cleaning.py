import pytest
import data_cleaning as DC
import load_data as L

def test_target_and_ids_unchanged(raw, cleaned):
    assert cleaned[L.TARGET].equals(raw[L.TARGET]) and cleaned["Order Id"].equals(raw["Order Id"])
    assert cleaned["Order Item Id"].equals(raw["Order Item Id"])

def test_private_and_empty_columns_removed(cleaned):
    for c in DC.PRIVATE_COLS + ["Product Description"]:
        assert c not in cleaned.columns

def test_label_standardised(cleaned, raw):
    assert "EE. UU." not in set(cleaned["Customer Country"]) and "United States" in set(cleaned["Customer Country"])
    assert "South of  USA " in set(raw["Order Region"])          # raw has double + trailing space
    assert "South of USA" in set(cleaned["Order Region"]) and "South of  USA " not in set(cleaned["Order Region"])

def test_no_imputation_before_split_and_zip_is_string(cleaned):
    assert cleaned["Order Zipcode"].isna().mean() > 0.86          # missing postal codes not invented
    assert cleaned["Customer Zipcode"].dropna().map(type).eq(str).all()

def test_raw_dataframe_not_modified(raw):
    before = raw["Customer Country"].copy()
    DC.clean_data(raw.head(2000))
    assert raw["Customer Country"].equals(before)

def test_invalid_target_stops(raw):
    bad = raw.head(100).copy(); bad.loc[0, L.TARGET] = 7
    with pytest.raises(ValueError):
        DC.clean_data(bad)

def test_inconsistent_order_target_stops(raw):
    d = raw.head(500).copy()
    oid = d["Order Id"].iloc[0]; idx = d.index[d["Order Id"] == oid]
    if len(idx) < 2:
        idx = d.index[d.duplicated("Order Id", keep=False)][:2]
    d.loc[idx[0], L.TARGET] = 1 - d.loc[idx[1], L.TARGET]
    with pytest.raises(ValueError):
        DC.clean_data(d)
