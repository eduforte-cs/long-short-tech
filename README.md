# Long/Short Tech 1v

Réplica de la symphony de Composer «Long/Short Tech 1v», con backtest realista para Alpaca y (después) capa de
ejecución. Mismo estándar que `high-octane` y `holy-grail`.

## Reglas (rebalanceo diario, siempre un único activo al 100%, RSI de Wilder de 10 días)

```
SI SPY > SMA200(SPY)
│  SI RSI(QQQ) > 79  O  RSI(SPY) > 80        → VIXY
│  SINO                                       → QQQ
SINO
   SI RSI(QQQ) < 31                           → XLK
   SINO SI RSI(SPY) < 30                      → SPY
   SINO SI RSI(VIXY) > 74
   │  SI RSI(VIXY) > 84 → [QQQ > SMA20(QQQ) ? QQQ : mayor RSI entre SQQQ y BSV]
   │  SINO              → VIXY
   SINO                 → [QQQ > SMA20(QQQ) ? QQQ : mayor RSI entre SQQQ y BSV]
```

Umbrales en `lstech/config.py`, árbol en `lstech/strategy.py` (`decide`).

## Uso

```
pip install -r requirements.txt
python run_backtest.py                 # capa 1: Composer vs. Alpaca MOC/OPG con datos diarios -> results/backtest.md
python run_execution.py --source yahoo # señal a las 15:30 (barras horarias, ~2 años) -> results/execution_yahoo.md
python run_execution.py                # señal a las 15:45 con barras de Alpaca desde 2016 (SIP e IEX) -> results/execution_alpaca.md
python -m pytest tests
```

`run_execution.py` (por defecto) necesita `ALPACA_API_KEY` y `ALPACA_SECRET_KEY` (cuenta paper, plan gratuito).

## Cómo se simula Alpaca (`lstech/alpaca_sim.py`)

- **MOC**: señal con el precio de las 15:45 ET (RSI y SMA con ese precio como «cierre de hoy»), orden market-on-close
  antes del corte de las 15:50, llenada al cierre oficial. **OPG**: señal al cierre, llenada en la subasta de apertura.
- Acciones enteras (Alpaca no admite fracciones en MOC/OPG), dimensionadas con el precio conocido al enviar la orden
  y con el precio realmente impreso ese día (sin ajustar: VIXY y SQQQ hacen contrasplits). El resto, en efectivo al 0%.
- Venta y compra en la misma subasta: requiere cuenta de margen (≥ 2.000 $).
- Costes: 3 pb por lado de deslizamiento, tasa SEC sobre ventas y FINRA TAF por acción vendida. Sin comisión.
- Dividendos reinvertidos en la posición (precios ajustados).
