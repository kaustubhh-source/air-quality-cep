import os
import sqlite3
import urllib.parse
from datetime import datetime
import pandas as pd
import streamlit as st
import plotly.express as px
from streamlit_geolocation import streamlit_geolocation

# Internal modules
from src.models import train_and_forecast_city
from src.live_feed import (
    fetch_live_air_quality_by_coords,
    geocode_place,
    reverse_geocode
)
from src.live_feed import (
    fetch_live_ground_sensor,
    geocode_place,
    reverse_geocode
)
# 1. Page Configuration (Must be first Streamlit command)
st.set_page_config(
    page_title="Pravaah | Pan-India Air Quality & Civic Intelligence",
    page_icon="🍃",
    layout="wide"
)


# Custom CSS to make tabs sticky at top of page during scroll
st.markdown(
    """
    <style>
    /* Pin the tab bar to the top of the main container */
    div[data-baseweb="tab-list"] {
        position: sticky;
        top: 2.875rem; /* Aligns below the Streamlit top header bar */
        background-color: #0e1117; /* Matches Streamlit dark theme */
        z-index: 999;
        padding: 10px 0;
        border-bottom: 1px solid #262730;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# 2. Paths Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROCESSED_DATA_PATH = os.path.join(BASE_DIR, "data", "processed", "processed_india.csv")
DB_PATH = os.path.join(BASE_DIR, "data", "civic_records.db")

# 3. Database Initialization (Admin Broadcasts & Anonymous Symptoms)
def init_db():
    os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Broadcast alerts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS broadcasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT NOT NULL,
            severity TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Anonymous health symptoms table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS symptoms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location TEXT NOT NULL,
            symptom TEXT NOT NULL,
            severity TEXT NOT NULL,
            logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

# 4. Cached Historical Dataset Loader
@st.cache_data
def load_historical_data():
    if os.path.exists(PROCESSED_DATA_PATH):
        df = pd.read_csv(PROCESSED_DATA_PATH)
        df['Date'] = pd.to_datetime(df['Date'])
        return df
    return pd.DataFrame()

df_historical = load_historical_data()

# ==========================================
# 5. CPCB DOMAIN UTILITIES & COLOR ENGINE
# ==========================================
def get_cpcb_info(aqi: int):
    if aqi <= 50:
        return "Good", "#00B050", "Air quality is satisfactory; air pollution poses little or no risk.", "Safe for all outdoor activities and exercise."
    elif aqi <= 100:
        return "Satisfactory", "#92D050", "Minor breathing discomfort to sensitive people.", "Sensitive groups should limit prolonged intense outdoor exertion."
    elif aqi <= 200:
        return "Moderate", "#FFC000", "Breathing discomfort to people with lungs, asthma, and heart diseases.", "Wear masks in traffic corridors; prefer afternoon outdoor walks."
    elif aqi <= 300:
        return "Poor", "#FF7C80", "Breathing discomfort to most people on prolonged exposure.", "Avoid strenuous outdoor cardio; N95 masks strongly recommended."
    elif aqi <= 400:
        return "Very Poor", "#C00000", "Respiratory illness on prolonged exposure. Significant public warning.", "Remain indoors; keep windows shut and run air purifiers."
    else:
        return "Severe", "#7030A0", "Emergency conditions. Affects healthy people and severely impacts vulnerable groups.", "Strictly avoid going outdoors. Immediate preventive action needed."

# ==========================================
# 6. ACTIVE EMERGENCY BROADCAST TICKER
# ==========================================
def render_active_broadcast():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT message, severity, created_at FROM broadcasts WHERE is_active = 1 ORDER BY id DESC LIMIT 1")
        active_alert = cursor.fetchone()
        conn.close()
        
        if active_alert:
            msg, sev, ts = active_alert
            color_map = {"Advisory": "#FFC000", "Warning": "#FF7C80", "Emergency": "#C00000"}
            badge_color = color_map.get(sev, "#C00000")
            st.markdown(
                f"""
                <div style="background-color: {badge_color}22; border-left: 6px solid {badge_color}; padding: 12px 18px; border-radius: 6px; margin-bottom: 20px;">
                    <span style="font-weight: bold; color: {badge_color}; font-size: 15px;">📢 ACTIVE CIVIC BROADCAST [{sev.upper()}]:</span>
                    <span style="color: #ffffff; font-size: 15px; margin-left: 8px;">{msg}</span>
                    <span style="font-size: 12px; color: #aaaaaa; margin-left: 12px;">(Published: {ts})</span>
                </div>
                """,
                unsafe_allow_html=True
            )
    except Exception as e:
        pass

render_active_broadcast()

# ==========================================
# 7. SIDEBAR NAVIGATION & ADMIN PIN GATE
# ==========================================
st.sidebar.markdown("## 🌿 PRAVAAH")
st.sidebar.caption("Pan-India Air Quality & Civic Intelligence")
st.sidebar.markdown("---")

portal_mode = st.sidebar.radio(
    "Select Interface Mode",
    ["Public Citizen Hub", "Admin Command Center (PIN Required)"],
    index=0
)

# Admin PIN Gatekeeper State
if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

admin_unlocked = False

if portal_mode == "Admin Command Center (PIN Required)":
    st.sidebar.markdown("### 🔐 Security Clearance")
    pin_input = st.sidebar.text_input("Enter 4-Digit Admin PIN", type="password", placeholder="Enter PIN")
    
    if pin_input == "1234":
        st.session_state.admin_authenticated = True
        admin_unlocked = True
        st.sidebar.success("Access Granted: Desk Authorized ✅")
    elif pin_input:
        st.session_state.admin_authenticated = False
        st.sidebar.error("Invalid PIN. Access Restricted ❌")
else:
    st.session_state.admin_authenticated = False

    # ==========================================
# 8. MAIN VIEW ROUTER & PUBLIC CITIZEN HUB
# ==========================================
if portal_mode == "Public Citizen Hub":
    st.markdown("## 🌿 PRAVAAH : Pan-India Air Quality & Civic Intelligence")
    st.caption("Real-Time Hyper-Local Ingestion, Health Advisories & ML-Powered 7-Day Forecasting")
    
    tab1, tab2, tab3 = st.tabs([
        "📍 My City Live Pulse & Health Advisory",
        "🗺️ Pan-India Live Interactive Map",
        "📢 Community Action & Awareness Hub"
    ])
    
    # -----------------------------------------------------------------
    # TAB 1: LIVE PULSE, HEALTH ADVISORIES & 7-DAY FORECAST
    # -----------------------------------------------------------------
    with tab1:
        st.markdown("### 📍 Hyper-Local Live Station Detection")
        
        # Dual-mode inputs: 1-Click GPS or OpenStreetMap Search
        c_gps, c_search = st.columns([1, 2])
        with c_gps:
            st.write("**One-Click Browser GPS**")
            geo_location = streamlit_geolocation()
        
        with c_search:
            st.write("**Or Search Any Indian Locality / Pin Code**")
            search_query = st.text_input(
                "Search query",
                placeholder="e.g., Chembur, Vashi Naka, Connaught Place, Whitefield",
                label_visibility="collapsed"
            )
        
        target_lat, target_lon, target_name = None, None, None
        
        # 1. Priority: 1-Click GPS
        if geo_location and geo_location.get("latitude") and geo_location.get("longitude"):
            target_lat = float(geo_location["latitude"])
            target_lon = float(geo_location["longitude"])
            with st.spinner("Resolving coordinates to exact locality..."):
                target_name = reverse_geocode(target_lat, target_lon)
        
        # 2. Priority: Custom Text Search
        elif search_query:
            with st.spinner(f"Locating '{search_query}' across India..."):
                geo_res = geocode_place(search_query)
            if geo_res:
                target_lat = geo_res["lat"]
                target_lon = geo_res["lon"]
                target_name = geo_res["display_name"]
            else:
                st.warning(f"Could not find coordinates for '{search_query}'. Defaulting to Mumbai.")
        
        # 3. Default Fallback: Chembur, Mumbai
        if not target_lat:
            target_lat, target_lon = 19.0522, 72.8994
            target_name = "Chembur, Mumbai, Maharashtra"
            
        # Ingest Real-Time Atmospheric Feed
        with st.spinner("Ingesting real-time sensor metrics..."):
            live_data = fetch_live_air_quality_by_coords(target_lat, target_lon, target_name)
            
        if live_data:
            aqi_val = live_data["aqi"]
            category, color, health_impact, action_advice = get_cpcb_info(aqi_val)
            
            st.markdown(f"#### 📍 **{target_name}**")
            st.caption(f"Coordinates: `{target_lat:.4f}, {target_lon:.4f}` | Station Feed Timestamp: **{live_data['timestamp']} IST**")
            
            # 4 KPI Metric Cards
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            kpi1.metric("Live CPCB AQI", f"{aqi_val}", delta=category, delta_color="inverse")
            kpi2.metric("PM2.5 Concentration", f"{live_data['pm25']} µg/m³")
            kpi3.metric("PM10 Concentration", f"{live_data['pm10']} µg/m³")
            kpi4.metric("Dominant Driver", live_data["dominant_pollutant"])
            
            # CPCB Color Badge
            st.markdown(
                f"""
                <div style="background-color: {color}; padding: 12px; border-radius: 8px; color: white; font-weight: bold; text-align: center; font-size: 18px; margin-top: 10px; margin-bottom: 20px;">
                    Air Quality Status: {category} (Composite AQI {aqi_val})
                </div>
                """,
                unsafe_allow_html=True
            )
            
            # Commute Windows & Protective Guidance
            adv_col1, adv_col2 = st.columns(2)
            with adv_col1:
                st.markdown("#### 🕒 Safe Commute & Outdoor Windows")
                if aqi_val <= 100:
                    st.success("🟢 **All-Day Safe:** Atmospheric dispersion is high. Ideal for morning jogging, outdoor school assemblies, and sports.")
                elif aqi_val <= 200:
                    st.warning("🟡 **Peak Inversion Alert (06:30 - 09:00 AM):** Ground-level particulate buildup. Prefer evening outdoor transit between **02:00 PM - 05:30 PM**.")
                else:
                    st.error("🔴 **High Pollution Alert (Morning & Late Evening):** Avoid intense outdoor cardio. Vulnerable individuals should reschedule outdoor tasks.")
                
                st.markdown("#### 🛡️ Protective Action Directives")
                st.info(f"**Action Required:** {action_advice}")
                
            with adv_col2:
                st.markdown("#### 🩺 Clinical & Vulnerability Advisory")
                st.write(health_impact)
                if aqi_val > 150:
                    st.warning("⚠️ **Sensitive Group Notice:** Individuals with asthma, COPD, or cardiac conditions must carry prescribed rescue inhalers.")
                if aqi_val > 200:
                    st.error("😷 **Mask Recommendation:** Well-fitted N95 / FFP2 respirators recommended for outdoor transit corridors.")

            st.markdown("---")
            
            
            # 7-DAY ML PREDICTIVE FORECAST (CITIZEN-OPTIMIZED UI)
            
            st.markdown("---")
            st.markdown("### 📅 7-Day Air Quality Outlook")
            st.caption("Machine-learning generated daily pollution projection for planning outdoor activities")

            matched_city = "Mumbai"
            for c in ["Delhi", "Bengaluru", "Kolkata", "Chennai", "Hyderabad", "Ahmedabad", "Jaipur", "Lucknow", "Patna"]:
                if c.lower() in target_name.lower():
                    matched_city = c
                    break

            with st.spinner(f"Generating 7-day outlook calibrated on {matched_city}..."):
                try:
                    forecast_df, metrics = train_and_forecast_city(matched_city, forecast_days=7)
                    
                    # Store metrics in session state so Admin Panel can display model diagnostics
                    st.session_state['latest_model_metrics'] = metrics
                    st.session_state['matched_city'] = matched_city

                    # 1. Citizen Daily Card Carousel (7 Columns)
                    cols = st.columns(7)
                    for idx, row in forecast_df.iterrows():
                        pred_aqi = int(row['Predicted_AQI'])
                        day_cat, day_color, _, _ = get_cpcb_info(pred_aqi)
                        with cols[idx]:
                            st.markdown(
                                f"""
                                <div style="border: 1px solid {day_color}55; background: rgba(255,255,255,0.03); border-radius: 10px; padding: 12px 6px; text-align: center; margin-bottom: 12px;">
                                    <div style="font-size: 13px; font-weight: 600; color: #bbb;">{row['Date']}</div>
                                    <div style="font-size: 24px; font-weight: 800; color: white; margin: 4px 0;">{pred_aqi}</div>
                                    <div style="background-color: {day_color}; color: white; font-size: 11px; font-weight: 700; border-radius: 12px; padding: 3px 6px; display: inline-block;">
                                        {day_cat}
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )

                    # 2. Polished Interactive Area Trendline
                    fig_fc = px.area(
                        forecast_df,
                        x="Date",
                        y="Predicted_AQI",
                        markers=True,
                        text="Predicted_AQI",
                        title=f"Expected AQI Trajectory ({target_name.split(',')[0]})"
                    )
                    
                    # Modern styling & clean dark theme integration
                    fig_fc.update_traces(
                        line_color="#00D2FF",
                        line_width=3,
                        marker=dict(size=9, color="#00D2FF", line=dict(width=2, color="#ffffff")),
                        textposition="top center",
                        textfont=dict(size=12, color="white", family="Arial Black"),
                        fillcolor="rgba(0, 210, 255, 0.12)"
                    )
                    
                    # Dynamic Y-axis scaling to prevent squishing
                    min_y = max(0, forecast_df['Predicted_AQI'].min() - 25)
                    max_y = forecast_df['Predicted_AQI'].max() + 35
                    
                    fig_fc.update_layout(
                        yaxis=dict(title="Air Quality Index (AQI)", range=[min_y, max_y], gridcolor="rgba(255,255,255,0.08)"),
                        xaxis=dict(title=None, gridcolor="rgba(255,255,255,0.05)"),
                        height=360,
                        margin=dict(l=20, r=20, t=40, b=20),
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)"
                    )

                    st.plotly_chart(fig_fc, use_container_width=True)

                except Exception as err:
                    st.warning(f"Unable to compute local ML projection: {err}")
# -----------------------------------------------------------------
    # TAB 2: PAN-INDIA INTERACTIVE MAP & HOTSPOTS LEADERBOARD
    # -----------------------------------------------------------------
    with tab2:
        st.markdown("### 🗺️ Pan-India Live Air Quality Intelligence Map")
        st.caption("Geospatial Sensor Grid & Real-Time Air Quality Distribution")

        # Major station network coordinates across India
        PAN_INDIA_STATIONS = {
            "Mumbai": {"lat": 19.0760, "lon": 72.8777},
            "Delhi (NCR)": {"lat": 28.6139, "lon": 77.2090},
            "Bengaluru": {"lat": 12.9716, "lon": 77.5946},
            "Kolkata": {"lat": 22.5726, "lon": 88.3639},
            "Chennai": {"lat": 13.0827, "lon": 80.2707},
            "Hyderabad": {"lat": 17.3850, "lon": 78.4867},
            "Pune": {"lat": 18.5204, "lon": 73.8567},
            "Ahmedabad": {"lat": 23.0225, "lon": 72.5714},
            "Jaipur": {"lat": 26.9124, "lon": 75.7873},
            "Lucknow": {"lat": 26.8467, "lon": 80.9462},
            "Patna": {"lat": 25.5941, "lon": 85.1376},
            "Bhopal": {"lat": 23.2599, "lon": 77.4126},
            "Chandigarh": {"lat": 30.7333, "lon": 76.7794},
            "Visakhapatnam": {"lat": 17.6868, "lon": 83.2185},
            "Kochi": {"lat": 9.9312, "lon": 76.2673},
            "Guwahati": {"lat": 26.1445, "lon": 91.7362},
            "Nagpur": {"lat": 21.1458, "lon": 79.0882},
            "Indore": {"lat": 22.7196, "lon": 75.8577},
            "Varanasi": {"lat": 25.3176, "lon": 82.9739},
            "Amritsar": {"lat": 31.6340, "lon": 74.8723}
        }

        # Cached National Sensor Pull
        @st.cache_data(ttl=600)
        def get_pan_india_metrics():
            records = []
            for city_label, coords in PAN_INDIA_STATIONS.items():
                data = fetch_live_air_quality_by_coords(coords["lat"], coords["lon"], city_label)
                if data:
                    cat, hex_color, _, _ = get_cpcb_info(data["aqi"])
                    records.append({
                        "City": city_label,
                        "Latitude": coords["lat"],
                        "Longitude": coords["lon"],
                        "AQI": data["aqi"],
                        "Category": cat,
                        "Color": hex_color,
                        "PM2.5": data["pm25"],
                        "PM10": data["pm10"],
                        "Dominant": data["dominant_pollutant"]
                    })
            return pd.DataFrame(records)

        with st.spinner("Polling live monitoring stations across India..."):
            df_map = get_pan_india_metrics()

        if not df_map.empty:
            # Interactive Map Visualization
            fig_map = px.scatter_mapbox(
                df_map,
                lat="Latitude",
                lon="Longitude",
                hover_name="City",
                hover_data={"AQI": True, "Category": True, "PM2.5": True, "PM10": True, "Latitude": False, "Longitude": False},
                color="AQI",
                size="AQI",
                size_max=22,
                color_continuous_scale=["#00B050", "#92D050", "#FFC000", "#FF7C80", "#C00000", "#7030A0"],
                range_color=[0, 400],
                zoom=3.8,
                center={"lat": 22.5937, "lon": 78.9629},
                mapbox_style="carto-positron",
                title="Pan-India Live Continuous Ambient Air Quality Monitoring Network"
            )
            fig_map.update_layout(margin={"r": 0, "t": 40, "l": 0, "b": 0}, height=500)
            st.plotly_chart(fig_map, use_container_width=True)

            st.markdown("---")

            # National Hotspots Leaderboard
            st.markdown("### 🏆 National Hotspots Leaderboard")
            col_clean, col_polluted = st.columns(2)

            # Top 5 Cleanest
            df_clean = df_map.sort_values("AQI", ascending=True).head(5)[["City", "AQI", "Category", "PM2.5"]]
            with col_clean:
                st.markdown("#### 🟢 Top 5 Cleanest Cities Right Now")
                st.dataframe(df_clean.reset_index(drop=True), use_container_width=True)

            # Top 5 Most Polluted
            df_polluted = df_map.sort_values("AQI", ascending=False).head(5)[["City", "AQI", "Category", "PM2.5"]]
            with col_polluted:
                st.markdown("#### 🔴 Top 5 Most Polluted Cities Right Now")
                st.dataframe(df_polluted.reset_index(drop=True), use_container_width=True)
        else:
            st.warning("National sensor data currently unavailable. Check internet connectivity.")