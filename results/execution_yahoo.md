# Ejecución realista: señal antes del cierre

## Yahoo 15:30 ET (2023-11-27 → 2026-10-22, 722 sesiones)

Señal en vivo = señal al cierre: **98.8%** de los días.

| margen   |   días | coincide   |
|:---------|-------:|:-----------|
| 0–1      |     57 | 86%        |
| 1–2      |     33 | 100%       |
| 2–5      |    106 | 99%        |
| 5–∞      |    526 | 100%       |

|                                                         | Total   | CAGR   | Vol   |   Sharpe |   Sortino | MaxDD   |   Calmar | Worst day   |
|:--------------------------------------------------------|:--------|:-------|:------|---------:|----------:|:--------|---------:|:------------|
| Señal al cierre, ejecución al cierre (ideal)            | 115.9%  | 30.9%  | 22.3% |     1.31 |      1.98 | -19.4%  |     1.59 | -6.6%       |
| Señal en vivo, MOC (vectorizado, sin costes)            | 89.1%   | 24.9%  | 22.4% |     1.1  |      1.62 | -19.4%  |     1.28 | -6.6%       |
| Señal en vivo, MOC en Alpaca (acciones enteras, costes) | 88.4%   | 24.8%  | 22.1% |     1.11 |      1.63 | -18.7%  |     1.33 | -6.5%       |
| Señal al cierre, OPG apertura siguiente                 | 143.9%  | 36.6%  | 22.2% |     1.52 |      2.34 | -14.0%  |     2.61 | -5.3%       |
| Señal al cierre, cierre siguiente                       | 168.0%  | 41.2%  | 22.4% |     1.65 |      2.62 | -13.8%  |     2.99 | -4.8%       |
| SPY                                                     | 68.2%   | 19.9%  | 15.3% |     1.26 |      1.67 | -18.8%  |     1.06 | -5.9%       |
| QQQ                                                     | 77.0%   | 22.1%  | 20.7% |     1.07 |      1.48 | -23.5%  |     0.94 | -6.2%       |

<details><summary>Días con señal distinta</summary>

| Date                | cierre   | en vivo   | rama cierre   | rama en vivo   |   margen |
|:--------------------|:---------|:----------|:--------------|:---------------|---------:|
| 2024-01-25 00:00:00 | VIXY     | QQQ       | bull_hot      | bull           |     0.72 |
| 2025-04-10 00:00:00 | BSV      | SQQQ      | bonds         | short          |     0.04 |
| 2025-05-19 00:00:00 | VIXY     | QQQ       | bull_hot      | bull           |     0.38 |
| 2026-03-20 00:00:00 | SPY      | XLK       | dip_spy       | dip_qqq        |     0.51 |
| 2026-03-23 00:00:00 | SQQQ     | QQQ       | short         | bull           |     0.22 |
| 2026-04-06 00:00:00 | QQQ      | BSV       | qqq_trend     | bonds          |     0    |
| 2026-04-07 00:00:00 | QQQ      | BSV       | qqq_trend     | bonds          |     0.08 |
| 2026-04-21 00:00:00 | QQQ      | VIXY      | bull          | bull_hot       |     3.39 |
| 2026-05-12 00:00:00 | VIXY     | QQQ       | bull_hot      | bull           |     0.34 |

</details>
