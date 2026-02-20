#!/bin/bash
# Bundle section-specific output data into dashboard/data/ for Vercel deployment
# Run before `next build` or as part of the build command
#
# Source directories:
#   portfolio/output/  - portfolio.csv, equity_curve.csv
#   scanner/output/    - signals.json, analysis_log.csv, current/, archive/
#   twitter/output/    - tweet queues, charts, tracking, workflow_status
#   substack/output/   - newsletter, posts, notes
#   trades/            - legacy fallback (used if section dirs missing)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DASHBOARD_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$DASHBOARD_DIR")"
DATA_DIR="$DASHBOARD_DIR/data"

# Section-specific output directories
PORTFOLIO_DIR="$PROJECT_ROOT/portfolio/output"
SCANNER_DIR="$PROJECT_ROOT/scanner/output"
TWITTER_DIR="$PROJECT_ROOT/twitter/output"
SUBSTACK_DIR="$PROJECT_ROOT/substack/output"

# Legacy fallback
LEGACY_TRADES_DIR="$PROJECT_ROOT/trades"

echo "Bundling data for deployment..."
echo "   Target: $DATA_DIR"
echo "   Sources:"
echo "     Portfolio: $PORTFOLIO_DIR"
echo "     Scanner:   $SCANNER_DIR"
echo "     Twitter:   $TWITTER_DIR"
echo "     Substack:  $SUBSTACK_DIR"
echo "     Legacy:    $LEGACY_TRADES_DIR"

# Helper: copy file from section dir with legacy fallback
copy_file() {
  local section_dir="$1"
  local legacy_subpath="$2"
  local dest="$3"
  local filename=$(basename "$legacy_subpath")

  if [ -f "$section_dir/$legacy_subpath" ]; then
    cp "$section_dir/$legacy_subpath" "$dest"
    echo "   + $filename (from section)"
  elif [ -f "$LEGACY_TRADES_DIR/$legacy_subpath" ]; then
    cp "$LEGACY_TRADES_DIR/$legacy_subpath" "$dest"
    echo "   + $filename (from legacy)"
  fi
}

# ─── Backfill equity curve (optional, requires Python + yfinance) ───
if command -v python3 &>/dev/null; then
  echo "   Running equity curve backfill..."
  python3 "$SCRIPT_DIR/backfill_equity_curve.py" 2>&1 | sed 's/^/   /' || {
    echo "   Warning: Backfill failed (non-fatal), continuing with existing data"
  }
else
  echo "   Warning: python3 not found, skipping equity curve backfill"
fi

# Clean previous bundle
rm -rf "$DATA_DIR"
mkdir -p "$DATA_DIR/current/substack_posts"
mkdir -p "$DATA_DIR/current/substack_notes"
mkdir -p "$DATA_DIR/archive"

# ─── Portfolio data ───
echo ""
echo "   --- Portfolio ---"
for f in portfolio.csv portfolio_google_sheets.csv equity_curve.csv; do
  copy_file "$PORTFOLIO_DIR" "$f" "$DATA_DIR/$f"
done

# ─── Scanner data ───
echo ""
echo "   --- Scanner ---"
for f in signals.json daily_signals.json; do
  copy_file "$SCANNER_DIR" "$f" "$DATA_DIR/$f"
done

# ─── Twitter data ───
echo ""
echo "   --- Twitter ---"
for f in live_content_queue.json failed_tweets.json tweet_tracking.json workflow_status.json; do
  copy_file "$TWITTER_DIR" "$f" "$DATA_DIR/$f"
done

# ─── Substack current week: newsletter ───
echo ""
echo "   --- Substack (current) ---"

# Newsletter
if [ -f "$SUBSTACK_DIR/current/newsletter.html" ]; then
  cp "$SUBSTACK_DIR/current/newsletter.html" "$DATA_DIR/current/"
  echo "   + current/newsletter.html (from section)"
elif [ -f "$LEGACY_TRADES_DIR/current/newsletter.html" ]; then
  cp "$LEGACY_TRADES_DIR/current/newsletter.html" "$DATA_DIR/current/"
  echo "   + current/newsletter.html (from legacy)"
fi

# Newsletter briefing
if [ -f "$SUBSTACK_DIR/current/newsletter_briefing.md" ]; then
  cp "$SUBSTACK_DIR/current/newsletter_briefing.md" "$DATA_DIR/current/"
  echo "   + current/newsletter_briefing.md (from section)"
elif [ -f "$LEGACY_TRADES_DIR/current/newsletter_briefing.md" ]; then
  cp "$LEGACY_TRADES_DIR/current/newsletter_briefing.md" "$DATA_DIR/current/"
  echo "   + current/newsletter_briefing.md (from legacy)"
fi

# Substack posts
if [ -d "$SUBSTACK_DIR/current/substack_posts" ]; then
  cp "$SUBSTACK_DIR/current/substack_posts/"*.html "$DATA_DIR/current/substack_posts/" 2>/dev/null || true
  echo "   + current/substack_posts/ (from section)"
elif [ -d "$LEGACY_TRADES_DIR/current/substack_posts" ]; then
  cp "$LEGACY_TRADES_DIR/current/substack_posts/"*.html "$DATA_DIR/current/substack_posts/" 2>/dev/null || true
  echo "   + current/substack_posts/ (from legacy)"
fi

# Substack notes
if [ -d "$SUBSTACK_DIR/current/substack_notes" ]; then
  cp "$SUBSTACK_DIR/current/substack_notes/"*.md "$DATA_DIR/current/substack_notes/" 2>/dev/null || true
  echo "   + current/substack_notes/ (from section)"
elif [ -d "$LEGACY_TRADES_DIR/current/substack_notes" ]; then
  cp "$LEGACY_TRADES_DIR/current/substack_notes/"*.md "$DATA_DIR/current/substack_notes/" 2>/dev/null || true
  echo "   + current/substack_notes/ (from legacy)"
fi

# Content schedule JSON (for dashboard schedule grid)
if [ -f "$SUBSTACK_DIR/current/content_schedule.json" ]; then
  cp "$SUBSTACK_DIR/current/content_schedule.json" "$DATA_DIR/current/"
  echo "   + current/content_schedule.json (from section)"
fi

# Handbook v5 (for dashboard prompt library)
if [ -f "$PROJECT_ROOT/substack/docs/content_prompt_handbook_v5.md" ]; then
  mkdir -p "$DATA_DIR/docs"
  cp "$PROJECT_ROOT/substack/docs/content_prompt_handbook_v5.md" "$DATA_DIR/docs/"
  echo "   + docs/content_prompt_handbook_v5.md"
fi

# ─── Week archives ───
echo ""
echo "   --- Archives ---"

# Check scanner archives first, then substack archives, then legacy
archive_source=""
if [ -d "$SCANNER_DIR/archive" ]; then
  archive_source="$SCANNER_DIR/archive"
elif [ -d "$LEGACY_TRADES_DIR/weeks" ]; then
  archive_source="$LEGACY_TRADES_DIR/weeks"
fi

substack_archive_source=""
if [ -d "$SUBSTACK_DIR/archive" ]; then
  substack_archive_source="$SUBSTACK_DIR/archive"
elif [ -d "$LEGACY_TRADES_DIR/weeks" ]; then
  substack_archive_source="$LEGACY_TRADES_DIR/weeks"
fi

# Collect all week names from both sources (POSIX-compatible, no declare -A)
all_weeks_file=$(mktemp)
if [ -n "$archive_source" ]; then
  for week_dir in "$archive_source"/2026-W*; do
    [ -d "$week_dir" ] && basename "$week_dir" >> "$all_weeks_file"
  done
fi
if [ -n "$substack_archive_source" ] && [ "$substack_archive_source" != "$archive_source" ]; then
  for week_dir in "$substack_archive_source"/2026-W*; do
    [ -d "$week_dir" ] && basename "$week_dir" >> "$all_weeks_file"
  done
fi

for week in $(sort -u "$all_weeks_file" 2>/dev/null); do
  mkdir -p "$DATA_DIR/archive/$week"

  # Scanner archive: signals, report
  scanner_week="$archive_source/$week"
  if [ -d "$scanner_week" ]; then
    [ -f "$scanner_week/signals.json" ] && cp "$scanner_week/signals.json" "$DATA_DIR/archive/$week/"
    [ -f "$scanner_week/newsletter_briefing.md" ] && cp "$scanner_week/newsletter_briefing.md" "$DATA_DIR/archive/$week/"
  fi

  # Substack archive: newsletter, posts, notes
  substack_week="${substack_archive_source}/$week"
  if [ -d "$substack_week" ]; then
    [ -f "$substack_week/newsletter.html" ] && cp "$substack_week/newsletter.html" "$DATA_DIR/archive/$week/"
    [ -f "$substack_week/newsletter_briefing.md" ] && cp "$substack_week/newsletter_briefing.md" "$DATA_DIR/archive/$week/"

    if [ -d "$substack_week/substack_posts" ]; then
      mkdir -p "$DATA_DIR/archive/$week/substack_posts"
      cp "$substack_week/substack_posts/"*.html "$DATA_DIR/archive/$week/substack_posts/" 2>/dev/null || true
    fi

    if [ -d "$substack_week/substack_notes" ]; then
      mkdir -p "$DATA_DIR/archive/$week/substack_notes"
      cp "$substack_week/substack_notes/"*.md "$DATA_DIR/archive/$week/substack_notes/" 2>/dev/null || true
    fi
  fi

  echo "   + archive/$week/"
done
rm -f "$all_weeks_file"

# ─── Generate manifest ───
echo "{\"bundled_at\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\", \"sources\": {\"portfolio\": \"$PORTFOLIO_DIR\", \"scanner\": \"$SCANNER_DIR\", \"twitter\": \"$TWITTER_DIR\", \"substack\": \"$SUBSTACK_DIR\"}}" > "$DATA_DIR/manifest.json"

echo ""
echo "Data bundled successfully!"
echo "   Files: $(find "$DATA_DIR" -type f | wc -l | tr -d ' ')"
echo "   Size: $(du -sh "$DATA_DIR" | cut -f1)"
