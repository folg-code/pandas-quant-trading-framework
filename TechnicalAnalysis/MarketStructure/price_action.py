import numpy as np
import pandas as pd


class PriceActionStateEngine:
    """
    Price Action detection with explicit EVENT vs STATE separation.

    Outputs per structure:
    - *_event        : True only on event bar
    - *_level        : price level created by event (ffilled)
    - *_event_idx    : index of event bar (ffilled, state)
    """

    def apply(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        idx = df.index
        out = {}

        actions = [
            # MSS
            {
                "name": "mss_bull",
                "cond": (df["close"] > df["LH"]) & (df["close"].shift(1) <= df["LH"]),
                "level": df["LH"],
            },
            {
                "name": "mss_bear",
                "cond": (df["close"] < df["HL"]) & (df["close"].shift(1) >= df["HL"]),
                "level": df["HL"],
            },

            # BOS
            {
                "name": "bos_bull",
                "cond": (df["close"] > df["HH"]) & (df["close"].shift(1) <= df["HH"]),
                "level": df["HH"],
            },
            {
                "name": "bos_bear",
                "cond": (df["close"] < df["LL"]) & (df["close"].shift(1) >= df["LL"]),
                "level": df["LL"],
            },
        ]

        for act in actions:
            name = act["name"]
            cond = act["cond"]

            # ==========================
            # EVENT (impulse)
            # ==========================
            event = cond.astype(bool)

            # ==========================
            # LEVEL CREATED BY EVENT
            # ==========================
            level = pd.Series(
                np.where(cond, act["level"], np.nan),
                index=idx
            ).ffill()

            # ==========================
            # EVENT INDEX (STATEFUL)
            # ==========================
            event_idx = pd.Series(
                np.where(cond, idx, np.nan),
                index=idx
            ).ffill()

            # ==========================
            # COLLECT OUTPUT
            # ==========================
            out[f"{name}_event"] = event
            out[f"{name}_level"] = level
            out[f"{name}_event_idx"] = event_idx

        return out