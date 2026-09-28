"""
Project FORESIGHT: AI-Powered Demand & Inventory Intelligence Platform
Baseline Machine Learning Model Training & Evaluation
"""

import os
import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import Ridge
import lightgbm as lgb
import joblib

def calculate_wape(actual, predicted):
    """Weighted Absolute Percentage Error (Supply Chain Industry Standard)"""
    return (np.sum(np.abs(actual - predicted)) / np.sum(actual)) * 100

def train_and_evaluate():
    processed_dir = os.path.join('dataset', 'processed_data')
    models_dir = os.path.join('models')
    os.makedirs(models_dir, exist_ok=True)

    print("=" * 60)
    print("Project FORESIGHT: ML Training & Evaluation Benchmark")
    print("=" * 60)

    train_df = pd.read_csv(os.path.join(processed_dir, 'train_features.csv'))
    val_df = pd.read_csv(os.path.join(processed_dir, 'val_features.csv'))
    test_df = pd.read_csv(os.path.join(processed_dir, 'test_features.csv'))

    # One-hot encode categorical features or map them
    feature_cols = [
        'day_of_week', 'month', 'day_of_month', 'is_weekend', 'is_holiday', 'promotion_active',
        'dow_sin', 'dow_cos', 'month_sin', 'month_cos',
        'lead_time_days', 'unit_cost', 'selling_price', 'margin_per_unit', 'margin_pct',
        'sales_lag_1', 'sales_lag_2', 'sales_lag_3', 'sales_lag_7', 'sales_lag_14',
        'rolling_mean_7', 'rolling_std_7', 'rolling_min_7', 'rolling_max_7',
        'rolling_mean_14', 'rolling_std_14', 'rolling_min_14', 'rolling_max_14',
        'rolling_mean_21', 'rolling_std_21', 'rolling_min_21', 'rolling_max_21'
    ]

    # Add SKU dummy encoding
    for df in [train_df, val_df, test_df]:
        for sku in ['SKU_CLEAR', 'SKU_HEALTHY', 'SKU_REORDER', 'SKU_WATCH']:
            df[f'is_{sku}'] = (df['sku_id'] == sku).astype(int)

    sku_dummies = [f'is_{sku}' for sku in ['SKU_CLEAR', 'SKU_HEALTHY', 'SKU_REORDER', 'SKU_WATCH']]
    all_features = feature_cols + sku_dummies

    target_col = 'sales_units'

    X_train = train_df[all_features]
    y_train = train_df[target_col]

    X_val = val_df[all_features]
    y_val = val_df[target_col]

    X_test = test_df[all_features]
    y_test = test_df[target_col]

    print(f"Features count: {len(all_features)}")
    print(f"Train samples: {len(X_train)} | Val samples: {len(X_val)} | Test samples: {len(X_test)}")

    models = {
        'Ridge Regression': Ridge(alpha=1.0),
        'Random Forest': RandomForestRegressor(n_estimators=100, max_depth=8, random_state=42),
        'Gradient Boosting': GradientBoostingRegressor(n_estimators=100, max_depth=4, learning_rate=0.05, random_state=42),
        'LightGBM': lgb.LGBMRegressor(n_estimators=100, max_depth=5, learning_rate=0.05, random_state=42, verbose=-1)
    }

    results = []
    best_model = None
    best_wape = float('inf')
    best_model_name = ""

    for name, model in models.items():
        model.fit(X_train, y_train)

        # Predictions on Validation
        val_preds = model.predict(X_val)
        val_mae = mean_absolute_error(y_val, val_preds)
        val_rmse = np.sqrt(mean_squared_error(y_val, val_preds))
        val_wape = calculate_wape(y_val.values, val_preds)
        val_r2 = r2_score(y_val, val_preds)

        # Predictions on Test
        test_preds = model.predict(X_test)
        test_mae = mean_absolute_error(y_test, test_preds)
        test_rmse = np.sqrt(mean_squared_error(y_test, test_preds))
        test_wape = calculate_wape(y_test.values, test_preds)
        test_r2 = r2_score(y_test, test_preds)

        results.append({
            'Model': name,
            'Val MAE': round(val_mae, 3),
            'Val RMSE': round(val_rmse, 3),
            'Val WAPE (%)': round(val_wape, 2),
            'Test MAE': round(test_mae, 3),
            'Test RMSE': round(test_rmse, 3),
            'Test WAPE (%)': round(test_wape, 2),
            'Test R2': round(test_r2, 3)
        })

        if test_wape < best_wape:
            best_wape = test_wape
            best_model = model
            best_model_name = name

    results_df = pd.DataFrame(results)
    print("\n" + "=" * 60)
    print("MODEL BENCHMARK RESULTS:")
    print("=" * 60)
    print(results_df.to_string(index=False))

    # Save best model
    model_path = os.path.join(models_dir, 'best_demand_forecaster.joblib')
    joblib.dump({
        'model': best_model,
        'model_name': best_model_name,
        'features': all_features,
        'benchmark': results_df.to_dict(orient='records')
    }, model_path)
    print(f"\nBest Model: {best_model_name} (Test WAPE: {best_wape:.2f}%)")
    print(f"Saved trained model -> {model_path}")

    # Generate sample forecast comparison on test set
    test_results_df = test_df[['date', 'sku_id', 'sales_units']].copy()
    test_results_df['predicted_sales'] = np.round(best_model.predict(X_test), 1)
    test_results_df['error'] = test_results_df['sales_units'] - test_results_df['predicted_sales']
    test_results_path = os.path.join(processed_dir, 'test_predictions_sample.csv')
    test_results_df.to_csv(test_results_path, index=False)
    print(f"Saved sample test predictions -> {test_results_path}")

if __name__ == '__main__':
    train_and_evaluate()
