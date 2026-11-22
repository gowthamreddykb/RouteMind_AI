import datetime as dt
import pandas as pd

def format_iso(dt_obj=None):
    if dt_obj is None:
        dt_obj = dt.datetime.now(dt.timezone.utc)
    return dt_obj.isoformat()

def parse_date(date_str):
    if not date_str:
        return None
    try:
        return pd.to_datetime(date_str)
    except Exception:
        return None

def days_between(start_date, end_date):
    s = parse_date(start_date)
    e = parse_date(end_date)
    if s is None or e is None:
        return 0.0
    return max((e - s).total_seconds() / 86400.0, 0.0)
