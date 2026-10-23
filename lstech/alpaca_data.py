"""Intraday prices from Alpaca's market-data API (free plan: SIP history except the last 15 min, IEX in real time).

`load_decision_prices` returns the price at a decision time (default 15:45 ET) for each session since 2016,
as the close of the 15-minute bar that ends then, rescaled to the adjusted (total-return) daily scale so
it can be fed to `strategy.indicators(live=...)`. Needs ALPACA_API_KEY / ALPACA_SECRET_KEY."""
import os
from datetime import datetime, time
from pathlib import Path
import pandas as pd

from .data import CACHE

ET = "America/New_York"


def _client():
    from alpaca.data.historical import StockHistoricalDataClient
    return StockHistoricalDataClient(os.environ["ALPACA_API_KEY"], os.environ["ALPACA_SECRET_KEY"])


def load_bars15(tickers, feed="sip", start="2016-01-01", refresh=False) -> pd.DataFrame:
    """Raw (unadjusted) 15-minute closes, index = bar END time in New York, cached per feed."""
    path = CACHE / f"bars15_{feed}.csv"
    if path.exists() and not refresh:
        px = pd.read_csv(path, index_col=0, parse_dates=True)
        if set(tickers) <= set(px.columns):
            return px[list(tickers)]
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
    from alpaca.data.enums import Adjustment, DataFeed
    req = StockBarsRequest(symbol_or_symbols=list(tickers), timeframe=TimeFrame(15, TimeFrameUnit.Minute),
                           start=pd.Timestamp(start, tz=ET).to_pydatetime(),
                           end=(pd.Timestamp.now(tz="UTC") - pd.Timedelta(minutes=16)).to_pydatetime(),
                           adjustment=Adjustment.RAW, feed=DataFeed(feed))
    df = _client().get_stock_bars(req).df.reset_index()
    df["end"] = pd.to_datetime(df["timestamp"]).dt.tz_convert(ET).dt.tz_localize(None) + pd.Timedelta(minutes=15)
    px = df.pivot(index="end", columns="symbol", values="close").sort_index()
    CACHE.mkdir(exist_ok=True)
    px.to_csv(path)
    return px[list(tickers)]


def load_decision_prices(d: dict, tickers, at=time(15, 45), feed="sip", early_close_at=time(12, 45)) -> pd.DataFrame:
    """Price at `at` on regular days (`early_close_at` on 13:00 half days), adjusted scale.
    `d` is load_daily(); raw->adjusted uses that day's close/raw_close ratio."""
    bars = load_bars15(tickers, feed)
    day = bars.index.normalize()
    last_bar = pd.Series(bars.index, index=bars.index).groupby(day).max()   # 16:00 or 13:00
    want = pd.Series([pd.Timestamp.combine(dd, at if lb.time() >= time(15, 59) else early_close_at)
                      for dd, lb in last_bar.items()], index=last_bar.index)
    # last bar ending at or before the decision time (ffill covers illiquid gaps such as BSV)
    px = bars.sort_index().ffill(limit=8)
    out = px.reindex(want.values, method="ffill")
    out.index = want.index
    ratio = d["close"] / d["raw_close"]
    return (out * ratio.reindex(out.index)).dropna(how="all")
