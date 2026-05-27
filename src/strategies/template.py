"""
BaseStrategy - the contract every strategy in this engine implements.

Subclasses produce two boolean Series (`entries`, `exits`) aligned with the
input price DataFrame. The engine handles fees, slippage, and KPI reporting,
so strategy code stays small, testable, and AI-generatable.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass
class StrategySignals:
    """Standard signal payload returned by BaseStrategy.generate_signals()."""
    entries: pd.Series  # bool, indexed like price
    exits: pd.Series    # bool, indexed like price
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.entries.index.equals(self.exits.index):
            raise ValueError("entries and exits must share the same index")
        if self.entries.dtype != bool or self.exits.dtype != bool:
            raise ValueError("entries and exits must be boolean Series")


class BaseStrategy(ABC):
    """Abstract base. AI-generated strategies should subclass this."""

    name: str = "base"

    def __init__(self, **params: Any) -> None:
        self.params: dict[str, Any] = params

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        """
        Compute entries/exits given an OHLCV DataFrame indexed by timestamp.
        Must NOT use future bars (no look-ahead).
        """

    # ----------------- introspection helpers -----------------
    def describe(self) -> dict[str, Any]:
        return {"name": self.name, "params": self.params, "class": self.__class__.__name__}

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"<{self.__class__.__name__} {self.params}>"
