from src.dispatch_prediction import validate_dispatch_records, get_dispatch_schema

def preprocess_dispatch(records):
    return validate_dispatch_records(records, get_dispatch_schema())
