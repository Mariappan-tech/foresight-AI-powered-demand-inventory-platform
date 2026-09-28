"""
Project FORESIGHT: AI-Powered Demand & Inventory Intelligence Platform
Data Preprocessing & Feature Engineering Pipeline
"""

import os
import pandas as pd
import numpy as np

def run_pipeline():
    raw_dir = os.path.join('dataset', 'raw_data')
    processed_dir = os.path.join('dataset', 'processed_data')
    os.makedirs(processed_dir, exist_ok=True)

    print("=" * 60)
    print("Project FORESIGHT: Starting Data Preprocessing Pipeline...")
    print("=" * 60)

    # 1. Load Raw Datasets
    calendar_df = pd.read_csv(os.path.join(raw_dir, 'calendar.csv'))
    inventory_df = pd.read_csv(os.path.join(raw_dir, 'inventory_snapshots.csv'))
    sales_df = pd.read_csv(os.path.join(raw_dir, 'sales_daily.csv'))
    sku_df = pd.read_csv(os.path.join(raw_dir, 'sku_master.csv'))

    print(f"Loaded calendar.csv: {calendar_df.shape}")
    print(f"Loaded inventory_snapshots.csv: {inventory_df.shape}")
    print(f"Loaded sales_daily.csv: {sales_df.shape}")
    print(f"Loaded sku_master.csv: {sku_df.shape}")

    # 2. Date parsing & Sorting
    for df in [calendar_df, inventory_df, sales_df]:
        df['date'] = pd.to_datetime(df['date'])

    # 3. Merge Datasets
    # Base merge: sales + calendar on date
    df_merged = pd.merge(sales_df, calendar_df, on='date', how='left')

    # Merge sku_master on sku_id
    df_merged = pd.merge(df_merged, sku_df, on='sku_id', how='left')

    # Merge inventory_snapshots on [date, sku_id]
    df_merged = pd.merge(df_merged, inventory_df, on=['date', 'sku_id'], how='left')

    # Sort chronologically by SKU and Date
    df_merged = df_merged.sort_values(by=['sku_id', 'date']).reset_index(drop=True)

    # 4. Temporal & Calendar Feature Engineering
    df_merged['day_of_month'] = df_merged['date'].dt.day
    df_merged['day_of_year'] = df_merged['date'].dt.dayofyear
    df_merged['is_weekend'] = df_merged['day_of_week'].apply(lambda x: 1 if x in [5, 6] else 0)

    # Cyclical encoding for day_of_week (0-6) and month (1-12)
    df_merged['dow_sin'] = np.sin(2 * np.pi * df_merged['day_of_week'] / 7.0)
    df_merged['dow_cos'] = np.cos(2 * np.pi * df_merged['day_of_week'] / 7.0)
    df_merged['month_sin'] = np.sin(2 * np.pi * df_merged['month'] / 12.0)
    df_merged['month_cos'] = np.cos(2 * np.pi * df_merged['month'] / 12.0)

    # 5. Financial & Revenue Metrics
    df_merged['margin_per_unit'] = df_merged['selling_price'] - df_merged['unit_cost']
    df_merged['margin_pct'] = (df_merged['margin_per_unit'] / df_merged['selling_price']) * 100
    df_merged['daily_revenue'] = df_merged['sales_units'] * df_merged['selling_price']
    df_merged['daily_cogs'] = df_merged['sales_units'] * df_merged['unit_cost']
    df_merged['daily_gross_profit'] = df_merged['daily_revenue'] - df_merged['daily_cogs']

    # 6. Time-Series Lag & Rolling Window Features (Per SKU)
    # Using shift() to prevent data leakage (only historical values known at time t-1 are used)
    lags = [1, 2, 3, 7, 14]
    for lag in lags:
        df_merged[f'sales_lag_{lag}'] = df_merged.groupby('sku_id')['sales_units'].shift(lag)

    # Rolling window statistics on shifted sales (avoiding lookahead bias)
    for window in [7, 14, 21]:
        shifted = df_merged.groupby('sku_id')['sales_units'].shift(1)
        df_merged[f'rolling_mean_{window}'] = shifted.groupby(df_merged['sku_id']).rolling(window).mean().reset_index(drop=True)
        df_merged[f'rolling_std_{window}'] = shifted.groupby(df_merged['sku_id']).rolling(window).std().reset_index(drop=True)
        df_merged[f'rolling_min_{window}'] = shifted.groupby(df_merged['sku_id']).rolling(window).min().reset_index(drop=True)
        df_merged[f'rolling_max_{window}'] = shifted.groupby(df_merged['sku_id']).rolling(window).max().reset_index(drop=True)

    # 7. SKU Inventory Intelligence Metrics & Health Classification
    sku_stats = df_merged.groupby('sku_id').agg(
        avg_daily_sales=('sales_units', 'mean'),
        std_daily_sales=('sales_units', 'std'),
        lead_time_days=('lead_time_days', 'first'),
        unit_cost=('unit_cost', 'first'),
        selling_price=('selling_price', 'first'),
        current_stock_on_hand=('stock_on_hand', 'last'),
        current_stock_on_order=('stock_on_order', 'last'),
        category=('category', 'first')
    ).reset_index()

    # Safety Stock formula (95% service level -> Z = 1.65)
    # Safety Stock = Z * std_demand * sqrt(lead_time)
    z_score = 1.65
    sku_stats['safety_stock'] = np.ceil(z_score * sku_stats['std_daily_sales'] * np.sqrt(sku_stats['lead_time_days'])).astype(int)
    sku_stats['lead_time_demand'] = np.ceil(sku_stats['avg_daily_sales'] * sku_stats['lead_time_days']).astype(int)
    sku_stats['reorder_point'] = sku_stats['lead_time_demand'] + sku_stats['safety_stock']
    sku_stats['days_of_supply'] = np.round(sku_stats['current_stock_on_hand'] / sku_stats['avg_daily_sales'], 1)

    # Inventory classification logic
    def classify_inventory(row):
        total_pipeline = row['current_stock_on_hand'] + row['current_stock_on_order']
        if row['current_stock_on_hand'] <= row['reorder_point']:
            if row['current_stock_on_order'] == 0:
                return 'STOCKOUT_RISK', 'CRITICAL: Place purchase order immediately! Stock below Reorder Point.'
            else:
                return 'EXPEDITE_PO', 'WARNING: Stock low, replenishment order pending in transit.'
        elif row['days_of_supply'] > 60:
            return 'OVERSTOCK_RISK', 'EXCESS: Run clearance promotion or discount campaign to free working capital.'
        elif row['std_daily_sales'] / row['avg_daily_sales'] > 0.5:
            return 'VOLATILE_WATCH', 'MONITOR: High demand volatility. Maintain dynamic safety stock buffer.'
        else:
            return 'HEALTHY', 'OPTIMAL: Inventory balanced. Regular replenishment schedule.'

    classifications = sku_stats.apply(classify_inventory, axis=1)
    sku_stats['inventory_status'] = [c[0] for c in classifications]
    sku_stats['action_recommendation'] = [c[1] for c in classifications]

    # Save Inventory Intelligence Summary
    sku_summary_path = os.path.join(processed_dir, 'inventory_intelligence_summary.csv')
    sku_stats.to_csv(sku_summary_path, index=False)
    print(f"Saved inventory intelligence summary -> {sku_summary_path}")

    # Merge ROP & Safety stock back into main dataset for tracking
    df_merged = pd.merge(df_merged, sku_stats[['sku_id', 'safety_stock', 'reorder_point', 'inventory_status']], on='sku_id', how='left')

    # 8. Handling NaNs from warm-up lags (drop first 14 days per SKU where 14-day lags are NaN)
    initial_len = len(df_merged)
    clean_df = df_merged.dropna().reset_index(drop=True)
    print(f"Dropped {initial_len - len(clean_df)} warm-up rows (first 14 days) with null lag features.")
    print(f"Clean ML-ready dataset shape: {clean_df.shape}")

    # Save Full Processed Features
    full_path = os.path.join(processed_dir, 'foresight_demand_features.csv')
    clean_df.to_csv(full_path, index=False)
    print(f"Saved full ML dataset -> {full_path}")

    # 9. Time-Series Train / Validation / Test Split (Prevent lookahead bias)
    unique_dates = sorted(clean_df['date'].unique())
    n_dates = len(unique_dates)
    train_end_idx = int(n_dates * 0.70)
    val_end_idx = int(n_dates * 0.85)

    train_dates = unique_dates[:train_end_idx]
    val_dates = unique_dates[train_end_idx:val_end_idx]
    test_dates = unique_dates[val_end_idx:]

    train_df = clean_df[clean_df['date'].isin(train_dates)].reset_index(drop=True)
    val_df = clean_df[clean_df['date'].isin(val_dates)].reset_index(drop=True)
    test_df = clean_df[clean_df['date'].isin(test_dates)].reset_index(drop=True)

    print(f"Train set: {len(train_df)} rows ({train_dates[0].strftime('%Y-%m-%d')} to {train_dates[-1].strftime('%Y-%m-%d')})")
    print(f"Validation set: {len(val_df)} rows ({val_dates[0].strftime('%Y-%m-%d')} to {val_dates[-1].strftime('%Y-%m-%d')})")
    print(f"Test set: {len(test_df)} rows ({test_dates[0].strftime('%Y-%m-%d')} to {test_dates[-1].strftime('%Y-%m-%d')})")

    train_df.to_csv(os.path.join(processed_dir, 'train_features.csv'), index=False)
    val_df.to_csv(os.path.join(processed_dir, 'val_features.csv'), index=False)
    test_df.to_csv(os.path.join(processed_dir, 'test_features.csv'), index=False)

    print("=" * 60)
    print("Preprocessing completed successfully!")
    print("=" * 60)

if __name__ == '__main__':
    run_pipeline()
