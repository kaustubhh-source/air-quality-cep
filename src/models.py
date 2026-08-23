from datetime import timedelta
import os
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

# 1. Resolve project file paths
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
PROCESSED_PATH = os.path.join(
    BASE_DIR, 'data', 'processed', 'processed_india.csv'
)


def build_time_series_features(city_df):
  """Creates time-lagged features from historical AQI data.

  These lag features allow standard ML models to learn temporal dependencies.
  """
  df = city_df.copy()

  # Ensure data is in proper chronological order
  df['Date'] = pd.to_datetime(df['Date'])
  df = df.sort_values('Date').reset_index(drop=True)

  # Feature 1: Previous day's AQI (t-1)
  df['Lag_1'] = df['AQI'].shift(1)

  # Feature 2: AQI from 2 days ago (t-2)
  df['Lag_2'] = df['AQI'].shift(2)

  # Feature 3: AQI from 3 days ago (t-3)
  df['Lag_3'] = df['AQI'].shift(3)

  # Feature 4: Rolling 7-day average of past AQI
  df['Rolling_Mean_7'] = df['AQI'].shift(1).rolling(window=7).mean()

  # Drop the initial rows that contain NaN due to shifting
  df = df.dropna(
      subset=['Lag_1', 'Lag_2', 'Lag_3', 'Rolling_Mean_7', 'AQI']
  ).reset_index(drop=True)
  return df


def train_and_forecast_city(city_name='Mumbai', forecast_days=7):
  """Trains a Random Forest model on historical city data, evaluates its accuracy

  (R2 Score & MAE), and predicts the next 7 days of AQI.
  """
  # Fallback response if dataset is missing
  default_forecast = pd.DataFrame({
      'Date': [
          (pd.Timestamp.now() + timedelta(days=i)).strftime('%a, %d %b')
          for i in range(1, forecast_days + 1)
      ],
      'Predicted_AQI': [150] * forecast_days,
  })
  default_metrics = {'r2_score': 0.0, 'mae': 0.0, 'status': 'Dataset missing'}

  # Check if processed dataset exists
  if not os.path.exists(PROCESSED_PATH):
    print(f'Warning: Processed dataset not found at {PROCESSED_PATH}')
    return default_forecast, default_metrics

  # 1. Load cleaned data and filter for the selected city
  df = pd.read_csv(PROCESSED_PATH)
  city_df = df[df['City'].str.lower() == city_name.lower()].copy()

  # Validate city data availability
  if city_df.empty or len(city_df) < 30:
    print(f'Insufficient records to train model for {city_name}.')
    return default_forecast, default_metrics

  # 2. Engineer features for machine learning
  featured_df = build_time_series_features(city_df)

  # Define feature columns (X) and target variable (y)
  feature_cols = ['Lag_1', 'Lag_2', 'Lag_3', 'Rolling_Mean_7']
  X = featured_df[feature_cols]
  y = featured_df['AQI']

  # 3. Train-Test Split (Chronological split without shuffling)
  X_train, X_test, y_train, y_test = train_test_split(
      X, y, test_size=0.2, shuffle=False
  )

  # 4. Initialize and train Random Forest Regressor
  model = RandomForestRegressor(
      n_estimators=100, max_depth=8, random_state=42
  )
  model.fit(X_train, y_train)

  # 5. Evaluate model performance and accuracy metrics
  test_predictions = model.predict(X_test)
  r2 = round(r2_score(y_test, test_predictions), 3)
  mae = round(mean_absolute_error(y_test, test_predictions), 2)

  metrics = {
      'r2_score': r2,  # Proportion of variance explained (e.g., 0.82 = 82%)
      'mae': (
          mae
      ),  # Average deviation in AQI units (e.g., +/- 12 AQI points)
      'status': 'Model Trained Successfully',
  }

  # 6. Multi-step autoregressive forecasting for the next N days
  future_dates = [
      (pd.Timestamp.now() + timedelta(days=i)).strftime('%a, %d %b')
      for i in range(1, forecast_days + 1)
  ]
  predictions = []

  # Get recent window of history to initialize sequential predictions
  history = list(featured_df['AQI'].tail(7).values)

  for _ in range(forecast_days):
    # Construct input vector using recent history values
    lag1 = history[-1]
    lag2 = history[-2]
    lag3 = history[-3]
    roll7 = np.mean(history[-7:])

    input_data = pd.DataFrame(
        [[lag1, lag2, lag3, roll7]], columns=feature_cols
    )

    # Predict next day's AQI
    pred_val = model.predict(input_data)[0]
    # Bound AQI within standard CPCB scale (0 to 500)
    pred_val = max(10, min(500, round(pred_val)))

    predictions.append(pred_val)
    history.append(pred_val)  # Append prediction to simulate next day's input

  forecast_df = pd.DataFrame(
      {'Date': future_dates, 'Predicted_AQI': predictions}
  )

  return forecast_df, metrics


# Verification test when running this file directly
if __name__ == '__main__':
  print('Testing model training on Mumbai data...')
  forecast, metrics = train_and_forecast_city('Mumbai', forecast_days=7)
  print('\n--- MODEL ACCURACY METRICS ---')
  print(f"R² Score (Accuracy): {metrics['r2_score'] * 100:.1f}%")
  print(f"Mean Absolute Error: ±{metrics['mae']} AQI points")
  print('\n--- 7-DAY PREDICTED AQI ---')
  print(forecast)