#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# LOCAL FRIDAY WORKFLOW - Run after GitHub Actions completes
# ═══════════════════════════════════════════════════════════════════════════════
#
# Captures TradingView charts with your proprietary Alpha/Bravo/Charlie indicators.
# Run this AFTER the Friday GitHub Actions workflow completes.
#
# Session persists for ~30-90 days. Re-login only needed if charts show errors.
#
# Usage:
#   ./run_local_friday.sh              # Normal run (headless, uses saved session)
#   ./run_local_friday.sh --login      # Re-authenticate with TradingView
#
# ═══════════════════════════════════════════════════════════════════════════════

cd "$(dirname "$0")"

echo ""
echo "═══════════════════════════════════════════════════════════════════════════════"
echo "  STERLING SIGNALS - CHART CAPTURE"
echo "═══════════════════════════════════════════════════════════════════════════════"
echo ""

# Check for login flag
if [ "$1" == "--login" ]; then
    echo "  🔑 Login mode: Browser will open for TradingView login"
    echo "  📌 Log in, wait for indicators to load, then the script continues."
    echo ""
    rm -rf .playwright_profile  # Clear old session
    python -m twitter.chart_capture --tickers-from scanner/output/signals.json --include-portfolio --save-cookies
else
    # Check if playwright profile exists
    if [ ! -d ".playwright_profile" ]; then
        echo "  ⚠️  No saved session found. Running in login mode..."
        echo "  📌 Log in to TradingView when the browser opens."
        echo ""
        python -m twitter.chart_capture --tickers-from scanner/output/signals.json --include-portfolio --save-cookies
    else
        echo "  ✓ Using saved TradingView session (headless)"
        echo ""
        python -m twitter.chart_capture --tickers-from scanner/output/signals.json --include-portfolio --headless --skip-wait
    fi
fi

# Check results
echo ""
echo "═══════════════════════════════════════════════════════════════════════════════"

if [ -f "twitter/output/charts/chart_manifest.json" ]; then
    CHART_COUNT=$(ls twitter/output/charts/*.png 2>/dev/null | wc -l | tr -d ' ')
    echo "  ✅ Captured $CHART_COUNT charts"
    echo ""
    echo "  📁 twitter/output/charts/"
    ls twitter/output/charts/*.png 2>/dev/null | while read f; do echo "     $(basename $f)"; done | head -15
    echo ""
    echo "  📱 Tweets: Charts auto-attached via content_queue.json"
    echo "  📰 Newsletter: Paste into Substack manually"
else
    echo "  ⚠️  No charts captured. Try: ./run_local_friday.sh --login"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════════════════════"
echo ""
