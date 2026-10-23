"""Yahoo daily data, cached in data/. `close`/`open` are split+dividend adjusted (total return);
`raw_close`/`raw_open` are the prices actually printed that day (needed for whole-share sizing)."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import yfinance as yf

CACHE = Path(__file__).resolve().parent.parent / "data"
FIELDS = ("close", "open", "raw_close", "raw_open")


def _download(t, start):
    adj = yf.download(t, start=start, auto_adjust=True, progress=False, threads=False)
    if adj.empty:
        raise RuntimeError(f"no data for {t}")
    adj = adj.droplevel(1, axis=1) if isinstance(adj.columns, pd.MultiIndex) else adj
    splits = yf.Ticker(t).splits
    splits.index = splits.index.tz_localize(None).normalize()
    # Yahoo's adjusted prices are split-adjusted backwards; undo it with the splits that happened later.
    factor = pd.Series(1.0, index=adj.index)
    for d, ratio in splits.items():
        factor[adj.index < d] *= ratio
    raw = yf.download(t, start=start, auto_adjust=False, progress=False, threads=False)
    raw = raw.droplevel(1, axis=1) if isinstance(raw.columns, pd.MultiIndex) else raw
    return {"close": adj["Close"], "open": adj["Open"],
            "raw_close": raw["Close"].reindex(adj.index) * factor,
            "raw_open": raw["Open"].reindex(adj.index) * factor}


def complete(df: pd.DataFrame) -> pd.DataFrame:
    """Drop today's row while the session is still running (Yahoo serves a partial bar)."""
    now = datetime.now(ZoneInfo("America/New_York"))
    if len(df) and df.index[-1].date() == now.date() and (now.hour, now.minute) < (16, 30):
        return df.iloc[:-1]
    return df


def load_daily(tickers, start="1999-01-01", refresh=False) -> dict:
    """{field: DataFrame[date x ticker]} for FIELDS, completed sessions only."""
    paths = {f: CACHE / f"daily_{f}.csv" for f in FIELDS}
    if not refresh and all(p.exists() for p in paths.values()):
        out = {f: pd.read_csv(p, index_col=0, parse_dates=True) for f, p in paths.items()}
        if set(tickers) <= set(out["close"].columns):
            return {f: complete(d[list(tickers)]) for f, d in out.items()}
    CACHE.mkdir(exist_ok=True)
    yf.set_tz_cache_location(str(CACHE / "tz"))
    per = {t: _download(t, start) for t in sorted(set(tickers))}  # one at a time: yfinance cache locks
    out = {f: pd.DataFrame({t: per[t][f] for t in per}).sort_index() for f in FIELDS}
    for f, d in out.items():
        d.to_csv(paths[f])
    return {f: complete(d[list(tickers)]) for f, d in out.items()}


def load_hourly(tickers, refresh=False) -> dict:
    """60-minute bars for the last ~730 days (Yahoo's limit), New York time, {'open','close'}."""
    paths = {f: CACHE / f"hourly_{f}.csv" for f in ("open", "close")}
    if not refresh and all(p.exists() for p in paths.values()):
        out = {f: pd.read_csv(p, index_col=0, parse_dates=True) for f, p in paths.items()}
        if set(tickers) <= set(out["close"].columns):
            return {f: d[list(tickers)] for f, d in out.items()}
    CACHE.mkdir(exist_ok=True)
    yf.set_tz_cache_location(str(CACHE / "tz"))
    frames = {f: {} for f in paths}
    for t in sorted(set(tickers)):
        df = yf.download(t, period="730d", interval="60m", auto_adjust=True, progress=False, threads=False)
        df = df.droplevel(1, axis=1) if isinstance(df.columns, pd.MultiIndex) else df
        for f in frames:
            frames[f][t] = df[f.capitalize()]
    out = {}
    for f, d in frames.items():
        x = pd.DataFrame(d).sort_index()
        x.index = x.index.tz_convert("America/New_York").tz_localize(None)
        x.to_csv(paths[f])
        out[f] = x
    return out
