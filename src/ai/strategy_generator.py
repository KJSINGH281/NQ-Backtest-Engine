"""
LLM -> strategy code pipeline.

This module is intentionally provider-agnostic. The Kiro agent (or any other
LLM caller) is expected to format MICHAEL_AUTOMATES_PROMPT, send it to a
model, and pass the JSON response back here for parsing + validation.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .prompt_templates import MICHAEL_AUTOMATES_PROMPT, VALIDATION_PROMPT


@dataclass
class GeneratedStrategy:
    strategy_name: str
    parameters: dict[str, Any]
    vectorbt_code: str
    expected_kpis: dict[str, Any]
    overfitting_warnings: list[str]


def render_generation_prompt(strategy_type: str, indicators: str) -> str:
    """Fill MICHAEL_AUTOMATES_PROMPT with the user's choices."""
    return MICHAEL_AUTOMATES_PROMPT.format(
        strategy_type=strategy_type,
        indicators=indicators,
    )


def render_validation_prompt(results: dict[str, Any]) -> str:
    return VALIDATION_PROMPT.format(results_json=json.dumps(results, indent=2))


def parse_generation_response(raw_json: str) -> GeneratedStrategy:
    """
    Parse a JSON blob produced by the LLM into a GeneratedStrategy.
    Raises ValueError on missing fields so the caller can re-prompt.
    """
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM response was not valid JSON: {e}") from e

    required = {"strategy_name", "parameters", "vectorbt_code", "expected_kpis"}
    missing = required - data.keys()
    if missing:
        raise ValueError(f"LLM response missing required fields: {sorted(missing)}")

    return GeneratedStrategy(
        strategy_name=str(data["strategy_name"]),
        parameters=dict(data["parameters"]),
        vectorbt_code=str(data["vectorbt_code"]),
        expected_kpis=dict(data["expected_kpis"]),
        overfitting_warnings=list(data.get("overfitting_warnings", [])),
    )


def kpi_plausibility_check(kpis: dict[str, float]) -> list[str]:
    """
    Cheap heuristics to catch obvious overfitting/curve-fit results before
    we even bother sending them to the validator LLM.
    """
    warnings: list[str] = []
    pct_profitable = float(kpis.get("percent_profitable", 0.0))
    pf = float(kpis.get("profit_factor", 0.0))
    n_trades = int(kpis.get("total_trades", 0))

    if pct_profitable > 0.70 and n_trades < 200:
        warnings.append(
            f"Win rate {pct_profitable:.0%} on only {n_trades} trades - likely curve-fit."
        )
    if pf > 5.0 and n_trades < 100:
        warnings.append(f"Profit factor {pf:.2f} on {n_trades} trades looks unrealistic.")
    if n_trades < 30:
        warnings.append(f"Only {n_trades} trades - statistically insignificant sample.")
    return warnings
