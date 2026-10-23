"""Long/Short Tech 1v decision tree. `indicators` builds the inputs (optionally with a live intraday price
for today, as Composer/Alpaca see it before the close), `decide` walks the tree on one row."""
import numpy as np
import pandas as pd
from .config import Config
from .indicators import rsi, rsi_live, sma_live

RSI_COLS = ["QQQ", "SPY", "VIXY", "SQQQ", "BSV"]


def indicators(close: pd.DataFrame, cfg: Config, live: pd.DataFrame = None) -> pd.DataFrame:
    """One row per day. With `live`, day t uses live[t] as today's price (history = closes to t-1)."""
    live = close if live is None else live.reindex_like(close).fillna(close)
    n = cfg.rsi_window
    r = rsi_live(close[RSI_COLS], live[RSI_COLS], n) if live is not close else rsi(close[RSI_COLS], n)
    out = r.add_prefix("rsi_")
    out["spy"], out["qqq"] = live["SPY"], live["QQQ"]
    out["spy_sma"] = sma_live(close[["SPY"]], live[["SPY"]], cfg.spy_sma)["SPY"]
    out["qqq_sma"] = sma_live(close[["QQQ"]], live[["QQQ"]], cfg.qqq_sma)["QQQ"]
    return out


def _qqq_block(x, cfg):
    if x.qqq > x.qqq_sma:
        return cfg.long_asset, "qqq_trend"
    a, b = cfg.short_pair
    return (a, "short") if getattr(x, f"rsi_{a}") >= getattr(x, f"rsi_{b}") else (b, "bonds")


def decide(x: pd.Series, cfg: Config):
    """(asset, branch) for one indicator row."""
    if x.spy > x.spy_sma:
        if x.rsi_QQQ > cfg.qqq_hot or x.rsi_SPY > cfg.spy_hot:
            return cfg.hot_asset, "bull_hot"
        return cfg.long_asset, "bull"
    if x.rsi_QQQ < cfg.qqq_dip:
        return cfg.dip_qqq_asset, "dip_qqq"
    if x.rsi_SPY < cfg.spy_dip:
        return cfg.dip_spy_asset, "dip_spy"
    if x.rsi_VIXY > cfg.vixy_hot:
        if x.rsi_VIXY > cfg.vixy_extreme:
            a, b = _qqq_block(x, cfg)
            return a, "vixy_extreme:" + b
        return cfg.hot_asset, "vixy_spike"
    return _qqq_block(x, cfg)


def signals(close: pd.DataFrame, cfg: Config = None, live: pd.DataFrame = None) -> pd.DataFrame:
    """DataFrame[asset, branch] for every day with complete indicators."""
    cfg = cfg or Config()
    ind = indicators(close, cfg, live).dropna()
    rows = [decide(x, cfg) for x in ind.itertuples(index=False)] if len(ind) else []
    return pd.DataFrame(rows, index=ind.index, columns=["asset", "branch"])


def weights(sig: pd.DataFrame, columns) -> pd.DataFrame:
    w = pd.DataFrame(0.0, index=sig.index, columns=list(columns))
    for a in w.columns:
        w.loc[sig["asset"] == a, a] = 1.0
    return w


def margin(x: pd.Series, cfg: Config) -> float:
    """Smallest distance (RSI points / % of price for the SMAs) between an indicator and a threshold that
    matters on the current path: how much the live reading could move before the decision flips."""
    d = [abs(x.spy / x.spy_sma - 1) * 100]
    if x.spy > x.spy_sma:
        d += [abs(x.rsi_QQQ - cfg.qqq_hot), abs(x.rsi_SPY - cfg.spy_hot)]
    else:
        d += [abs(x.rsi_QQQ - cfg.qqq_dip), abs(x.rsi_SPY - cfg.spy_dip), abs(x.rsi_VIXY - cfg.vixy_hot),
              abs(x.rsi_VIXY - cfg.vixy_extreme), abs(x.qqq / x.qqq_sma - 1) * 100,
              abs(getattr(x, f"rsi_{cfg.short_pair[0]}") - getattr(x, f"rsi_{cfg.short_pair[1]}"))]
    return float(np.min(d))
