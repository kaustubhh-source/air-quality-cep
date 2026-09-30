import os
import sqlite3
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "civic_records.db")

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    """Initializes SQLite schema for symptoms logging and emergency broadcasts."""
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
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
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
