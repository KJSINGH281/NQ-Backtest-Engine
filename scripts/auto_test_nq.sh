#!/usr/bin/env bash
# scripts/auto_test_nq.sh
#
# One-shot build & test entrypoint for the NQ-Backtest-Engine.
# Idempotent: re-running reuses .venv. Safe to run on a fresh clone.
#
# Pipeline:
#   1. Create / reuse .venv
#   2. Install requirements + the package in editable mode
#   3. Run pytest (engine tests gracefully skip if vectorbt is unavailable)
#   4. Run a sample backtest against data/sample_nq_1m.csv
#   5. Print KPIs
#
# Env vars:
#   PYTHON          override interpreter (default: python3)
#   VENV_DIR        venv path           (default: ./.venv)
#   SKIP_BACKTEST=1 skip step 4         (just dep install + tests)
#   SKIP_TESTS=1    skip step 3
#
# Exit codes:
#   0  success
#   1  any step failed

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

VENV_DIR="${VENV_DIR:-${ROOT}/.venv}"
MIN_PY_MAJOR=3
MIN_PY_MINOR=10

log()  { printf "\n\033[1;36m==> %s\033[0m\n" "$*"; }
warn() { printf "\033[1;33m[WARN]\033[0m %s\n" "$*" >&2; }
ok()   { printf "\033[1;32m[OK]\033[0m %s\n" "$*"; }
die()  { printf "\033[1;31m[FAIL]\033[0m %s\n" "$*" >&2; exit 1; }

# Find a Python interpreter that satisfies pyproject.toml (>= 3.10).
# Honors $PYTHON override; otherwise probes common candidates.
pick_python() {
    local candidates=()
    [[ -n "${PYTHON:-}" ]] && candidates+=("$PYTHON")
    candidates+=(python3.13 python3.12 python3.11 python3.10 python3)
    for cand in "${candidates[@]}"; do
        command -v "$cand" >/dev/null 2>&1 || continue
        if "$cand" -c "import sys; sys.exit(0 if sys.version_info >= (${MIN_PY_MAJOR},${MIN_PY_MINOR}) else 1)" 2>/dev/null; then
            echo "$cand"
            return 0
        fi
    done
    return 1
}

# ---------------------------------------------------------------------------
# 1. Virtualenv
# ---------------------------------------------------------------------------
PYTHON_BIN="$(pick_python)" \
    || die "No Python >= ${MIN_PY_MAJOR}.${MIN_PY_MINOR} found (set PYTHON=/path/to/python3.${MIN_PY_MINOR}+)"
log "Python: $("$PYTHON_BIN" --version 2>&1) ($PYTHON_BIN)"
if [[ ! -d "$VENV_DIR" ]]; then
    log "Creating venv at $VENV_DIR"
    "$PYTHON_BIN" -m venv "$VENV_DIR" || die "venv creation failed"
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

# ---------------------------------------------------------------------------
# 2. Dependencies
# ---------------------------------------------------------------------------
log "Upgrading pip"
pip install --quiet --upgrade pip

log "Installing requirements (vectorbt + numba can take 2-4 min on first run)"
pip install --quiet -r requirements.txt || die "pip install -r requirements.txt failed"

log "Installing project (editable)"
pip install --quiet -e . || die "pip install -e . failed"

# ---------------------------------------------------------------------------
# 3. Tests
# ---------------------------------------------------------------------------
if [[ "${SKIP_TESTS:-0}" != "1" ]]; then
    log "Running pytest"
    pytest tests/ -v --tb=short || die "pytest failed"
    ok "tests passed"
else
    warn "SKIP_TESTS=1 -> skipping pytest"
fi

# ---------------------------------------------------------------------------
# 4. Sample backtest
# ---------------------------------------------------------------------------
if [[ "${SKIP_BACKTEST:-0}" != "1" ]]; then
    log "Running sample backtest (ema_cross fast=3 slow=7 on data/sample_nq_1m.csv)"
    mkdir -p results
    out="results/auto_$(date +%Y%m%d_%H%M%S).json"

    # The sample CSV is only 20 bars; use --all-hours so the RTH filter
    # doesn't accidentally empty the input on edge timestamps.
    python scripts/run_backtest.py \
        --strategy ema_cross \
        --data data/sample_nq_1m.csv \
        --output "$out" \
        --params '{"fast":3,"slow":7}' \
        --all-hours \
        || die "sample backtest failed"

    ok "Sample backtest complete -> $out"
    log "KPIs:"
    python -c "import json,sys; print(json.dumps(json.load(open('$out'))['kpis'], indent=2))"

    log "Building dashboard"
    python scripts/build_dashboard.py --result "$out" \
        || warn "dashboard build failed (non-fatal)"
else
    warn "SKIP_BACKTEST=1 -> skipping sample backtest"
fi

ok "auto_test_nq.sh: ALL CHECKS PASSED"

# ---------------------------------------------------------------------------
# 5. Open-dashboard hint (platform-aware, no auto-open from a CI / SSH session)
# ---------------------------------------------------------------------------
DASH="${ROOT}/dashboard/index.html"
if [[ -f "$DASH" ]]; then
    echo
    echo "Open the dashboard:"
    case "$(uname -s)" in
        Linux*)  echo "  xdg-open $DASH" ;;
        Darwin*) echo "  open $DASH" ;;
        MINGW*|MSYS*|CYGWIN*) echo "  start $DASH" ;;
        *)       echo "  $DASH" ;;
    esac
    echo "Or paste this URL into a browser: file://$DASH"
fi
