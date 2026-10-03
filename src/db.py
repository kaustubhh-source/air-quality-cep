import os
import sqlite3
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "civic_records.db")

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    """Initializes SQLite schema for symptoms logging, emergency broadcasts, and field calibrations."""
    conn = get_connection()
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS field_calibrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location_query TEXT,
            override_aqi INTEGER,
            override_pm25 REAL,
            override_pm10 REAL,
            notes TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Schema migration for existing databases
    try:
        c.execute("ALTER TABLE field_calibrations ADD COLUMN override_pm25 REAL")
    except Exception:
        pass
    try:
        c.execute("ALTER TABLE field_calibrations ADD COLUMN override_pm10 REAL")
    except Exception:
        pass

    conn.commit()
    conn.close()

def get_active_broadcast():
    """Returns the latest active emergency broadcast message and severity, if any."""
    try:
        conn = get_connection()
        row = conn.execute(
            "SELECT message, severity FROM broadcasts WHERE is_active = 1 ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()
        return row
    except Exception:
        return None

def publish_broadcast(message: str, severity: str = "Advisory"):
    """Deactivates previous broadcasts and inserts a new active broadcast banner."""
    conn = get_connection()
    conn.execute("UPDATE broadcasts SET is_active = 0 WHERE is_active = 1")
    conn.execute(
        "INSERT INTO broadcasts (message, severity, is_active) VALUES (?, ?, 1)",
        (message, severity)
    )
    conn.commit()
    conn.close()

def revoke_broadcast():
    """Revokes all currently active emergency broadcasts."""
    conn = get_connection()
    conn.execute("UPDATE broadcasts SET is_active = 0 WHERE is_active = 1")
    conn.commit()
    conn.close()

def get_field_calibration(location_query: str = ""):
    """Returns active field calibration override for a location or global override."""
    try:
        conn = get_connection()
        c = conn.cursor()
        if location_query:
            clean_q = location_query.lower().split(',')[0].strip()
            row = c.execute(
                """SELECT override_aqi, location_query, notes, override_pm25, override_pm10 FROM field_calibrations 
                   WHERE is_active = 1 AND (LOWER(location_query) LIKE ? OR LOWER(?) LIKE '%' || LOWER(location_query) || '%') 
                   ORDER BY id DESC LIMIT 1""",
                (f"%{clean_q}%", clean_q)
            ).fetchone()
            if row:
                conn.close()
                return {
                    "override_aqi": row[0],
                    "location_query": row[1],
                    "notes": row[2],
                    "override_pm25": row[3] if len(row) > 3 and row[3] is not None else None,
                    "override_pm10": row[4] if len(row) > 4 and row[4] is not None else None
                }
        
        # Fallback to global active calibration
        row = c.execute(
            "SELECT override_aqi, location_query, notes, override_pm25, override_pm10 FROM field_calibrations WHERE is_active = 1 ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()
        if row:
            return {
                "override_aqi": row[0],
                "location_query": row[1],
                "notes": row[2],
                "override_pm25": row[3] if len(row) > 3 and row[3] is not None else None,
                "override_pm10": row[4] if len(row) > 4 and row[4] is not None else None
            }
    except Exception:
        pass
    return None

def set_field_calibration(location_query: str, override_aqi: int, notes: str = "Field Visit Public Display Calibration", override_pm25: float = None, override_pm10: float = None):
    """Sets an active field calibration AQI, PM2.5, and PM10 override."""
    conn = get_connection()
    conn.execute("UPDATE field_calibrations SET is_active = 0 WHERE is_active = 1")
    conn.execute(
        "INSERT INTO field_calibrations (location_query, override_aqi, override_pm25, override_pm10, notes, is_active) VALUES (?, ?, ?, ?, ?, 1)",
        (location_query, int(override_aqi), override_pm25, override_pm10, notes)
    )
    conn.commit()
    conn.close()

def clear_field_calibration():
    """Deactivates all field calibrations and restores automated live satellite telemetry."""
    conn = get_connection()
    conn.execute("UPDATE field_calibrations SET is_active = 0 WHERE is_active = 1")
    conn.commit()
    conn.close()

def log_symptom(location: str, symptom: str, severity: str):
    """Inserts a new anonymous citizen health observation into the database."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO symptoms (location, symptom, severity) VALUES (?, ?, ?)",
        (location, symptom, severity)
    )
    conn.commit()
    conn.close()

def get_symptom_distribution():
    """Fetches symptom distribution summary for pie chart visualization."""
    try:
        conn = get_connection()
        df = pd.read_sql_query(
            "SELECT symptom, COUNT(*) as count FROM symptoms GROUP BY symptom ORDER BY count DESC",
            conn
        )
        conn.close()
        return df
    except Exception:
        return pd.DataFrame(columns=["symptom", "count"])

def get_symptom_registry(limit: int = 50):
    """Fetches recent symptom observations registry table."""
    try:
        conn = get_connection()
        df = pd.read_sql_query(
            f"SELECT id, location, symptom, severity, logged_at FROM symptoms ORDER BY id DESC LIMIT {limit}",
            conn
        )
        conn.close()
        return df
    except Exception:
        return pd.DataFrame(columns=["id", "location", "symptom", "severity", "logged_at"])

# Initialize DB and run schema migrations automatically
try:
    init_db()
except Exception:
    pass
