import pandas as pd
from src.feature_engineering import engineer_order_features

def preprocess_order_creation(raw_df):
    return engineer_order_features(raw_df)
