"""Standardized KPIs that mirror NinjaTrader 8 Strategy Analyzer's summary tab."""
from __future__ import annotations

from typing import Any

import numpy as np


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        v = float(x)
        return v if np.isfinite(v) else default
    except (TypeError, ValueError):
        return default


def compute_kpis(portfolio: Any) -> dict[str, float]:
    """
    Extract a standardized KPI dict from a vbt.Portfolio.

    Keys match NT8 Strategy Analyzer terminology where possible:
      total_net_profit, gross_profit, gross_loss, profit_factor,
      total_trades, percent_profitable, max_drawdown, sharpe_ratio,
      avg_trade, total_return_pct
    """
    trades = portfolio.trades
    pnl = trades.pnl.values if hasattr(trades.pnl, "values") else np.asarray(trades.pnl)

    wins = pnl[pnl > 0]
    losses = pnl[pnl < 0]
    gross_profit = float(wins.sum()) if wins.size else 0.0
    gross_loss = float(losses.sum()) if losses.size else 0.0   # negative
    n_trades = int(pnl.size)

    profit_factor = (gross_profit / abs(gross_loss)) if gross_loss < 0 else float("inf") if gross_profit > 0 else 0.0
    pct_profitable = float(wins.size / n_trades) if n_trades else 0.0
    avg_trade = float(pnl.mean()) if n_trades else 0.0
    total_net_profit = gross_profit + gross_loss

    # vectorbt accessors (different vbt versions expose these slightly differently)
    try:
        max_drawdown = _safe_float(portfolio.max_drawdown())
    except Exception:
        max_drawdown = _safe_float(getattr(portfolio, "max_drawdown", 0.0))

    try:
        sharpe = _safe_float(portfolio.sharpe_ratio())
    except Exception:
        sharpe = _safe_float(getattr(portfolio, "sharpe_ratio", 0.0))

    try:
        total_return_pct = _safe_float(portfolio.total_return()) * 100.0
    except Exception:
        total_return_pct = 0.0

    return {
        "total_net_profit": round(total_net_profit, 2),
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
        "profit_factor": round(profit_factor, 4) if np.isfinite(profit_factor) else float("inf"),
        "total_trades": n_trades,
        "percent_profitable": round(pct_profitable, 4),
        "avg_trade": round(avg_trade, 2),
        "max_drawdown": round(max_drawdown, 4),
        "sharpe_ratio": round(sharpe, 4),
        "total_return_pct": round(total_return_pct, 4),
    }
