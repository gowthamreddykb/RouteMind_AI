import pytest
import load_data as L

def test_dataset_loads(raw):
    assert raw.shape[0] > 100000 and raw.shape[1] == 53

def test_expected_candidate_columns_exist(raw):
    L.check_candidates_exist(raw)           # raises KeyError if anything is missing
    assert len(L.CANDIDATES) == 29

def test_missing_candidate_column_is_reported(raw):
    with pytest.raises(KeyError, match="Sales"):
        L.check_candidates_exist(raw.drop(columns=["Sales"]))

def test_target_exists_and_valid(raw):
    assert L.TARGET in raw.columns
    assert set(raw[L.TARGET].unique()) == {0, 1}

def test_missing_file_gives_clear_error():
    with pytest.raises(FileNotFoundError):
        L.load_dataset("does_not_exist.csv")

def test_non_utf8_file_falls_back(tmp_path):
    p = tmp_path / "x.csv"; p.write_bytes("a,b\n1,Mexic\xf3\n".encode("latin1"))
    assert L.load_dataset(str(p)).iloc[0, 1] == "Mexicó"
