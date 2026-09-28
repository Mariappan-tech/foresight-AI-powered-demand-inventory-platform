"""
Project FORESIGHT: AI-Powered Demand & Inventory Intelligence Platform
Advanced Hyperparameter Tuning & Model Optimization
"""

import os
import pandas as pd
import numpy as np
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, VotingRegressor
from xgboost import XGBRegressor
import lightgbm as lgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib

def calculate_wape(actual, predicted):
    """Weighted Absolute Percentage Error (Supply Chain Industry Standard)"""
    return (np.sum(np.abs(actual - predicted)) / np.sum(actual)) * 100

def run_hyperparameter_tuning():
    processed_dir = os.path.join('dataset', 'processed_data')
    models_dir = os.path.join('models')
    os.makedirs(models_dir, exist_ok=True)

    print("=" * 65)
    print("Project FORESIGHT: Hyperparameter Tuning & Model Optimization")
    print("=" * 65)

    train_df = pd.read_csv(os.path.join(processed_dir, 'train_features.csv'))
    val_df = pd.read_csv(os.path.join(processed_dir, 'val_features.csv'))
    test_df = pd.read_csv(os.path.join(processed_dir, 'test_features.csv'))

    feature_cols = [
        'day_of_week', 'month', 'day_of_month', 'is_weekend', 'is_holiday', 'promotion_active',
        'dow_sin', 'dow_cos', 'month_sin', 'month_cos',
        'lead_time_days', 'unit_cost', 'selling_price', 'margin_per_unit', 'margin_pct',
        'sales_lag_1', 'sales_lag_2', 'sales_lag_3', 'sales_lag_7', 'sales_lag_14',
        'rolling_mean_7', 'rolling_std_7', 'rolling_min_7', 'rolling_max_7',
        'rolling_mean_14', 'rolling_std_14', 'rolling_min_14', 'rolling_max_14',
        'rolling_mean_21', 'rolling_std_21', 'rolling_min_21', 'rolling_max_21'
    ]

    for df in [train_df, val_df, test_df]:
        for sku in ['SKU_CLEAR', 'SKU_HEALTHY', 'SKU_REORDER', 'SKU_WATCH']:
            df[f'is_{sku}'] = (df['sku_id'] == sku).astype(int)

    sku_dummies = [f'is_{sku}' for sku in ['SKU_CLEAR', 'SKU_HEALTHY', 'SKU_REORDER', 'SKU_WATCH']]
    all_features = feature_cols + sku_dummies
    target_col = 'sales_units'

    # Combine train + val for optimal training size (preserving chronological sequence)
    train_val_df = pd.concat([train_df, val_df], ignore_index=True)

    X_train_val = train_val_df[all_features]
    y_train_val = train_val_df[target_col]

    X_test = test_df[all_features]
    y_test = test_df[target_col]

    print(f"Features: {len(all_features)} | Training (Train+Val) Samples: {len(X_train_val)} | Test Samples: {len(X_test)}")

    # Time-series cross-validation to prevent temporal leakage during CV
    tscv = TimeSeriesSplit(n_splits=4)

    # 1. Tune Random Forest
    print("\nTuning Random Forest Regressor...")
    param_grid_rf = {
        'n_estimators': [100, 200],
        'max_depth': [6, 10, None],
        'min_samples_split': [2, 5],
        'min_samples_leaf': [1, 2]
    }
    grid_rf = GridSearchCV(
        RandomForestRegressor(random_state=42),
        param_grid_rf,
        cv=tscv,
        scoring='neg_mean_absolute_error',
        n_jobs=1
    )
    grid_rf.fit(X_train_val, y_train_val)
    best_rf = grid_rf.best_estimator_
    print(f"Best RF Params: {grid_rf.best_params_}")

    # 2. Tune XGBoost
    print("\nTuning XGBoost Regressor...")
    param_grid_xgb = {
        'n_estimators': [80, 120, 160],
        'max_depth': [3, 4, 5],
        'learning_rate': [0.03, 0.06, 0.1],
        'subsample': [0.8, 1.0],
        'colsample_bytree': [0.8, 1.0]
    }
    grid_xgb = GridSearchCV(
        XGBRegressor(random_state=42),
        param_grid_xgb,
        cv=tscv,
        scoring='neg_mean_absolute_error',
        n_jobs=1
    )
    grid_xgb.fit(X_train_val, y_train_val)
    best_xgb = grid_xgb.best_estimator_
    print(f"Best XGB Params: {grid_xgb.best_params_}")

    # 3. Tune LightGBM
    print("\nTuning LightGBM Regressor...")
    param_grid_lgb = {
        'n_estimators': [80, 120, 160],
        'max_depth': [3, 5, 8],
        'learning_rate': [0.03, 0.06, 0.1],
        'num_leaves': [15, 31]
    }
    grid_lgb = GridSearchCV(
        lgb.LGBMRegressor(random_state=42, verbose=-1),
        param_grid_lgb,
        cv=tscv,
        scoring='neg_mean_absolute_error',
        n_jobs=1
    )
    grid_lgb.fit(X_train_val, y_train_val)
    best_lgb = grid_lgb.best_estimator_
    print(f"Best LightGBM Params: {grid_lgb.best_params_}")

    # 4. Ensemble (Voting Regressor)
    print("\nBuilding Optimized Voting Ensemble...")
    ensemble = VotingRegressor(
        estimators=[
            ('rf', best_rf),
            ('xgb', best_xgb),
            ('lgb', best_lgb)
        ],
        weights=[0.35, 0.40, 0.25]
    )
    ensemble.fit(X_train_val, y_train_val)

    # Candidate Models Dictionary
    candidate_models = {
        'Tuned Random Forest': best_rf,
        'Tuned XGBoost': best_xgb,
        'Tuned LightGBM': best_lgb,
        'Optimized Ensemble (RF+XGB+LGB)': ensemble
    }

    results = []
    champion_model = None
    champion_name = ""
    champion_wape = float('inf')

    for name, model in candidate_models.items():
        preds = model.predict(X_test)
        mae = mean_absolute_error(y_test, preds)
        rmse = np.sqrt(mean_squared_error(y_test, preds))
        wape = calculate_wape(y_test.values, preds)
        r2 = r2_score(y_test, preds)

        results.append({
            'Model': name,
            'Test MAE': round(mae, 3),
            'Test RMSE': round(rmse, 3),
            'Test WAPE (%)': round(wape, 2),
            'Test R2': round(r2, 3)
        })

        if wape < champion_wape:
            champion_wape = wape
            champion_model = model
            champion_name = name

    results_df = pd.DataFrame(results)
    print("\n" + "=" * 65)
    print("HYPERPARAMETER TUNING BENCHMARK RESULTS (OUT-OF-SAMPLE TEST):")
    print("=" * 65)
    print(results_df.to_string(index=False))

    # Feature Importance analysis (using XGBoost & Random Forest)
    importances = best_xgb.feature_importances_
    feat_imp = pd.DataFrame({'feature': all_features, 'importance': importances}).sort_values('importance', ascending=False)
    print("\nTop 10 Most Influential Demand Predictors:")
    for idx, row in feat_imp.head(10).iterrows():
        print(f"  - {row['feature']:20s}: {row['importance']*100:.2f}%")

    # Save Champion Model
    model_path = os.path.join(models_dir, 'best_demand_forecaster.joblib')
    joblib.dump({
        'model': champion_model,
        'model_name': champion_name,
        'features': all_features,
        'benchmark': results_df.to_dict(orient='records'),
        'feature_importance': feat_imp.to_dict(orient='records')
    }, model_path)
    print(f"\nSaved Champion Model -> {model_path} [{champion_name}] (Test WAPE: {champion_wape:.2f}%)")

    # Update Test predictions sample
    test_results_df = test_df[['date', 'sku_id', 'sales_units']].copy()
    test_results_df['predicted_sales'] = np.round(champion_model.predict(X_test), 1)
    test_results_df['error'] = test_results_df['sales_units'] - test_results_df['predicted_sales']
    test_results_path = os.path.join(processed_dir, 'test_predictions_sample.csv')
    test_results_df.to_csv(test_results_path, index=False)
    print(f"Saved updated test predictions -> {test_results_path}")

    # SKU level metrics for champion
    print("\nChampion Model Performance by SKU:")
    for sku, group in test_results_df.groupby('sku_id'):
        sku_mae = mean_absolute_error(group['sales_units'], group['predicted_sales'])
        sku_wape = np.sum(np.abs(group['sales_units'] - group['predicted_sales'])) / np.sum(group['sales_units']) * 100
        print(f"  SKU: {sku:12s} | Actual Mean: {group['sales_units'].mean():.1f} | Pred Mean: {group['predicted_sales'].mean():.1f} | MAE: {sku_mae:.2f} | WAPE: {sku_wape:.2f}%")

    print("=" * 65)
    print("Hyperparameter tuning successfully finished!")
    print("=" * 65)

if __name__ == '__main__':
    run_hyperparameter_tuning()
