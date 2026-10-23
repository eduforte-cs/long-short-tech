"""Vectorized close-to-close engine (Composer-style) and performance stats."""
import numpy as np
import pandas as pd


def run(w: pd.DataFrame, close: pd.DataFrame, lag: int = 0, cost_bps: float = 0.0) -> pd.Series:
    """Weights decided on day t earn close t+lag -> t+lag+1. lag 0 = trade at the signal's own close."""
    R = close.pct_change().reindex(index=w.index, columns=w.columns).fillna(0.0)
    held = w.shift(1 + lag).fillna(0.0)
    turnover = held.diff().abs().sum(axis=1).fillna(held.abs().sum(axis=1))
    return ((held * R).sum(axis=1) - turnover * cost_bps / 1e4).iloc[1 + lag:]


def stats(r: pd.Series) -> dict:
    r = r.dropna()
    eq = (1 + r).cumprod()
    yrs = len(r) / 252
    cagr = eq.iloc[-1] ** (1 / yrs) - 1
    vol = r.std() * np.sqrt(252)
    dd = eq / eq.cummax() - 1
    downside = r[r < 0].std() * np.sqrt(252)
    return {
        "Total": eq.iloc[-1] - 1,
        "CAGR": cagr,
        "Vol": vol,
        "Sharpe": r.mean() * 252 / vol if vol else np.nan,
        "Sortino": r.mean() * 252 / downside if downside else np.nan,
        "MaxDD": dd.min(),
        "Calmar": cagr / -dd.min() if dd.min() < 0 else np.nan,
        "Worst day": r.min(),
    }


def table(series: dict) -> pd.DataFrame:
    t = pd.DataFrame({k: stats(v) for k, v in series.items()}).T
    pct = ["Total", "CAGR", "Vol", "MaxDD", "Worst day"]
    out = t.copy().astype(object)
    for c in t.columns:
        out[c] = t[c].map(lambda v: f"{v:.1%}" if c in pct else f"{v:.2f}")
    return out
