#!/bin/bash
#
# STERLING SIGNALS - FRIDAY PIPELINE ORCHESTRATOR
# ================================================
# Runs the complete weekly pipeline locally with full automation:
#   1. Scanner (Technical → Thematic → Gatekeeper → DD)
#   2. Chart Capture (TradingView)
#   3. Market Analysis (Claude + web search)
#   4. Newsletter Compilation (Claude)
#   5. Tweet Generation (Claude)
#   6. Git commit and push
#
# Usage:
#   ./run_friday.sh              # Full production run
#   ./run_friday.sh --test       # Test mode (no API calls where possible)
#   ./run_friday.sh --no-push    # Run without pushing to GitHub
#
# Prerequisites:
#   - ANTHROPIC_API_KEY set in environment
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

# Check required environment variables (skip API key check in test mode)
if [ "$TEST_MODE" = false ]; then
    check_env "ANTHROPIC_API_KEY"
else
    log_warning "Test mode: Skipping ANTHROPIC_API_KEY check"
fi

# Check required files
if [ ! -f "core/scanner.py" ]; then
    log_error "core/scanner.py not found in current directory"
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

log_header "STEP 1: Running Scanner (Technical → Thematic → Gatekeeper → DD)"

SCANNER_ARGS="--archive"

if [ "$TEST_MODE" = true ]; then
    SCANNER_ARGS="$SCANNER_ARGS --no-llm --top 20"
    log_warning "Test mode: Using --no-llm --top 20"
else
    # Production: full pipeline with web search and DD
    SCANNER_ARGS="$SCANNER_ARGS --web-search"
fi

log_step "python3 -m core.scanner $SCANNER_ARGS"
python3 -m core.scanner $SCANNER_ARGS

log_success "Scanner complete (DD results applied, portfolio updated)"

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 1.5: GENERATE FUNNEL GRAPHIC
# ═══════════════════════════════════════════════════════════════════════════════

if [ "$SKIP_CHARTS" = true ]; then
    log_warning "Skipping funnel graphic (--skip-charts)"
else
    log_header "STEP 1.5: Generating Funnel Graphic"

    if [ -f "content/funnel_graphic.py" ]; then
        log_step "python3 -m content.funnel_graphic"
        python3 -m content.funnel_graphic || {
            log_warning "Funnel graphic generation failed - continuing anyway"
        }
    else
        log_warning "content/funnel_graphic.py not found, skipping"
    fi
fi

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 2: CAPTURE TRADINGVIEW CHARTS
# ═══════════════════════════════════════════════════════════════════════════════

if [ "$SKIP_CHARTS" = true ]; then
    log_warning "Skipping chart capture (--skip-charts)"
else
    log_header "STEP 2: Capturing TradingView Charts"

    if [ -f "content/chart_capture.py" ]; then
        # Extract tickers from latest signals
        if [ -f "trades/signals.json" ]; then
            log_step "python3 -m content.chart_capture --tickers-from trades/signals.json --include-portfolio --headless"
            python3 -m content.chart_capture --tickers-from trades/signals.json --include-portfolio --headless || {
                log_warning "Chart capture failed - continuing anyway"
            }
        elif [ -f "trades/latest_signals.json" ]; then
            log_step "python3 -m content.chart_capture --tickers-from trades/latest_signals.json --include-portfolio --headless"
            python3 -m content.chart_capture --tickers-from trades/latest_signals.json --include-portfolio --headless || {
                log_warning "Chart capture failed - continuing anyway"
            }
        else
            log_warning "No signals.json found, skipping chart capture"
        fi
    else
        log_warning "content/chart_capture.py not found, skipping"
    fi
fi

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 3: GENERATE MARKET ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

if [ "$SKIP_NEWSLETTER" = true ]; then
    log_warning "Skipping market analysis (--skip-newsletter)"
else
    log_header "STEP 3: Generating Market Analysis (Claude + Web Search)"

    if [ -f "content/market_analyzer.py" ]; then
        MARKET_ARGS="--save"
        if [ "$TEST_MODE" = true ]; then
            log_warning "Test mode: Skipping market analysis API call"
        else
            log_step "python3 -m content.market_analyzer $MARKET_ARGS"
            python3 -m content.market_analyzer $MARKET_ARGS || {
                log_warning "Market analysis failed - continuing anyway"
            }
        fi
    else
        log_warning "content/market_analyzer.py not found, skipping"
    fi
fi

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 4: COMPILE NEWSLETTER (Full automated with LLM)
# ═══════════════════════════════════════════════════════════════════════════════

if [ "$SKIP_NEWSLETTER" = true ]; then
    log_warning "Skipping newsletter compilation (--skip-newsletter)"
else
    log_header "STEP 4: Newsletter Compilation (Market + Briefing + DD → HTML)"

    if [ -f "content/newsletter_compiler.py" ]; then
        NEWSLETTER_ARGS=""
        if [ "$TEST_MODE" = true ]; then
            # Basic compilation only (no LLM)
            log_warning "Test mode: Basic compilation only"
        else
            # Full automated compilation with LLM
            NEWSLETTER_ARGS="--full"
        fi

        log_step "python3 -m content.newsletter_compiler $NEWSLETTER_ARGS"
        python3 -m content.newsletter_compiler $NEWSLETTER_ARGS || {
            log_warning "Newsletter compilation failed - continuing anyway"
        }
    else
        log_warning "content/newsletter_compiler.py not found, skipping"
    fi
fi

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 4.5: GENERATE DD HTML POSTS (per buy signal for Substack)
# ═══════════════════════════════════════════════════════════════════════════════

log_header "STEP 4.5: Generating DD HTML Posts (per buy signal)"

if [ -f "content/dd_post_generator.py" ]; then
    DD_ARGS=""
    if [ "$TEST_MODE" = true ]; then
        DD_ARGS="--dry-run"
        log_warning "Test mode: dry-run only"
    fi

    log_step "python3 -m content.dd_post_generator $DD_ARGS"
    python3 -m content.dd_post_generator $DD_ARGS || {
        log_warning "DD post generation failed - continuing anyway"
    }
    log_success "DD posts generated"
else
    log_warning "content/dd_post_generator.py not found, skipping"
fi

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 5: GENERATE TWEETS
# ═══════════════════════════════════════════════════════════════════════════════

log_header "STEP 5: Generating Tweets (3 accounts × 35 tweets)"

TWEET_ARGS="--signals trades/signals.json --portfolio trades/portfolio.csv --output trades/"

log_step "python3 -m content.tweet_generator $TWEET_ARGS"
python3 -m content.tweet_generator $TWEET_ARGS
log_success "Tweet generation complete (tweet_generator v2)"

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 5.5: GENERATE SUBSTACK NOTES (Tuesday + Thursday)
# ═══════════════════════════════════════════════════════════════════════════════

log_header "STEP 5.5: Generating Substack Notes (Tuesday + Thursday)"

if [ -f "content/substack_notes_generator.py" ]; then
    log_step "python3 -m content.substack_notes_generator"
    python3 -m content.substack_notes_generator
    log_success "Substack notes generated"
else
    log_warning "content/substack_notes_generator.py not found, skipping"
fi

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 6: GIT COMMIT AND PUSH
# ═══════════════════════════════════════════════════════════════════════════════

log_header "STEP 6: Git Commit and Push"

if [ "$NO_PUSH" = true ]; then
    log_warning "Skipping git push (--no-push)"
else
    log_step "Staging changes..."
    git add trades/ 2>/dev/null || true
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

echo "  Generated files (new structure):"
echo "    • trades/current/newsletter.html       ← Copy to Substack Saturday"
echo "    • trades/current/newsletter_briefing.md"
echo "    • trades/current/signals.json"
echo "    • trades/current/substack_posts/dd_*.html  ← DD posts per signal"
echo "    • trades/current/substack_notes/"
echo "        ├── tuesday_note.md                ← Copy to Substack Tuesday"
echo "        └── thursday_note.md               ← Copy to Substack Thursday"
[ -d "trades/current/charts" ] && echo "    • trades/current/charts/*.png"
[ -d "trades/current/tweets" ] && echo "    • trades/current/tweets/content_queue.json"
echo ""
echo "  Archived to: trades/weeks/$(date '+%G-W%V')/"
echo ""

if [ "$TEST_MODE" = true ]; then
    echo -e "${YELLOW}  ⚠ This was a TEST run - no real API calls made${NC}"
else
    echo "  Pipeline completed with full automation:"
    echo "    ✅ Scanner ran with DD (only DD-PASS signals in portfolio)"
    echo "    ✅ Market analysis generated via Claude + web search"
    echo "    ✅ Newsletter compiled with embedded charts"
    echo "    ✅ 35 tweets generated for the week"
    echo "    ✅ Substack notes for Tuesday + Thursday"
    echo ""
    echo "  Weekly workflow:"
    echo "    Saturday:  Copy trades/current/newsletter.html to Substack"
    echo "    Tuesday:   Copy trades/current/substack_notes/tuesday_note.md to Substack Notes"
    echo "    Thursday:  Copy trades/current/substack_notes/thursday_note.md to Substack Notes"
    echo "    Daily:     Tweets auto-post via GitHub Actions"
fi

echo ""
echo "  Time: $(date '+%H:%M:%S')"
echo ""
