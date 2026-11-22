# RouteMind AI - Execution and Verification Instructions

## 1. Environment Setup

Activate the project Python environment:
```powershell
Set-Location "c:\gowtham_mithraz\RouteMind_AI project"
$PYTHON = "C:\gowtham_mithraz\RouteMind_AI\RouteMind_AI_venv\Scripts\python.exe"
```

---

## 2. Running the 13-Stage Production Pipeline

### Run on Historical DataCo Dataset:
```powershell
& $PYTHON pipeline/run_pipeline.py --dataset historical
```

### Run on Newly Provided Excel Dataset (Independent Run):
```powershell
& $PYTHON pipeline/run_pipeline.py --dataset new_excel
```

### Quick Verification Run (Subsampled):
```powershell
& $PYTHON pipeline/run_pipeline.py --dataset historical --sample 15000
```

---

## 3. Running Automated Tests

Run the complete integration and unit test suite:
```powershell
& $PYTHON -m pytest test_pipeline_and_db.py -v
```

Run the Flask REST API & Prediction Service test suite:
```powershell
& $PYTHON test_flask_service.py
```

---

## 4. Starting the Flask REST API & Web Dashboard

Start the server:
```powershell
& $PYTHON app.py
```

The service is available on port 5000:
- **Interactive Control Tower Dashboard**: `http://localhost:5000/dashboard`
- **Health Check & Model Inventory**: `http://localhost:5000/health`
- **Model Registry Catalog**: `http://localhost:5000/models/registry`
- **Live Event Prediction**: `POST http://localhost:5000/predict/live-event`
- **Control Tower Assessment**: `POST http://localhost:5000/predict/control-tower`
- **Batch Prediction**: `POST http://localhost:5000/predict/batch`
- **Official Model Metrics**: `http://localhost:5000/metrics`
- **Recent Persisted Scores**: `http://localhost:5000/database/recent-scores`

---

## 5. Testing Live Event Prediction via cURL

```powershell
curl -X POST http://localhost:5000/predict/live-event `
  -H "Content-Type: application/json" `
  -d '{
    "Order Id": "LIVE-TEST-101",
    "Days for shipment (scheduled)": 4,
    "Type": "DEBIT",
    "Shipping Mode": "Standard Class",
    "Order Region": "South Asia",
    "Sales": 350.0
  }'
```
