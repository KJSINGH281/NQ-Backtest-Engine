"""
AI Prompt Templates for Strategy Generation
Modeled after Michael Automates' Claude workflow [[autotrading.vip]]
"""

MICHAEL_AUTOMATES_PROMPT = """
You are an expert quantitative developer specializing in E-mini Nasdaq-100 (NQ) futures.

## Task
Create a complete, backtest-ready trading strategy for NQ 1-minute data using VectorBT.

## Strategy Requirements
- Type: {strategy_type} (e.g., "Opening Range Breakout", "Mean Reversion", "Trend Following")
- Indicators: {indicators} (e.g., "EMA(9/21), ATR(14), Volume Profile POC")
- Timeframe: 1-minute bars, Regular Trading Hours (09:30-16:00 ET)
- Risk: Fixed fractional sizing, 1% risk per trade, stop based on ATR(14)*1.5

## Output Format (STRICT JSON)
{{
  "strategy_name": "NQ_{strategy_type}_v1",
  "parameters": {{"param1": value1, "param2": value2}},
  "vectorbt_code": "Python code using vbt.Portfolio.from_signals(...)",
  "expected_kpis": {{
    "win_rate_range": [0.35, 0.55],
    "profit_factor_min": 1.5,
    "max_drawdown_max": 0.25
  }},
  "overfitting_warnings": ["List any curve-fit risks"]
}}

## Critical Constraints
1. NO look-ahead bias: indicators must only use data up to current bar [[7]]
2. Include realistic NQ fees: $2.50/round-turn + 0.25 tick slippage
3. If win_rate > 0.65 on single-asset backtest, add strong overfitting warning [[37]]
4. Code must run in <30 seconds on 5 years of 1-min NQ data

## Sample Data Context
- Symbol: NQ (E-mini Nasdaq-100)
- Tick size: 0.25 index points = $5 per tick
- Point value: $20 per full index point
- Typical daily range: 150-400 points

Generate the strategy now.
"""

VALIDATION_PROMPT = """
Validate this backtest result against NinjaTrader Strategy Analyzer expectations:

Given results: {results_json}

Check for:
1. KPI plausibility (win_rate 0.3-0.7, PF 1.0-3.0 for NQ strategies)
2. Overfitting signals: 
   - Win rate >70% on single asset → likely curve-fit [[37]]
   - Parameter sensitivity: ±10% change causes >20% performance drop
3. NinjaTrader parity: results should match NT8 Strategy Analyzer within ±2% [[4]]

Return validation report as JSON:
{{
  "is_plausible": bool,
  "nt8_parity_estimate_pct": float,
  "overfitting_risk": "low|medium|high",
  "recommendations": ["list of next steps"]
}}
"""
