import os
import pandas as pd
import numpy as np
from datetime import timedelta
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, mean_absolute_error

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DATA_PATH = os.path.join(BASE_DIR, "data", "processed", "processed_india.csv")

def prepare_city_features(city_name: str, data_path: str = PROCESSED_DATA_PATH):
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Processed data file not found at: {data_path}")

    df = pd.read_csv(data_path)
    df['Date'] = pd.to_datetime(df['Date'])
    
    # Filter for city and sort chronologically
    city_df = df[df['City'] == city_name].sort_values('Date').reset_index(drop=True)
    if city_df.empty:
        raise ValueError(f"No records found for city: {city_name}")

    # 1. Autoregressive Lags for AQI
    for lag in [1, 2, 3]:
        city_df[f'aqi_lag_{lag}'] = city_df['AQI'].shift(lag)

    # 2. Multi-Pollutant Covariate Lags (PM2.5, PM10, NO2 if present)
    for col in ['PM2.5', 'PM10', 'NO2']:
        if col in city_df.columns:
            for lag in [1, 2]:
                city_df[f'{col.lower()}_lag_{lag}'] = city_df[col].shift(lag)

    # 3. Rolling Momentum & Volatility
    city_df['aqi_rolling_mean_3'] = city_df['AQI'].shift(1).rolling(window=3, min_periods=1).mean()
    city_df['aqi_rolling_mean_7'] = city_df['AQI'].shift(1).rolling(window=7, min_periods=1).mean()
    city_df['aqi_rolling_std_7'] = city_df['AQI'].shift(1).rolling(window=7, min_periods=1).std().fillna(0)
    city_df['aqi_trend_delta_3'] = city_df['aqi_lag_1'] - city_df['aqi_lag_3']

    # 4. Cyclical Calendar Seasonality
    city_df['month'] = city_df['Date'].dt.month
    city_df['dayofweek'] = city_df['Date'].dt.dayofweek
    city_df['is_weekend'] = (city_df['dayofweek'] >= 5).astype(int)
    
    city_df['sin_month'] = np.sin(2 * np.pi * city_df['month'] / 12)
    city_df['cos_month'] = np.cos(2 * np.pi * city_df['month'] / 12)
    city_df['sin_dow'] = np.sin(2 * np.pi * city_df['dayofweek'] / 7)
    city_df['cos_dow'] = np.cos(2 * np.pi * city_df['dayofweek'] / 7)

    # Drop intermediate and target-correlated raw columns from feature space
    drop_cols = ['City', 'Date', 'AQI', 'AQI_Bucket', 'month', 'dayofweek']
    feature_cols = [c for c in city_df.columns if c not in drop_cols]

    # Drop warmup rows where shifts created NaNs
    clean_df = city_df.dropna(subset=feature_cols + ['AQI']).reset_index(drop=True)
    return clean_df, feature_cols

def train_and_forecast_city(city_name: str, forecast_days: int = 7):
    df, feature_cols = prepare_city_features(city_name)

    # Chronological 80/20 train/test split (no future data leakage)
    split_idx = int(len(df) * 0.8)
    train_data = df.iloc[:split_idx]
    test_data = df.iloc[split_idx:]

    X_train, y_train = train_data[feature_cols], train_data['AQI']
    X_test, y_test = test_data[feature_cols], test_data['AQI']

    model = RandomForestRegressor(
        n_estimators=150,
        max_depth=12,
        min_samples_split=4,
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train, y_train)

    # Evaluate accuracy on unseen test period
    preds_test = model.predict(X_test)
    metrics = {
        "r2_score": round(float(r2_score(y_test, preds_test)), 3),
        "mae": round(float(mean_absolute_error(y_test, preds_test)), 2)
    }

    # 7-Day Recursive Multi-Step Forecast
    last_known_row = df.iloc[-1].copy()
    current_aqi_history = list(df['AQI'].values)
    forecast_results = []
    current_date = last_known_row['Date']

    for step in range(1, forecast_days + 1):
        step_date = current_date + timedelta(days=step)
        
        # Build feature vector for step
        step_feats = {
            'aqi_lag_1': current_aqi_history[-1],
            'aqi_lag_2': current_aqi_history[-2] if len(current_aqi_history) >= 2 else current_aqi_history[-1],
            'aqi_lag_3': current_aqi_history[-3] if len(current_aqi_history) >= 3 else current_aqi_history[-1],
            'aqi_rolling_mean_3': np.mean(current_aqi_history[-3:]),
            'aqi_rolling_mean_7': np.mean(current_aqi_history[-7:]),
            'aqi_rolling_std_7': np.std(current_aqi_history[-7:]) if len(current_aqi_history) >= 7 else 0.0,
            'aqi_trend_delta_3': current_aqi_history[-1] - (current_aqi_history[-3] if len(current_aqi_history) >= 3 else current_aqi_history[-1]),
            'is_weekend': int(step_date.weekday() >= 5),
            'sin_month': np.sin(2 * np.pi * step_date.month / 12),
            'cos_month': np.cos(2 * np.pi * step_date.month / 12),
            'sin_dow': np.sin(2 * np.pi * step_date.weekday() / 7),
            'cos_dow': np.cos(2 * np.pi * step_date.weekday() / 7)
        }

        # Match missing pollutant lags with last known sensor levels
        for col in ['pm2.5_lag_1', 'pm2.5_lag_2', 'pm10_lag_1', 'pm10_lag_2', 'no2_lag_1', 'no2_lag_2']:
            if col in feature_cols:
                step_feats[col] = last_known_row.get(col, 0.0)

        step_df = pd.DataFrame([step_feats])[feature_cols]
        predicted_val = round(float(model.predict(step_df)[0]))

        forecast_results.append({
            "Date": step_date.strftime('%a, %d %b'),
            "Predicted_AQI": int(predicted_val)
        })
        current_aqi_history.append(predicted_val)

    return pd.DataFrame(forecast_results), metrics

if __name__ == "__main__":
    test_city = "Mumbai"
    print(f"Testing enhanced model training on {test_city} data...")
    forecast_df, metrics = train_and_forecast_city(test_city)
    
    print("\n--- UPDATED MODEL ACCURACY METRICS ---")
    print(f"R² Score (Accuracy): {metrics['r2_score'] * 100:.1f}%")
    print(f"Mean Absolute Error: ±{metrics['mae']} AQI points")
    print("\n--- 7-DAY PREDICTED AQI ---")
    print(forecast_df.to_string(index=False))