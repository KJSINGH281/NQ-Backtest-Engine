"""
NinjaTrader 8 Strategy Analyzer parity check.

Workflow
--------
1. User runs the same strategy in NT8 Strategy Analyzer and exports the
   summary report as JSON (or types the headline numbers into a dict).
2. We compare those numbers to our VectorBT KPIs and flag any KPI that
   diverges by more than `tolerance_pct`.

Parity target: results should match NT8 within +/-2 percent on the
headline KPIs (total_net_profit, profit_factor, percent_profitable,
total_trades, max_drawdown).
"""
from __future__ import annotations

from dataclasses import dataclass, field

DEFAULT_TOLERANCE_PCT: float = 2.0

# KPIs we actually compare. Anything else in either dict is ignored.
COMPARED_KPIS: tuple[str, ...] = (
    "total_net_profit",
    "gross_profit",
    "gross_loss",
    "profit_factor",
    "total_trades",
    "percent_profitable",
    "max_drawdown",
)


@dataclass
class NT8ParityReport:
    is_parity: bool
    tolerance_pct: float
    diffs: dict[str, dict[str, float]] = field(default_factory=dict)  # kpi -> {vbt, nt8, diff_pct}
    failed_kpis: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"NT8 parity: {'PASS' if self.is_parity else 'FAIL'}  (tol +/-{self.tolerance_pct}%)"
        ]
        for kpi, d in self.diffs.items():
            marker = "  " if kpi not in self.failed_kpis else "X "
            lines.append(
                f"{marker}{kpi:>22s}: vbt={d['vbt']:.4f}  nt8={d['nt8']:.4f}  "
                f"diff={d['diff_pct']:+.2f}%"
            )
        return "\n".join(lines)


def _pct_diff(vbt: float, nt8: float) -> float:
    if nt8 == 0:
        return 0.0 if vbt == 0 else float("inf")
    return ((vbt - nt8) / abs(nt8)) * 100.0


def check_nt8_parity(
    vbt_kpis: dict[str, float],
    nt8_kpis: dict[str, float],
    tolerance_pct: float = DEFAULT_TOLERANCE_PCT,
) -> NT8ParityReport:
    """Compare our KPIs against NT8's and report per-KPI deviation."""
    diffs: dict[str, dict[str, float]] = {}
    failed: list[str] = []

    for kpi in COMPARED_KPIS:
        if kpi not in vbt_kpis or kpi not in nt8_kpis:
            continue
        vbt_v = float(vbt_kpis[kpi])
        nt8_v = float(nt8_kpis[kpi])
        diff = _pct_diff(vbt_v, nt8_v)
        diffs[kpi] = {"vbt": vbt_v, "nt8": nt8_v, "diff_pct": diff}
        if abs(diff) > tolerance_pct:
            failed.append(kpi)

    return NT8ParityReport(
        is_parity=len(failed) == 0,
        tolerance_pct=tolerance_pct,
        diffs=diffs,
        failed_kpis=failed,
    )
