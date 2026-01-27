import numpy as np
import pandas as pd


class FiboBatched:
    def __init__(
        self,
        *,
        pivot_range: int,
        mode: str = "swing",
        levels: tuple[float, ...] = (0.5, 0.618, 0.66, 1.25, 1.618),
        prefix: str = "fibo",
    ):
        self.pivot_range = pivot_range
        self.mode = mode
        self.levels = levels
        self.prefix = prefix

    def apply(
        self,
        *,
        pivots: dict[str, pd.Series],
    ) -> dict[str, pd.Series]:

        if self.mode == "swing":
            return self._fibo_swing(pivots)
        elif self.mode == "range":
            return self._fibo_range(pivots)
        else:
            raise ValueError(f"Unknown fibo mode: {self.mode}")

    def _fibo_swing(
            self,
            pivots: dict[str, pd.Series]
    ) -> dict[str, pd.Series]:

        idx = pivots["HH"].index

        HH = pivots["HH"]
        LL = pivots["LL"]
        LH = pivots["LH"]
        HL = pivots["HL"]

        HH_idx = pivots["HH_idx"]
        LL_idx = pivots["LL_idx"]
        LH_idx = pivots["LH_idx"]
        HL_idx = pivots["HL_idx"]

        last_low = np.where(LL_idx > HL_idx, LL, HL)
        last_high = np.where(HH_idx > LH_idx, HH, LH)

        last_low = pd.Series(last_low, index=idx)
        last_high = pd.Series(last_high, index=idx)

        rise = last_high - last_low

        cond_up = last_low < last_high
        cond_down = ~cond_up

        out: dict[str, pd.Series] = {}

        for coeff in self.levels:
            key = str(coeff).replace(".", "")

            bull = last_high - rise * coeff
            bear = last_low + rise * coeff

            out[f"{self.prefix}_{key}"] = bull.where(cond_up)
            out[f"{self.prefix}_{key}_bear"] = bear.where(cond_down)

        return out

    def _fibo_range(
            self,
            pivots: dict[str, pd.Series]
    ) -> dict[str, pd.Series]:

        HH = pivots["HH"]
        LL = pivots["LL"]
        HH_idx = pivots["HH_idx"]
        LL_idx = pivots["LL_idx"]

        valid_LL = LL.where(LL_idx < HH_idx)
        base_LL = valid_LL.ffill()

        rise = HH - base_LL

        out: dict[str, pd.Series] = {}

        for coeff in self.levels:
            key = str(coeff).replace(".", "")

            out[f"{self.prefix}_{key}"] = HH - rise * coeff

            if coeff > 1:
                out[f"{self.prefix}_ext_{key}"] = HH + rise * (coeff - 1)

        return out