#!/bin/bash
#
# STERLING SIGNALS - FRIDAY PIPELINE ORCHESTRATOR
# ================================================
# Runs the complete weekly pipeline locally.
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
        -h|--help)
            echo "Usage: ./run_friday.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --test         Run in test mode (minimal API calls)"
            echo "  --no-push      Don't push to GitHub"
            echo "  --skip-charts  Skip chart capture step"
            echo "  -h, --help     Show this help"
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
if [ ! -f "scanner.py" ]; then
    log_error "scanner.py not found in current directory"
    exit 1
fi

if [ ! -f "complete_tickers.txt" ]; then
    log_error "complete_tickers.txt not found"
    exit 1
fi

log_success "Pre-flight checks passed"

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 1: RUN SCANNER
# ═══════════════════════════════════════════════════════════════════════════════

log_header "STEP 1: Running Scanner"

SCANNER_ARGS="--archive"

if [ "$TEST_MODE" = true ]; then
    SCANNER_ARGS="$SCANNER_ARGS --no-llm --top 20"
    log_warning "Test mode: Using --no-llm --top 20"
else
    SCANNER_ARGS="$SCANNER_ARGS --web-search"
fi

log_step "python3 scanner.py $SCANNER_ARGS"
python3 scanner.py $SCANNER_ARGS

log_success "Scanner complete"

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 2: CAPTURE CHARTS
# ═══════════════════════════════════════════════════════════════════════════════

if [ "$SKIP_CHARTS" = true ]; then
    log_warning "Skipping chart capture (--skip-charts)"
else
    log_header "STEP 2: Capturing TradingView Charts"
    
    if [ -f "chart_capture.py" ]; then
        # Extract tickers from latest signals
        if [ -f "trades/latest_signals.json" ]; then
            log_step "python3 chart_capture.py --tickers-from trades/latest_signals.json --headless"
            python3 chart_capture.py --tickers-from trades/latest_signals.json --headless || {
                log_warning "Chart capture failed - continuing anyway"
            }
        else
            log_warning "No latest_signals.json found, skipping chart capture"
        fi
    else
        log_warning "chart_capture.py not found, skipping"
    fi
fi

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 3: GENERATE TWEETS
# ═══════════════════════════════════════════════════════════════════════════════

log_header "STEP 3: Generating Tweets"

if [ -f "tweet_generator.py" ]; then
    TWEET_ARGS=""
    if [ "$TEST_MODE" = true ]; then
        TWEET_ARGS="--mock"
        log_warning "Test mode: Using --mock"
    fi
    
    log_step "python3 tweet_generator.py $TWEET_ARGS"
    python3 tweet_generator.py $TWEET_ARGS
    log_success "Tweet generation complete"
else
    log_warning "tweet_generator.py not found, skipping"
    
    # Fallback to old grok prompts
    if [ -f "grok_prompts_generator.py" ]; then
        log_step "Falling back to grok_prompts_generator.py"
        python3 grok_prompts_generator.py
    fi
fi

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 4: COMPILE NEWSLETTER (Optional)
# ═══════════════════════════════════════════════════════════════════════════════

log_header "STEP 4: Newsletter Compilation"

if [ -f "newsletter_compiler.py" ]; then
    log_step "python3 newsletter_compiler.py"
    python3 newsletter_compiler.py || {
        log_warning "Newsletter compilation failed - continuing anyway"
    }
else
    log_warning "newsletter_compiler.py not found, skipping"
fi

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 5: PUBLISH TO SUBSTACK (Optional)
# ═══════════════════════════════════════════════════════════════════════════════

log_header "STEP 5: Substack Publishing"

if [ -f "substack_publisher.py" ]; then
    log_step "python3 substack_publisher.py --draft"
    python3 substack_publisher.py --draft || {
        log_warning "Substack publishing failed - continuing anyway"
    }
else
    log_warning "substack_publisher.py not found, skipping"
    echo "  To publish manually:"
    echo "  1. Open trades/latest_newsletter.html"
    echo "  2. Copy to Substack editor"
    echo "  3. Add images from trades/charts/"
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

echo "  Generated files:"
echo "    • trades/latest_newsletter_briefing.md"
[ -f "trades/content_queue.json" ] && echo "    • trades/content_queue.json"
[ -d "trades/charts" ] && echo "    • trades/charts/*.png"
[ -f "trades/latest_newsletter.html" ] && echo "    • trades/latest_newsletter.html"
echo ""

if [ "$TEST_MODE" = true ]; then
    echo -e "${YELLOW}  ⚠ This was a TEST run - no real API calls made${NC}"
else
    echo "  Next steps:"
    echo "    1. Review newsletter in trades/"
    echo "    2. Publish to Substack (if not auto-published)"
    echo "    3. Daily tweets will post Mon-Sun via GitHub Actions"
fi

echo ""
echo "  Time: $(date '+%H:%M:%S')"
echo ""
