#!/bin/bash
# auto_test_nq.sh - Complete build, test, and browser dashboard for NQ futures

set -e  # Exit on error

echo "🎯 NQ Backtest Engine - Auto Test Suite"
echo "========================================"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Environment Setup
echo -e "\n${BLUE}[1/6] Setting up Python environment...${NC}"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Step 2: Download/Generate NQ Data
echo -e "\n${BLUE}[2/6] Fetching NQ historical data...${NC}"
python scripts/download_nq_data.py --symbol NQ --start 2024-01-01 --end 2026-05-28 --output data/nq_test_1m.csv

# Step 3: Run Core Tests
echo -e "\n${BLUE}[3/6] Running unit tests...${NC}"
pytest tests/ -v --cov=src --cov-report=html

# Step 4: Execute Backtests
echo -e "\n${BLUE}[4/6] Running strategy backtests on NQ data...${NC}"
python scripts/run_backtest.py \
  --strategy orb_retrace \
  --data data/nq_test_1m.csv \
  --output results/orb_retrace_$(date +%Y%m%d_%H%M).json \
  --generate-report

python scripts/run_backtest.py \
  --strategy ema_cross \
  --data data/nq_test_1m.csv \
  --output results/ema_cross_$(date +%Y%m%d_%H%M).json \
  --generate-report

# Step 5: Generate Web Dashboard
echo -e "\n${BLUE}[5/6] Building interactive dashboard...${NC}"
python scripts/generate_dashboard.py \
  --input-dir results/ \
  --output dashboard/index.html \
  --open-browser

# Step 6: Summary
echo -e "\n${GREEN}✅ All tests completed successfully!${NC}"
echo -e "\n${YELLOW}📊 View Results:${NC}"
echo "   Dashboard: http://localhost:8050 (if using Dash)"
echo "   Static HTML: file://$(pwd)/dashboard/index.html"
echo -e "\n${YELLOW}📁 Test Artifacts:${NC}"
echo "   - Results: $(ls -lh results/*.json | tail -2)"
echo "   - Coverage: file://$(pwd)/htmlcov/index.html"
echo "   - Logs: $(ls -lh logs/*.log 2>/dev/null | tail -1 || echo 'No logs yet')"

echo -e "\n${BLUE}🌐 Opening dashboard in browser...${NC}"
# Auto-open based on OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    open dashboard/index.html
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    xdg-open dashboard/index.html
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    start dashboard/index.html
else
    echo "Please open: file://$(pwd)/dashboard/index.html in Edge/Chrome"
fi
