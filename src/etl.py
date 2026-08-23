import os
import numpy as np
import pandas as pd

# File paths
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
RAW_PATH = os.path.join(BASE_DIR, "data", "raw", "city_day.csv")
PROCESSED_PATH = os.path.join(
    BASE_DIR, "data", "processed", "processed_india.csv"
)


# Linear interpolation formula for AQI sub-index
def calc_sub_index(conc, breakpoints):
  if pd.isna(conc) or conc < 0:
    return np.nan

  # Find matching range
  for b_lo, b_hi, i_lo, i_hi in breakpoints:
    if b_lo <= conc <= b_hi:
      return ((i_hi - i_lo) / (b_hi - b_lo)) * (conc - b_lo) + i_lo

  # Cap at 500 if above max range
  if conc > breakpoints[-1][1]:
    return 500.0

  return np.nan


# CPCB PM2.5 breakpoints
def get_pm25_subindex(conc):
  bp = [
      (0.0, 30.0, 0.0, 50.0),
      (30.1, 60.0, 51.0, 100.0),
      (60.1, 90.0, 101.0, 200.0),
      (90.1, 120.0, 201.0, 300.0),
      (120.1, 250.0, 301.0, 400.0),
      (250.1, 500.0, 401.0, 500.0),
  ]
  return calc_sub_index(conc, bp)


# CPCB PM10 breakpoints
def get_pm10_subindex(conc):
  bp = [
      (0.0, 50.0, 0.0, 50.0),
      (50.1, 100.0, 51.0, 100.0),
      (100.1, 250.0, 101.0, 200.0),
      (250.1, 350.0, 201.0, 300.0),
      (350.1, 430.0, 301.0, 400.0),
      (430.1, 600.0, 401.0, 500.0),
  ]
  return calc_sub_index(conc, bp)


# Overall AQI is the maximum of PM2.5 and PM10 sub-indices
def compute_overall_aqi(row):
  pm25_idx = get_pm25_subindex(row.get("PM2.5", np.nan))
  pm10_idx = get_pm10_subindex(row.get("PM10", np.nan))

  valid_indices = [x for x in [pm25_idx, pm10_idx] if not pd.isna(x)]

  # If both missing, use original AQI
  if not valid_indices:
    return row.get("AQI", np.nan)

  return round(max(valid_indices))


# Main cleaning function
def run_etl():
  # Check if raw file exists
  if not os.path.exists(RAW_PATH):
    print(f"File not found: {RAW_PATH}")
    return

  # Step 1: Load raw data
  print("Loading dataset...")
  df = pd.read_csv(RAW_PATH)

  # Step 2: Format dates and sort
  print("Formatting dates...")
  df["Date"] = pd.to_datetime(df["Date"])
  df = df.sort_values(by=["City", "Date"]).reset_index(drop=True)

  # Step 3: Fill missing values for each city
  print("Filling missing values...")
  pollutants = ["PM2.5", "PM10", "NO2", "CO", "SO2", "O3"]
  for p in pollutants:
    if p in df.columns:
      df[p] = df.groupby("City")[p].transform(lambda grp: grp.ffill().bfill())

  # Step 4: Calculate AQI where missing
  print("Calculating AQI...")
  df["Calculated_AQI"] = df.apply(compute_overall_aqi, axis=1)
  df["AQI"] = df["AQI"].fillna(df["Calculated_AQI"])

  # Step 5: Save cleaned data
  os.makedirs(os.path.dirname(PROCESSED_PATH), exist_ok=True)
  df.to_csv(PROCESSED_PATH, index=False)
  print(f"Saved cleaned file to: {PROCESSED_PATH}")


if __name__ == "__main__":
  run_etl()