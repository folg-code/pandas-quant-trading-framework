import pandas as pd
import pytest
from core.strategy.BaseStrategy import BaseStrategy, FixedExitPlan, ManagedExitPlan
from core.strategy.exception import StrategyConfigError


def test_fixed_exit_plan():
    row = pd.Series({
        "signal_entry": {"direction": "long", "tag": "test"},
        "levels": {
            "SL": {"level": 1.0},
            "TP1": {"level": 2.0},
            "TP2": {"level": 3.0},
        },
        "signal_exit": None,
        "custom_stop_loss": None,
        "close": 1.5,
    })

    strat = BaseStrategy(
        df=pd.DataFrame([row]),
        symbol="EURUSD",
        strategy_config={"USE_TRAILING": False}
    )

    plan = strat.build_trade_plan(row=row)

    assert isinstance(plan.exit_plan, FixedExitPlan)

def test_managed_exit_by_trailing():
    row = pd.Series({
        "signal_entry": {"direction": "long", "tag": "test"},
        "levels": {
            "SL": {"level": 1.0},
            "TP1": {"level": 2.0},
            "TP2": {"level": 3.0},
        },
        "signal_exit": None,
        "custom_stop_loss": {"level": 1.2, "reason": "trail"},
        "close": 1.5,
    })

    strat = BaseStrategy(
        df=pd.DataFrame([row]),
        symbol="EURUSD",
        strategy_config={"USE_TRAILING": True}
    )

    plan = strat.build_trade_plan(row=row)

    assert isinstance(plan.exit_plan, ManagedExitPlan)

def test_managed_exit_by_signal_exit():
    row = pd.Series({
        "signal_entry": {"direction": "long", "tag": "test"},
        "levels": {
            "SL": {"level": 1.0},
            "TP1": {"level": 2.0},
            "TP2": {"level": 3.0},
        },
        "signal_exit": {
            "direction": "close",
            "exit_tag": "manual",
            "entry_tag_to_close": "test",
        },
        "custom_stop_loss": None,
        "close": 1.5,
    })

    strat = BaseStrategy(
        df=pd.DataFrame([row]),
        symbol="EURUSD",
        strategy_config={}
    )

    plan = strat.build_trade_plan(row=row)

    assert isinstance(plan.exit_plan, ManagedExitPlan)


def test_invalid_config_trailing_without_tp1():
    with pytest.raises(StrategyConfigError):
        BaseStrategy(
            df=pd.DataFrame(),
            symbol="EURUSD",
            strategy_config={
                "USE_TRAILING": True,
                "TRAIL_FROM": "tp1",
                "USE_TP1": False,
            }
        )