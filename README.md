# 🌿 PRAVAAH | Indian Air Quality & Civic Intelligence Platform

> **Academic Alignment:** University of Mumbai Under-Graduate Community Engagement Project (CEP) under NEP 2020 (*"Use digital skills to implement socially impactful tech projects"*).  
> **Repository:** [`kaustubhh-source/air-quality-cep`](https://github.com/kaustubhh-source/air-quality-cep)  
> **Deployment:** Streamlit Community Cloud  

---

## 🎯 Executive Overview

**PRAVAAH** is a multi-dimensional environmental data science and civic intelligence platform built to tackle hyper-local air pollution across India. By bridging physical CPCB CAAQMS ground telemetry with auto-regressive machine learning models, PRAVAAH provides real-time atmospheric diagnostics, 7-day forward AQI forecasts, and actionable public health advisories tailored to vulnerable populations.

---

## 🏗️ System Architecture

```text
air-quality-cep/
├── app.py                  # Main 5-tab Streamlit Application UI + Universal Location Search
├── src/
│   ├── __init__.py         # Package initializer
│   ├── db.py               # SQLite database access layer (symptoms logging & broadcasts)
│   ├── live_feed.py        # OpenAQ v3 ground ingestion, Open-Meteo fallback, Nominatim geocoding
│   ├── models.py           # RandomForestRegressor multi-step 7-day AQI forecast pipeline
│   └── etl.py              # Data cleaning & CPCB sub-index calculation script
├── data/
│   ├── raw/                # Raw CPCB city day telemetry
│   └── processed/          # Cleaned historical dataset (processed_india.csv)
├── civic_records.db        # SQLite database for symptoms & admin emergency announcements
├── requirements.txt        # Cloud python dependencies
├── .env                    # Environment configuration (OPENAQ_API_KEY)
└── .gitignore              # Git exclusions (*.db, .env, __pycache__)
```

---

## 🚀 Key Modules & Dashboard Features

### 📍 Tab 1: Live Pulse & Clinical Advisory
- **CPCB NAQI Standard**: Displays live composite AQI, dominant pollutant, and 6 key pollutant metrics: **PM2.5, PM10, NO₂, SO₂, CO, O₃**.
- **Visual CPCB Scale Bar**: Multi-color gradient indicator positioning current AQI within official CPCB bands (Good, Satisfactory, Moderate, Poor, Very Poor, Severe).
- **Vulnerable Group Defense**: Tailored action cards for school children, elderly/asthma patients, and outdoor transit commuters.

### 📈 Tab 2: 7-Day ML Forecast
- **Auto-Regressive Random Forest**: Multi-step recursive forecasting trained on historical CPCB telemetry with autoregressive lags, rolling momentum, and cyclical calendar features.
- **Model Reliability Badges**: Displays live R² score and Mean Absolute Error (MAE in AQI units).
- **Interactive City Selector**: Instant forecast switching across major Indian metropolitan hubs (Mumbai, Delhi, Bengaluru, Kolkata, Chennai, Hyderabad, Pune, etc.).

### 🗺️ Pan-India Live Map & Hotspots
- **Dual Mapbox/Map Lib Compatibility**: Dynamic Plotly fallback (`scatter_map` vs `scatter_mapbox`) compatible across Plotly v5 and Plotly v6.
- **Hotspot Leaderboard & Station Filter**: Text filter for searching stations or cities alongside cleanest vs. highest smog indicators.

### 📢 Civic Intelligence & Health Hub (NEP 2020 CEP Alignment)
- **Driver Occupational Exposure Findings**: Empirical field evidence highlighting PM exposure in open auto-rickshaws and traffic intersections.
- **Anonymous Health Logger**: SQLite-backed symptom logging for civic epidemiological tracking.
- **1-Click WhatsApp Advisory**: Broadcast real-time localized warnings directly to community WhatsApp groups.

### 🛡️ Admin Command Center
- **Security PIN Gateway**: PIN `1234` protected admin console.
- **Emergency Civic Broadcasts**: Issue or revoke live emergency banner directives visible across all user sessions.
- **Symptom Registry & CSV Export**: Detailed symptom log table and CSV download button.

---

## 🛠️ Local Installation & Setup

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/kaustubhh-source/air-quality-cep.git
   cd air-quality-cep
   ```

2. **Set Up Python Virtual Environment**:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install Pinned Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables (Optional)**:
   Create a `.env` file in the root directory:
   ```env
   OPENAQ_API_KEY=your_openaq_api_key_here
   ```

5. **Launch Application**:
   ```bash
   streamlit run app.py
   ```

---

## 📜 Academic Attribution

Developed as part of the **University of Mumbai Under-Graduate Community Engagement Project (CEP)** under **NEP 2020**.

- **Focus Area**: Digital Innovation for Social & Environmental Impact.
- **License**: MIT License.
