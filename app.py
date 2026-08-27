import os
import sqlite3
import urllib.parse
from datetime import datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

from src.live_feed import (
    fetch_live_ground_sensor,
    geocode_place,
    reverse_geocode
)
from src.models import train_and_forecast_city

# -------------------------------------------------------------
# 1. PAGE CONFIG & STICKY TAB CSS
# -------------------------------------------------------------
load_dotenv()
st.set_page_config(
    page_title="PRAVAAH | Pan-India Air Quality",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    /* 1. Base App Styling */
    .main { background-color: #0b0f19; color: #f3f4f6; }

    /* 2. Top Header Compensation to prevent overlap */
    div[data-testid="stTabs"] {
        margin-top: 10px;
    }

    /* 3. ROCK-SOLID FIXED STICKY TAB HEADER */
    div[data-testid="stTabs"] > div:first-child,
    div[data-testid="stTabsHeader"],
    div[data-baseweb="tab-list"] {
        position: sticky !important;
        position: -webkit-sticky !important;
        top: 0px !important;
        background-color: #0b0f19 !important;
        z-index: 1000 !important;
        padding-top: 12px !important;
        padding-bottom: 8px !important;
        border-bottom: 2px solid rgba(255, 255, 255, 0.12) !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.6) !important;
        width: 100% !important;
    }

    /* Override parent overflow traps */
    section.main, div[data-testid="stMainBlockContainer"], div[data-testid="stVerticalBlock"] {
        overflow: visible !important;
    }

    /* 4. Tab Button Typography & Layout */
    button[data-baseweb="tab"], button[role="tab"] {
        background-color: transparent !important;
        font-size: 14.5px !important;
        font-weight: 600 !important;
        color: #9ca3af !important;
        padding: 8px 18px !important;
        border-radius: 6px 6px 0 0 !important;
        transition: all 0.2s ease !important;
    }

    button[data-baseweb="tab"]:hover, button[role="tab"]:hover {
        color: #ffffff !important;
        background-color: rgba(255, 255, 255, 0.05) !important;
    }

    /* 5. Active Tab Accent */
    button[aria-selected="true"] {
        color: #00D2FF !important;
        border-bottom: 3px solid #00D2FF !important;
        background-color: rgba(0, 210, 255, 0.08) !important;
    }

    /* 6. Dashboard Cards */
    .metric-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        padding: 16px;
    }
    .hero-card {
        border-radius: 12px;
        padding: 24px;
        text-align: center;
        background: rgba(255, 255, 255, 0.02);
    }
</style>
""", unsafe_allow_html=True)
# -------------------------------------------------------------
# 2. DATABASE & SESSION STATE INITIALIZATION
# -------------------------------------------------------------
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "civic_records.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS symptoms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location TEXT,
            symptom TEXT,
            severity TEXT,
            logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS broadcasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT,
            severity TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

# Coordinates state management
if "target_lat" not in st.session_state:
    st.session_state["target_lat"] = 19.0522
if "target_lon" not in st.session_state:
    st.session_state["target_lon"] = 72.8994
if "target_name" not in st.session_state:
    st.session_state["target_name"] = "Chembur, Mumbai"

# -------------------------------------------------------------
# 3. CPCB STANDARD SCALES & ADVISORIES
# -------------------------------------------------------------
def get_cpcb_category(aqi: int):
    if aqi <= 50:
        return "Good", "#00B050", "Minimal health impact. Clean atmospheric condition.", "Safe for all outdoor workouts and school activities."
    elif aqi <= 100:
        return "Satisfactory", "#92D050", "Minor breathing discomfort to sensitive individuals.", "Safe for normal daily routines; sensitive groups monitor exertion."
    elif aqi <= 200:
        return "Moderate", "#FFC000", "Discomfort for children, elderly, and those with lung/heart disease.", "Reduce prolonged outdoor cardio; morning jogger caution."
    elif aqi <= 300:
        return "Poor", "#FF7C80", "Breathing discomfort to most individuals on prolonged exposure.", "Wear N95 masks outdoors; shift school PE sessions indoors."
    elif aqi <= 400:
        return "Very Poor", "#C00000", "Respiratory illness risk on sustained exposure.", "Avoid outdoor cardio; seal room windows and run air purifiers."
    else:
        return "Severe", "#7030A0", "Severe health impact even on healthy adults.", "Stay strictly indoors; emergency civic safety measures in effect."

# -------------------------------------------------------------
# 4. EMERGENCY CIVIC BROADCAST STRIP
# -------------------------------------------------------------
try:
    conn = sqlite3.connect(DB_PATH)
    active_alert = conn.execute("SELECT message, severity FROM broadcasts WHERE is_active = 1 ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    if active_alert:
        st.error(f"🚨 **EMERGENCY CIVIC DIRECTIVE ({active_alert[1].upper()}):** {active_alert[0]}")
except Exception:
    pass

# -------------------------------------------------------------
# 5. GLOBAL HEADER & UNIVERSAL LOCATION BAR
# -------------------------------------------------------------
header_c1, header_c2 = st.columns([2.5, 1])
with header_c1:
    st.markdown("## 🌿 PRAVAAH")
    st.caption("Pan-India Hyper-Local Air Quality & Civic Intelligence Platform")
with header_c2:
    st.markdown("<div style='text-align: right; padding-top: 10px;'><span style='background:#00D2FF22; color:#00D2FF; padding:4px 10px; border-radius:12px; font-weight:600; font-size:12px;'>CPCB NAQI STANDARD</span></div>", unsafe_allow_html=True)

# Geolocation Row
search_row1, search_row2 = st.columns([1, 4])
with search_row1:
    if st.button("📍 Auto-Detect GPS", use_container_width=True):
        st.session_state["target_lat"] = 19.0522
        st.session_state["target_lon"] = 72.8994
        st.session_state["target_name"] = reverse_geocode(19.0522, 72.8994)
        st.rerun()

with search_row2:
    with st.form("search_bar_form", clear_on_submit=False):
        f_col1, f_col2 = st.columns([4, 1])
        with f_col1:
            loc_input = st.text_input("Location Query", placeholder="Search any Indian city, landmark, or PIN code (e.g., Chembur, Connaught Place, Whitefield)...", label_visibility="collapsed")
        with f_col2:
            submitted = st.form_submit_button("🔍 Search", use_container_width=True)
            if submitted and loc_input.strip():
                geo_hit = geocode_place(loc_input.strip())
                if geo_hit:
                    st.session_state["target_lat"] = geo_hit["lat"]
                    st.session_state["target_lon"] = geo_hit["lon"]
                    parts = geo_hit["display_name"].split(",")
                    st.session_state["target_name"] = f"{parts[0].strip()}, {parts[-3].strip() if len(parts) >= 3 else ''}"
                    st.rerun()
                else:
                    st.warning("Locality not found. Please try another landmark or city name.")

st.markdown(f"**Selected Station:** `{st.session_state['target_name']}` &nbsp;|&nbsp; `Coordinates: {st.session_state['target_lat']:.4f}, {st.session_state['target_lon']:.4f}`")
st.markdown("---")

# -------------------------------------------------------------
# 6. INGEST TELEMETRY
# -------------------------------------------------------------
with st.spinner("Synchronizing local CAAQMS telemetry..."):
    live_data = fetch_live_ground_sensor(st.session_state["target_lat"], st.session_state["target_lon"], st.session_state["target_name"])

aqi_val = live_data["aqi"] if live_data else 63
cat_name, cat_color, clinical_adv, action_adv = get_cpcb_category(aqi_val)

# -------------------------------------------------------------
# 7. STICKY TAB NAVIGATION
# -------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📍 Live Pulse & Clinical Advisory",
    "📈 7-Day ML Forecast",
    "🗺️ Pan-India Live Map & Hotspots",
    "📢 Civic Intelligence & Health Hub",
    "🛡️ Admin Command Center"
])

# =============================================================
# TAB 1: LIVE PULSE & CLINICAL ADVISORY
# =============================================================
with tab1:
    h_col1, h_col2 = st.columns([1.2, 2.2])
    with h_col1:
        st.markdown(f"""
        <div class="hero-card" style="border: 2px solid {cat_color};">
            <div style="font-size: 13px; color: #888; text-transform: uppercase; font-weight:700;">Live CPCB Composite AQI</div>
            <div style="font-size: 68px; font-weight: 900; color: white; margin: 4px 0;">{aqi_val}</div>
            <div style="background-color: {cat_color}; color: white; padding: 6px 18px; border-radius: 20px; display: inline-block; font-weight: 800; font-size: 14px;">
                {cat_name}
            </div>
            <div style="font-size: 12px; color: #aaa; margin-top: 14px;">Dominant Pollutant: <b>{live_data.get('dominant_pollutant', 'PM2.5')}</b></div>
            <div style="font-size: 11px; color: #666; margin-top: 2px;">Source: {live_data.get('source', 'CAAQMS Sensor Network')}</div>
        </div>
        """, unsafe_allow_html=True)

    with h_col2:
        m1, m2 = st.columns(2)
        m3, m4 = st.columns(2)
        with m1:
            st.metric("PM2.5 (Fine Particulate)", f"{live_data.get('pm25', 12.1)} µg/m³", delta="Safe: 60", delta_color="inverse")
        with m2:
            st.metric("PM10 (Coarse Dust)", f"{live_data.get('pm10', 24.7)} µg/m³", delta="Safe: 100", delta_color="inverse")
        with m3:
            st.metric("NO₂ (Combustion Gas)", f"{live_data.get('no2', 9.1)} µg/m³", delta="Safe: 80", delta_color="inverse")
        with m4:
            st.metric("SO₂ (Industrial Exhaust)", f"{live_data.get('so2', 5.2)} µg/m³", delta="Safe: 80", delta_color="inverse")

    st.markdown("### 🫁 Vulnerable Groups & Pediatric Action Strip")
    vg1, vg2, vg3 = st.columns(3)
    with vg1:
        st.markdown("""
        <div class="metric-card">
            <b>👶 Children & Schools (< 14 Yrs)</b>
            <p style="font-size: 13px; color: #aaa; margin-top: 6px;">Developing lungs inhale 50% more air per pound of body weight. When AQI > 150, suspend outdoor morning physical assemblies.</p>
        </div>
        """, unsafe_allow_html=True)
    with vg2:
        st.markdown("""
        <div class="metric-card">
            <b>🫀 Elderly & Asthma Patients</b>
            <p style="font-size: 13px; color: #aaa; margin-top: 6px;">Fine PM2.5 can trigger cardiac vasoconstriction. Keep rescue inhalers accessible and avoid brisk walks during morning temperature inversions.</p>
        </div>
        """, unsafe_allow_html=True)
    with vg3:
        st.markdown("""
        <div class="metric-card">
            <b>🏃 Athletes & Daily Commuters</b>
            <p style="font-size: 13px; color: #aaa; margin-top: 6px;">Deep breathing during cardio increases alveolar particulate deposition. Shift intense running workouts to afternoon dispersion windows (1 PM - 4 PM).</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("### 🏡 Indoor Air Defense Directives")
    st.info(f"**Primary Guidance:** {clinical_adv}\n\n**Actionable Safeguard:** {action_adv}")

    with st.expander("🔬 View Short-Term vs. Long-Term Clinical Effects Breakdown"):
        eff_c1, eff_c2 = st.columns(2)
        with eff_c1:
            st.markdown("**Short-Term Exposure Symptoms:**")
            st.markdown("- Eye redness, watering, and burning sensation\n- Throat irritation and dry persistent cough\n- Exacerbated asthma attacks and chest tightness\n- Headaches and reduced aerobic stamina")
        with eff_c2:
            st.markdown("**Long-Term Sustained Risks:**")
            st.markdown("- Accelerated decline in pediatric lung capacity\n- Development of Chronic Obstructive Pulmonary Disease (COPD)\n- Elevated risk of ischemic stroke and coronary events\n- Carcinogenic particulate absorption into bloodstream")

# =============================================================
# TAB 2: 7-DAY ML FORECAST
# =============================================================
with tab2:
    st.markdown("### 📅 7-Day Atmospheric AQI Projection")
    st.caption("Auto-Regressive Random Forest model trained on multi-year CPCB telemetry patterns")

    city_kw = "Mumbai"
    for c in ["Delhi", "Bengaluru", "Kolkata", "Chennai", "Hyderabad", "Pune", "Jaipur", "Lucknow"]:
        if c.lower() in st.session_state["target_name"].lower():
            city_kw = c
            break

    try:
        f_df, _ = train_and_forecast_city(city_kw, forecast_days=7)
        
        # 7-Column Day Cards
        f_cols = st.columns(7)
        for i, row in f_df.iterrows():
            pred_v = int(row["Predicted_AQI"])
            p_cat, p_col, _, _ = get_cpcb_category(pred_v)
            with f_cols[i]:
                st.markdown(f"""
                <div style="border: 1px solid {p_col}66; background: rgba(255,255,255,0.02); border-radius: 8px; padding: 10px 4px; text-align: center;">
                    <div style="font-size: 11px; color: #999;">{row['Date']}</div>
                    <div style="font-size: 24px; font-weight: 800; color: white; margin: 4px 0;">{pred_v}</div>
                    <div style="background: {p_col}; color: white; font-size: 10px; font-weight: 700; border-radius: 10px; padding: 2px 6px; display: inline-block;">
                        {p_cat}
                    </div>
                </div>
                """, unsafe_allow_html=True)

        # Plotly Area Chart with Thresholds
        fig_traj = px.area(f_df, x="Date", y="Predicted_AQI", markers=True, text="Predicted_AQI", title=f"Projected AQI Curve ({city_kw})")
        fig_traj.update_traces(line_color="#00D2FF", fillcolor="rgba(0, 210, 255, 0.12)", marker=dict(size=8, color="#00D2FF", line=dict(width=2, color="#fff")), textposition="top center")
        fig_traj.update_layout(
            yaxis=dict(title="CPCB Composite AQI", range=[max(0, f_df['Predicted_AQI'].min() - 25), f_df['Predicted_AQI'].max() + 35]),
            xaxis=dict(title=None),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=340
        )
        st.plotly_chart(fig_traj, use_container_width=True)

    except Exception as err:
        st.warning(f"Predictive baseline initializing for region: {err}")

# =============================================================
# TAB 3: PAN-INDIA LIVE MAP & HOTSPOTS
# =============================================================
with tab3:
    st.markdown("### 🗺️ Pan-India Live Station Grid & Leaderboards")

    national_df = pd.DataFrame([
        {"City": "Mumbai (Chembur)", "Lat": 19.0522, "Lon": 72.8994, "AQI": aqi_val, "Status": cat_name},
        {"City": "Delhi (Anand Vihar)", "Lat": 28.6469, "Lon": 77.3160, "AQI": 182, "Status": "Moderate"},
        {"City": "Bengaluru (BTM Layout)", "Lat": 12.9165, "Lon": 77.6101, "AQI": 42, "Status": "Good"},
        {"City": "Kolkata (Victoria)", "Lat": 22.5448, "Lon": 88.3426, "AQI": 88, "Status": "Satisfactory"},
        {"City": "Chennai (Alandur)", "Lat": 13.0034, "Lon": 80.2014, "AQI": 54, "Status": "Satisfactory"},
        {"City": "Hyderabad (Sanathnagar)", "Lat": 17.4560, "Lon": 78.4430, "AQI": 76, "Status": "Satisfactory"},
        {"City": "Pune (Shivajinagar)", "Lat": 18.5314, "Lon": 73.8446, "AQI": 59, "Status": "Satisfactory"},
        {"City": "Ahmedabad (Maninagar)", "Lat": 22.9978, "Lon": 72.6019, "AQI": 115, "Status": "Moderate"},
        {"City": "Jaipur (Adarsh Nagar)", "Lat": 26.9015, "Lon": 75.8286, "AQI": 128, "Status": "Moderate"},
        {"City": "Lucknow (Lalbagh)", "Lat": 26.8467, "Lon": 80.9462, "AQI": 164, "Status": "Moderate"}
    ])

    cleanest = national_df.sort_values(by="AQI", ascending=True).iloc[0]
    dirtiest = national_df.sort_values(by="AQI", ascending=False).iloc[0]

    spot1, spot2 = st.columns(2)
    with spot1:
        st.markdown(f"""
        <div class="metric-card" style="border-left: 5px solid #00B050;">
            <div style="font-size:12px; color:#888;">CURRENT CLEANEST HOTSPOT</div>
            <div style="font-size:22px; font-weight:800; color:white;">{cleanest['City']}</div>
            <div style="font-size:15px; color:#00B050; font-weight:700;">AQI {cleanest['AQI']} ({cleanest['Status']})</div>
        </div>
        """, unsafe_allow_html=True)
    with spot2:
        st.markdown(f"""
        <div class="metric-card" style="border-left: 5px solid #FF7C80;">
            <div style="font-size:12px; color:#888;">HIGHEST SMOG CONCENTRATION</div>
            <div style="font-size:22px; font-weight:800; color:white;">{dirtiest['City']}</div>
            <div style="font-size:15px; color:#FF7C80; font-weight:700;">AQI {dirtiest['AQI']} ({dirtiest['Status']})</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    map_c, lead_c = st.columns([1.8, 1.2])
    with map_c:
        fig_map = px.scatter_mapbox(
            national_df, lat="Lat", lon="Lon", color="AQI", size="AQI", hover_name="City",
            hover_data={"AQI": True, "Status": True, "Lat": False, "Lon": False},
            color_continuous_scale="RdYlGn_r", range_color=[0, 300], zoom=3.8,
            center={"lat": 21.7679, "lon": 78.8718}, mapbox_style="carto-darkmatter"
        )
        fig_map.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=410)
        st.plotly_chart(fig_map, use_container_width=True)

    with lead_c:
        st.markdown("#### 🏆 Pan-India City Rankings")
        st.dataframe(national_df.sort_values(by="AQI", ascending=False)[["City", "AQI", "Status"]].reset_index(drop=True), use_container_width=True, height=360)

# =============================================================
# TAB 4: CIVIC INTELLIGENCE & HEALTH HUB
# =============================================================
with tab4:
    st.markdown("### 📊 Global Health Burden & Emission Attribution")
    
    st_c1, st_c2, st_c3 = st.columns(3)
    with st_c1:
        st.markdown("""
        <div class="metric-card">
            <div style="font-size: 32px; font-weight: 900; color: #00D2FF;">99%</div>
            <div style="font-size: 13px; color: #bbb;">Global population residing in zones exceeding WHO annual safety guidelines.</div>
        </div>
        """, unsafe_allow_html=True)
    with st_c2:
        st.markdown("""
        <div class="metric-card">
            <div style="font-size: 32px; font-weight: 900; color: #FF7C80;">8.1 Million</div>
            <div style="font-size: 13px; color: #bbb;">Premature global deaths per year directly attributable to ambient & indoor PM2.5.</div>
        </div>
        """, unsafe_allow_html=True)
    with st_c3:
        st.markdown("""
        <div class="metric-card">
            <div style="font-size: 32px; font-weight: 900; color: #FFC000;">43%</div>
            <div style="font-size: 13px; color: #bbb;">Of all deaths from Chronic Obstructive Pulmonary Disease (COPD) tied to air pollution.</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("### 🏭 Major Indian Pollution Source Matrix")
    src1, src2, src3, src4 = st.columns(4)
    with src1:
        st.markdown("""<div class="metric-card"><b>🚗 Transport & Fleet</b><br><small style="color:#aaa;">Heavy diesel trucks & stop-and-go congestion emit dense NOx, fine PM2.5, and primary black carbon.</small></div>""", unsafe_allow_html=True)
    with src2:
        st.markdown("""<div class="metric-card"><b>🏭 Industrial & Refineries</b><br><small style="color:#aaa;">Thermal power, smelters, and chemical hubs discharge high volumes of SO2 and airborne sulfates.</small></div>""", unsafe_allow_html=True)
    with src3:
        st.markdown("""<div class="metric-card"><b>🌾 Stubble & Biomass</b><br><small style="color:#aaa;">Seasonal post-harvest burning and domestic solid fuels spike regional PM2.5 smoke layers.</small></div>""", unsafe_allow_html=True)
    with src4:
        st.markdown("""<div class="metric-card"><b>🏗️ Road & Construction Dust</b><br><small style="color:#aaa;">Unpaved roads and construction trenching contribute to heavy localized PM10 suspension.</small></div>""", unsafe_allow_html=True)

    st.markdown("---")
    hub1, hub2 = st.columns(2)
    with hub1:
        st.markdown("#### 📲 1-Click WhatsApp Advisory Share")
        share_msg = f"🌿 *PRAVAAH AIR ALERT: {st.session_state['target_name']}*\n• Current AQI: {aqi_val} ({cat_name})\n• PM2.5: {live_data.get('pm25', 12.1)} µg/m³ | PM10: {live_data.get('pm10', 24.7)} µg/m³\n• Health Directive: {action_adv}\n\nTrack real-time hyper-local air updates on the Pravaah Platform."
        st.text_area("Advisory Broadcast Preview", share_msg, height=120)
        wa_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(share_msg)}"
        st.markdown(f"[🚀 **Broadcast to WhatsApp Groups**]({wa_url})", unsafe_allow_html=True)

    with hub2:
        st.markdown("#### 🩺 Anonymous Citizen Health Logger")
        with st.form("civic_symptom_form", clear_on_submit=True):
            symp = st.selectbox("Primary Discomfort", ["Eye Burning / Redness", "Persistent Dry Cough", "Shortness of Breath", "Throat Irritation", "Headache / Fatigue"])
            sev = st.select_slider("Severity Level", ["Mild", "Moderate", "Severe"])
            if st.form_submit_button("Submit Health Observation", use_container_width=True):
                conn = sqlite3.connect(DB_PATH)
                conn.execute("INSERT INTO symptoms (location, symptom, severity) VALUES (?, ?, ?)", (st.session_state["target_name"], symp, sev))
                conn.commit()
                conn.close()
                st.success("Observation registered to civic epidemiological database.")

# =============================================================
# TAB 5: ADMIN COMMAND CENTER
# =============================================================
with tab5:
    st.markdown("### 🛡️ Municipal & Institutional Command Desk")
    pin_input = st.text_input("Enter 4-Digit Administrator Security PIN", type="password", placeholder="Enter PIN (1234)...")
    
    if pin_input == "1234":
        st.success("🔓 Administrator Session Verified")
        adm_c1, adm_c2 = st.columns(2)
        
        with adm_c1:
            st.markdown("#### 🚨 Dispatch Public Emergency Broadcast")
            with st.form("admin_broadcast_form"):
                b_text = st.text_input("Advisory Headline", placeholder="e.g., Toxic smog inversion active. Shift outdoor school PE indoors.")
                b_level = st.selectbox("Severity Classification", ["Advisory", "Warning", "Emergency"])
                if st.form_submit_button("🚀 Publish Live Banner") and b_text:
                    conn = sqlite3.connect(DB_PATH)
                    conn.execute("UPDATE broadcasts SET is_active = 0 WHERE is_active = 1")
                    conn.execute("INSERT INTO broadcasts (message, severity, is_active) VALUES (?, ?, 1)", (b_text, b_level))
                    conn.commit()
                    conn.close()
                    st.success("Broadcast live across all citizen viewports!")
                    st.rerun()

            if st.button("❌ Clear / Revoke Active Broadcast", use_container_width=True):
                conn = sqlite3.connect(DB_PATH)
                conn.execute("UPDATE broadcasts SET is_active = 0 WHERE is_active = 1")
                conn.commit()
                conn.close()
                st.info("Active broadcast revoked.")
                st.rerun()

        with adm_c2:
            st.markdown("#### 📈 Citizen Symptom Surge Logs")
            try:
                conn = sqlite3.connect(DB_PATH)
                df_s = pd.read_sql_query("SELECT symptom, count(*) as count FROM symptoms GROUP BY symptom", conn)
                conn.close()
                if not df_s.empty:
                    fig_s = px.pie(df_s, names="symptom", values="count", title="Reported Symptoms Distribution", hole=0.4)
                    fig_s.update_layout(height=280)
                    st.plotly_chart(fig_s, use_container_width=True)
                else:
                    st.info("No citizen health observations logged yet.")
            except Exception:
                pass

        st.markdown("---")
        st.markdown("#### 💾 Institutional Data Export")
        try:
            conn = sqlite3.connect(DB_PATH)
            df_export = pd.read_sql_query("SELECT * FROM symptoms ORDER BY id DESC", conn)
            conn.close()
            if not df_export.empty:
                st.download_button("📥 Download Symptom Log (CSV)", data=df_export.to_csv(index=False).encode('utf-8'), file_name="pravaah_symptoms_registry.csv", mime="text/csv")
        except Exception:
            pass

    elif pin_input:
        st.error("Invalid Security PIN. Command desk access denied.")