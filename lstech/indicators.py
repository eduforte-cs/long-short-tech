import pandas as pd


def wilder_avgs(px: pd.DataFrame, window: int):
    """Wilder-smoothed average gain and loss per column."""
    d = px.diff()
    kw = dict(alpha=1 / window, adjust=False, min_periods=window)
    return d.clip(lower=0).ewm(**kw).mean(), (-d.clip(upper=0)).ewm(**kw).mean()


def rsi(px: pd.DataFrame, window: int) -> pd.DataFrame:
    """Wilder RSI on each column."""
    up, dn = wilder_avgs(px, window)
    return 100 - 100 / (1 + up / dn)


def rsi_live(close: pd.DataFrame, live: pd.DataFrame, window: int) -> pd.DataFrame:
    """RSI on day t if today's price were `live[t]` instead of `close[t]` (history = closes up to t-1)."""
    up, dn = wilder_avgs(close, window)
    a = 1 / window
    d = live - close.shift(1)
    up_l = (1 - a) * up.shift(1) + a * d.clip(lower=0)
    dn_l = (1 - a) * dn.shift(1) + a * (-d.clip(upper=0))
    return 100 - 100 / (1 + up_l / dn_l)


def sma_live(close: pd.DataFrame, live: pd.DataFrame, window: int) -> pd.DataFrame:
    """SMA on day t with today's price `live[t]` in place of `close[t]`."""
    prev = close.shift(1).rolling(window - 1, min_periods=window - 1).sum()
    return (prev + live) / window
