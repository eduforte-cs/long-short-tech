import numpy as np
import pandas as pd
import pytest
from lstech.config import UNIVERSE, Config
from lstech.strategy import decide, signals, weights
from lstech.indicators import rsi, rsi_live, sma_live
from lstech import backtest as bt
from lstech.alpaca_sim import simulate, SimConfig


def row(**kw):
    base = dict(spy=100, spy_sma=90, qqq=100, qqq_sma=95, rsi_QQQ=50, rsi_SPY=50, rsi_VIXY=50,
                rsi_SQQQ=50, rsi_BSV=40)
    base.update(kw)
    return pd.Series(base)


@pytest.mark.parametrize("kw,expected", [
    ({}, ("QQQ", "bull")),
    ({"rsi_QQQ": 80}, ("VIXY", "bull_hot")),
    ({"rsi_SPY": 81}, ("VIXY", "bull_hot")),          # "Any of"
    ({"spy": 80, "rsi_QQQ": 30}, ("XLK", "dip_qqq")),
    ({"spy": 80, "rsi_SPY": 29}, ("SPY", "dip_spy")),
    ({"spy": 80, "rsi_VIXY": 80}, ("VIXY", "vixy_spike")),
    ({"spy": 80, "rsi_VIXY": 90}, ("QQQ", "vixy_extreme:qqq_trend")),
    ({"spy": 80, "rsi_VIXY": 90, "qqq": 90}, ("SQQQ", "vixy_extreme:short")),
    ({"spy": 80, "qqq": 90}, ("SQQQ", "short")),
    ({"spy": 80, "qqq": 90, "rsi_BSV": 60}, ("BSV", "bonds")),
    ({"spy": 80}, ("QQQ", "qqq_trend")),
])
def test_tree(kw, expected):
    assert decide(row(**kw), Config()) == expected


def fake_prices(n=400, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2020-01-01", periods=n)
    px = pd.DataFrame(100 * np.exp(np.cumsum(rng.normal(0, 0.02, (n, len(UNIVERSE))), axis=0)),
                      index=idx, columns=UNIVERSE)
    return {"close": px, "open": px * (1 + rng.normal(0, 0.003, px.shape)),
            "raw_close": px * 2, "raw_open": None}


def test_live_equals_close_when_live_is_close():
    d = fake_prices()
    a, b = signals(d["close"]), signals(d["close"], live=d["close"])
    pd.testing.assert_frame_equal(a, b)


def test_live_indicators():
    c = fake_prices()["close"][["SPY"]]
    pd.testing.assert_frame_equal(rsi_live(c, c, 10).iloc[30:], rsi(c, 10).iloc[30:])
    pd.testing.assert_frame_equal(sma_live(c, c, 20).iloc[30:], c.rolling(20).mean().iloc[30:])


def test_ideal_simulation_matches_vectorized():
    d = fake_prices()
    d["raw_open"] = d["open"] * 2
    s = signals(d["close"])
    vec = bt.run(weights(s, UNIVERSE), d["close"])
    o, _ = simulate(s["asset"], d, SimConfig(whole_shares=False, fees=False, slip_bps=0, invest=1))
    np.testing.assert_allclose(o["ret"].iloc[1:].values, vec.values, atol=1e-12)


def test_whole_shares_leave_cash():
    d = fake_prices()
    d["raw_open"] = d["open"] * 2
    s = signals(d["close"])
    o, tl = simulate(s["asset"], d, SimConfig())
    buys = tl[tl.side == "buy"]
    assert (buys.shares == buys.shares.round()).all()
    assert (o["cash"] > -0.02 * o["equity"]).all()
