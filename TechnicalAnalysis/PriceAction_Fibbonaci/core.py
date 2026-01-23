#TechnicalAnalysis/PriceAction_Fibbonaci/core.py
import numpy as np
import pandas as pd

from TechnicalAnalysis.MarketStructure.engine import MarketStructureEngine
from TechnicalAnalysis.MarketStructure.pivots import PivotDetector, PivotDetectorBatched
from TechnicalAnalysis.MarketStructure.price_action_liquidity import PriceActionLiquidityResponse, \
    PriceActionLiquidityResponseBatched
from TechnicalAnalysis.MarketStructure.relations import PivotRelations, PivotRelationsBatched
from TechnicalAnalysis.MarketStructure.fibo import FiboCalculator, FiboBatched
from TechnicalAnalysis.MarketStructure.price_action import PriceActionStateEngine, PriceActionStateEngineBatched
from TechnicalAnalysis.MarketStructure.follow_through import PriceActionFollowThrough, PriceActionFollowThroughBatched
from TechnicalAnalysis.MarketStructure.structural_volatility import PriceActionStructuralVolatility, \
    PriceActionStructuralVolatilityBatched
from TechnicalAnalysis.MarketStructure.trend_regime import PriceActionTrendRegime


class IntradayMarketStructure:
    """
    Deterministic intraday market structure pipeline.

    Responsibilities:
    - compute structural features (pivots, PA, liquidity, volatility, regime)
    - NO signals
    - NO execution logic
    - NO experimental features
    """

    def __init__(
        self,
        pivot_range: int = 15,
        min_percentage_change: float = 0.01,
        use_engine: bool = False,
    ):
        self.pivot_range = pivot_range
        self.min_percentage_change = min_percentage_change
        self.use_engine = use_engine

        # =========================
        # FIBO DEFINITIONS
        # =========================
        self.fibo_swing = FiboCalculator(
            pivot_range=pivot_range,
            mode="swing",
            prefix="fibo_swing",
        )

        self.fibo_range = FiboCalculator(
            pivot_range=pivot_range,
            mode="range",
            prefix="fibo_range",
        )

        # =========================
        # PRICE ACTION
        # =========================
        self.price_action_engine = PriceActionStateEngine()

        # =========================
        # ENGINE (PARTIAL, FUTURE)
        # =========================
        self.engine = MarketStructureEngine(
            pivot_detector=PivotDetector(self.pivot_range),
            relations=PivotRelations(),
            fibo=None,
            price_action=None,
        )

    # =============================================================
    # PUBLIC ENTRYPOINT
    # =============================================================
    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        if self.use_engine:
            return self.apply_engine(df)
        return self.apply_legacy(df)

    # =============================================================
    # LEGACY PIPELINE (CLEAN, BATCH)
    # =============================================================
    def apply_legacy(self, df: pd.DataFrame) -> pd.DataFrame:
        out: dict[str, pd.Series] = {}



        def equal_series(a: pd.Series, b: pd.Series) -> bool:
            return (
                a.fillna(-1).astype(int)
                .equals(
                    b.fillna(-1).astype(int)
                )
            )

        def eq(a, b):
            return a.fillna(-1).equals(b.fillna(-1))

        # legacy
        pivots_legacy = PivotDetector(self.pivot_range).apply(df)
        df_legacy = df.assign(**pivots_legacy)
        relations_legacy = PivotRelations().apply(df_legacy)

        # batched
        pivots_batched = PivotDetectorBatched(self.pivot_range).apply(df)
        relations_batched = PivotRelationsBatched().apply(
            pivots=pivots_batched,
            atr=df["atr"]
        )

        # compare
        for k in relations_legacy:
            assert equal_series(relations_legacy[k], relations_batched[k]), k

        print("COLUMNS SAME")

        legacy = FiboCalculator(
            pivot_range=self.pivot_range,
            mode="swing",
            prefix="fibo_swing",
        ).apply(df.assign(**pivots_legacy))

        batched = FiboBatched(
            pivot_range=self.pivot_range,
            mode="swing",
            prefix="fibo_swing",).apply(pivots=pivots_batched)

        for k in legacy:
            assert eq(legacy[k], batched[k]), k

        print("FIBO SAME")

        legacy_out = PriceActionStateEngine().apply(df_legacy)

        df_legacy = df_legacy.assign(**legacy_out)

        batched_out = PriceActionStateEngineBatched().apply(
            pivots=pivots_legacy,
            close=df["close"],
        )

        for k in legacy_out:
            assert eq(legacy_out[k], batched_out[k]), k

        print("PRICE ACTION STATE ENGINE: 1:1 OK")

        # ===== legacy =====

        print(df_legacy)
        legacy = PriceActionFollowThrough(event_source="bos").apply(df_legacy)

        batched = PriceActionFollowThroughBatched(
            event_source="bos",
            atr_mult=1.0,
            lookahead=5,
        ).apply(
            events={
                "bos_bull_event": batched_out["bos_bull_event"],
                "bos_bear_event": batched_out["bos_bear_event"],
            },
            levels={
                "bos_bull_level": batched_out["bos_bull_level"],
                "bos_bear_level": batched_out["bos_bear_level"],
            },
            high=df["high"],
            low=df["low"],
            atr=df["atr"],
        )

        for k in legacy:
            assert eq(legacy[k], batched[k]), k

        print("FOLLOW THROUGH BATCHED: 1:1 OK")


        legacy = PriceActionLiquidityResponse(
            event_source="bos",
            direction="bull",
        ).apply(df_legacy)

        batched = PriceActionLiquidityResponseBatched(
            event_source="bos",
            direction="bull",
        ).apply(
            events={
                "bos_bull_event": batched_out["bos_bull_event"],
            },
            levels={
                "bos_bull_level": batched_out["bos_bull_level"],
            },
            df=df,
        )


        for k in legacy:
            assert eq(legacy[k], batched[k]), k

        print("LIQUIDITY RESPONSE BATCHED: 1:1 OK")

        legacy = PriceActionStructuralVolatility(
            event_source="bos",
            direction="bull",
        ).apply(df_legacy)

        batched = PriceActionStructuralVolatilityBatched(
            event_source="bos",
            direction="bull",
        ).apply(
            events={
                "bos_bull_event": batched_out["bos_bull_event"],
            },
            df=df,
        )

        for k in legacy:
            assert legacy[k].fillna(-1).equals(batched[k].fillna(-1)), k

        print("STRUCTURAL VOLATILITY BATCHED: 1:1 OK")

        #out.update(self.detect_trend_regime(df))

        return df.assign(**out)

    # =============================================================
    # ENGINE PIPELINE (PLACEHOLDER)
    # =============================================================
    def apply_engine(self, df: pd.DataFrame) -> pd.DataFrame:
        out = self.engine.apply(df)
        return df.assign(**out)

    # =============================================================
    # DETECTORS (PURE FUNCTIONS)
    # =============================================================
    def detect_peaks(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        return PivotDetector(self.pivot_range).apply(df)

    def detect_eqh_eql_from_pivots(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        return PivotRelations().apply(df)

    def detect_fibo(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        out: dict[str, pd.Series] = {}
        out.update(self.fibo_swing.apply(df))
        out.update(self.fibo_range.apply(df))
        return out

    def detect_price_action(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        return self.price_action_engine.apply(df)

    def detect_follow_through(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        out: dict[str, pd.Series] = {}
        out.update(PriceActionFollowThrough("bos").apply(df))
        out.update(PriceActionFollowThrough("mss").apply(df))
        return out

    def detect_price_action_liquidity_response(
        self,
        df: pd.DataFrame,
    ) -> dict[str, pd.Series]:
        out: dict[str, pd.Series] = {}

        for src in ("bos", "mss"):
            for side in ("bull", "bear"):
                liq = PriceActionLiquidityResponse(
                    event_source=src,
                    direction=side,
                )
                out.update(liq.apply(df))

        return out

    def calculate_structural_volatility(
        self,
        df: pd.DataFrame,
    ) -> dict[str, pd.Series]:
        out: dict[str, pd.Series] = {}

        for src in ("bos", "mss"):
            for side in ("bull", "bear"):
                sv = PriceActionStructuralVolatility(
                    event_source=src,
                    direction=side,
                )
                out.update(sv.apply(df))

        return out

    def detect_trend_regime(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        return PriceActionTrendRegime().apply(df)










