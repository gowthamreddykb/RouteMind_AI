"""data_preprocessing.py - Phase 7: ColumnTransformer builders (fit on TRAINING data only, by the caller)."""
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

# Categories seen in fewer than this many training rows are pooled into one 'infrequent' bucket.
# This keeps high-cardinality columns (cities, countries, products) from creating thousands of columns,
# and also gives unseen categories at prediction time a safe bucket.
MIN_CATEGORY_FREQ = 200

def build_preprocessor(numeric, categorical, scale_numeric):
    """Numeric: median impute (+ scale for Logistic Regression). Categorical: 'Unknown' + one-hot."""
    num_steps = [("imputer", SimpleImputer(strategy="median"))]
    if scale_numeric:
        num_steps.append(("scaler", StandardScaler()))
    cat_steps = [("imputer", SimpleImputer(strategy="constant", fill_value="Unknown")),
                 ("onehot", OneHotEncoder(handle_unknown="infrequent_if_exist",
                                          min_frequency=MIN_CATEGORY_FREQ, sparse_output=True))]
    return ColumnTransformer([("num", Pipeline(num_steps), numeric),
                              ("cat", Pipeline(cat_steps), categorical)])
