"""
JAN-MANAS Civic Sentiment Engine
Uses NLTK VADER / TextBlob to compute polarity score (-1.0 to +1.0)
and maps it into civic emotional states (Frustrated, Moderate Concern, Neutral/Satisfied)
and sentiment labels (Positive, Neutral, Negative).
"""

import logging
from typing import Dict, Any

logger = logging.getLogger("jan_manas.sentiment_engine")

# Attempt NLTK VADER initialization
_vader_analyzer = None
try:
    import nltk
    from nltk.sentiment.vader import SentimentIntensityAnalyzer
    try:
        nltk.data.find('sentiment/vader_lexicon.zip')
    except LookupError:
        nltk.download('vader_lexicon', quiet=True)
    _vader_analyzer = SentimentIntensityAnalyzer()
    
    # Custom civic domain lexicon adjustments for VADER
    civic_lexicon_updates = {
        'overflowing': -2.5,
        'smell': -1.8,
        'stink': -2.5,
        'pothole': -2.0,
        'sparking': -3.0,
        'hazard': -3.0,
        'filthy': -2.5,
        'dengue': -3.0,
        'mosquitoes': -2.2,
        'broken': -2.0,
        'leaking': -1.8,
        'dark': -1.5,
        'unsafe': -2.5,
        'unbearable': -3.0,
        'resolved': 2.5,
        'prompt': 2.0,
        'clean': 2.0,
        'thank': 2.0,
        'thanks': 2.0,
        'excellent': 2.5,
        'improved': 2.0
    }
    _vader_analyzer.lexicon.update(civic_lexicon_updates)
except Exception as e:
    logger.warning(f"Could not initialize NLTK VADER: {e}")

# Attempt TextBlob import as secondary engine / fallback
_has_textblob = False
try:
    from textblob import TextBlob
    _has_textblob = True
except ImportError:
    _has_textblob = False


def compute_polarity(text: str) -> float:
    """
    Computes a polarity score between -1.0 and +1.0 for given input text.
    Uses NLTK VADER compound score primary, TextBlob polarity secondary,
    with keyword fallback.
    """
    if not text or not text.strip():
        return 0.0

    # 1. Primary: NLTK VADER
    if _vader_analyzer is not None:
        try:
            scores = _vader_analyzer.polarity_scores(text)
            return float(scores.get("compound", 0.0))
        except Exception as e:
            logger.error(f"VADER scoring error: {e}")

    # 2. Secondary: TextBlob
    if _has_textblob:
        try:
            blob = TextBlob(text)
            return float(blob.sentiment.polarity)
        except Exception as e:
            logger.error(f"TextBlob scoring error: {e}")

    # 3. Fallback heuristic keyword scoring
    text_lower = text.lower()
    neg_words = {'overflowing', 'garbage', 'pothole', 'broken', 'smell', 'sparking', 'leak',
                 'dark', 'mosquitoes', 'filthy', 'terrible', 'bad', 'delay', 'danger', 'hazard', 'stink'}
    pos_words = {'good', 'clean', 'thanks', 'thank', 'fixed', 'resolved', 'excellent', 'happy', 'great', 'prompt'}

    neg_count = sum(1 for word in neg_words if word in text_lower)
    pos_count = sum(1 for word in pos_words if word in text_lower)

    if pos_count > neg_count:
        return min(1.0, 0.3 * (pos_count - neg_count))
    elif neg_count > pos_count:
        return max(-1.0, -0.3 * (neg_count - pos_count))
    return 0.0


def map_sentiment_label(score: float) -> str:
    """
    Maps polarity score to Positive, Neutral, or Negative.
    """
    if score > 0.05:
        return "Positive"
    elif score < -0.05:
        return "Negative"
    else:
        return "Neutral"


def map_civic_emotional_state(score: float) -> str:
    """
    Maps polarity score to clear civic emotional states:
    - Frustrated: score <= -0.30
    - Moderate Concern: -0.30 < score < 0.10
    - Neutral/Satisfied: score >= 0.10
    """
    if score <= -0.30:
        return "Frustrated"
    elif score < 0.10:
        return "Moderate Concern"
    else:
        return "Neutral/Satisfied"


def analyze_sentiment(text: str) -> Dict[str, Any]:
    """
    Analyzes civic text feedback and returns sentiment score, sentiment label,
    and civic emotional state.
    """
    score = compute_polarity(text)
    score = max(-1.0, min(1.0, round(score, 4)))
    
    label = map_sentiment_label(score)
    emotional_state = map_civic_emotional_state(score)

    return {
        "sentiment_score": score,
        "sentiment_label": label,
        "emotional_state": emotional_state
    }


if __name__ == "__main__":
    # Self-test
    sample_texts = [
        "Open manhole near GTB station platform 1 entrance is extremely dangerous!",
        "Garbage bins near Punjabi Colony central market are overflowing for 3 days, foul smell spreading everywhere.",
        "Mild water pressure issue during morning hours in Sardar Nagar block B.",
        "Prompt resolution of streetlight complaint near GTB Station west exit. Thank you BMC."
    ]
    for sample in sample_texts:
        res = analyze_sentiment(sample)
        print(f"Text: '{sample[:40]}...' => Score: {res['sentiment_score']}, Label: {res['sentiment_label']}, State: {res['emotional_state']}")
