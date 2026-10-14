"""
JAN-MANAS Database Manager
SQLite database helper for managing civic feedback records, initializing schemas,
querying with filters, updating statuses, and pre-seeding starter datasets.
"""

import os
import sqlite3
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List, Optional

# Import internal NLP modules
import sys
from pathlib import Path

# Add project root to sys.path to ensure module imports work smoothly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from models.sentiment_engine import analyze_sentiment
from models.department_classifier import classify_department
from models.urgency_scorer import calculate_urgency

DB_DIR = PROJECT_ROOT / "data"
DB_PATH = DB_DIR / "jan_manas.db"

LOCATION_CLUSTERS = ["GTB Station", "Sardar Nagar", "Punjabi Colony", "Flank Road"]
DEPARTMENTS = [
    "Solid Waste Management",
    "Roads & Infrastructure",
    "Water Supply & Sewage",
    "Street Lighting & Public Safety"
]
URGENCY_LEVELS = ["High", "Medium", "Low"]
STATUS_OPTIONS = ["Pending", "In Progress", "Resolved"]

# 25 Realistic Synthetic Civic Feedback items from GTB Nagar (BMC F-North Ward)
STARTER_DATASET = [
    {
        "location_cluster": "GTB Station",
        "raw_text": "Open manhole near GTB Station platform 1 entrance is extremely dangerous for commuters at night.",
        "status": "Pending",
        "timestamp": "2026-10-06 08:30:00"
    },
    {
        "location_cluster": "Punjabi Colony",
        "raw_text": "Garbage bins near Punjabi Colony central market are overflowing for 3 days, foul smell spreading everywhere.",
        "status": "Pending",
        "timestamp": "2026-10-06 09:15:00"
    },
    {
        "location_cluster": "Flank Road",
        "raw_text": "Sparking electrical wires hanging low near Flank Road bus stop. Risk of short circuit!",
        "status": "Pending",
        "timestamp": "2026-10-06 10:00:00"
    },
    {
        "location_cluster": "Sardar Nagar",
        "raw_text": "Contaminated black water coming out of taps in Sardar Nagar sector 3 since yesterday morning.",
        "status": "In Progress",
        "timestamp": "2026-10-06 10:45:00"
    },
    {
        "location_cluster": "GTB Station",
        "raw_text": "Massive potholes on GTB Station road causing traffic congestion and bike accidents.",
        "status": "Pending",
        "timestamp": "2026-10-06 11:20:00"
    },
    {
        "location_cluster": "Punjabi Colony",
        "raw_text": "Stagnant drain water near Punjabi Colony park leading to severe mosquitoes menace and dengue threat.",
        "status": "Pending",
        "timestamp": "2026-10-06 12:00:00"
    },
    {
        "location_cluster": "Flank Road",
        "raw_text": "Main pipeline broken near Flank Road crossroad, gallons of clean water wasting on road.",
        "status": "In Progress",
        "timestamp": "2026-10-06 12:30:00"
    },
    {
        "location_cluster": "Sardar Nagar",
        "raw_text": "Streetlights on Sardar Nagar main street have not been working for the past week. Very unsafe for women at night.",
        "status": "Pending",
        "timestamp": "2026-10-06 13:10:00"
    },
    {
        "location_cluster": "GTB Station",
        "raw_text": "Construction debris dumped on footpath near GTB Station blocking pedestrian walking space.",
        "status": "Pending",
        "timestamp": "2026-10-05 14:00:00"
    },
    {
        "location_cluster": "Punjabi Colony",
        "raw_text": "Broken pavement slabs near Punjabi Colony school gates, children might trip and fall.",
        "status": "In Progress",
        "timestamp": "2026-10-05 14:45:00"
    },
    {
        "location_cluster": "Sardar Nagar",
        "raw_text": "Irregular garbage collection van timing in Sardar Nagar area creating uncollected waste buildup.",
        "status": "Pending",
        "timestamp": "2026-10-05 15:30:00"
    },
    {
        "location_cluster": "Flank Road",
        "raw_text": "Speed breaker marking worn out on Flank Road near hospital zone causing sudden braking.",
        "status": "Pending",
        "timestamp": "2026-10-05 16:15:00"
    },
    {
        "location_cluster": "GTB Station",
        "raw_text": "Drainage cover loose near GTB Station auto stand, makes loud noise whenever heavy vehicles pass.",
        "status": "Pending",
        "timestamp": "2026-10-05 17:00:00"
    },
    {
        "location_cluster": "Punjabi Colony",
        "raw_text": "Streetlight flickering continuously outside Punjabi Colony community hall.",
        "status": "In Progress",
        "timestamp": "2026-10-04 18:20:00"
    },
    {
        "location_cluster": "Sardar Nagar",
        "raw_text": "Mild water pressure issue during morning hours in Sardar Nagar block B.",
        "status": "Resolved",
        "timestamp": "2026-10-04 19:00:00"
    },
    {
        "location_cluster": "Flank Road",
        "raw_text": "Public dustbin near Flank Road garden is getting filled fast, needs daily morning cleanup routine.",
        "status": "Resolved",
        "timestamp": "2026-10-04 09:30:00"
    },
    {
        "location_cluster": "GTB Station",
        "raw_text": "Pothole repaired quickly near GTB Station post office. Good work by BMC repair crew!",
        "status": "Resolved",
        "timestamp": "2026-10-04 10:15:00"
    },
    {
        "location_cluster": "Punjabi Colony",
        "raw_text": "Garbage collector came on time today in Punjabi Colony sector 2 and cleaned the lane properly.",
        "status": "Resolved",
        "timestamp": "2026-10-03 11:00:00"
    },
    {
        "location_cluster": "Flank Road",
        "raw_text": "New LED streetlights installed along Flank Road look very bright and clean.",
        "status": "Resolved",
        "timestamp": "2026-10-03 12:30:00"
    },
    {
        "location_cluster": "Sardar Nagar",
        "raw_text": "Water quality in Sardar Nagar block A has improved significantly after pipeline cleaning.",
        "status": "Resolved",
        "timestamp": "2026-10-03 14:00:00"
    },
    {
        "location_cluster": "GTB Station",
        "raw_text": "Overflowing sewage line behind GTB Station local market causing unbearable stink.",
        "status": "Pending",
        "timestamp": "2026-10-06 14:15:00"
    },
    {
        "location_cluster": "Punjabi Colony",
        "raw_text": "Electric pole leaning dangerously near Punjabi Colony plot 45 after storm.",
        "status": "In Progress",
        "timestamp": "2026-10-06 15:00:00"
    },
    {
        "location_cluster": "Sardar Nagar",
        "raw_text": "Accumulation of plastic waste near Sardar Nagar storm drain line blocking water flow.",
        "status": "Pending",
        "timestamp": "2026-10-06 15:45:00"
    },
    {
        "location_cluster": "Flank Road",
        "raw_text": "Uneven road asphalt surface on Flank Road near police chowki needs leveling.",
        "status": "Pending",
        "timestamp": "2026-10-06 16:30:00"
    },
    {
        "location_cluster": "GTB Station",
        "raw_text": "Prompt resolution of streetlight complaint near GTB Station west exit. Thank you BMC F-North Ward!",
        "status": "Resolved",
        "timestamp": "2026-10-06 17:15:00"
    }
]


def get_db_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """
    Creates and returns a connection to the SQLite database.
    """
    os.makedirs(db_path.parent, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path = DB_PATH, force_reseed: bool = False) -> None:
    """
    Initializes the SQLite database table and seeds 25 starter records if empty or if force_reseed=True.
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS civic_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            location_cluster TEXT NOT NULL,
            raw_text TEXT NOT NULL,
            category TEXT NOT NULL,
            sentiment_score REAL NOT NULL,
            sentiment_label TEXT NOT NULL,
            emotional_state TEXT NOT NULL,
            urgency_level TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending'
        )
    """)
    conn.commit()

    # Check if table is empty
    cursor.execute("SELECT COUNT(*) FROM civic_feedback")
    count = cursor.fetchone()[0]

    if count == 0 or force_reseed:
        if force_reseed:
            cursor.execute("DELETE FROM civic_feedback")
            conn.commit()
        seed_starter_data(db_path)

    conn.close()


def process_feedback_item(
    raw_text: str,
    location_cluster: str,
    category: Optional[str] = None,
    status: str = "Pending",
    timestamp: Optional[str] = None
) -> Dict[str, Any]:
    """
    Runs sentiment analysis, department classification, and urgency scoring on raw text.
    """
    if not timestamp:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. Sentiment Engine
    sentiment_res = analyze_sentiment(raw_text)
    sentiment_score = sentiment_res["sentiment_score"]
    sentiment_label = sentiment_res["sentiment_label"]
    emotional_state = sentiment_res["emotional_state"]

    # 2. Department Classifier (if not manually overridden)
    if not category:
        dept_res = classify_department(raw_text)
        category = dept_res["category"]

    # 3. Urgency Scorer
    urgency_res = calculate_urgency(raw_text, sentiment_score)
    urgency_level = urgency_res["urgency_level"]

    return {
        "timestamp": timestamp,
        "location_cluster": location_cluster,
        "raw_text": raw_text,
        "category": category,
        "sentiment_score": sentiment_score,
        "sentiment_label": sentiment_label,
        "emotional_state": emotional_state,
        "urgency_level": urgency_level,
        "status": status
    }


def insert_feedback(
    raw_text: str,
    location_cluster: str,
    category: Optional[str] = None,
    status: str = "Pending",
    timestamp: Optional[str] = None,
    db_path: Path = DB_PATH
) -> int:
    """
    Processes feedback through NLP engines and inserts it into SQLite database.
    Returns the newly inserted row ID.
    """
    processed = process_feedback_item(raw_text, location_cluster, category, status, timestamp)

    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO civic_feedback (
            timestamp, location_cluster, raw_text, category,
            sentiment_score, sentiment_label, emotional_state, urgency_level, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        processed["timestamp"],
        processed["location_cluster"],
        processed["raw_text"],
        processed["category"],
        processed["sentiment_score"],
        processed["sentiment_label"],
        processed["emotional_state"],
        processed["urgency_level"],
        processed["status"]
    ))
    conn.commit()
    inserted_id = cursor.lastrowid
    conn.close()
    return inserted_id


def seed_starter_data(db_path: Path = DB_PATH) -> None:
    """
    Seeds the 25 starter synthetic feedback records into the database.
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    for item in STARTER_DATASET:
        processed = process_feedback_item(
            raw_text=item["raw_text"],
            location_cluster=item["location_cluster"],
            status=item.get("status", "Pending"),
            timestamp=item.get("timestamp")
        )
        cursor.execute("""
            INSERT INTO civic_feedback (
                timestamp, location_cluster, raw_text, category,
                sentiment_score, sentiment_label, emotional_state, urgency_level, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            processed["timestamp"],
            processed["location_cluster"],
            processed["raw_text"],
            processed["category"],
            processed["sentiment_score"],
            processed["sentiment_label"],
            processed["emotional_state"],
            processed["urgency_level"],
            processed["status"]
        ))
    
    conn.commit()
    conn.close()


def get_all_feedback(
    location_cluster: Optional[str] = None,
    category: Optional[str] = None,
    urgency_level: Optional[str] = None,
    status: Optional[str] = None,
    db_path: Path = DB_PATH
) -> pd.DataFrame:
    """
    Fetches civic feedback records with optional filtering as a pandas DataFrame.
    """
    conn = get_db_connection(db_path)
    query = "SELECT * FROM civic_feedback WHERE 1=1"
    params: List[Any] = []

    if location_cluster and location_cluster != "All":
        query += " AND location_cluster = ?"
        params.append(location_cluster)
    if category and category != "All":
        query += " AND category = ?"
        params.append(category)
    if urgency_level and urgency_level != "All":
        query += " AND urgency_level = ?"
        params.append(urgency_level)
    if status and status != "All":
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY id DESC"

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def update_feedback_status(feedback_id: int, new_status: str, db_path: Path = DB_PATH) -> bool:
    """
    Updates the status ('Pending', 'In Progress', 'Resolved') of a given feedback item.
    """
    if new_status not in STATUS_OPTIONS:
        raise ValueError(f"Invalid status '{new_status}'. Must be one of {STATUS_OPTIONS}")

    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE civic_feedback SET status = ? WHERE id = ?", (new_status, feedback_id))
    conn.commit()
    updated = cursor.rowcount > 0
    conn.close()
    return updated


def get_summary_stats(db_path: Path = DB_PATH) -> Dict[str, Any]:
    """
    Generates summary statistics for JAN-MANAS dashboard.
    """
    df = get_all_feedback(db_path=db_path)
    if df.empty:
        return {
            "total_tickets": 0,
            "high_urgency_count": 0,
            "avg_sentiment": 0.0,
            "pending_count": 0,
            "in_progress_count": 0,
            "resolved_count": 0,
            "by_location": {},
            "by_category": {},
            "by_urgency": {},
            "by_emotional_state": {}
        }

    return {
        "total_tickets": int(len(df)),
        "high_urgency_count": int((df["urgency_level"] == "High").sum()),
        "avg_sentiment": float(round(df["sentiment_score"].mean(), 4)),
        "pending_count": int((df["status"] == "Pending").sum()),
        "in_progress_count": int((df["status"] == "In Progress").sum()),
        "resolved_count": int((df["status"] == "Resolved").sum()),
        "by_location": df["location_cluster"].value_counts().to_dict(),
        "by_category": df["category"].value_counts().to_dict(),
        "by_urgency": df["urgency_level"].value_counts().to_dict(),
        "by_emotional_state": df["emotional_state"].value_counts().to_dict()
    }


if __name__ == "__main__":
    # Test initialization and data seeding
    print(f"Initializing database at: {DB_PATH}")
    init_db(force_reseed=True)
    stats = get_summary_stats()
    print("Database Initialized successfully!")
    print(f"Total Feedback Records: {stats['total_tickets']}")
    print(f"High Urgency Count: {stats['high_urgency_count']}")
    print(f"Average Sentiment Score: {stats['avg_sentiment']}")
    print("By Category:", stats['by_category'])
    print("By Urgency:", stats['by_urgency'])
    print("By Location:", stats['by_location'])
