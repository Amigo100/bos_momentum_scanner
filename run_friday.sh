#!/bin/bash
#
# STERLING SIGNALS - FRIDAY PIPELINE ORCHESTRATOR
# ================================================
# Runs the complete weekly pipeline locally:
#   1. Scanner (Pure Technical Signal Detector — $0 cost)
#   2. Chart Capture (TradingView)
#   3. Tweet Generation (Claude — only LLM cost)
#   4. Content Production Guide + Notes
#   5. Git commit and push
#
# LLM analysis (thematic + investment gate + DD) now runs via Claude.ai chat.
# Attach sterling_prompt_library.md to Claude.ai after reviewing signals.
#
# Usage:
#   ./run_friday.sh              # Full production run
#   ./run_friday.sh --test       # Test mode (no API calls where possible)
#   ./run_friday.sh --no-push    # Run without pushing to GitHub
#
# Prerequisites:
#   - ANTHROPIC_API_KEY set in environment (for tweet generation)
#   - TradingView logged in (for chart capture)
#   - Git configured with push access to repo
#

set -e  # Exit on error

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load .env file if it exists
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default options
TEST_MODE=false
NO_PUSH=false
SKIP_CHARTS=false
SKIP_NEWSLETTER=false

# ═══════════════════════════════════════════════════════════════════════════════
# ARGUMENT PARSING
# ═══════════════════════════════════════════════════════════════════════════════

while [[ $# -gt 0 ]]; do
    case $1 in
        --test)
            TEST_MODE=true
            shift
            ;;
        --no-push)
            NO_PUSH=true
            shift
            ;;
        --skip-charts)
            SKIP_CHARTS=true
            shift
            ;;
        --skip-newsletter)
            SKIP_NEWSLETTER=true
            shift
            ;;
        -h|--help)
            echo "Usage: ./run_friday.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --test             Run in test mode (minimal API calls)"
            echo "  --no-push          Don't push to GitHub"
            echo "  --skip-charts      Skip chart capture step"
            echo "  --skip-newsletter  Skip newsletter compilation"
            echo "  -h, --help         Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

log_header() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
}

log_step() {
    echo -e "${GREEN}▶ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

log_error() {
    echo -e "${RED}✗ $1${NC}"
}

log_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

check_env() {
    if [ -z "${!1}" ]; then
        log_error "Missing environment variable: $1"
        exit 1
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════
# PRE-FLIGHT CHECKS
# ═══════════════════════════════════════════════════════════════════════════════

log_header "STERLING SIGNALS - FRIDAY PIPELINE"
echo "  Date: $(date '+%Y-%m-%d %H:%M:%S')"
echo "  Mode: $([ "$TEST_MODE" = true ] && echo 'TEST' || echo 'PRODUCTION')"
echo ""

log_step "Running pre-flight checks..."

# Check API key (needed for tweet generation, NOT for scanner)
if [ -z "$ANTHROPIC_API_KEY" ]; then
    log_warning "ANTHROPIC_API_KEY not set — scanner will work but tweet generation will fail"
fi

# Check required files
if [ ! -f "scanner/scanner.py" ]; then
    log_error "scanner/scanner.py not found in current directory"
    exit 1
fi

if [ ! -f "complete_tickers.txt" ]; then
    log_error "complete_tickers.txt not found"
    exit 1
fi

log_success "Pre-flight checks passed"

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 1: RUN SCANNER (with DD enabled by default)
# ═══════════════════════════════════════════════════════════════════════════════

log_header "STEP 1: Running Scanner (Pure Technical Signal Detector)"

SCANNER_ARGS="--archive"

if [ "$TEST_MODE" = true ]; then
    SCANNER_ARGS="$SCANNER_ARGS --top 20"
    log_warning "Test mode: Using --top 20"
fi

log_step "python3 -m scanner.scanner $SCANNER_ARGS"
python3 -m scanner.scanner $SCANNER_ARGS

log_success "Scanner complete (signals_technical.json generated — $0 cost)"

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 1.5: GENERATE FUNNEL GRAPHIC
# ═══════════════════════════════════════════════════════════════════════════════

if [ "$SKIP_CHARTS" = true ]; then
    log_warning "Skipping funnel graphic (--skip-charts)"
else
    log_header "STEP 1.5: Generating Funnel Graphic"

    if [ -f "twitter/funnel_graphic.py" ]; then
        log_step "python3 -m twitter.funnel_graphic"
        python3 -m twitter.funnel_graphic || {
            log_warning "Funnel graphic generation failed - continuing anyway"
        }
    else
        log_warning "twitter/funnel_graphic.py not found, skipping"
    fi
fi

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 2: CAPTURE TRADINGVIEW CHARTS
# ═══════════════════════════════════════════════════════════════════════════════

if [ "$SKIP_CHARTS" = true ]; then
    log_warning "Skipping chart capture (--skip-charts)"
else
    log_header "STEP 2: Capturing TradingView Charts"

    if [ -f "twitter/chart_capture.py" ]; then
        # Extract tickers from latest signals
        if [ -f "scanner/output/signals.json" ]; then
            log_step "python3 -m twitter.chart_capture --tickers-from scanner/output/signals.json --include-portfolio --headless"
            python3 -m twitter.chart_capture --tickers-from scanner/output/signals.json --include-portfolio --headless || {
                log_warning "Chart capture failed - continuing anyway"
            }
        else
            log_warning "No signals.json found, skipping chart capture"
        fi
    else
        log_warning "twitter/chart_capture.py not found, skipping"
    fi
fi

# Steps 3-4 (market analysis + newsletter compilation) removed.
# Newsletter is now produced manually in Claude.ai chat using the
# content production guide as context. Use --from-html to import:
#   python3 -m substack.newsletter_compiler --from-html path/to/newsletter.html

# ARCHIVED: DD HTML posts now generated via Claude.ai chat workflow
# The scanner no longer runs LLM gates, so DD data is not available here.
# Use: Attach sterling_prompt_library.md to Claude.ai after reviewing signals.

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 5: GENERATE TWEETS
# ═══════════════════════════════════════════════════════════════════════════════

log_header "STEP 5: Generating Tweets (3 accounts × 35 tweets)"

TWEET_ARGS="--signals scanner/output/signals.json --portfolio portfolio/output/portfolio.csv --output twitter/output/"

log_step "python3 -m twitter.tweet_generator $TWEET_ARGS"
python3 -m twitter.tweet_generator $TWEET_ARGS
log_success "Tweet generation complete (tweet_generator v2)"

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 5.5: GENERATE CONTENT PRODUCTION GUIDE
# ═══════════════════════════════════════════════════════════════════════════════

log_header "STEP 5.5: Generating Content Production Guide"

if [ -f "substack/content_production_guide.py" ]; then
    GUIDE_ARGS=""
    if [ "$TEST_MODE" = true ]; then
        GUIDE_ARGS="--dry-run"
        log_warning "Test mode: dry-run only"
    fi

    log_step "python3 -m substack.content_production_guide $GUIDE_ARGS"
    python3 -m substack.content_production_guide $GUIDE_ARGS || {
        log_warning "Content production guide generation failed - continuing anyway"
    }
    log_success "Content production guide generated"
    log_warning "Generate posts on-demand: attach guide to Claude.ai (Opus 4.6)"
else
    log_warning "substack/content_production_guide.py not found, skipping"
fi

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 5.6: GENERATE SUBSTACK NOTES BATCH (21 notes for the week)
# ═══════════════════════════════════════════════════════════════════════════════

log_header "STEP 5.6: Generating Substack Notes Batch (21 notes for the week)"

if [ -f "substack/notes_batch_generator.py" ]; then
    NOTES_ARGS=""
    if [ "$TEST_MODE" = true ]; then
        NOTES_ARGS="--no-llm"
        log_warning "Test mode: Using --no-llm for notes"
    fi

    log_step "python3 -m substack.notes_batch_generator $NOTES_ARGS"
    python3 -m substack.notes_batch_generator $NOTES_ARGS || {
        log_warning "Notes batch generation failed - continuing anyway"
        # Fallback to legacy 2-note generator
        log_step "Falling back to legacy notes generator..."
        if [ -f "substack/notes_generator.py" ]; then
            python3 -m substack.notes_generator || {
                log_warning "Legacy notes generation also failed"
            }
        fi
    }
    log_success "Substack notes batch generated"
else
    # Fallback to legacy 2-note generator
    log_warning "Batch generator not found, using legacy 2-note generator"
    if [ -f "substack/notes_generator.py" ]; then
        log_step "python3 -m substack.notes_generator"
        python3 -m substack.notes_generator
        log_success "Legacy substack notes generated"
    fi
fi

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 6: GIT COMMIT AND PUSH
# ═══════════════════════════════════════════════════════════════════════════════

log_header "STEP 6: Git Commit and Push"

if [ "$NO_PUSH" = true ]; then
    log_warning "Skipping git push (--no-push)"
else
    log_step "Staging changes..."
    git add scanner/output/ 2>/dev/null || true
    git add portfolio/output/ 2>/dev/null || true
    git add substack/output/ 2>/dev/null || true
    git add twitter/output/ 2>/dev/null || true
    git add *.json 2>/dev/null || true

    if git diff --cached --quiet; then
        log_warning "No changes to commit"
    else
        DATE=$(date '+%Y-%m-%d')
        COMMIT_MSG="Weekly scan results $DATE"

        if [ "$TEST_MODE" = true ]; then
            COMMIT_MSG="[TEST] $COMMIT_MSG"
        fi

        log_step "Committing: $COMMIT_MSG"
        git commit -m "$COMMIT_MSG"

        log_step "Pushing to GitHub..."
        git push

        log_success "Pushed to GitHub"
    fi
fi

# ═══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════

log_header "PIPELINE COMPLETE"

echo "  Generated files:"
echo "    • scanner/output/signals_technical.json   ← PRIMARY output"
echo "    • scanner/output/signals.json             ← Transitional (downstream compat)"
echo "    • substack/output/current/content_production_guide.md ← Attach to Claude.ai"
echo "    • substack/output/current/substack_notes/"
echo "        ├── *_1_*.md, *_2_*.md, *_3_*.md     ← 21 notes (3/day)"
echo "        └── notes_manifest.json               ← Batch tracking"
[ -d "twitter/output/charts" ] && echo "    • twitter/output/charts/*.png"
echo ""
echo "  Archived to: scanner/output/archive/$(date '+%G-W%V')/"
echo ""

if [ "$TEST_MODE" = true ]; then
    echo -e "${YELLOW}  ⚠ This was a TEST run - minimal API calls made${NC}"
else
    echo "  Pipeline completed:"
    echo "    ✅ Scanner ran (pure technical, \$0 cost)"
    echo "    ✅ Content production guide generated"
    echo "    ✅ 21 Substack notes generated (3/day)"
    echo "    ✅ Tweets generated for the week"
    echo ""
    echo "  Next steps (manual via Claude.ai chat):"
    echo "    1. Review signals_technical.json for buy/sell signals"
    echo "    2. Open Claude.ai → attach sterling_prompt_library.md"
    echo "    3. Run thematic analysis + investment gate in chat"
    echo "    4. Update portfolio with final decisions"
    echo ""
    echo "  Daily content workflow (handbook v5 — 4-category adaptive system):"
    echo "    1. Open content_production_guide.md → check today's category + topic"
    echo "    2. Open content_prompt_handbook_v5.md → copy the matching category prompt"
    echo "    3. Attach content_production_guide.md to Claude.ai (Opus 4.6 + extended thinking)"
    echo "    4. Paste prompt → get HTML post + 3 HTML notes"
    echo "    5. Paste into Substack"
fi

echo ""
echo "  Time: $(date '+%H:%M:%S')"
echo ""
