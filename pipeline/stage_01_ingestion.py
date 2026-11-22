"""
stage_01_ingestion.py - Stage 1: Data Ingestion & Dataset Isolation
Handles independent data loading for historical DataCo CSV and newly provided XLSX datasets.
Ensures zero cross-contamination and generates cryptographic integrity checksums.
"""

import os
import hashlib
import json
import pandas as pd
from datetime import datetime
try:
    from pipeline.config import PROJECT_ROOT, DATA_DIR, REPORTS_DIR
except ImportError:
    from config import PROJECT_ROOT, DATA_DIR, REPORTS_DIR

class DataIngestion:
    DATASET_CONFIGS = {
        "historical": {
            "name": "DataCo Supply Chain Historical Dataset",
            "version": "dataco_v1_historical_csv",
            "path": os.path.join(DATA_DIR, "raw", "historical_dataco", "DataCoSupplyChainDataset.csv"),
            "format": "csv",
            "encoding": "cp1252"
        },
        "new_excel": {
            "name": "DataCo Supply Chain Newly Provided Dataset",
            "version": "dataco_v2_new_excel",
            "path": os.path.join(DATA_DIR, "raw", "newly_provided_dataset", "DataCoSupplyChainDataset_new_dataset.xlsx"),
            "format": "excel",
            "sheet_name": "DataCoSupplyChainDataset"
        }
    }

    @staticmethod
    def compute_sha256(filepath):
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def load_dataset(self, dataset_key="historical", sample_rows=None):
        """Loads the requested dataset in strict isolation."""
        if dataset_key not in self.DATASET_CONFIGS:
            raise ValueError(f"Unknown dataset key: {dataset_key}. Choose 'historical' or 'new_excel'.")

        cfg = self.DATASET_CONFIGS[dataset_key]
        filepath = cfg["path"]
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Dataset file not found at: {filepath}")

        sha256 = self.compute_sha256(filepath)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Ingesting {cfg['name']} ({cfg['version']}) from {filepath}...")

        if cfg["format"] == "csv":
            df = pd.read_csv(filepath, encoding=cfg["encoding"], nrows=sample_rows, low_memory=False)
        else:
            df = pd.read_excel(filepath, sheet_name=cfg["sheet_name"], nrows=sample_rows)
            # Retain core 53 supply chain columns, dropping trailing Excel pivot/summary columns if present
            if len(df.columns) > 53:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Filtering out {len(df.columns) - 53} trailing auxiliary Excel columns from raw file.")
                df = df.iloc[:, :53]

        manifest = {
            "dataset_key": dataset_key,
            "dataset_name": cfg["name"],
            "dataset_version": cfg["version"],
            "source_path": filepath,
            "sha256": sha256,
            "rows_loaded": len(df),
            "columns_count": len(df.columns),
            "columns": list(df.columns),
            "ingested_at": datetime.utcnow().isoformat() + "Z"
        }

        manifest_path = os.path.join(REPORTS_DIR, f"ingestion_manifest_{dataset_key}.json")
        os.makedirs(REPORTS_DIR, exist_ok=True)
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Ingested {len(df):,} rows x {len(df.columns)} columns. SHA256: {sha256[:16]}...")
        return df, manifest
