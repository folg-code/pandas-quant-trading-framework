#TechnicalAnalysis/PriceAction_Fibbonaci/core.py
import numpy as np
import pandas as pd

from TechnicalAnalysis.MarketStructure.engine import MarketStructureEngine
from TechnicalAnalysis.MarketStructure.pivots import PivotDetector, PivotDetectorBatched
from TechnicalAnalysis.MarketStructure.price_action_liquidity import PriceActionLiquidityResponse
from TechnicalAnalysis.MarketStructure.relations import PivotRelations, PivotRelationsBatched
from TechnicalAnalysis.MarketStructure.fibo import FiboCalculator
from TechnicalAnalysis.MarketStructure.price_action import PriceActionStateEngine
from TechnicalAnalysis.MarketStructure.follow_through import PriceActionFollowThrough
from TechnicalAnalysis.MarketStructure.structural_volatility import PriceActionStructuralVolatility
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

        #out.update(self.detect_fibo(df))
        #out.update(self.detect_price_action(df))
        #out.update(self.detect_follow_through(df))
        #out.update(self.detect_price_action_liquidity_response(df))
        #out.update(self.calculate_structural_volatility(df))
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










