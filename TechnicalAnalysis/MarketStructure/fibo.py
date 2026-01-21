import numpy as np
import pandas as pd


class FiboCalculator:
    def __init__(
        self,
        pivot_range: int,
        mode: str = "swing",  # "swing" | "range"
        levels: tuple[float, ...] = (0.5, 0.618, 0.66, 1.25, 1.618),
        prefix: str = "fibo",
    ):
        self.pivot_range = pivot_range
        self.mode = mode
        self.levels = levels
        self.prefix = prefix

    def apply(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        if self.mode == "swing":
            return self._fibo_swing(df)
        elif self.mode == "range":
            return self._fibo_range(df)
        else:
            raise ValueError(f"Unknown fibo mode: {self.mode}")

        # ==========================================================
        # MODE A: SWING (last HH/LH vs LL/HL)
        # ==========================================================

    def _fibo_swing(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        idx = df.index

        HH = df.get("HH", pd.Series(np.nan, index=idx))
        LL = df.get("LL", pd.Series(np.nan, index=idx))
        LH = df.get("LH", pd.Series(np.nan, index=idx))
        HL = df.get("HL", pd.Series(np.nan, index=idx))

        HH_idx = df.get("HH_idx", pd.Series(np.nan, index=idx))
        LL_idx = df.get("LL_idx", pd.Series(np.nan, index=idx))
        LH_idx = df.get("LH_idx", pd.Series(np.nan, index=idx))
        HL_idx = df.get("HL_idx", pd.Series(np.nan, index=idx))

        # 1️⃣ last_low / last_high (1:1 jak w starym kodzie)
        last_low = np.where(LL_idx > HL_idx, LL, HL)
        last_high = np.where(HH_idx > LH_idx, HH, LH)

        last_low = pd.Series(last_low, index=idx)
        last_high = pd.Series(last_high, index=idx)

        rise = last_high - last_low

        cond_up = last_low < last_high
        cond_down = ~cond_up

        out = {}

        for coeff in self.levels:
            key = str(coeff).replace(".", "")

            bull = last_high - rise * coeff
            bear = last_low + rise * coeff

            out[f"{self.prefix}_{key}"] = bull.where(cond_up)
            out[f"{self.prefix}_{key}_bear"] = bear.where(cond_down)

        return out

        # ==========================================================
        # MODE B: RANGE / STRUCTURAL (HH vs LAST VALID LL)
        # ==========================================================

    def _fibo_range(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        idx = df.index

        HH = df.get("HH", pd.Series(np.nan, index=idx))
        LL = df.get("LL", pd.Series(np.nan, index=idx))
        HH_idx = df.get("HH_idx", pd.Series(np.nan, index=idx))
        LL_idx = df.get("LL_idx", pd.Series(np.nan, index=idx))

        # 1️⃣ wybór LL: ostatnie LL z indeksem < HH_idx
        valid_LL = LL.where(LL_idx < HH_idx)
        base_LL = valid_LL.ffill()

        rise = HH - base_LL

        out = {}

        for coeff in self.levels:
            key = str(coeff).replace(".", "")

            # retracement
            out[f"{self.prefix}_{key}"] = HH - rise * coeff

            # extension
            if coeff > 1:
                out[f"{self.prefix}_ext_{key}"] = HH + rise * (coeff - 1)

        return out