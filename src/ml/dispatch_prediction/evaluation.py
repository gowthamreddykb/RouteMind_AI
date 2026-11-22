from src.model_evaluation import compute_metrics

def evaluate(y_true, y_prob, threshold=0.39):
    return compute_metrics(y_true, y_prob, threshold)
