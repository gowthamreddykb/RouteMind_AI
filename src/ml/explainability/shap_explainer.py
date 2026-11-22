from src.shap_explainability import explain_rows

def explain(pipeline, df, top_k=3):
    return explain_rows(pipeline, df, top_k=top_k)
