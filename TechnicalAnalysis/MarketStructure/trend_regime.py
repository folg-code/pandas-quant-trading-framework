import pandas as pd


class PriceActionTrendRegimeBatched:
    """
    1:1 batched version of PriceActionTrendRegime.

    Semantics preserved:
    - identical bias accumulation
    - identical volatility gating
    - identical regime resolution

    FIXES:
    - safe defaults for missing struct_vol series
    - explicit NaN → False normalization for high_vol
    """

    def __init__(self, vol_required: bool = True):
        self.vol_required = vol_required

    def apply(
        self,
        *,
        pivots: dict[str, pd.Series],
        events: dict[str, pd.Series],
        struct_vol: dict[str, pd.Series],
        follow_through: dict[str, pd.Series],
        df: pd.DataFrame,
    ) -> dict[str, pd.Series]:

        idx = df.index

        # =====================================================
        # 1️⃣ STRUCTURAL BIAS (PIVOT-BASED)  ✅ FINAL FIX
        # =====================================================
        pivot_state = pivots["pivot"]

        bullish_structure = (pivot_state == 3) | (pivot_state == 6)
        bearish_structure = (pivot_state == 4) | (pivot_state == 5)

        struct_bias = pd.Series(0, index=idx)
        struct_bias[bullish_structure] = 1
        struct_bias[bearish_structure] = -1
        struct_bias = struct_bias.ffill().fillna(0)

        # =====================================================
        # 2️⃣ EVENT DOMINANCE (BOS / MSS)
        # =====================================================
        bull_events = (
            events.get("bos_bull_event", pd.Series(False, index=idx))
            | events.get("mss_bull_event", pd.Series(False, index=idx))
        )

        bear_events = (
            events.get("bos_bear_event", pd.Series(False, index=idx))
            | events.get("mss_bear_event", pd.Series(False, index=idx))
        )

        event_bias = pd.Series(0, index=idx)
        event_bias[bull_events] = 1
        event_bias[bear_events] = -1
        event_bias = event_bias.ffill().fillna(0)

        # =====================================================
        # 3️⃣ FOLLOW-THROUGH CONFIRMATION
        # =====================================================
        bull_ft = (
            follow_through.get("bos_bull_ft_valid", pd.Series(False, index=idx))
            | follow_through.get("mss_bull_ft_valid", pd.Series(False, index=idx))
        )

        bear_ft = (
            follow_through.get("bos_bear_ft_valid", pd.Series(False, index=idx))
            | follow_through.get("mss_bear_ft_valid", pd.Series(False, index=idx))
        )

        ft_bias = pd.Series(0, index=idx)
        ft_bias[bull_ft] = 1
        ft_bias[bear_ft] = -1
        ft_bias = ft_bias.ffill().fillna(0)

        # =====================================================
        # 4️⃣ STRUCTURAL VOLATILITY FILTER  ✅ FIXED
        # =====================================================
        if self.vol_required:
            high_vol = (
                (struct_vol.get("bos_bull_struct_vol", pd.Series(False, index=idx)) == "high")
                | (struct_vol.get("bos_bear_struct_vol", pd.Series(False, index=idx)) == "high")
                | (struct_vol.get("mss_bull_struct_vol", pd.Series(False, index=idx)) == "high")
                | (struct_vol.get("mss_bear_struct_vol", pd.Series(False, index=idx)) == "high")
            )

            # 🔒 CRITICAL: legacy-equivalent semantics
            high_vol = high_vol.fillna(False)
        else:
            high_vol = pd.Series(True, index=idx)

        # =====================================================
        # 5️⃣ FINAL REGIME DECISION
        # =====================================================
        trend_bias = struct_bias + event_bias + ft_bias

        regime = pd.Series("range", index=idx)

        # potem trendy (nadpisują transition)
        regime[(trend_bias >= 1) & high_vol] = "trend_up"
        regime[(trend_bias <= -1) & high_vol] = "trend_down"

        # najpierw transition
        regime[(trend_bias.abs() >= 1) & ~high_vol] = "transition"

        # =====================================================
        # 6️⃣ STRENGTH (NORMALIZED)
        # =====================================================
        trend_strength = (trend_bias.abs() / 3.0).clip(0, 1)

        return {
            "trend_regime": regime,
            "trend_bias": trend_bias,
            "trend_strength": trend_strength,
        }