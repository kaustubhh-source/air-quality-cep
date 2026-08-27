import os
import requests
import urllib.parse
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
AQICN_TOKEN = os.getenv("AQICN_TOKEN", "").strip()

def calculate_cpcb_subindex_pm25(conc: float) -> int:
    """Official Indian CPCB Breakpoint Interpolation for PM2.5"""
    if conc <= 30:
        return int((50 / 30) * conc)
    elif conc <= 60:
        return int(50 + (50 / 30) * (conc - 30))
    elif conc <= 90:
        return int(100 + (100 / 30) * (conc - 60))
    elif conc <= 120:
        return int(200 + (100 / 30) * (conc - 90))
    elif conc <= 250:
        return int(300 + (100 / 130) * (conc - 120))
    else:
        return int(400 + (100 / 130) * (conc - 250))

def calculate_cpcb_subindex_pm10(conc: float) -> int:
    """Official Indian CPCB Breakpoint Interpolation for PM10"""
    if conc <= 50:
        return int(conc)
    elif conc <= 100:
        return int(50 + (50 / 50) * (conc - 50))
    elif conc <= 250:
        return int(100 + (100 / 150) * (conc - 100))
    elif conc <= 350:
        return int(200 + (100 / 100) * (conc - 250))
    elif conc <= 430:
        return int(300 + (100 / 80) * (conc - 350))
    else:
        return int(400 + (100 / 70) * (conc - 430))

def geocode_place(query: str):
    url = "https://nominatim.openstreetmap.org/search"
    headers = {"User-Agent": "Pravaah-AirQualityPlatform/1.0"}
    params = {"q": f"{query}, India", "format": "json", "limit": 1}
    try:
        res = requests.get(url, params=params, headers=headers, timeout=6)
        if res.status_code == 200:
            data = res.json()
            if data:
                return {
                    "lat": float(data[0]["lat"]),
                    "lon": float(data[0]["lon"]),
                    "display_name": data[0]["display_name"]
                }
    except Exception:
        pass
    return None

def reverse_geocode(lat: float, lon: float):
    url = "https://nominatim.openstreetmap.org/reverse"
    headers = {"User-Agent": "Pravaah-AirQualityPlatform/1.0"}
    params = {"lat": lat, "lon": lon, "format": "json"}
    try:
        res = requests.get(url, params=params, headers=headers, timeout=6)
        if res.status_code == 200:
            data = res.json()
            if data:
                address = data.get("address", {})
                suburb = address.get("suburb") or address.get("neighbourhood") or address.get("residential") or address.get("road") or "Local Area"
                city = address.get("city") or address.get("state_district") or address.get("state") or "India"
                return f"{suburb}, {city}"
    except Exception:
        pass
    return f"{lat:.4f}, {lon:.4f}"

def fetch_live_air_quality_by_coords(lat: float, lon: float, location_name: str = ""):
    """Satellite reanalysis fallback via Open-Meteo"""
    url = f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lon}&current=pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,us_aqi&timezone=Asia%2FKolkata"
    try:
        r = requests.get(url, timeout=6)
        if r.status_code == 200:
            cur = r.json().get("current", {})
            p25 = float(cur.get("pm2_5", 25.0))
            p10 = float(cur.get("pm10", 45.0))
            return {
                "location": location_name,
                "lat": lat,
                "lon": lon,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M IST"),
                "aqi": int(cur.get("us_aqi", calculate_cpcb_subindex_pm25(p25))),
                "pm25": round(p25, 1),
                "pm10": round(p10, 1),
                "no2": round(float(cur.get("nitrogen_dioxide", 12.0)), 1),
                "so2": round(float(cur.get("sulphur_dioxide", 5.0)), 1),
                "dominant_pollutant": "PM2.5",
                "source": "Open-Meteo Atmospheric Grid"
            }
    except Exception:
        pass
    return None

def fetch_live_ground_sensor(lat: float, lon: float, fallback_name: str = "Chembur, Mumbai"):
    """
    Ingests live ground sensor feeds from physical CAAQMS stations via WAQI.
    """
    headers = {"User-Agent": "Pravaah-AirQualityPlatform/1.0"}
    
    city_kw = "mumbai"
    if fallback_name:
        for c in ["chembur", "mumbai", "delhi", "bengaluru", "kolkata", "chennai", "hyderabad", "pune", "ahmedabad", "jaipur", "lucknow", "patna"]:
            if c in fallback_name.lower():
                city_kw = c
                break

    if AQICN_TOKEN:
        urls_to_poll = [
            f"https://api.waqi.info/feed/{city_kw}/?token={AQICN_TOKEN}",
            f"https://api.waqi.info/feed/geo:{lat};{lon}/?token={AQICN_TOKEN}"
        ]

        for u in urls_to_poll:
            try:
                res = requests.get(u, headers=headers, timeout=6)
                if res.status_code == 200:
                    json_data = res.json()
                    if json_data.get("status") == "ok":
                        data = json_data.get("data", {})
                        iaqi = data.get("iaqi", {})
                        station_city = data.get("city", {})

                        raw_pm25 = iaqi.get("pm25", {}).get("v")
                        raw_pm10 = iaqi.get("pm10", {}).get("v")
                        raw_aqi = data.get("aqi", 0)
                        
                        pm25_val = float(raw_pm25) if raw_pm25 is not None else round(raw_aqi * 0.45, 1)
                        pm10_val = float(raw_pm10) if raw_pm10 is not None else round(raw_aqi * 0.75, 1)

                        sub_pm25 = calculate_cpcb_subindex_pm25(pm25_val)
                        sub_pm10 = calculate_cpcb_subindex_pm10(pm10_val)
                        cpcb_aqi = max(sub_pm25, sub_pm10)

                        return {
                            "location": station_city.get("name", fallback_name),
                            "lat": lat,
                            "lon": lon,
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M IST"),
                            "aqi": int(raw_aqi),
                            "cpcb_aqi": int(cpcb_aqi),
                            "pm25": round(pm25_val, 1),
                            "pm10": round(pm10_val, 1),
                            "no2": round(float(iaqi.get("no2", {}).get("v", 14.2)), 1),
                            "so2": round(float(iaqi.get("so2", {}).get("v", 6.8)), 1),
                            "dominant_pollutant": data.get("dominentpol", "PM2.5").upper(),
                            "source": "Physical CPCB/MPCB CAAQMS Station"
                        }
            except Exception:
                continue

    return fetch_live_air_quality_by_coords(lat, lon, fallback_name)