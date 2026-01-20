def timeframe_to_pandas_freq(timeframe: str) -> str:
    """
    Convert trading timeframe notation (M1, M30, H1, D1)
    to pandas-compatible frequency string.
    """
    tf = timeframe.upper()

    if tf.startswith("M"):
        return f"{int(tf[1:])}min"

    if tf.startswith("H"):
        return f"{int(tf[1:])}H"

    if tf.startswith("D"):
        return f"{int(tf[1:])}D"

    raise ValueError(f"Unsupported timeframe: {timeframe}")