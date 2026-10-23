from dataclasses import dataclass, field

UNIVERSE = ["SPY", "QQQ", "XLK", "VIXY", "SQQQ", "BSV"]


@dataclass
class Config:
    """Long/Short Tech 1v (Composer). Every leaf holds a single asset at 100%."""
    rsi_window: int = 10
    spy_sma: int = 200          # SPY > SMA200(SPY) -> bull branch
    qqq_sma: int = 20           # QQQ > SMA20(QQQ) -> QQQ, else best RSI of SQQQ/BSV
    qqq_hot: float = 79         # bull: RSI(QQQ) > 79 OR RSI(SPY) > 80 -> VIXY ("Any of")
    spy_hot: float = 80
    qqq_dip: float = 31         # bear: RSI(QQQ) < 31 -> XLK
    spy_dip: float = 30         #       RSI(SPY) < 30 -> SPY
    vixy_hot: float = 74        #       RSI(VIXY) > 74 -> VIXY ...
    vixy_extreme: float = 84    #       ... unless > 84 -> back to the QQQ/SMA20 block
    hot_asset: str = "VIXY"
    dip_qqq_asset: str = "XLK"
    dip_spy_asset: str = "SPY"
    long_asset: str = "QQQ"
    short_pair: tuple = ("SQQQ", "BSV")
    benchmarks: list = field(default_factory=lambda: ["SPY", "QQQ"])
