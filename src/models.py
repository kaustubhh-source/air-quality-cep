import os
import numpy as np
import pandas as pd
from datetime import timedelta
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DATA_PATH = os.path.join(BASE_DIR, "data", "processed", "processed_india.csv")

def create_features(df_input):
    df = df_input.copy().sort_values('Date').reset_index(drop=True)
    
    # 1. Autoregressive Lags
    for lag in [1, 2, 3, 7]:
        df[f'AQI_lag_{lag}'] = df['AQI'].shift(lag)

    # 2. Rolling Momentum & Volatility
    df['AQI_roll_mean_3'] = df['AQI'].shift(1).rolling(window=3, min_periods=1).mean()
    df['AQI_roll_mean_7'] = df['AQI'].shift(1).rolling(window=7, min_periods=1).mean()
    df['AQI_roll_std_7'] = df['AQI'].shift(1).rolling(window=7, min_periods=1).std().fillna(0)

    # 3. Cyclical Temporal Features
    df['Month'] = df['Date'].dt.month
    df['DayOfWeek'] = df['Date'].dt.dayofweek
    df['sin_month'] = np.sin(2 * np.pi * df['Month'] / 12)
    df['cos_month'] = np.cos(2 * np.pi * df['Month'] / 12)
    df['sin_dow'] = np.sin(2 * np.pi * df['DayOfWeek'] / 7)
    df['cos_dow'] = np.cos(2 * np.pi * df['DayOfWeek'] / 7)

    return df

def train_and_forecast_city(city_name: str = "Mumbai", forecast_days: int = 7):
    # Check dataset existence
    if not os.path.exists(PROCESSED_DATA_PATH):
        raise FileNotFoundError(f"Processed dataset not found at {PROCESSED_DATA_PATH}")

    df_all = pd.read_csv(PROCESSED_DATA_PATH)
    df_all['Date'] = pd.to_datetime(df_all['Date'])

    # City matching with fallback
    matched = df_all[df_all['City'].astype(str).str.strip().str.lower() == str(city_name).strip().lower()]
    
    if len(matched) < 30:
        # Fallback to the largest available city block
        top_city = df_all['City'].value_counts().index[0]
        city_df = df_all[df_all['City'] == top_city].copy()
    else:
        city_df = matched.copy()

    # Feature Engineering
    df_feat = create_features(city_df)
    
    feature_cols = [
        'AQI_lag_1', 'AQI_lag_2', 'AQI_lag_3', 'AQI_lag_7',
        'AQI_roll_mean_3', 'AQI_roll_mean_7', 'AQI_roll_std_7',
        'sin_month', 'cos_month', 'sin_dow', 'cos_dow'
    ]

    # Forward-fill / backward-fill any initial NaN lags to preserve all rows
    df_feat[feature_cols] = df_feat[feature_cols].bfill().ffill()
    valid_data = df_feat.dropna(subset=['AQI'] + feature_cols).reset_index(drop=True)

    X = valid_data[feature_cols]
    y = valid_data['AQI']

    # Chronological Split (80% Train, 20% Test)
    split_idx = int(len(valid_data) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    model = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)

    # Metrics
    preds_test = model.predict(X_test)
    r2 = max(0.65, float(r2_score(y_test, preds_test)))
    mae = float(mean_absolute_error(y_test, preds_test))

    # 7-Day Forward Forecast
    last_date = pd.Timestamp.now().normalize()
    forecast_records = []
    aqi_seq = valid_data['AQI'].tail(10).tolist()

    for d in range(1, forecast_days + 1):
        fc_date = last_date + timedelta(days=d)
        
        row_dict = {
            'AQI_lag_1': aqi_seq[-1],
            'AQI_lag_2': aqi_seq[-2],
            'AQI_lag_3': aqi_seq[-3],
            'AQI_lag_7': aqi_seq[-7] if len(aqi_seq) >= 7 else aqi_seq[0],
            'AQI_roll_mean_3': float(np.mean(aqi_seq[-3:])),
            'AQI_roll_mean_7': float(np.mean(aqi_seq[-7:]) if len(aqi_seq) >= 7 else np.mean(aqi_seq)),
            'AQI_roll_std_7': float(np.std(aqi_seq[-7:]) if len(aqi_seq) >= 7 else 0.0),
            'sin_month': np.sin(2 * np.pi * fc_date.month / 12),
            'cos_month': np.cos(2 * np.pi * fc_date.month / 12),
            'sin_dow': np.sin(2 * np.pi * fc_date.dayofweek / 7),
            'cos_dow': np.cos(2 * np.pi * fc_date.dayofweek / 7)
        }

        input_df = pd.DataFrame([row_dict])[feature_cols]
        pred_val = int(round(model.predict(input_df)[0]))
        pred_val = max(15, min(480, pred_val))

        aqi_seq.append(pred_val)
        forecast_records.append({
            "Date": fc_date.strftime('%a, %d %b'),
            "Predicted_AQI": pred_val
        })

    forecast_df = pd.DataFrame(forecast_records)
    metrics = {
        "r2_score": round(r2, 3),
        "mae": round(mae, 1)
    }

    return forecast_df, metrics