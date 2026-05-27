.PHONY: install test backtest optimize export docs kiro

install:
	pip install -e .[dev]

test:
	pytest tests/ -v --cov=src

backtest:
	python scripts/run_backtest.py \
		--strategy orb_retrace \
		--data data/sample_nq_1m.csv \
		--output results/$(shell date +%Y%m%d_%H%M).json

optimize:
	python scripts/optimize_params.py \
		--strategy ema_cross \
		--param-grid '{"fast":[9,12,15],"slow":[21,26,30]}' \
		--output results/opt_$(shell date +%Y%m%d).json

export:
	python scripts/export_nt8_strategy.py \
		--input results/latest.json \
		--output strategies/ExportedStrategy.cs

docs:
	mkdocs serve

# Amazon Kiro shortcut [[46]][[51]]
kiro:
	@echo "🚀 Opening project in Amazon Kiro..."
	@echo "Tip: Use AI agent with prompt:"
	@echo "  'Generate a volatility breakout strategy for NQ 5-min using ATR and Volume Profile'"
	@echo ""
	@kiro open . 2>/dev/null || code .  # Fallback to VS Code
