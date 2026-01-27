import numpy as np
import pandas as pd


class PriceActionStateEngineBatched:
    """
    1:1 replica of legacy PriceActionStateEngine.

    Outputs per structure:
    - *_event        : True only on event bar
    - *_level        : price level created by event (ffilled)
    - *_event_idx    : index of event bar (ffilled, state)
    """

    def apply(
        self,
        *,
        pivots: dict[str, pd.Series],
        close: pd.Series,
    ) -> dict[str, pd.Series]:

        idx = close.index

        HH = pivots["HH"]
        LL = pivots["LL"]
        LH = pivots["LH"]
        HL = pivots["HL"]

        # ==========================
        # EVENT DEFINITIONS (1:1)
        # ==========================

        mss_bull_event = (close > LH) & (close.shift(1) <= LH)
        mss_bear_event = (close < HL) & (close.shift(1) >= HL)

        bos_bull_event = (close > HH) & (close.shift(1) <= HH)
        bos_bear_event = (close < LL) & (close.shift(1) >= LL)

        out: dict[str, pd.Series] = {}

        def emit(name: str, event: pd.Series, level: pd.Series):
            event = event.fillna(False)

            out[f"{name}_event"] = event

            lvl = pd.Series(np.nan, index=idx)
            lvl[event] = level[event]
            out[f"{name}_level"] = lvl.ffill()

            eidx = pd.Series(np.nan, index=idx)
            eidx[event] = np.arange(len(idx))[event]
            out[f"{name}_event_idx"] = eidx.ffill()

        # ==========================
        # MSS
        # ==========================
        emit("mss_bull", mss_bull_event, LH)
        emit("mss_bear", mss_bear_event, HL)

        # ==========================
        # BOS
        # ==========================
        emit("bos_bull", bos_bull_event, HH)
        emit("bos_bear", bos_bear_event, LL)

        return out
