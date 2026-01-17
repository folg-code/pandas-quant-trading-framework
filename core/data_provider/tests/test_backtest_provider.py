from __future__ import annotations

from pathlib import Path
import pandas as pd
import pytest

from core.data_provider.cache import MarketDataCache
from core.data_provider.default_provider import DefaultOhlcvDataProvider
from core.data_provider.exceptions import InvalidDataRequest
from core.data_provider.tests.fakes import FakeBackend


@pytest.fixture
def ohlcv_df():
    times = pd.date_range(
        "2024-01-01",
        periods=10,
        freq="5min",
        tz="UTC",
    )
    return pd.DataFrame(
        {
            "time": times,
            "open": range(10),
            "high": range(10),
            "low": range(10),
            "close": range(10),
            "volume": range(10),
        }
    )


@pytest.fixture
def provider(tmp_path: Path, ohlcv_df: pd.DataFrame):
    backend = FakeBackend(ohlcv_df)
    cache = MarketDataCache(tmp_path)

    return DefaultOhlcvDataProvider(
        backend=backend,
        cache=cache,
    )


def test_invalid_request_modes(provider):
    with pytest.raises(InvalidDataRequest):
        provider.get_ohlcv(symbol="EURUSD", timeframe="M5")


def test_backtest_fetch_and_cache(provider):
    start = pd.Timestamp("2024-01-01T00:00:00Z")
    end = pd.Timestamp("2024-01-01T00:25:00Z")

    df1 = provider.get_ohlcv(
        symbol="EURUSD",
        timeframe="M5",
        start=start,
        end=end,
    )

    # second call should hit cache
    df2 = provider.get_ohlcv(
        symbol="EURUSD",
        timeframe="M5",
        start=start,
        end=end,
    )

    assert len(df1) == len(df2)
    assert df1.equals(df2)


def test_backend_called_once(provider):
    start = pd.Timestamp("2024-01-01T00:00:00Z")
    end = pd.Timestamp("2024-01-01T00:25:00Z")

    backend = provider.backend

    provider.get_ohlcv(
        symbol="EURUSD",
        timeframe="M5",
        start=start,
        end=end,
    )
    provider.get_ohlcv(
        symbol="EURUSD",
        timeframe="M5",
        start=start,
        end=end,
    )

    assert len(backend.calls) == 1


def test_informative_timeframe(provider):
    start = pd.Timestamp("2024-01-01T00:00:00Z")
    end = pd.Timestamp("2024-01-01T00:25:00Z")

    df_m5 = provider.get_ohlcv(
        symbol="EURUSD",
        timeframe="M5",
        start=start,
        end=end,
    )

    df_h1 = provider.get_ohlcv(
        symbol="EURUSD",
        timeframe="H1",
        start=start,
        end=end,
    )

    assert not df_m5.empty
    assert not df_h1.empty