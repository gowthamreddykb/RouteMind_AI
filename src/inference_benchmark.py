"""inference_benchmark.py - Phase 12.3: latency, throughput, memory and model-loading time (measured in the CURRENT environment)."""
import os, resource, time, json
import numpy as np
import pandas as pd
import prediction as PR

def benchmark(records, models_dir, n_single=300, batch=1000, version=None):
    t = time.perf_counter(); PR.load_model("order_creation", models_dir, reload=True, version=version); load_ms = (time.perf_counter() - t) * 1000
    out = {"model_load_ms": load_ms, "cpu_count_in_environment": os.cpu_count()}
    for explain in (False, True):
        ts = []
        for i in range(n_single):
            t = time.perf_counter(); PR.predict_at_order_creation(records[i % len(records)], explain=explain, models_dir=models_dir, version=version); ts.append((time.perf_counter() - t) * 1000)
        ts = np.array(ts[10:]); k = "with_shap" if explain else "no_shap"
        out[f"single_{k}"] = {"mean_ms": float(ts.mean()), "p50_ms": float(np.percentile(ts, 50)), "p95_ms": float(np.percentile(ts, 95)), "max_ms": float(ts.max()),
                               "throughput_per_s": float(1000 / ts.mean())}
    big = [records[i % len(records)] for i in range(batch)]
    for explain in (False, True):
        t = time.perf_counter(); PR.predict_at_order_creation(big, explain=explain, models_dir=models_dir, version=version); s = time.perf_counter() - t
        out[f"batch{batch}_{'with_shap' if explain else 'no_shap'}"] = {"seconds": s, "throughput_per_s": batch / s}
    out["peak_memory_mb_process"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    return out
