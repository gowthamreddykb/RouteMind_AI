# Dataset Separation and Isolation Report

## 1. Dataset Isolation Mandate
To ensure scientific reproducibility and prevent data mixing or weight contamination:
- The historical DataCo dataset and the newly provided Excel dataset are stored and processed independently.
- Neither dataset is appended to or blended with the other.
- Feature scalers, encoders, and cleaning pipelines are fitted independently per dataset run.

---

## 2. Cryptographic Fingerprints & Provenance

| Property | Dataset 1: Historical DataCo | Dataset 2: Newly Provided Dataset |
|---|---|---|
| **Identifier** | `dataco_v1_historical_csv` | `dataco_v2_new_excel` |
| **File Format** | CSV (`cp1252` encoding) | Microsoft Excel OpenXML (`.xlsx`) |
| **Isolated Path** | `data/raw/historical_dataco/DataCoSupplyChainDataset.csv` | `data/raw/newly_provided_dataset/DataCoSupplyChainDataset_new_dataset.xlsx` |
| **File Size** | 95,501,472 bytes (~95.5 MB) | 59,796,281 bytes (~59.8 MB) |
| **SHA-256 Checksum** | `fa6d022ed437155e1a2f0378710602848703c8a7f203f7ff5d77805bf8480aa6` | `de5024211b623ac7a887c89d38745cbd1ce72dc793700c8f88fca3ac8b8981ea` |
| **Data Rows** | 180,519 records | 180,519 records |
| **Raw Columns** | 53 columns | 67 columns (53 core + 14 auxiliary pivot columns) |
| **Core Target Column** | `Late_delivery_risk` (54.83% positive rate) | `Late_delivery_risk` (54.83% positive rate) |

---

## 3. Schema Reconciliation & Auxiliary Column Filtering
Analysis of the 67 columns in the new Excel dataset revealed that columns 0 through 52 perfectly correspond to the original 53 DataCo supply chain features.
Columns 53 through 66 consist of analyst pivot tables and summary aggregations created in Excel:
- `Order Status.1`, `Delivery Status.1`: Aggregated pivot status counts
- `Unnamed: 68` through `Unnamed: 74`: Pivot table percentages (e.g., Late delivery count: 98,977, 54.83%)

`stage_01_ingestion.py` automatically strips these trailing 14 auxiliary columns upon ingestion, ensuring the cleaned data matrix contains only legitimate feature columns.

---

## 4. Pipeline Execution Isolation

Each dataset can be processed through the entire 13-stage pipeline via:
- Historical run: `python pipeline/run_pipeline.py --dataset historical`
- New Excel run: `python pipeline/run_pipeline.py --dataset new_excel`

All resulting intermediate files (`data/processed/historical/`, `data/splits/historical/` vs `data/processed/new_excel/`, `data/splits/new_excel/`) are stored in isolated subdirectories. Zero cross-contamination is verified.
