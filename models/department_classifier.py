"""
JAN-MANAS Department Classifier
Rule-based and keyword dictionary matching across 4 core departments:
- Solid Waste Management
- Roads & Infrastructure
- Water Supply & Sewage
- Street Lighting & Public Safety
"""

import re
from typing import Dict, Any, List

DEPARTMENT_KEYWORDS: Dict[str, List[str]] = {
    "Solid Waste Management": [
        "garbage", "trash", "waste", "bin", "dustbin", "dump", "dumped", "litter",
        "muck", "filth", "foul smell", "stink", "stinking", "debris", "sweeping",
        "kachra", "plastic", "cleanup", "refuse", "clean up", "sanitation"
    ],
    "Roads & Infrastructure": [
        "pothole", "potholes", "road", "roads", "pavement", "footpath", "crater",
        "tar", "asphalt", "bridge", "divider", "construction", "roadwork",
        "traffic signal", "street repair", "uneven surface", "speed breaker",
        "asphalt", "concrete", "pedestrian"
    ],
    "Water Supply & Sewage": [
        "water", "sewage", "sewer", "pipeline", "pipe", "pipes", "leak", "leakage",
        "leaking", "drainage", "drain", "drains", "gutter", "dirty water",
        "contamination", "contaminated", "water supply", "water pressure",
        "overflow", "overflowing", "manhole", "manholes", "stagnant water",
        "tap water", "drinking water", "gully trap", "sump"
    ],
    "Street Lighting & Public Safety": [
        "streetlight", "streetlights", "street light", "street lights", "light",
        "lights", "dark", "darkness", "pole", "electric pole", "lamp", "wire",
        "wires", "sparking", "electric", "electrical", "shock", "safety",
        "dark alley", "transformer", "illumination", "short circuit", "cctv",
        "high voltage", "power outage"
    ]
}


def classify_department(text: str) -> Dict[str, Any]:
    """
    Classifies input text into one of the 4 BMC departments based on keyword matching.
    Returns dictionary with predicted category, scores for all categories, and matched keywords.
    """
    if not text or not text.strip():
        return {
            "category": "Solid Waste Management",
            "confidence": 0.0,
            "scores": {dep: 0 for dep in DEPARTMENT_KEYWORDS},
            "matched_keywords": []
        }

    text_lower = text.lower()
    scores: Dict[str, int] = {dep: 0 for dep in DEPARTMENT_KEYWORDS}
    matched_words: Dict[str, List[str]] = {dep: [] for dep in DEPARTMENT_KEYWORDS}

    for department, keywords in DEPARTMENT_KEYWORDS.items():
        for keyword in keywords:
            # Word boundary search for multi-word or single-word matches
            pattern = r'\b' + re.escape(keyword) + r'\b'
            matches = re.findall(pattern, text_lower)
            if matches:
                weight = 2 if " " in keyword else 1  # Multi-word phrases carry slightly higher weight
                score_gain = len(matches) * weight
                scores[department] += score_gain
                matched_words[department].append(keyword)

    # Determine highest scoring department
    max_score = -1
    best_department = "Solid Waste Management"  # Default fallback
    all_matched = []

    for dep, score in scores.items():
        if score > max_score:
            max_score = score
            best_department = dep
            all_matched = matched_words[dep]

    total_score = sum(scores.values())
    confidence = round(max_score / total_score, 2) if total_score > 0 else 0.0

    return {
        "category": best_department,
        "confidence": confidence,
        "scores": scores,
        "matched_keywords": list(set(all_matched))
    }


if __name__ == "__main__":
    # Self-test
    test_cases = [
        "Open manhole near GTB station platform 1 entrance is dangerous",
        "Garbage bins near Punjabi Colony central market are overflowing for 3 days",
        "Sparking electrical wires hanging low near Flank Road bus stop",
        "Massive potholes on GTB Station road causing traffic congestion"
    ]
    for case in test_cases:
        res = classify_department(case)
        print(f"Text: '{case[:45]}...' => Category: {res['category']} (Confidence: {res['confidence']})")
