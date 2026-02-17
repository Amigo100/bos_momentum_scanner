#!/bin/bash
# Bundle trades/ data into dashboard/data/ for Vercel deployment
# Run before `next build` or as part of the build command

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DASHBOARD_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$DASHBOARD_DIR")"
TRADES_DIR="$PROJECT_ROOT/trades"
DATA_DIR="$DASHBOARD_DIR/data"

echo "📦 Bundling trades data for deployment..."
echo "   Source: $TRADES_DIR"
echo "   Target: $DATA_DIR"

# ─── Backfill equity curve (optional, requires Python + yfinance) ───
if command -v python3 &>/dev/null; then
  echo "   Running equity curve backfill..."
  python3 "$SCRIPT_DIR/backfill_equity_curve.py" 2>&1 | sed 's/^/   /' || {
    echo "   ⚠ Backfill failed (non-fatal), continuing with existing data"
  }
else
  echo "   ⚠ python3 not found, skipping equity curve backfill"
fi

# Clean previous bundle
rm -rf "$DATA_DIR"
mkdir -p "$DATA_DIR/current/substack_posts"
mkdir -p "$DATA_DIR/current/substack_notes"
mkdir -p "$DATA_DIR/weeks"

# ─── Core data files ───
for f in portfolio.csv portfolio_google_sheets.csv equity_curve.csv signals.json daily_signals.json \
         live_content_queue.json failed_tweets.json tweet_tracking.json \
         workflow_status.json; do
  if [ -f "$TRADES_DIR/$f" ]; then
    cp "$TRADES_DIR/$f" "$DATA_DIR/$f"
    echo "   ✓ $f"
  fi
done

# ─── Current week substack posts ───
if [ -d "$TRADES_DIR/current/substack_posts" ]; then
  cp "$TRADES_DIR/current/substack_posts/"*.html "$DATA_DIR/current/substack_posts/" 2>/dev/null || true
  echo "   ✓ current/substack_posts/"
fi

# ─── Current week substack notes ───
if [ -d "$TRADES_DIR/current/substack_notes" ]; then
  cp "$TRADES_DIR/current/substack_notes/"*.md "$DATA_DIR/current/substack_notes/" 2>/dev/null || true
  echo "   ✓ current/substack_notes/"
fi

# ─── Current week newsletter + briefing ───
if [ -f "$TRADES_DIR/current/newsletter.html" ]; then
  cp "$TRADES_DIR/current/newsletter.html" "$DATA_DIR/current/"
  echo "   ✓ current/newsletter.html"
fi
if [ -f "$TRADES_DIR/current/newsletter_briefing.md" ]; then
  cp "$TRADES_DIR/current/newsletter_briefing.md" "$DATA_DIR/current/"
  echo "   ✓ current/newsletter_briefing.md"
fi

# ─── Week archives ───
if [ -d "$TRADES_DIR/weeks" ]; then
  for week_dir in "$TRADES_DIR/weeks"/2026-W*; do
    if [ -d "$week_dir" ]; then
      week=$(basename "$week_dir")
      mkdir -p "$DATA_DIR/weeks/$week"

      # Copy signals and newsletter
      [ -f "$week_dir/signals.json" ] && cp "$week_dir/signals.json" "$DATA_DIR/weeks/$week/"
      [ -f "$week_dir/newsletter.html" ] && cp "$week_dir/newsletter.html" "$DATA_DIR/weeks/$week/"
      [ -f "$week_dir/newsletter_briefing.md" ] && cp "$week_dir/newsletter_briefing.md" "$DATA_DIR/weeks/$week/"

      # Copy substack posts
      if [ -d "$week_dir/substack_posts" ]; then
        mkdir -p "$DATA_DIR/weeks/$week/substack_posts"
        cp "$week_dir/substack_posts/"*.html "$DATA_DIR/weeks/$week/substack_posts/" 2>/dev/null || true
      fi

      # Copy substack notes
      if [ -d "$week_dir/substack_notes" ]; then
        mkdir -p "$DATA_DIR/weeks/$week/substack_notes"
        cp "$week_dir/substack_notes/"*.md "$DATA_DIR/weeks/$week/substack_notes/" 2>/dev/null || true
      fi

      echo "   ✓ weeks/$week/"
    fi
  done
fi

# ─── Generate manifest ───
echo "{\"bundled_at\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\", \"source\": \"$TRADES_DIR\"}" > "$DATA_DIR/manifest.json"

echo ""
echo "✅ Data bundled successfully!"
echo "   Files: $(find "$DATA_DIR" -type f | wc -l | tr -d ' ')"
echo "   Size: $(du -sh "$DATA_DIR" | cut -f1)"
