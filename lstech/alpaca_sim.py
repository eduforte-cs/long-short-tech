"""Day-by-day simulation of the strategy as an Alpaca account would trade it.

- One asset at a time; trades only when the target asset changes.
- MOC: decision on day t with the price seen at decision time (`live`, e.g. 15:45 ET), filled at the official
  close of t. OPG: decision with the close of t, filled at the opening auction of t+1.
- Whole shares (Alpaca has no fractional MOC/OPG orders), sized with the price known when the order is sent;
  the rest stays in cash at 0%. Requires a margin account: the buy is sent together with the sell, and
  a fill above the sizing price can push cash slightly negative.
- Costs: `slip_bps` per side on the auction price, SEC fee on sell notional, FINRA TAF per share sold.
- Positions are carried in total-return units (adjusted prices), so dividends are reinvested in the position.
"""
from dataclasses import dataclass
import numpy as np
import pandas as pd

SEC_FEE = 27.80 / 1e6          # $ per $ sold (conservative: last non-zero rate)
TAF, TAF_MAX = 0.000166, 8.30  # $ per share sold, cap per trade


@dataclass
class SimConfig:
    mode: str = "moc"           # "moc" or "opg"
    capital: float = 10_000.0
    invest: float = 0.99        # fraction of available cash used to size the buy
    slip_bps: float = 3.0
    whole_shares: bool = True
    fees: bool = True


def simulate(asset: pd.Series, d: dict, cfg: SimConfig = SimConfig(), live_raw: pd.DataFrame = None):
    """`asset[t]`: target decided on day t. `d`: load_daily() dict. `live_raw`: raw price used to size MOC orders
    (defaults to the close). Returns (daily DataFrame with equity/asset/trade flags, trade log)."""
    adj_c, adj_o, raw_c, raw_o = d["close"], d["open"], d["raw_close"], d["raw_open"]
    idx = asset.index
    size_px = raw_c if live_raw is None else live_raw.reindex_like(raw_c).fillna(raw_c)
    cash, held, units = cfg.capital, None, 0.0
    rows, trades = [], []
    slip = cfg.slip_bps / 1e4

    def sell(px_adj, px_raw, day):
        nonlocal cash, units
        notional = units * px_adj
        shares = notional / px_raw
        fee = (notional * SEC_FEE + min(shares * TAF, TAF_MAX)) if cfg.fees else 0.0
        cash += notional * (1 - slip) - fee
        trades.append((day, "sell", held, shares, px_raw, notional, fee + notional * slip))
        units = 0.0

    def buy(a, px_adj, px_raw, sizing_px, day):
        nonlocal cash, units
        qty = cash * cfg.invest / sizing_px
        qty = np.floor(qty) if cfg.whole_shares else qty
        if qty <= 0:
            return
        cost = qty * px_raw * (1 + slip)
        cash -= cost
        units = qty * px_raw / px_adj
        trades.append((day, "buy", a, qty, px_raw, qty * px_raw, qty * px_raw * slip))

    for k, day in enumerate(idx):
        traded = False
        if cfg.mode == "moc":
            target = asset.iloc[k]
            if target != held:
                if held is not None:
                    sell(adj_c.at[day, held], raw_c.at[day, held], day)
                buy(target, adj_c.at[day, target], raw_c.at[day, target], size_px.at[day, target], day)
                held, traded = target, True
        else:  # opg: yesterday's close signal fills at today's open
            target = asset.iloc[k - 1] if k else None
            if target is not None and target != held:
                if held is not None:
                    sell(adj_o.at[day, held], raw_o.at[day, held], day)
                prev = idx[k - 1]
                buy(target, adj_o.at[day, target], raw_o.at[day, target], raw_c.at[prev, target], day)
                held, traded = target, True
        eq = cash + (units * adj_c.at[day, held] if held else 0.0)
        rows.append((day, eq, held, traded, cash))
    out = pd.DataFrame(rows, columns=["date", "equity", "held", "traded", "cash"]).set_index("date")
    out["ret"] = out["equity"].pct_change()
    tl = pd.DataFrame(trades, columns=["date", "side", "ticker", "shares", "price", "notional", "cost"])
    return out, tl
