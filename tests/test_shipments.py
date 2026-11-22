import pytest
from src.utils.date_utils import days_between

def test_days_between():
    assert days_between('2026-11-01', '2026-11-04') == 3.0
    assert days_between('2026-11-04', '2026-11-01') == 0.0
