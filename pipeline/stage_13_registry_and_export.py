"""
stage_13_registry_and_export.py - Stage 13: Model Artifact Serialization & Registry Management
Saves trained model artifacts, feature schemas, and metadata without overwriting existing models.
Registers models into a centralized models/registry.json catalog.
"""

import os
import json
import joblib
from datetime import datetime
try:
    from pipeline.config import MODELS_DIR
except ImportError:
    from config import MODELS_DIR

class ModelRegistryExport:
    REGISTRY_PATH = os.path.join(MODELS_DIR, "registry.json")

    def export_model(
        self,
        model_id: str,
        stage: str,
        pipeline,
        numeric_features: list[str],
        categorical_features: list[str],
        metrics: dict,
        threshold: float = 0.5,
        version: str = "1.0.0",
        dataset_version: str = "dataco_v1_historical_csv"
    ) -> dict:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Registering and Exporting Artifacts for '{model_id}'...")

        export_dir = os.path.join(MODELS_DIR, f"{stage}_reference_pipeline")
        os.makedirs(export_dir, exist_ok=True)

        model_artifact_path = os.path.join(export_dir, f"{model_id}.joblib")
        schema_path = os.path.join(export_dir, "feature_schema.json")
        metadata_path = os.path.join(export_dir, "metadata.json")

        # 1. Save serialized model bundle
        joblib.dump(pipeline, model_artifact_path)

        # 2. Save feature schema
        schema = {
            "model_id": model_id,
            "prediction_stage": stage,
            "numeric_features": numeric_features,
            "categorical_features": categorical_features,
            "required_raw_columns": numeric_features + categorical_features,
            "decision_threshold": threshold
        }
        with open(schema_path, "w") as f:
            json.dump(schema, f, indent=2)

        # 3. Save metadata
        metadata = {
            "model_id": model_id,
            "model_version": version,
            "prediction_stage": stage,
            "dataset_version": dataset_version,
            "algorithm": type(pipeline.named_steps["classifier"]).__name__,
            "trained_at": datetime.utcnow().isoformat() + "Z",
            "decision_threshold": threshold,
            "evaluation_metrics": metrics
        }
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        # 4. Update centralized registry.json without overwriting existing entries
        registry = {"models": []}
        if os.path.exists(self.REGISTRY_PATH):
            try:
                with open(self.REGISTRY_PATH, "r") as f:
                    registry = json.load(f)
            except Exception:
                registry = {"models": []}

        existing_ids = {m.get("model_id") for m in registry.get("models", [])}
        registry_entry = {
            "model_id": model_id,
            "model_name": f"RouteMind {stage.title()} {metadata['algorithm']}",
            "model_version": version,
            "prediction_stage": stage,
            "dataset_version": dataset_version,
            "algorithm": metadata["algorithm"],
            "artifact_location": model_artifact_path,
            "feature_schema_location": schema_path,
            "decision_threshold": threshold,
            "evaluation_metrics": metrics,
            "registered_at": datetime.utcnow().isoformat() + "Z",
            "approval_status": "APPROVED_FOR_STAGING"
        }

        if model_id in existing_ids:
            registry["models"] = [m if m.get("model_id") != model_id else registry_entry for m in registry["models"]]
        else:
            registry["models"].append(registry_entry)

        with open(self.REGISTRY_PATH, "w") as f:
            json.dump(registry, f, indent=2)

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Successfully exported to {model_artifact_path} and updated {self.REGISTRY_PATH}.")
        return registry_entry
