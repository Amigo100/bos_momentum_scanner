#!/usr/bin/env python3
"""
SUBSTACK CONTENT UTILITIES
===========================

Shared data loading, formatting, validation, and HTML utilities used by
multiple Substack content modules. Extracted from content_generator.py
to survive its deletion in Phase 6.

Consumers:
    - content_production_guide.py (data loading + formatting)
    - newsletter_compiler.py (DD/theme/benchmark loaders)
    - daily_context_builder.py (future — Phase 2)
    - daily_notes_generator.py (future — Phase 3)
"""

import csv
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ─── Project imports ───────────────────────────────────────────────────────────

from config import (
    BRANDING,
    SIGNALS_FILE,
    PORTFOLIO_FILE,
    EQUITY_CURVE_FILE,
    get_conviction_text,
)
from config.banned_terms import (
    INTERNAL_TERMINOLOGY_MAP,
    check_banned_phrases,
    validate_content,
)

try:
    from config.output_paths import (
        SCANNER_OUTPUT,
        CHARTS_DIR,
        get_scanner_current_dir,
        get_substack_current_dir,
        list_weekly_archives,
    )
    OUTPUT_PATHS_AVAILABLE = True
except ImportError:
    OUTPUT_PATHS_AVAILABLE = False

try:
    from config import MARKETING_THRESHOLDS
except ImportError:
    MARKETING_THRESHOLDS = {
        'min_win_to_highlight': 15.0,
        'big_win_threshold': 25.0,
    }

# Import canonical SPY benchmark function
try:
    from portfolio.manager import get_spy_ytd_return
except ImportError:
    get_spy_ytd_return = None


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

SUBSTACK_URL = BRANDING.get("substack_url", "https://sterlingsignals.substack.com")
MIN_WIN_THRESHOLD = MARKETING_THRESHOLDS.get('min_win_to_highlight', 15.0)
BIG_WIN_THRESHOLD = MARKETING_THRESHOLDS.get('big_win_threshold', 25.0)


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class PostSpec:
    """Specification for a single Substack post."""
    post_type: str          # WEEKLY_RECAP, THEME_DEEP_DIVE, DD_DEEP_DIVE, PORTFOLIO_SPOTLIGHT,
                            # STOCK_DEEP_DIVE, QUICK_TAKE, PORTFOLIO_SHOWCASE, EDUCATIONAL
    title: str
    publish_day: str        # Saturday, Tuesday, Wednesday, Thursday, Friday
    filename: str
    template_theme: str = "dashboard"   # "dashboard" or "editorial"
    priority: int = 1       # 1 = must generate


# Map post types to HTML template themes
TEMPLATE_MAP = {
    "WEEKLY_RECAP": "dashboard",
    "THEME_DEEP_DIVE": "dashboard",
    "DD_DEEP_DIVE": "dashboard",
    "PORTFOLIO_SPOTLIGHT": "dashboard",
    "STOCK_DEEP_DIVE": "editorial",
    "QUICK_TAKE": "dashboard",
    "PORTFOLIO_SHOWCASE": "dashboard",
    "EDUCATIONAL": "editorial",
}


@dataclass
class ContentContext:
    """All available data for content generation."""
    signals: Dict = field(default_factory=dict)
    market_analysis: str = ""
    themes: List[Dict] = field(default_factory=list)
    buy_signals: List[Dict] = field(default_factory=list)
    assessed_signals: List[Dict] = field(default_factory=list)
    portfolio_stats: Dict = field(default_factory=dict)
    historical_winners: List[Dict] = field(default_factory=list)
    benchmark: str = ""
    theme_details: str = ""
    theme_history: Dict = field(default_factory=dict)
    chart_manifest: Dict = field(default_factory=dict)
    week_number: int = 0
    pass_count: int = 0
    scan_stats: Dict = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════════

def load_signals(signals_path: Optional[Path] = None) -> Dict:
    """Load signals.json from auto-detected or specified path."""
    paths_to_try = []
    if signals_path:
        paths_to_try.append(signals_path)
    if OUTPUT_PATHS_AVAILABLE:
        paths_to_try.append(get_scanner_current_dir() / "signals.json")
    paths_to_try.append(SIGNALS_FILE)

    for p in paths_to_try:
        if p.exists():
            with open(p) as f:
                return json.load(f)
    return {}


def load_market_analysis() -> str:
    """Load market analysis markdown from current outputs."""
    paths_to_try = []
    if OUTPUT_PATHS_AVAILABLE:
        paths_to_try.append(get_scanner_current_dir() / "market_analysis.md")
    paths_to_try.append(SCANNER_OUTPUT / "current" / "market_analysis.md")

    for p in paths_to_try:
        if p.exists():
            content = p.read_text()
            # Extract content after the header if present
            marker = "## \U0001f4ca Market Context"
            if marker in content:
                content = content[content.index(marker) + len(marker):]
            return content.strip()
    return ""


def load_portfolio_winners(snapshot_path=None, csv_fallback=True) -> List[Dict]:
    """Load all open positions for transparent showcase.

    Fallback chain:
    1. portfolio_snapshot.json (if exists) — pre-computed, preferred
    2. portfolio.csv via CSV loading — compute P&L manually
    3. Empty list (no crash)
    """
    # Try snapshot first
    if snapshot_path is None:
        try:
            from config.output_paths import PORTFOLIO_OUTPUT
            snapshot_path = PORTFOLIO_OUTPUT / "portfolio_snapshot.json"
        except ImportError:
            snapshot_path = None

    if snapshot_path and Path(snapshot_path).exists():
        try:
            snapshot = json.loads(Path(snapshot_path).read_text())
            return snapshot.get("winners", [])
        except (json.JSONDecodeError, KeyError):
            pass

    # Fallback to CSV
    if not csv_fallback:
        return []

    portfolio_path = PORTFOLIO_FILE
    if not portfolio_path.exists():
        return []

    positions = []
    with open(portfolio_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("status", "").upper() != "OPEN":
                continue
            try:
                entry = float(row.get("entry_price", 0))
                highest = float(row.get("highest_close", 0))
                if entry > 0 and highest > 0:
                    pnl_pct = ((highest - entry) / entry) * 100
                    positions.append({
                        "ticker": row.get("ticker", ""),
                        "entry_price": entry,
                        "highest_close": highest,
                        "pnl_pct": round(pnl_pct, 1),
                        "theme": row.get("theme", ""),
                        "entry_date": row.get("entry_date", ""),
                        "show_entry": True,
                    })
            except (ValueError, TypeError):
                continue

    positions.sort(key=lambda w: w["pnl_pct"], reverse=True)
    return positions


def load_equity_curve() -> Dict:
    """Load portfolio stats from equity_curve.csv."""
    curve_path = EQUITY_CURVE_FILE
    if not curve_path.exists():
        return {}

    rows = []
    with open(curve_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    if not rows:
        return {}

    latest = rows[-1]
    try:
        return {
            "nav": float(latest.get("nav", 0)),
            "total_return_pct": float(latest.get("total_return_pct", 0)),
            "spy_return_pct": float(latest.get("spy_return_pct", 0)),
            "alpha_pct": float(latest.get("alpha_pct", 0)),
            "qqq_return_pct": float(latest.get("qqq_return_pct", 0)),
            "alpha_vs_qqq_pct": float(latest.get("alpha_vs_qqq_pct", 0)),
            "open_count": int(float(latest.get("open_count", 0))),
            "date": latest.get("date", ""),
            "data_points": len(rows),
        }
    except (ValueError, TypeError):
        return {}


def load_historical_themes() -> Dict[str, List[Dict]]:
    """Load theme data from the last 4 weekly archives for trend analysis."""
    if not OUTPUT_PATHS_AVAILABLE:
        return {}

    try:
        archives = list_weekly_archives()
    except Exception:
        return {}

    # Take last 4 weeks (excluding current)
    recent_weeks = sorted(archives)[-5:-1] if len(archives) > 4 else sorted(archives)[:-1]
    history = {}

    for week_id in recent_weeks:
        week_dir = SCANNER_OUTPUT / "archive" / week_id
        signals_path = week_dir / "signals.json"
        if not signals_path.exists():
            continue

        try:
            with open(signals_path) as f:
                data = json.load(f)
            for theme in data.get("themes", []):
                name = theme.get("name", "")
                if name:
                    if name not in history:
                        history[name] = []
                    history[name].append({
                        "week": week_id,
                        "score": theme.get("composite_score", 0),
                        "classification": theme.get("classification", ""),
                    })
        except (json.JSONDecodeError, KeyError):
            continue

    return history


def load_chart_manifest() -> Dict[str, str]:
    """Load chart manifest mapping tickers to file paths."""
    manifest_path = CHARTS_DIR / "chart_manifest.json"
    if manifest_path.exists():
        try:
            with open(manifest_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, KeyError):
            pass
    return {}


# ── Functions moved from newsletter_compiler.py ──────────────────────────────

def load_dd_results() -> tuple:
    """Load DD results from signals.json.

    Returns:
        tuple: (dd_results_text, pass_signal_count)
    """
    # Try current/ folder first
    signals_file = None
    if OUTPUT_PATHS_AVAILABLE:
        signals_file = get_scanner_current_dir() / "signals.json"
        if not signals_file.exists():
            signals_file = SIGNALS_FILE
    else:
        signals_file = SIGNALS_FILE

    if not signals_file.exists():
        return "", 0

    with open(signals_file, 'r') as f:
        data = json.load(f)

    buy_signals = data.get("buy_signals", [])

    # Count PASS signals (not CONSIDER) - CRIT-1: Use PASS, keep TRADE for backwards compat
    pass_signals = [s for s in buy_signals if s.get("final_decision") in ["PASS", "TRADE"]]
    pass_count = len(pass_signals)

    # Handle zero PASS signals case
    if pass_count == 0:
        return "[No PASS signals this week - themes-only newsletter]", 0

    lines = []
    for signal in buy_signals:
        decision = signal.get("final_decision", "")
        symbol = signal.get("symbol", "???")

        # Build header with verdict/decision
        verdict = signal.get("dd_verdict", decision or "N/A")
        lines.append(f"### {symbol} - {verdict}")

        # Core DD fields
        if signal.get("dd_conviction"):
            lines.append(f"- **Conviction:** {signal['dd_conviction']}/10")
        elif signal.get("conviction"):
            lines.append(f"- **Conviction:** {signal['conviction']}/10")
        if signal.get("dd_position_size"):
            lines.append(f"- **Position Size:** {signal['dd_position_size']}")

        # Deep DD fields (written by scanner but previously ignored)
        if signal.get("dd_elevator_pitch"):
            lines.append(f"- **The Pitch:** {signal['dd_elevator_pitch']}")
        if signal.get("dd_why_now"):
            lines.append(f"- **Why Now:** {signal['dd_why_now']}")
        if signal.get("dd_the_math"):
            lines.append(f"- **The Math:** {signal['dd_the_math']}")
        if signal.get("dd_bear_case"):
            lines.append(f"- **Bear Case:** {signal['dd_bear_case']}")
        if signal.get("dd_risk_to_monitor"):
            lines.append(f"- **Risk to Monitor:** {signal['dd_risk_to_monitor']}")
        if signal.get("dd_action"):
            lines.append(f"- **Action:** {signal['dd_action']}")

        # Investment Gate fields (fallback context)
        if signal.get("gate_math"):
            lines.append(f"- **Return Path:** {signal['gate_math']}")
        if signal.get("gate_bear_case"):
            lines.append(f"- **Gate Bear Case:** {signal['gate_bear_case']}")

        # Legacy fields
        if signal.get("dd_key_catalyst"):
            lines.append(f"- **Key Catalyst:** {signal['dd_key_catalyst']}")
        if signal.get("dd_fatal_flaw"):
            lines.append(f"- **Fatal Flaw:** {signal['dd_fatal_flaw']}")

        # Bullish/risk factors
        if signal.get("bullish_factors"):
            lines.append("- **Bullish Factors:** " + "; ".join(signal["bullish_factors"]))
        if signal.get("risk_factors"):
            lines.append("- **Risk Factors:** " + "; ".join(signal["risk_factors"]))

        lines.append("")

    return "\n".join(lines) if lines else "[DD not yet run]", pass_count


def load_theme_details() -> str:
    """Load theme sub-score details from signals.json.

    Extracts composite_score, catalyst_score, momentum_score, crowding_score,
    runway_score plus thesis_summary, key_catalysts, and classification for
    each theme discovered by the thematic analyzer.

    Returns:
        Formatted markdown table with theme sub-score breakdown.
    """
    # Find signals.json
    signals_file = None
    if OUTPUT_PATHS_AVAILABLE:
        signals_file = get_scanner_current_dir() / "signals.json"
        if not signals_file.exists():
            signals_file = SIGNALS_FILE
    else:
        signals_file = SIGNALS_FILE

    if not signals_file.exists():
        return ""

    with open(signals_file, 'r') as f:
        data = json.load(f)

    themes = data.get("themes", [])
    if not themes:
        return ""

    lines = [
        "### Theme Sub-Scores",
        "",
        "| Theme | Class | Composite | Catalyst | Momentum | Crowding | Runway |",
        "|-------|-------|-----------|----------|----------|----------|--------|",
    ]

    for theme in themes:
        name = theme.get("name", "Unknown")
        classification = theme.get("classification", "N/A")
        composite = theme.get("composite_score", 0)
        catalyst = theme.get("catalyst_score", 0)
        momentum = theme.get("momentum_score", 0)
        crowding = theme.get("crowding_score", 0)
        runway = theme.get("runway_score", 0)

        lines.append(
            f"| {name} | {classification} | {composite:.1f} | "
            f"{catalyst:.1f} | {momentum:.1f} | {crowding:.1f} | {runway:.1f} |"
        )

    lines.append("")

    # Add thesis summaries and catalysts for PRIME/INVESTABLE themes
    top_themes = [t for t in themes if t.get("classification") in ("PRIME", "INVESTABLE")]
    if top_themes:
        lines.append("#### Top Theme Details")
        lines.append("")
        for theme in top_themes:
            name = theme.get("name", "Unknown")
            thesis = theme.get("thesis_summary", "")
            catalysts = theme.get("key_catalysts", [])

            lines.append(f"**{name}** ({theme.get('classification', 'N/A')})")
            if thesis:
                lines.append(f"- Thesis: {thesis}")
            if catalysts:
                lines.append(f"- Key Catalysts: {', '.join(catalysts[:3])}")
            lines.append("")

    return "\n".join(lines)


def calculate_portfolio_ytd_return() -> float:
    """Calculate portfolio YTD return from portfolio.csv."""
    portfolio_file = PORTFOLIO_FILE
    if not portfolio_file.exists():
        return 0.0

    try:
        import yfinance as yf

        total_pnl_pct = 0.0
        open_count = 0

        with open(portfolio_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('status') == 'OPEN':
                    ticker = row.get('ticker', '')
                    entry_price = float(row.get('entry_price') or 0)

                    if ticker and entry_price > 0:
                        try:
                            # Get current price
                            stock = yf.Ticker(ticker)
                            current_price = stock.info.get('regularMarketPrice') or stock.info.get('currentPrice', 0)

                            if current_price > 0:
                                pnl_pct = ((current_price / entry_price) - 1) * 100
                                total_pnl_pct += pnl_pct
                                open_count += 1
                        except Exception:
                            pass

        if open_count > 0:
            return total_pnl_pct / open_count  # Average return across positions

    except ImportError:
        print("  Note: yfinance not available for portfolio calculation")
    except Exception as e:
        print(f"  Warning: Could not calculate portfolio return: {e}")

    return 0.0


def generate_benchmark_comparison() -> str:
    """Generate Performance vs Benchmark using compounding returns since inception.

    Uses the EquityTracker compounding model (£5k per position, profits reinvested)
    for an accurate since-inception comparison vs SPY. Falls back to YTD average
    if the compounding summary is unavailable.
    """
    # Try compounding returns first (accurate since-inception)
    compounding = None
    try:
        from portfolio.manager import PortfolioManager
        pm = PortfolioManager()
        pm.update_prices()
        compounding = pm.get_compounding_summary()
    except Exception:
        pass

    if compounding and compounding.get('inception_date'):
        portfolio_return = compounding['total_return_pct']
        spy_return = compounding['spy_return_pct']
        alpha_spy = compounding['alpha_pct']
        qqq_return = compounding.get('qqq_return_pct', 0.0)
        alpha_qqq = compounding.get('alpha_vs_qqq_pct', 0.0)

        # Get max drawdown if available
        max_dd = None
        try:
            max_dd = pm.et.get_max_drawdown() if hasattr(pm, 'et') else None
        except Exception:
            pass

        lines = [
            "### Performance vs Benchmark (Since Inception)",
            "",
            "| Metric | Return |",
            "|--------|--------|",
            f"| **Portfolio (Compounding)** | {portfolio_return:+.1f}% |",
            f"| **S&P 500** | {spy_return:+.1f}% |",
            f"| **Alpha vs S&P 500** | {alpha_spy:+.1f}% |",
            f"| **NASDAQ (QQQ)** | {qqq_return:+.1f}% |",
            f"| **Alpha vs NASDAQ** | {alpha_qqq:+.1f}% |",
        ]

        if max_dd is not None:
            lines.append(f"| **Max Drawdown** | {max_dd:+.1f}% |")

        lines.append(f"| **Since** | {compounding['inception_date']} |")
        lines.append("")

        if alpha_spy > 0:
            lines.append(f"*Outperforming the S&P 500 by {alpha_spy:.1f}pp and NASDAQ by {alpha_qqq:.1f}pp since inception.*")
        elif alpha_spy < 0 and alpha_qqq < 0:
            lines.append(f"*Underperforming SPY by {abs(alpha_spy):.1f}pp since inception. Staying disciplined.*")
        else:
            lines.append("*Tracking the market benchmarks.*")
        lines.append("")
        return "\n".join(lines)

    # Fallback to YTD comparison
    portfolio_return = calculate_portfolio_ytd_return()
    spy_return = get_spy_ytd_return() if get_spy_ytd_return else 0.0
    alpha = portfolio_return - spy_return

    lines = [
        "### Performance vs Benchmark",
        "",
        "| Metric | Return |",
        "|--------|--------|",
        f"| **Portfolio YTD** | {portfolio_return:+.1f}% |",
        f"| **SPY YTD** | {spy_return:+.1f}% |",
        f"| **Alpha** | {alpha:+.1f}% |",
        "",
    ]

    if alpha > 0:
        lines.append(f"*Outperforming the S&P 500 by {alpha:.1f} percentage points.*")
    elif alpha < 0:
        lines.append(f"*Underperforming SPY by {abs(alpha):.1f}pp. Staying disciplined - process over short-term results.*")
    else:
        lines.append("*Tracking the market benchmark.*")

    lines.append("")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# CONTENT CONTEXT BUILDER
# ═══════════════════════════════════════════════════════════════════════════════

def build_content_context(signals_path: Optional[Path] = None) -> ContentContext:
    """Build the full content context from all available data sources."""
    ctx = ContentContext()

    # Load signals
    ctx.signals = load_signals(signals_path)
    ctx.themes = ctx.signals.get("themes", [])
    ctx.buy_signals = [
        s for s in ctx.signals.get("buy_signals", [])
        if s.get("final_decision", "").upper() in ("PASS", "TRADE", "STRONG_BUY", "SPEC_BUY")
    ]
    ctx.assessed_signals = ctx.signals.get("assessed_signals", ctx.signals.get("all_assessed", []))
    ctx.scan_stats = ctx.signals.get("stats", {})
    ctx.pass_count = len(ctx.buy_signals)

    # Week number
    ctx.week_number = datetime.now().isocalendar()[1]

    # Market analysis
    ctx.market_analysis = load_market_analysis()

    # Portfolio
    ctx.historical_winners = load_portfolio_winners()
    ctx.portfolio_stats = load_equity_curve()

    # Benchmark comparison — now a local function
    try:
        ctx.benchmark = generate_benchmark_comparison()
    except Exception:
        ctx.benchmark = ""

    # Theme details — now a local function
    try:
        ctx.theme_details = load_theme_details()
    except Exception:
        ctx.theme_details = ""

    # Historical themes for trend analysis
    ctx.theme_history = load_historical_themes()

    # Charts
    ctx.chart_manifest = load_chart_manifest()

    return ctx


# ═══════════════════════════════════════════════════════════════════════════════
# FORMAT HELPERS (for LLM prompts and context docs)
# ═══════════════════════════════════════════════════════════════════════════════

def _format_themes_for_prompt(themes: List[Dict]) -> str:
    """Format theme data for inclusion in LLM prompts."""
    if not themes:
        return "No themes identified this week."

    lines = []
    for t in themes:
        name = t.get("name", "Unknown")
        classification = t.get("classification", "")
        score = t.get("composite_score", 0)
        thesis = t.get("thesis_summary", "")[:400]
        catalysts = t.get("key_catalysts", [])
        cat_str = "; ".join(catalysts[:3]) if catalysts else "None identified"
        lines.append(f"- **{name}** ({classification}, {score}/10): {thesis}\n  Catalysts: {cat_str}")

    return "\n".join(lines)


def _format_signals_for_prompt(signals: List[Dict]) -> str:
    """Format buy signals for inclusion in LLM prompts."""
    if not signals:
        return "[No new GREEN signals this week — the system found zero stocks that cleared all gates]"

    lines = []
    for s in signals:
        ticker = s.get("symbol", "???")
        price = s.get("price", 0)
        theme = s.get("theme", "")
        conv = s.get("dd_conviction", s.get("conviction", 0))
        conv_text = get_conviction_text(conv) or "Watching"
        pitch = s.get("dd_elevator_pitch", s.get("catalyst_summary", ""))[:300]
        lines.append(f"- **${ticker}** at ${price:.2f} | Theme: {theme} | Outlook: {conv_text}\n  {pitch}")

    return "\n".join(lines)


def _format_winners_for_prompt(winners: List[Dict]) -> str:
    """Format positions for inclusion in LLM prompts (full transparency)."""
    if not winners:
        return "No open positions currently."

    lines = []
    for w in winners[:6]:
        ticker = w["ticker"]
        pnl = w["pnl_pct"]
        theme = w.get("theme", "")
        pnl_str = f"+{pnl:.1f}%" if pnl >= 0 else f"{pnl:.1f}%"
        lines.append(f"- ${ticker}: ${w['entry_price']:.2f} entry, {pnl_str} ({theme})")

    return "\n".join(lines)


def _format_assessed_for_prompt(assessed: List[Dict]) -> str:
    """Format assessed-but-failed signals for 'why we passed' content."""
    if not assessed:
        return ""

    lines = []
    for s in assessed[:5]:
        ticker = s.get("symbol", "???")
        decision = s.get("final_decision", "")
        reason = s.get("dd_fatal_flaw", s.get("reasoning", ""))[:200]
        if decision.upper() in ("FAIL", "NO_GO", "NO GO"):
            lines.append(f"- ${ticker}: Did not clear our screening — {reason}")

    return "\n".join(lines) if lines else ""


def _format_equity_stats(stats: Dict) -> str:
    """Format equity curve stats for prompts."""
    if not stats:
        return "Portfolio statistics not available."

    lines = [
        f"- Portfolio Return: +{stats.get('total_return_pct', 0):.1f}%",
        f"- S&P 500 Return: {stats.get('spy_return_pct', 0):+.1f}%",
        f"- Alpha vs SPY: +{stats.get('alpha_pct', 0):.1f}%",
    ]
    if stats.get("qqq_return_pct"):
        lines.append(f"- NASDAQ Return: {stats['qqq_return_pct']:+.1f}%")
        lines.append(f"- Alpha vs NASDAQ: +{stats.get('alpha_vs_qqq_pct', 0):.1f}%")
    lines.append(f"- Open Positions: {stats.get('open_count', 0)}")
    return "\n".join(lines)


def _format_theme_history(theme_name: str, history: Dict) -> str:
    """Format theme trend data across weeks."""
    if theme_name not in history:
        return "First appearance this week — no prior history."

    entries = history[theme_name]
    scores = [e["score"] for e in entries]
    if len(scores) < 2:
        return f"Appeared in {len(scores)} prior week(s). Latest score: {scores[-1]}/10."

    trend = "rising" if scores[-1] > scores[0] else "falling" if scores[-1] < scores[0] else "stable"
    avg = sum(scores) / len(scores)
    return f"Trend over {len(scores)} weeks: {trend} (avg {avg:.1f}/10, latest {scores[-1]}/10)"


# ═══════════════════════════════════════════════════════════════════════════════
# TEXT SANITIZATION & VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

def sanitize_text(text: str) -> str:
    """Replace internal terminology with public-facing alternatives."""
    if not text:
        return text
    for internal, public in INTERNAL_TERMINOLOGY_MAP.items():
        pattern = re.compile(re.escape(internal), re.IGNORECASE)
        text = pattern.sub(public, text)
    return text


def scrub_llm_output(text: str) -> str:
    """Post-LLM scrub for content cleanup.

    Transparency mode: negative P&L and STOPPED mentions are allowed
    (shown with positive framing). Only clean up formatting issues.
    """
    if not text:
        return text

    # Clean up any triple+ blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


def validate_post_content(text: str) -> Tuple[bool, List[str]]:
    """Validate post content for banned terms and marketing compliance."""
    issues = []

    # Check banned phrases
    violations = check_banned_phrases(text)
    if violations:
        issues.extend(violations)

    # Negative P&L and STOPPED mentions are allowed (transparency policy)

    # Validate via marketing vocabulary
    is_valid, term_issues = validate_content(text)
    if not is_valid:
        issues.extend(term_issues)

    return (len(issues) == 0, issues)


# ═══════════════════════════════════════════════════════════════════════════════
# VISUAL ELEMENT HELPERS (HTML components injected post-LLM)
# ═══════════════════════════════════════════════════════════════════════════════

def build_scan_funnel_html(stats: Dict) -> str:
    """Build HTML scan funnel visualization from scanner stats."""
    tickers = stats.get("tickers_loaded", 0)
    technical = stats.get("technical_signals", stats.get("buy_signal", 0))
    theme_confirmed = stats.get("theme_confirmed", 0)
    final = stats.get("final_trade", 0)

    stages = [
        ("Universe", tickers, "#6366F1"),
        ("Technical Gates", technical, "#8B5CF6"),
        ("Theme Confirmed", theme_confirmed, "#A78BFA"),
        ("GREEN Signals", final, "#22C55E"),
    ]

    html = '<div style="margin: 24px 0;">\n'
    max_val = max(tickers, 1)
    for label, value, color in stages:
        width_pct = max(int((value / max_val) * 100), 4)
        html += f'''  <div style="display: flex; align-items: center; margin: 6px 0;">
    <div style="width: 140px; font-size: 13px; color: #666; text-align: right; padding-right: 12px;">{label}</div>
    <div style="background: {color}; height: 30px; width: {width_pct}%; border-radius: 4px; display: flex; align-items: center; padding: 0 12px;">
      <span style="color: white; font-weight: 700; font-size: 13px;">{value:,}</span>
    </div>
  </div>\n'''
    html += '</div>\n'
    return html


def build_theme_scores_html(themes: List[Dict]) -> str:
    """Build HTML theme score cards with progress bars."""
    if not themes:
        return ""

    html = ""
    for theme in themes[:4]:  # Top 4 themes
        name = theme.get("name", "Unknown")
        classification = theme.get("classification", "")
        composite = theme.get("composite_score", 0)
        catalyst = theme.get("catalyst_score", 0)
        momentum = theme.get("momentum_score", 0)
        thesis = theme.get("thesis_summary", "")[:300]

        badge_color = "#22C55E" if classification == "PRIME" else "#F59E0B"

        html += f'''<div style="background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 10px; padding: 20px; margin: 16px 0;">
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
    <strong style="font-size: 16px;">{name}</strong>
    <span style="background: {badge_color}; color: white; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: 700;">{classification}</span>
  </div>
  <div style="font-size: 28px; font-weight: 800; color: #1a1a1a;">{composite}<span style="font-size: 14px; color: #666;">/10</span></div>
  <div style="display: flex; gap: 16px; margin: 12px 0;">
    <div style="flex: 1;">
      <div style="font-size: 11px; color: #666; text-transform: uppercase;">Catalyst</div>
      <div style="background: #e5e7eb; height: 6px; border-radius: 3px; margin-top: 4px;">
        <div style="background: {badge_color}; height: 6px; border-radius: 3px; width: {min(catalyst * 10, 100)}%;"></div>
      </div>
    </div>
    <div style="flex: 1;">
      <div style="font-size: 11px; color: #666; text-transform: uppercase;">Momentum</div>
      <div style="background: #e5e7eb; height: 6px; border-radius: 3px; margin-top: 4px;">
        <div style="background: {badge_color}; height: 6px; border-radius: 3px; width: {min(momentum * 10, 100)}%;"></div>
      </div>
    </div>
  </div>
  <p style="color: #666; font-size: 14px; margin: 8px 0 0 0;">{thesis}</p>
</div>\n'''

    return html


def build_winners_table_html(winners: List[Dict]) -> str:
    """Build HTML table showcasing winning positions."""
    if not winners:
        return ""

    html = '<table style="width: 100%; border-collapse: collapse; margin: 16px 0;">\n'
    html += '<tr style="background: #f5f5f5;"><th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Ticker</th>'
    html += '<th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Theme</th>'
    html += '<th style="padding: 10px; text-align: right; border: 1px solid #ddd;">P&L</th></tr>\n'

    for w in winners[:8]:
        ticker = w["ticker"]
        pnl = w["pnl_pct"]
        theme = w.get("theme", "")
        entry_str = f" (${w['entry_price']:.2f} entry)"
        html += f'<tr><td style="padding: 10px; border: 1px solid #ddd; font-weight: 700;">${ticker}{entry_str}</td>'
        html += f'<td style="padding: 10px; border: 1px solid #ddd;">{theme}</td>'
        html += f'<td style="padding: 10px; border: 1px solid #ddd; text-align: right; color: #16a34a; font-weight: 700;">+{pnl:.1f}%</td></tr>\n'

    html += '</table>\n'
    return html


def inject_visual_elements(md_content: str, ctx: ContentContext) -> str:
    """Replace visual element markers in markdown with HTML components."""
    # Scan funnel
    if "[SCAN_FUNNEL]" in md_content:
        funnel_html = build_scan_funnel_html(ctx.scan_stats)
        md_content = md_content.replace("[SCAN_FUNNEL]", funnel_html)

    # Theme scores
    if "[THEME_SCORES]" in md_content:
        scores_html = build_theme_scores_html(ctx.themes)
        md_content = md_content.replace("[THEME_SCORES]", scores_html)

    # Winners table
    if "[WINNERS_TABLE]" in md_content:
        winners_html = build_winners_table_html(ctx.historical_winners)
        md_content = md_content.replace("[WINNERS_TABLE]", winners_html)

    return md_content
