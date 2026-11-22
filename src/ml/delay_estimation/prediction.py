def predict_delay_days(records):
    # Heuristic regression estimation fallback or CatBoost
    return [max(float(r.get('warehouse_time', 2.0)) - float(r.get('scheduled_days', 4)), 0.0) for r in (records if isinstance(records, list) else [records])]
