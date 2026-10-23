"""Layer 2: the signal as it can actually be computed before Alpaca's 15:50 MOC cutoff.
--source alpaca: 15:45 ET from Alpaca 15-min bars since 2016 (SIP history and IEX, the free real-time feed).
--source yahoo:  15:30 ET from Yahoo 60-min bars (last ~2 years, no keys needed).
Writes results/execution_<source>.md."""
import argparse
import pandas as pd
from lstech.config import UNIVERSE, Config
from lstech.data import load_daily, load_hourly
from lstech.strategy import signals, weights, indicators, margin
from lstech import backtest as bt
from lstech.alpaca_sim import simulate, SimConfig


def yahoo_1530(d):
    h = load_hourly(UNIVERSE)
    t = pd.Timestamp("15:30").time()
    o = h["open"][h["open"].index.time == t]
    lc = h["close"][h["close"].index.time == t]
    o.index, lc.index = o.index.normalize(), lc.index.normalize()
    # Yahoo intraday is split- but not dividend-adjusted: rescale with the last bar's close
    return o * (d["close"].reindex(lc.index) / lc)


def section(name, d, live, cfg):
    c = d["close"]
    s_close, s_live = signals(c, cfg), signals(c, cfg, live=live.reindex(c.index))
    idx = s_close.index[s_close.index.isin(live.dropna().index)]
    a, b = s_close["asset"][idx], s_live["asset"][idx]
    ind = indicators(c, cfg).loc[idx]
    m = ind.apply(lambda x: margin(x, cfg), axis=1)
    buckets = []
    for lo, hi in [(0, 1), (1, 2), (2, 5), (5, 1e9)]:
        k = (m >= lo) & (m < hi)
        buckets.append({"margen": f"{lo}–{hi if hi < 1e9 else '∞'}", "días": int(k.sum()),
                        "coincide": f"{(a[k] == b[k]).mean():.0%}" if k.any() else "-"})
    sub = {f: x.loc[idx[0]:] for f, x in d.items()}
    R = {"Señal al cierre, ejecución al cierre (ideal)": bt.run(weights(s_close.loc[idx], UNIVERSE), c),
         "Señal en vivo, MOC (vectorizado, sin costes)": bt.run(weights(s_live.loc[idx], UNIVERSE), c)}
    live_raw = live.reindex(idx) * (d["raw_close"] / c).reindex(idx)   # size the order with the 15:45 price
    o, tl = simulate(s_live["asset"].loc[idx], sub, SimConfig(mode="moc"), live_raw=live_raw)
    R["Señal en vivo, MOC en Alpaca (acciones enteras, costes)"] = o["ret"].iloc[1:]
    o2, _ = simulate(s_close["asset"].loc[idx], sub, SimConfig(mode="opg"))
    R["Señal al cierre, OPG apertura siguiente"] = o2["ret"].iloc[1:]
    R["Señal al cierre, cierre siguiente"] = bt.run(weights(s_close.loc[idx], UNIVERSE), c, 1)
    for k in ["SPY", "QQQ"]:
        R[k] = c[k].pct_change().reindex(R["Señal al cierre, ejecución al cierre (ideal)"].index)
    dis = pd.DataFrame({"cierre": a, "en vivo": b, "rama cierre": s_close["branch"][idx],
                        "rama en vivo": s_live["branch"][idx], "margen": m.round(2)})[a != b]
    return [f"## {name} ({idx[0].date()} → {idx[-1].date()}, {len(idx)} sesiones)", "",
            f"Señal en vivo = señal al cierre: **{(a == b).mean():.1%}** de los días.", "",
            pd.DataFrame(buckets).to_markdown(index=False), "", bt.table(R).to_markdown(), "",
            "<details><summary>Días con señal distinta</summary>", "", dis.to_markdown(), "", "</details>", ""]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["alpaca", "yahoo"], default="alpaca")
    a = ap.parse_args()
    cfg = Config()
    d = load_daily(UNIVERSE)
    lines = ["# Ejecución realista: señal antes del cierre", ""]
    if a.source == "yahoo":
        lines += section("Yahoo 15:30 ET", d, yahoo_1530(d), cfg)
    else:
        from lstech.alpaca_data import load_decision_prices
        for feed in ("sip", "iex"):
            lines += section(f"Alpaca 15:45 ET, feed {feed}", d, load_decision_prices(d, UNIVERSE, feed=feed), cfg)
    open(f"results/execution_{a.source}.md", "w").write("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
