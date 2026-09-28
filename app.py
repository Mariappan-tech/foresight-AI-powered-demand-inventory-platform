"""
Project FORESIGHT: AI-Powered Demand & Inventory Intelligence Platform
Production Flask Application & REST API
"""

import os
import json
import datetime
import pandas as pd
import numpy as np
import joblib
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from asgiref.wsgi import WsgiToAsgi

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)
asgi_app = WsgiToAsgi(app)

# Configuration & Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, 'models')
PROCESSED_DIR = os.path.join(BASE_DIR, 'dataset', 'processed_data')
RAW_DIR = os.path.join(BASE_DIR, 'dataset', 'raw_data')

MODEL_PATH = os.path.join(MODELS_DIR, 'best_demand_forecaster.joblib')
INVENTORY_SUMMARY_PATH = os.path.join(PROCESSED_DIR, 'inventory_intelligence_summary.csv')
FULL_FEATURES_PATH = os.path.join(PROCESSED_DIR, 'foresight_demand_features.csv')

# Global cache for loaded artifacts
_model_bundle = None
_inventory_df = None
_features_df = None

def get_model_bundle():
    global _model_bundle
    if _model_bundle is None and os.path.exists(MODEL_PATH):
        try:
            _model_bundle = joblib.load(MODEL_PATH)
        except Exception as e:
            print(f"Error loading model bundle: {e}")
    return _model_bundle

def get_inventory_data():
    global _inventory_df
    if _inventory_df is None and os.path.exists(INVENTORY_SUMMARY_PATH):
        _inventory_df = pd.read_csv(INVENTORY_SUMMARY_PATH)
    return _inventory_df

def get_features_data():
    global _features_df
    if _features_df is None and os.path.exists(FULL_FEATURES_PATH):
        _features_df = pd.read_csv(FULL_FEATURES_PATH)
        _features_df['date'] = pd.to_datetime(_features_df['date'])
    return _features_df

# -------------------------------------------------------------
# Web & Static Routes
# -------------------------------------------------------------
@app.route('/')
def serve_index():
    index_path = os.path.join(BASE_DIR, 'static', 'index.html')
    if os.path.exists(index_path):
        return send_from_directory('static', 'index.html')
    return jsonify({
        "message": "Project FORESIGHT API is online.",
        "docs": "Endpoints available: /health, /api/kpis, /api/inventory, /api/sales-history, /api/forecast, /api/model-metrics, /api/predict"
    })

# -------------------------------------------------------------
# Health Check Endpoint (Deployment Ready)
# -------------------------------------------------------------
@app.route('/health', methods=['GET'])
def health_check():
    bundle = get_model_bundle()
    return jsonify({
        "status": "healthy",
        "service": "Project FORESIGHT API",
        "version": "1.0.0",
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "model_loaded": bundle is not None,
        "champion_model": bundle.get('model_name', 'Unknown') if bundle else None
    }), 200

# -------------------------------------------------------------
# High-Level Executive KPIs
# -------------------------------------------------------------
@app.route('/api/kpis', methods=['GET'])
def get_kpis():
    inv_df = get_inventory_data()
    feat_df = get_features_data()
    bundle = get_model_bundle()

    if inv_df is None or feat_df is None:
        return jsonify({"error": "Data artifacts not ready. Please run data preprocessing first."}), 500

    total_skus = int(len(inv_df))
    stockout_risks = int((inv_df['inventory_status'] == 'STOCKOUT_RISK').sum())
    overstock_risks = int((inv_df['inventory_status'] == 'OVERSTOCK_RISK').sum())
    watch_skus = int((inv_df['inventory_status'].isin(['VOLATILE_WATCH', 'EXPEDITE_PO'])).sum())
    healthy_skus = int((inv_df['inventory_status'] == 'HEALTHY').sum())

    total_stock_units = int(inv_df['current_stock_on_hand'].sum())
    total_stock_value = float(np.round((inv_df['current_stock_on_hand'] * inv_df['unit_cost']).sum(), 2))
    total_pipeline_orders = int(inv_df['current_stock_on_order'].sum())

    # Calculate model accuracy if available
    benchmark = bundle.get('benchmark', []) if bundle else []
    best_wape = 32.82
    best_r2 = 0.533
    if benchmark:
        champ = min(benchmark, key=lambda x: x.get('Test WAPE (%)', 100))
        best_wape = champ.get('Test WAPE (%)', 32.82)
        best_r2 = champ.get('Test R2', 0.533)

    return jsonify({
        "total_skus": total_skus,
        "stockout_risk_count": stockout_risks,
        "overstock_risk_count": overstock_risks,
        "watch_skus_count": watch_skus,
        "healthy_skus_count": healthy_skus,
        "total_stock_on_hand": total_stock_units,
        "total_stock_value_usd": total_stock_value,
        "total_stock_on_order": total_pipeline_orders,
        "forecast_wape_pct": best_wape,
        "forecast_accuracy_pct": round(100.0 - best_wape, 2),
        "model_r2_score": best_r2
    }), 200

# -------------------------------------------------------------
# Detailed Inventory Intelligence Table
# -------------------------------------------------------------
@app.route('/api/inventory', methods=['GET'])
def get_inventory():
    inv_df = get_inventory_data()
    if inv_df is None:
        return jsonify({"error": "Inventory data not found"}), 404

    records = inv_df.to_dict(orient='records')
    # Round float values for presentation
    for r in records:
        r['avg_daily_sales'] = round(r['avg_daily_sales'], 2)
        r['std_daily_sales'] = round(r['std_daily_sales'], 2)
        r['margin_per_unit'] = round(r['selling_price'] - r['unit_cost'], 2)
        r['margin_pct'] = round(((r['selling_price'] - r['unit_cost']) / r['selling_price']) * 100, 1)

    return jsonify({
        "count": len(records),
        "data": records
    }), 200

# -------------------------------------------------------------
# Historical Sales Data (Charts & Trends)
# -------------------------------------------------------------
@app.route('/api/sales-history', methods=['GET'])
def get_sales_history():
    feat_df = get_features_data()
    if feat_df is None:
        return jsonify({"error": "Features data not found"}), 404

    sku_filter = request.args.get('sku_id', None)
    days_limit = int(request.args.get('days', 60))

    df = feat_df.copy()
    if sku_filter:
        df = df[df['sku_id'] == sku_filter]

    # Get latest N days
    latest_dates = sorted(df['date'].unique())[-days_limit:]
    df = df[df['date'].isin(latest_dates)]

    cols_to_return = [
        'date', 'sku_id', 'sales_units', 'day_of_week', 'promotion_active',
        'is_holiday', 'daily_revenue', 'daily_gross_profit', 'rolling_mean_7'
    ]
    df['date'] = df['date'].dt.strftime('%Y-%m-%d')
    records = df[cols_to_return].to_dict(orient='records')

    return jsonify({
        "count": len(records),
        "days": days_limit,
        "data": records
    }), 200

# -------------------------------------------------------------
# Forward-Looking 14-Day Demand Forecast
# -------------------------------------------------------------
@app.route('/api/forecast', methods=['GET'])
def get_forecast():
    bundle = get_model_bundle()
    feat_df = get_features_data()
    inv_df = get_inventory_data()

    if bundle is None or feat_df is None:
        return jsonify({"error": "Forecasting model or data unavailable"}), 500

    model = bundle['model']
    features_list = bundle['features']
    forecast_days = int(request.args.get('days', 14))

    # Multi-step recursive forecasting per SKU
    skus = ['SKU_CLEAR', 'SKU_HEALTHY', 'SKU_REORDER', 'SKU_WATCH']
    sku_info = {row['sku_id']: row for _, row in inv_df.iterrows()} if inv_df is not None else {}

    all_forecasts = []
    last_date = feat_df['date'].max()

    for sku in skus:
        sku_df = feat_df[feat_df['sku_id'] == sku].sort_values('date').copy()
        recent_sales = list(sku_df['sales_units'].values)
        unit_price = sku_info.get(sku, {}).get('selling_price', 50.0)
        unit_cost = sku_info.get(sku, {}).get('unit_cost', 25.0)

        current_date = last_date
        simulated_sales = list(recent_sales)

        for step in range(1, forecast_days + 1):
            next_date = current_date + pd.Timedelta(days=step)
            dow = next_date.dayofweek
            month = next_date.month
            day = next_date.day
            is_weekend = 1 if dow in [5, 6] else 0

            # Lags from simulated history
            lag_1 = simulated_sales[-1]
            lag_2 = simulated_sales[-2] if len(simulated_sales) >= 2 else lag_1
            lag_3 = simulated_sales[-3] if len(simulated_sales) >= 3 else lag_2
            lag_7 = simulated_sales[-7] if len(simulated_sales) >= 7 else lag_1
            lag_14 = simulated_sales[-14] if len(simulated_sales) >= 14 else lag_7

            roll_7 = simulated_sales[-7:]
            roll_14 = simulated_sales[-14:]
            roll_21 = simulated_sales[-21:] if len(simulated_sales) >= 21 else simulated_sales

            feature_dict = {
                'day_of_week': dow,
                'month': month,
                'day_of_month': day,
                'is_weekend': is_weekend,
                'is_holiday': 0,
                'promotion_active': 0,
                'dow_sin': np.sin(2 * np.pi * dow / 7.0),
                'dow_cos': np.cos(2 * np.pi * dow / 7.0),
                'month_sin': np.sin(2 * np.pi * month / 12.0),
                'month_cos': np.cos(2 * np.pi * month / 12.0),
                'lead_time_days': sku_info.get(sku, {}).get('lead_time_days', 5),
                'unit_cost': unit_cost,
                'selling_price': unit_price,
                'margin_per_unit': unit_price - unit_cost,
                'margin_pct': ((unit_price - unit_cost) / unit_price) * 100,
                'sales_lag_1': lag_1,
                'sales_lag_2': lag_2,
                'sales_lag_3': lag_3,
                'sales_lag_7': lag_7,
                'sales_lag_14': lag_14,
                'rolling_mean_7': np.mean(roll_7),
                'rolling_std_7': np.std(roll_7) if len(roll_7) > 1 else 0.5,
                'rolling_min_7': np.min(roll_7),
                'rolling_max_7': np.max(roll_7),
                'rolling_mean_14': np.mean(roll_14),
                'rolling_std_14': np.std(roll_14) if len(roll_14) > 1 else 0.5,
                'rolling_min_14': np.min(roll_14),
                'rolling_max_14': np.max(roll_14),
                'rolling_mean_21': np.mean(roll_21),
                'rolling_std_21': np.std(roll_21) if len(roll_21) > 1 else 0.5,
                'rolling_min_21': np.min(roll_21),
                'rolling_max_21': np.max(roll_21),
                'is_SKU_CLEAR': 1 if sku == 'SKU_CLEAR' else 0,
                'is_SKU_HEALTHY': 1 if sku == 'SKU_HEALTHY' else 0,
                'is_SKU_REORDER': 1 if sku == 'SKU_REORDER' else 0,
                'is_SKU_WATCH': 1 if sku == 'SKU_WATCH' else 0
            }

            input_row = pd.DataFrame([feature_dict])[features_list]
            pred_demand = max(0.0, float(model.predict(input_row)[0]))
            pred_demand_rounded = round(pred_demand, 1)

            # Append to simulated series for next step
            simulated_sales.append(pred_demand_rounded)

            all_forecasts.append({
                'date': next_date.strftime('%Y-%m-%d'),
                'sku_id': sku,
                'forecast_day': step,
                'predicted_demand': pred_demand_rounded,
                'projected_revenue': round(pred_demand * unit_price, 2),
                'projected_cogs': round(pred_demand * unit_cost, 2),
                'projected_profit': round(pred_demand * (unit_price - unit_cost), 2)
            })

    return jsonify({
        "forecast_horizon_days": forecast_days,
        "count": len(all_forecasts),
        "data": all_forecasts
    }), 200

# -------------------------------------------------------------
# What-If Demand Simulation Endpoint
# -------------------------------------------------------------
@app.route('/api/predict', methods=['POST'])
def predict_scenario():
    bundle = get_model_bundle()
    feat_df = get_features_data()
    inv_df = get_inventory_data()

    if bundle is None:
        return jsonify({"error": "Model bundle not loaded"}), 500

    payload = request.get_json() or {}
    sku_id = payload.get('sku_id', 'SKU_REORDER')
    promotion_active = int(payload.get('promotion_active', 0))
    is_holiday = int(payload.get('is_holiday', 0))
    day_of_week = int(payload.get('day_of_week', 5))  # Default Saturday
    custom_price = payload.get('selling_price', None)

    # Fetch baseline stats
    sku_row = inv_df[inv_df['sku_id'] == sku_id].iloc[0] if inv_df is not None else None
    selling_price = float(custom_price) if custom_price else (sku_row['selling_price'] if sku_row is not None else 100.0)
    unit_cost = sku_row['unit_cost'] if sku_row is not None else 50.0

    sku_df = feat_df[feat_df['sku_id'] == sku_id].sort_values('date') if feat_df is not None else None
    recent_sales = list(sku_df['sales_units'].values) if sku_df is not None else [10] * 21

    lag_1 = recent_sales[-1]
    lag_2 = recent_sales[-2]
    lag_3 = recent_sales[-3]
    lag_7 = recent_sales[-7]
    lag_14 = recent_sales[-14]

    roll_7 = recent_sales[-7:]
    roll_14 = recent_sales[-14:]
    roll_21 = recent_sales[-21:]

    month = 9
    day = 28
    is_weekend = 1 if day_of_week in [5, 6] else 0

    feature_dict = {
        'day_of_week': day_of_week,
        'month': month,
        'day_of_month': day,
        'is_weekend': is_weekend,
        'is_holiday': is_holiday,
        'promotion_active': promotion_active,
        'dow_sin': np.sin(2 * np.pi * day_of_week / 7.0),
        'dow_cos': np.cos(2 * np.pi * day_of_week / 7.0),
        'month_sin': np.sin(2 * np.pi * month / 12.0),
        'month_cos': np.cos(2 * np.pi * month / 12.0),
        'lead_time_days': sku_row['lead_time_days'] if sku_row is not None else 5,
        'unit_cost': unit_cost,
        'selling_price': selling_price,
        'margin_per_unit': selling_price - unit_cost,
        'margin_pct': ((selling_price - unit_cost) / selling_price) * 100,
        'sales_lag_1': lag_1,
        'sales_lag_2': lag_2,
        'sales_lag_3': lag_3,
        'sales_lag_7': lag_7,
        'sales_lag_14': lag_14,
        'rolling_mean_7': np.mean(roll_7),
        'rolling_std_7': np.std(roll_7),
        'rolling_min_7': np.min(roll_7),
        'rolling_max_7': np.max(roll_7),
        'rolling_mean_14': np.mean(roll_14),
        'rolling_std_14': np.std(roll_14),
        'rolling_min_14': np.min(roll_14),
        'rolling_max_14': np.max(roll_14),
        'rolling_mean_21': np.mean(roll_21),
        'rolling_std_21': np.std(roll_21),
        'rolling_min_21': np.min(roll_21),
        'rolling_max_21': np.max(roll_21),
        'is_SKU_CLEAR': 1 if sku_id == 'SKU_CLEAR' else 0,
        'is_SKU_HEALTHY': 1 if sku_id == 'SKU_HEALTHY' else 0,
        'is_SKU_REORDER': 1 if sku_id == 'SKU_REORDER' else 0,
        'is_SKU_WATCH': 1 if sku_id == 'SKU_WATCH' else 0
    }

    input_df = pd.DataFrame([feature_dict])[bundle['features']]
    predicted_val = max(0.0, float(bundle['model'].predict(input_df)[0]))

    return jsonify({
        "sku_id": sku_id,
        "predicted_demand_units": round(predicted_val, 1),
        "estimated_revenue": round(predicted_val * selling_price, 2),
        "estimated_profit": round(predicted_val * (selling_price - unit_cost), 2),
        "scenario_parameters": {
            "promotion_active": promotion_active,
            "is_holiday": is_holiday,
            "day_of_week": day_of_week,
            "selling_price": selling_price
        }
    }), 200

# -------------------------------------------------------------
# Model Benchmark & Architecture Info
# -------------------------------------------------------------
@app.route('/api/model-metrics', methods=['GET'])
def get_model_metrics():
    bundle = get_model_bundle()
    if bundle is None:
        return jsonify({"error": "Model bundle not loaded"}), 404

    return jsonify({
        "champion_model": bundle.get('model_name', 'Unknown'),
        "features_count": len(bundle.get('features', [])),
        "features": bundle.get('features', []),
        "benchmark": bundle.get('benchmark', []),
        "feature_importance": bundle.get('feature_importance', [])[:10]
    }), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"[Project FORESIGHT] ASGI Server starting via Uvicorn on http://0.0.0.0:{port}")
    try:
        import uvicorn
        uvicorn.run("app:asgi_app", host="0.0.0.0", port=port, reload=False)
    except Exception as e:
        print(f"Uvicorn startup error, falling back to WSGI: {e}")
        app.run(host='0.0.0.0', port=port, debug=False)
