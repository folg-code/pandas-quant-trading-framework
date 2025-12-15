import re
import time
from datetime import datetime
import config

TF_MINUTES = {
    "M1": 1,
    "M5": 5,
    "M15": 15,
    "M30": 30,
    "H1": 60,
    "H4": 240,
    "D1": 1440,
}

TIME_MULTIPLIERS = {
    "h": 60,
    "d": 1440,
    "w": 10080,
    "m": 43200,
}


def timeframe_to_minutes(tf: str) -> int:
    if tf not in TF_MINUTES:
        raise ValueError(f"Nieznany TF: {tf}")
    return TF_MINUTES[tf]


def parse_lookback(tf: str, lookback_str: str) -> int:
    """
    Konwertuje lookback w formie '7d' lub '24h' na liczbę świec w danym TF.
    """
    import re

    m = re.match(r"(\d+)([hd])", lookback_str)
    if not m:
        raise ValueError(f"Niepoprawny lookback: {tf}")

    value, unit = m.groups()
    value = int(value)

    if tf.startswith("M"):  # minuty
        tf_min = int(tf[1:])
        if unit == "h":
            return value * 60 // tf_min
        elif unit == "d":
            return value * 24 * 60 // tf_min
    elif tf.startswith("H"):  # godziny
        tf_hour = int(tf[1:])
        if unit == "h":
            return value // tf_hour
        elif unit == "d":
            return value * 24 // tf_hour
    elif tf.startswith("D"):  # dni
        return value
    else:
        raise ValueError(f"Nieobsługiwany timeframe: {tf}")


def wait_for_next_candle(timeframe: str):
    """
    Czeka do zamknięcia kolejnej świecy execution TF
    """
    tf_minutes = {
        "M1": 1,
        "M5": 5,
        "M15": 15,
        "M30": 30,
        "H1": 60,
    }.get(timeframe)

    if tf_minutes is None:
        raise ValueError(f"Nieobsługiwany timeframe: {timeframe}")

    now = datetime.now(config.SERVER_TIMEZONE)
    wait_seconds = (
        tf_minutes * 60
        - ((now.minute % tf_minutes) * 60 + now.second)
    )

    if wait_seconds <= 0:
        wait_seconds = tf_minutes * 60

    time.sleep(wait_seconds + 1)