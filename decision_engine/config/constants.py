from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30), name="IST")

def now_ist() -> datetime:
    """Returns the current datetime in Indian Standard Time (IST, UTC+05:30)."""
    return datetime.now(IST)

def now_ist_iso() -> str:
    """Returns the current ISO 8601 formatted timestamp in Indian Standard Time (IST)."""
    return datetime.now(IST).isoformat()

HIGH_CONFIDENCE_THRESHOLD: float = 0.85
MEDIUM_CONFIDENCE_THRESHOLD: float = 0.65

def get_confidence_level(confidence: float) -> str:
    """
    Classifies a numeric confidence score [0.0, 1.0] into HIGH, MEDIUM, or LOW
    based on standardized thresholds (HIGH >= 0.85, MEDIUM >= 0.65).
    """
    if confidence >= HIGH_CONFIDENCE_THRESHOLD:
        return "HIGH"
    elif confidence >= MEDIUM_CONFIDENCE_THRESHOLD:
        return "MEDIUM"
    return "LOW"
