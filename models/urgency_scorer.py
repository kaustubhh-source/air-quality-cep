"""
JAN-MANAS Urgency Scorer
Inspects text for critical hazard keywords (manhole, accident, overflowing, mosquitoes,
sparking, electric, broken pipeline) and combines with sentiment score to flag High/Medium/Low Urgency.
"""

import re
from typing import Dict, Any, List

HIGH_HAZARD_KEYWORDS = [
    "manhole", "open manhole", "accident", "accidents", "overflowing", "mosquitoes",
    "dengue", "sparking", "electric", "electrical shock", "exposed wire",
    "broken pipeline", "short circuit", "cholera", "flooding", "collapse",
    "fire", "hazard", "emergency", "contamination", "contaminated", "hanging wire",
    "live wire", "gas leak"
]

MEDIUM_HAZARD_KEYWORDS = [
    "pothole", "potholes", "garbage bin full", "leak", "leaking", "dark street",
    "smell", "foul smell", "stink", "stinking", "delay", "clogged", "no water",
    "broken light", "debris", "uneven", "flickering", "litter", "uncollected",
    "loose cover"
]


def calculate_urgency(text: str, sentiment_score: float = 0.0) -> Dict[str, Any]:
    """
    Calculates urgency level (High, Medium, Low) for civic feedback based on
    hazard keywords and sentiment intensity.
    """
    if not text or not text.strip():
        return {
            "urgency_level": "Low",
            "hazard_keywords": [],
            "reason": "Default low for empty text"
        }

    text_lower = text.lower()
    found_high_hazards: List[str] = []
    found_medium_hazards: List[str] = []

    for kw in HIGH_HAZARD_KEYWORDS:
        pattern = r'\b' + re.escape(kw) + r'\b'
        if re.search(pattern, text_lower):
            found_high_hazards.append(kw)

    for kw in MEDIUM_HAZARD_KEYWORDS:
        pattern = r'\b' + re.escape(kw) + r'\b'
        if re.search(pattern, text_lower):
            found_medium_hazards.append(kw)

    # Classification logic
    if found_high_hazards:
        urgency = "High"
        reason = f"Critical hazard keywords detected: {', '.join(found_high_hazards)}"
    elif sentiment_score <= -0.50:
        urgency = "High"
        reason = f"High severity sentiment score ({sentiment_score})"
    elif found_medium_hazards or sentiment_score <= -0.20:
        urgency = "Medium"
        reason = f"Moderate hazard keywords ({', '.join(found_medium_hazards)}) or negative sentiment ({sentiment_score})"
    else:
        urgency = "Low"
        reason = "No critical hazards detected and neutral/positive sentiment"

    return {
        "urgency_level": urgency,
        "hazard_keywords": list(set(found_high_hazards + found_medium_hazards)),
        "reason": reason
    }


if __name__ == "__main__":
    # Self-test
    test_cases = [
        ("Open manhole near GTB station platform 1 entrance is dangerous", -0.7),
        ("Garbage bins near Punjabi Colony central market are overflowing for 3 days", -0.6),
        ("Mild water pressure issue during morning hours in Sardar Nagar", -0.1),
        ("Prompt resolution of streetlight complaint near GTB Station. Thanks BMC", 0.6)
    ]
    for text, score in test_cases:
        res = calculate_urgency(text, score)
        print(f"Text: '{text[:45]}...' => Urgency: {res['urgency_level']} ({res['reason']})")
