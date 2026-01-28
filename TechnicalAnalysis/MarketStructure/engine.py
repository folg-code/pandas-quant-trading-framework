import pandas as pd

from TechnicalAnalysis.MarketStructure.fibo import FiboBatched
from TechnicalAnalysis.MarketStructure.follow_through import PriceActionFollowThroughBatched
from TechnicalAnalysis.MarketStructure.pivots import PivotDetectorBatched
from TechnicalAnalysis.MarketStructure.price_action import PriceActionStateEngineBatched

from TechnicalAnalysis.MarketStructure.price_action_liquidity import PriceActionLiquidityResponseBatched
from TechnicalAnalysis.MarketStructure.relations import PivotRelationsBatched
from TechnicalAnalysis.MarketStructure.structural_volatility import PriceActionStructuralVolatilityBatched
from TechnicalAnalysis.MarketStructure.trend_regime import PriceActionTrendRegimeBatched


class _Modules:
    """
    Single source of truth for concrete implementations.
    """

    pivot_detector = PivotDetectorBatched
    relations = PivotRelationsBatched
    fibo = FiboBatched
    price_action = PriceActionStateEngineBatched
    follow_through = PriceActionFollowThroughBatched
    liquidity = PriceActionLiquidityResponseBatched
    structural_vol = PriceActionStructuralVolatilityBatched
    trend_regime = PriceActionTrendRegimeBatched


class MarketStructureEngine:
    """
    Deterministic, dependency-aware market structure engine.

    User controls WHAT is computed.
    Engine controls HOW it is computed.
    """

    FEATURE_DEPENDENCIES = {
        "pivots": [],
        "relations": ["pivots"],
        "fibo": ["pivots"],
        "price_action": ["pivots"],
        "follow_through": ["price_action"],
        "liquidity": ["price_action", "follow_through"],
        "structural_vol": ["price_action"],
        "trend_regime": ["pivots", "price_action", "structural_vol", "follow_through"],
    }

    # =============================================================
    # PUBLIC ENTRYPOINT
    # =============================================================
    @classmethod
    def apply(
        cls,
        df: pd.DataFrame,
        *,
        features: list[str],
        pivot_range: int = 15,
        return_context: bool = False,
    ):
        cls._validate_features(features)
        cls._validate_dependencies(features)

        out: dict[str, pd.Series] = {}
        context: dict[str, dict] = {}

        M = _Modules

        # =========================================================
        # 1️⃣ PIVOTS
        # =========================================================
        if "pivots" in features:
            pivots = M.pivot_detector(pivot_range).apply(df)
            context["pivots"] = pivots
        else:
            pivots = None

        # =========================================================
        # 2️⃣ RELATIONS
        # =========================================================
        if "relations" in features:
            rel = M.relations().apply(
                pivots=pivots,
                atr=df["atr"],
            )
            out.update(rel)

        # =========================================================
        # 3️⃣ FIBO
        # =========================================================
        if "fibo" in features:
            fibo = M.fibo(
                pivot_range=pivot_range,
                mode="swing",
                prefix="fibo_swing",
            ).apply(pivots=pivots)

            fibo.update(
                M.fibo(
                    pivot_range=pivot_range,
                    mode="range",
                    prefix="fibo_range",
                ).apply(pivots=pivots)
            )
            context["fibo"] = fibo

        # =========================================================
        # 4️⃣ PRICE ACTION
        # =========================================================
        if "price_action" in features:
            pa = M.price_action().apply(
                pivots=pivots,
                close=df["close"],
            )
            context["price_action"] = pa
            out.update(pa)
        else:
            pa = None

        # =========================================================
        # 5️⃣ FOLLOW THROUGH
        # =========================================================
        if "follow_through" in features:
            ft = {}
            for src in ("bos", "mss"):
                ft[src] = M.follow_through(
                    event_source=src,
                ).apply(
                    events=pa,
                    levels=pa,
                    high=df["high"],
                    low=df["low"],
                    atr=df["atr"],
                )
                out.update(ft[src])

            context["follow_through"] = ft
        else:
            ft = None

        # =========================================================
        # 6️⃣ LIQUIDITY RESPONSE
        # =========================================================
        if "liquidity" in features:
            for src in ("bos", "mss"):
                for side in ("bull", "bear"):
                    out.update(
                        M.liquidity(
                            event_source=src,
                            direction=side,
                        ).apply(
                            events=pa,
                            levels=pa,
                            follow_through=ft[src],
                            df=df,
                        )
                    )

        # =========================================================
        # 7️⃣ STRUCTURAL VOLATILITY
        # =========================================================
        if "structural_vol" in features:
            sv = {}
            for src in ("bos", "mss"):
                for side in ("bull", "bear"):
                    part = M.structural_vol(
                        event_source=src,
                        direction=side,
                    ).apply(
                        events=pa,
                        df=df,
                    )
                    sv.update(part)
                    out.update(part)

            context["structural_vol"] = sv

        else:
            sv = None

        # =========================================================
        # 8️⃣ TREND REGIME
        # =========================================================
        if "trend_regime" in features:
            trend = M.trend_regime().apply(
                pivots={"pivot": pivots["pivot"]},
                events=pa,
                struct_vol=sv,
                follow_through=ft,
                df=df,
            )
            out.update(trend)

        df_out = df.copy()
        for k, v in out.items():
            df_out[k] = v

        return (df_out, context) if return_context else df_out

    # =============================================================
    # VALIDATION
    # =============================================================
    @classmethod
    def _validate_features(cls, features: list[str]):
        unknown = set(features) - set(cls.FEATURE_DEPENDENCIES)
        if unknown:
            raise ValueError(f"Unknown features requested: {sorted(unknown)}")

    @classmethod
    def _validate_dependencies(cls, features: list[str]):
        enabled = set(features)
        for feat in features:
            for dep in cls.FEATURE_DEPENDENCIES[feat]:
                if dep not in enabled:
                    raise ValueError(
                        f"Feature '{feat}' requires '{dep}' "
                        f"but it is not enabled."
                    )
