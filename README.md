# 📈 Project FORESIGHT: AI-Powered Demand & Inventory Intelligence Platform

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Framework-Flask%20%2B%20ASGI-black.svg)](https://flask.palletsprojects.com/)
[![Uvicorn](https://img.shields.io/badge/Server-Uvicorn%20ASGI-purple.svg)](https://www.uvicorn.org/)
[![Scikit-Learn](https://img.shields.io/badge/ML-Scikit--Learn%20%7C%20XGBoost%20%7C%20LightGBM-orange.svg)](https://scikit-learn.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**Project FORESIGHT** is an enterprise-grade demand forecasting and inventory triage platform designed to eradicate retail stockouts, eliminate excess working capital in overstocked inventory, and provide executives with real-time AI-driven supply chain decision intelligence.

---

## 🌟 Key Capabilities & Features

### 1. 📊 Executive Decision KPIs
- **Forecast Accuracy & WAPE**: Live tracking of champion model performance (70.21% accuracy, 29.79% WAPE, $R^2 = 0.58$).
- **Supply Chain Risk Counters**: Immediate identification of SKUs at Stockout Risk (ROP breaches) vs Overstock Excess.
- **Inventory Valuation**: Total stock value on hand with pipeline tracking (+units on order).

### 2. 📉 14-Day Multi-Step Demand Forecasting
- Interactive Chart.js time-series visualization comparing 30-day historical sales with 14-day forward AI demand forecasts.
- SKU filtering with confidence envelopes and smooth curve connectors.
- One-click CSV dataset export for offline reporting and ERP ingestion.

### 3. 🛡️ Real-Time Inventory Triage Matrix
- Dynamic calculations for **Safety Stock (SS)**, **Reorder Points (ROP)**, and **Days of Supply (DOS)** based on lead times and demand volatility.
- Visual risk status badges: `Critical Reorder`, `Overstock Excess`, `Volatile Watch`, `Balanced`.
- Interactive supply chain actions: Instant Purchase Order (PO) creation, Clearance Flash Promos, and Carrier Expedite alerts with live toast confirmations.

### 4. 🎛️ Interactive "What-If" Demand & Margin Simulator
- Real-time simulation playground powered by the trained ML inference engine.
- Test scenarios by tweaking:
  - **SKU selection**
  - **Marketing promotion activation**
  - **Retail holiday effects**
  - **Day of week variations**
  - **Dynamic pricing elasticity**
- Instant readouts of **Predicted Demand Units**, **Projected Revenue**, **Estimated Gross Profit**, and **Margin %**.

### 5. 💱 Dual Currency Switcher ($ USD & ₹ INR)
- Single-click toggle between **US Dollar ($)** and **Indian Rupee (₹)**.
- Automatically converts all monetary metrics across Executive KPIs, Inventory Tables, Doughnut Tooltips, and What-If Simulator.
- Automatically normalizes inputs to USD before sending to the ML inference model, ensuring 100% prediction accuracy.
- Persistent state saved to `localStorage`.

### 6. 🌓 Dual Theme Engine (Minimalist Clean White & Dark Cyber)
- **Clean White Theme (Default)**: Pure white background (`#ffffff`) with deep black typography (`#000000`), subtle silver borders, and high-contrast monochrome charts.
- **Vibrant Color Theme**: Deep dark cyber mode with glassmorphic cards and neon accents.
- Seamless one-click header switcher.

### 7. 🧠 Machine Learning Model Intelligence & Explainability
- Benchmark leaderboard comparing **Tuned Random Forest**, **Tuned XGBoost**, **Tuned LightGBM**, and **Optimized Ensemble**.
- Top 10 Influential Demand Predictors visualization (Feature Importance).

---

## 🔬 Machine Learning Architecture

The forecasting engine utilizes a multi-model regression pipeline evaluated on out-of-sample temporal test splits:

| Model Architecture | Test MAE | Test RMSE | Test WAPE (%) | Test $R^2$ | Status |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Tuned Random Forest** | **2.487** | **4.477** | **29.79%** | **0.580** | 🏆 **Champion** |
| Optimized Ensemble (RF+XGB+LGB) | 2.524 | 4.596 | 30.23% | 0.557 | Runner-Up |
| Tuned XGBoost Regressor | 2.592 | 4.703 | 31.04% | 0.536 | Benchmark |
| Tuned LightGBM Regressor | 2.797 | 4.809 | 33.49% | 0.515 | Benchmark |

### Feature Engineering Pipeline:
- **Lags**: $t-1$, $t-2$, $t-3$, $t-7$, $t-14$ demand lags.
- **Rolling Windows**: 7, 14, and 21-day rolling means, standard deviations, min, and max.
- **Cyclical Encoding**: Sine and cosine transforms for Day-of-Week and Month.
- **Calendar & Events**: Weekend flags, holiday indicators, promotion triggers.
- **Product Economics**: Selling price, unit cost, margin per unit, margin percentage, lead time.

---

## 📁 Repository Structure

```
foresight-dashboard/
├── app.py                     # Production Flask API + Uvicorn ASGI Server
├── requirements.txt           # Python dependencies
├── Procfile                   # Cloud PaaS deployment configuration
├── README.md                  # Comprehensive platform documentation
│
├── dataset/
│   ├── raw_data/              # Original SKU master, calendar, inventory snapshots & sales
│   └── processed_data/        # Feature engineered splits & summary tables
│       ├── foresight_demand_features.csv
│       ├── inventory_intelligence_summary.csv
│       ├── train_features.csv
│       ├── val_features.csv
│       ├── test_features.csv
│       └── DATA_DICTIONARY.md
│
├── models/
│   └── best_demand_forecaster.joblib  # Serialized champion model bundle & artifacts
│
├── src/
│   ├── data_preprocessing.py   # ETL and feature engineering pipeline
│   └── train_baseline_models.py# Model training, tuning, and evaluation pipeline
│
└── static/                    # Frontend UI Dashboard
    ├── index.html             # Single-page executive application layout
    ├── css/
    │   └── style.css          # Design system, glassmorphism, responsive styles
    └── js/
        └── app.js             # API controller, Chart.js integrations, theme & currency
```

---

## 🚀 Getting Started

### 1. Prerequisites
- **Python 3.10+**
- **Git**
- Web browser (Chrome, Edge, Firefox, Safari)

### 2. Installation

1. Clone or extract the repository:
   ```bash
   git clone https://github.com/your-org/foresight-dashboard.git
   cd foresight-dashboard
   ```

2. Create and activate a virtual environment:
   ```bash
   # Windows (PowerShell)
   python -m venv venv
   .\venv\Scripts\Activate.ps1

   # macOS / Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

### 3. Launching the Platform

Start the high-performance ASGI server:
```bash
python app.py
```

The application will start on **`http://localhost:5000`**.

### 4. Viewing the Dashboard

Open your browser and navigate to:
- 👉 **[http://localhost:5000](http://localhost:5000)** *(Direct Flask/Uvicorn server)*
- Or open via VS Code Live Server at `http://127.0.0.1:5500/static/index.html` (auto-connects to backend via CORS).

---

## 📡 REST API Documentation

| Method | Endpoint | Description | Sample Query / Body |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Service health status and timestamp | `curl http://localhost:5000/health` |
| `GET` | `/api/kpis` | Executive summary metrics and stockout counters | `curl http://localhost:5000/api/kpis` |
| `GET` | `/api/inventory` | Complete inventory triage data and ROP calculations | `curl http://localhost:5000/api/inventory` |
| `GET` | `/api/forecast` | 14-day multi-step forward demand predictions | `/api/forecast?days=14` |
| `GET` | `/api/sales-history` | Historical SKU actual sales units | `/api/sales-history?days=30` |
| `GET` | `/api/model-metrics` | Benchmark leaderboard and feature importance scores | `curl http://localhost:5000/api/model-metrics` |
| `POST` | `/api/predict` | Live What-If demand scenario inference | JSON payload *(see below)* |

#### Sample `/api/predict` Request:
```bash
curl -X POST http://localhost:5000/api/predict \
  -H "Content-Type: application/json" \
  -d '{
    "sku_id": "SKU_REORDER",
    "promotion_active": 1,
    "is_holiday": 0,
    "day_of_week": 5,
    "selling_price": 249.99
  }'
```

#### Sample Response:
```json
{
  "sku_id": "SKU_REORDER",
  "predicted_demand_units": 14.8,
  "estimated_revenue": 3699.85,
  "estimated_profit": 1923.85,
  "scenario_parameters": {
    "day_of_week": 5,
    "is_holiday": 0,
    "promotion_active": 1,
    "selling_price": 249.99
  }
}
```

---

## ☁️ Deployment

The project is production-ready for deployment on **Heroku**, **Render**, **Railway**, **AWS ECS**, or any Docker/container platform.

- **Procfile** included:
  ```procfile
  web: python app.py
  ```
- Uses **Uvicorn ASGI** via `asgiref.wsgi.WsgiToAsgi` for high-concurrency asynchronous throughput with automatic fallback to standard WSGI.

---

## 📄 License
This project is licensed under the MIT License — see the LICENSE file for details.
