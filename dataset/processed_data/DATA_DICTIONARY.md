# Project FORESIGHT — Data Dictionary & Preprocessing Documentation

## 1. Overview
This document outlines the end-to-end dataset transformation for **Project FORESIGHT: AI-Powered Demand & Inventory Intelligence Platform**.
The raw data from `calendar.csv`, `inventory_snapshots.csv`, `sales_daily.csv`, and `sku_master.csv` has been analyzed, integrated, and transformed into high-dimensional, ML-ready feature matrices for demand forecasting and inventory optimization.

---

## 2. Processed Files Generated
All processed files are stored in `dataset/processed_data/`:

| File Name | Description | Rows / Columns |
| :--- | :--- | :--- |
| `foresight_demand_features.csv` | Full transformed dataset with all temporal, lag, rolling, economic, and inventory features. | 392 rows, 46 cols |
| `train_features.csv` | Training split (first 70% time window: 2026-05-22 to 2026-07-28). | 272 rows, 46 cols |
| `val_features.csv` | Validation split (15% time window: 2026-07-29 to 2026-08-12). | 60 rows, 46 cols |
| `test_features.csv` | Out-of-sample Test split (last 15% time window: 2026-08-13 to 2026-08-27). | 60 rows, 46 cols |
| `inventory_intelligence_summary.csv` | SKU-level supply chain KPIs (Safety Stock, ROP, DOS, Stockout/Overstock risks & Actions). | 4 SKUs, 15 cols |
| `test_predictions_sample.csv` | Model validation predictions comparing actual vs predicted sales units. | 60 rows, 5 cols |

---

## 3. SKU Diagnostic & Supply Chain Intelligence Analysis

| SKU ID | Category | Lead Time | Daily Sales (Mean ± Std) | Stock On Hand | On Order | Days of Supply (DOS) | Safety Stock | Reorder Point (ROP) | Health Status | Recommended Action |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **SKU_REORDER** | Furniture | 5 days | 9.86 ± 2.18 | 20 | 0 | **2.0 days** | 9 | 59 | **STOCKOUT_RISK** | 🚨 **Critical**: Stock (20) < ROP (59). Place purchase order immediately! |
| **SKU_CLEAR** | Decor | 7 days | 1.54 ± 0.55 | 150 | 0 | **97.5 days** | 3 | 14 | **OVERSTOCK_RISK** | ⚠️ **Excess Stock**: Run clearance/markdown promotion to release working capital. |
| **SKU_WATCH** | Textiles | 10 days | 15.27 ± 8.62 | 60 | 40 | **3.9 days** | 45 | 198 | **EXPEDITE_PO** | 🔍 **Watch / High Volatility**: Lead time 10 days. Expedite inbound shipment of 40 units. |
| **SKU_HEALTHY** | Lighting | 5 days | 7.70 ± 1.25 | 50 | 0 | **6.5 days** | 5 | 44 | **HEALTHY** | ✅ **Optimal**: Inventory balanced. Maintain standard replenishment schedule. |

---

## 4. Feature Dictionary

### A. Temporal & Calendar Features
- `date`: Daily timestamp (YYYY-MM-DD)
- `day_of_week`: Day of the week integer (0 = Monday, 6 = Sunday)
- `day_of_month`: Day index within month (1–31)
- `month`: Calendar month (1–12)
- `is_weekend`: Flag indicating Saturday/Sunday (1) or weekday (0)
- `is_holiday`: National / retail holiday flag from calendar
- `promotion_active`: Binary indicator of active marketing campaign
- `dow_sin`, `dow_cos`: Sine and cosine cyclical encodings for day of the week
- `month_sin`, `month_cos`: Sine and cosine cyclical encodings for seasonality

### B. Product & Economics
- `sku_id`: Unique identifier for the product
- `category`: Product category (Furniture, Decor, Textiles, Lighting)
- `lead_time_days`: Supplier delivery turnaround in days
- `unit_cost`: Cost of goods sold (COGS) per unit
- `selling_price`: Retail sales price per unit
- `margin_per_unit`: Unit profit margin (`selling_price - unit_cost`)
- `margin_pct`: Margin percentage
- `daily_revenue`: Daily gross sales revenue
- `daily_gross_profit`: Daily gross profit

### C. Time-Series Historical Demand & Rolling Features (Leakage-Free)
- `sales_lag_1`: Previous day's sales ($t-1$)
- `sales_lag_2`, `sales_lag_3`: Sales from $t-2$ and $t-3$
- `sales_lag_7`: Sales from same day last week ($t-7$)
- `sales_lag_14`: Sales from two weeks ago ($t-14$)
- `rolling_mean_7`: 7-day moving average demand
- `rolling_std_7`: 7-day demand standard deviation (short-term volatility)
- `rolling_min_7`, `rolling_max_7`: 7-day range
- `rolling_mean_14`, `rolling_std_14`: 14-day rolling window statistics
- `rolling_mean_21`, `rolling_std_21`: 21-day rolling window statistics

### D. Inventory Policy & Risk Features
- `stock_on_hand`: Physical warehouse inventory snapshot
- `stock_on_order`: Quantities currently in transit from vendor
- `safety_stock`: Buffer calculated using $SS = Z \times \sigma_d \times \sqrt{L}$ (95% service level, $Z=1.65$)
- `reorder_point`: Threshold $ROP = \text{Lead Time Demand} + \text{Safety Stock}$
- `inventory_status`: Automated supply chain triage classification

---

## 5. Machine Learning Benchmark Results

Trained on `train_features.csv` (272 samples), evaluated on `test_features.csv` (60 samples):

| Model | Test MAE | Test RMSE | Test WAPE (%) | Test $R^2$ |
| :--- | :--- | :--- | :--- | :--- |
| **Random Forest Regressor** | **2.740** | **4.722** | **32.82%** | **0.533** |
| **Gradient Boosting Regressor** | 2.852 | 5.238 | 34.15% | 0.425 |
| **LightGBM Regressor** | 2.998 | 4.891 | 35.91% | 0.498 |
| **Ridge Regression** | 3.111 | 5.029 | 37.25% | 0.470 |

*Saved best model artifact: `models/best_demand_forecaster.joblib`*
