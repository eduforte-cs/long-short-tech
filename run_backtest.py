"""Layer 1: Composer-style backtest with the real funds (2011-01 ->), plus the Alpaca account simulation
with daily data (MOC sized at the close / OPG next open). Writes results/backtest.md."""
import argparse
import numpy as np
import pandas as pd
from lstech.config import UNIVERSE, Config
from lstech.data import load_daily
from lstech.strategy import signals, weights
from lstech import backtest as bt
from lstech.alpaca_sim import simulate, SimConfig


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    a = ap.parse_args()
    d = load_daily(UNIVERSE, refresh=a.refresh)
    c = d["close"]
    s = signals(c)
    w = weights(s, UNIVERSE)
    R = {"Composer (señal y ejecución al cierre)": bt.run(w, c, 0),
         "Ídem, 10 pb por cambio": bt.run(w, c, 0, 10),
         "Retraso 1 día (cierre siguiente)": bt.run(w, c, 1)}
    logs = {}
    for m, name in [("moc", "Alpaca MOC (acciones enteras, 3 pb + tasas)"),
                    ("opg", "Alpaca OPG (apertura siguiente)")]:
        o, tl = simulate(s["asset"], d, SimConfig(mode=m))
        R[name] = o["ret"].iloc[1:]
        logs[name] = tl
    idx = R["Composer (señal y ejecución al cierre)"].index
    for b in ["SPY", "QQQ"]:
        R[b] = c[b].pct_change().reindex(idx)

    ret_next = c.pct_change().shift(-1)
    nxt = pd.Series([ret_next.at[t, x] for t, x in s["asset"].items()], index=s.index)
    br = pd.DataFrame({"rama": s["branch"], "r": nxt}).groupby("rama")["r"].agg(
        días="count", media=lambda x: f"{x.mean():.2%}", contribución_log=lambda x: round(np.log1p(x).sum(), 2))
    r0 = R["Composer (señal y ejecución al cierre)"]
    yr = pd.DataFrame({k: v.groupby(v.index.year).apply(lambda x: (1 + x).prod() - 1)
                       for k, v in R.items() if k in ("Composer (señal y ejecución al cierre)",
                                                      "Retraso 1 día (cierre siguiente)", "QQQ")})
    ex2020 = r0[r0.index.year != 2020]
    trades = len(logs["Alpaca MOC (acciones enteras, 3 pb + tasas)"]) / 2 / (len(idx) / 252)

    lines = [f"# Backtest base ({idx[0].date()} → {idx[-1].date()})", "",
             "Fondos reales, datos diarios de Yahoo ajustados por dividendos. Señal con el cierre del día *t*.", "",
             bt.table(R).to_markdown(), "",
             f"Cambios de activo por año: {trades:.0f}. Sin 2020, el CAGR de la versión Composer es "
             f"{bt.stats(ex2020)['CAGR']:.1%}.", "",
             "## Retorno del día siguiente por rama", "", br.sort_values("contribución_log").to_markdown(), "",
             "## Año a año", "", yr.map(lambda v: f"{v:.1%}").to_markdown(), ""]
    open("results/backtest.md", "w").write("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
