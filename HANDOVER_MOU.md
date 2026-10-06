# 📜 PRAVAAH PROJECT HANDOVER MEMORANDUM OF UNDERSTANDING (MOU)
### University of Mumbai Under-Graduate Community Engagement Project (CEP) under NEP 2020

---

## 🏛️ Executive Overview

This document constitutes the official **Project Handover Memorandum of Understanding (MOU)** and **Operational Adoption Guide** for **PRAVAAH: Indian Air Quality & Civic Intelligence Platform**, developed in compliance with the **University of Mumbai NEP 2020 Under-Graduate Community Engagement Project (CEP)** guidelines.

- **Project Repository:** [`https://github.com/kaustubhh-source/air-quality-cep`](https://github.com/kaustubhh-source/air-quality-cep)
- **Deployment Platform:** Streamlit Community Cloud
- **Open-Source License:** MIT License

---

## 👥 Parties to the Handover

1. **Student Lead / Developer Author:** Kaustubh (University of Mumbai Under-Graduate CEP Lead)
2. **Designated Recipient Community Stakeholders:**
   - College NSS Unit & Student Environmental Cell
   - Chembur & MMR Auto-Rickshawmen Driver Unions
   - Local Traffic Police Division & Warden Cell
   - Resident Welfare Associations (RWAs) & Municipal Ward Offices

---

## 📋 Terms of Handover & Transfer of Responsibilities

1. **Source Code & System Ownership:**
   - Full read/write access to the open-source repository, database schema (`civic_records.db`), and predictive machine learning models (`RandomForestRegressor` 7-day AQI pipeline) is transferred under the MIT License.

2. **Operational Responsibilities Transferred:**
   - **Daily Telemetry Dissemination:** Monitoring real-time CPCB ground telemetry across Indian metropolitan hubs and local municipal wards.
   - **Civic Advisories & Emergency Alerts:** Utilizing the 1-Click WhatsApp Advisory Broadcast and Admin Security Console (Default PIN: `1234`) to issue public warning banners during high smog inversions.
   - **Epidemiological Tracking:** Collecting citizen health observations (symptoms logged by drivers and residents) to maintain local health surveillance.

---

## 📖 Quick-Start Volunteer Operating Manual

```text
+-----------------------------------------------------------------------------------+
|                           COMMUNITY OPERATOR QUICK START                          |
+-----------------------------------------------------------------------------------+
| 1. Live Telemetry & Location Search:                                              |
|    - Use the top search bar to query any Indian city, landmark, or PIN code.      |
|    - Click "Auto-Detect GPS" for instant hyper-local updates.                      |
|                                                                                   |
| 2. 1-Click WhatsApp Advisory Broadcast (Tab 4):                                   |
|    - Scroll to "Multi-Channel Civic Advisory Broadcast".                          |
|    - Click "Share Advisory to WhatsApp Group" to dispatch warnings.               |
|                                                                                   |
| 3. Emergency Public Banner Dispatch (Tab 5 Admin Console):                        |
|    - Access Institutional Console via URL query ?admin=true or footer link.       |
|    - Authenticate with PIN 1234.                                                  |
|    - Type headline and click "Publish Live Banner".                               |
|                                                                                   |
| 4. Export Symptom Registry CSV:                                                   |
|    - Inside Admin Console, click "Download Exportable Symptom Registry (CSV)".    |
+-----------------------------------------------------------------------------------+
```

---

## 📊 Summary of CEP Impact Metrics

| Metric Category | Value / Achievement |
| :--- | :--- |
| **Field Survey Sample Size** | N=150 Open-Cabin Auto-Rickshaw & Traffic Personnel (Chembur & MMR) |
| **ML Predictive Model Performance** | Autoregressive Random Forest / Gradient Boost (R² = 0.88, MAE = ±12.4 AQI) |
| **Ground Telemetry Integration** | CAAQMS OpenAQ v3 API with Open-Meteo Satellite Fallback |
| **Occupational Exposure Finding** | Auto-rickshaw drivers experience 3.4x higher particulate intake during 8-12h shifts |
| **Civic Tools** | Anonymous SQLite Symptom Logger, 1-Click WhatsApp Advisory, Admin Field Calibration |

---

## ✍️ Verification & Dual Signature Sign-Off

```text
__________________________________            __________________________________
Kaustubh (CEP Student Author Lead)            Designated Representative / Custodian
University of Mumbai CEP                      Recipient Community Organization
Date: October 06, 2026                        Date: October 06, 2026
```
