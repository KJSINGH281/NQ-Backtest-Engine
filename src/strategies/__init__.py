from .template import BaseStrategy, StrategySignals
from .ema_cross import EmaCross
from .orb_retrace import OrbRetrace

# Registry used by scripts/run_backtest.py and the AI generator.
STRATEGY_REGISTRY: dict[str, type[BaseStrategy]] = {
    EmaCross.name: EmaCross,
    OrbRetrace.name: OrbRetrace,
}

__all__ = ["BaseStrategy", "StrategySignals", "EmaCross", "OrbRetrace", "STRATEGY_REGISTRY"]
