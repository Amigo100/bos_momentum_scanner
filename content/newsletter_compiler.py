#!/usr/bin/env python3
"""
STERLING SIGNALS - NEWSLETTER COMPILER
======================================
Compiles the full newsletter with automated market analysis, DD integration,
and chart embedding. Converts to HTML for Substack.

Usage:
    python newsletter_compiler.py              # Generate HTML from latest briefing
    python newsletter_compiler.py --full       # Full automated pipeline (market + compile)
    python newsletter_compiler.py --preview    # Open in browser for preview
"""

import argparse
import base64
import json
import os
import re
import sys
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

try:
    import anthropic
except ImportError:
    anthropic = None

# Import output path helpers
try:
    from config.output_paths import (
        get_current_dir,
        get_week_dir,
        ensure_output_structure,
        get_relative_path
    )
    OUTPUT_PATHS_AVAILABLE = True
except ImportError:
    OUTPUT_PATHS_AVAILABLE = False

# Import banned terms (single source of truth)
from config.banned_terms import ALL_BANNED as BANNED_TERMS

# Import marketing vocabulary for validation
try:
    from config.marketing_vocabulary import validate_content
    MARKETING_VOCABULARY_AVAILABLE = True
except ImportError:
    MARKETING_VOCABULARY_AVAILABLE = False

# Import canonical SPY benchmark function
try:
    from core.portfolio_manager import get_spy_ytd_return
except ImportError:
    get_spy_ytd_return = None

TRADES_DIR = Path(__file__).resolve().parent.parent / "trades"
CHARTS_DIR = TRADES_DIR / "charts"

# Sterling Signals branding
SUBSTACK_URL = "https://sterlingsignals.substack.com"
NEWSLETTER_NAME = "Sterling Signals"


# ═══════════════════════════════════════════════════════════════════════════════
# LLM NEWSLETTER COMPILATION
# ═══════════════════════════════════════════════════════════════════════════════

COMPILATION_SYSTEM = """You are the editor of Sterling Signals, a weekly momentum trading newsletter on Substack for US active investors and swing traders.

Your job is to compile a polished, publication-ready newsletter from the raw inputs provided.

STYLE:
- Professional but accessible
- Data-driven with specific numbers
- Confident without being arrogant
- Educational - explain WHY, not just WHAT
- US investor perspective
- Reference SPY/QQQ comparison when outperforming
- Use "GREEN signal" branding (not "PASS signal")

CRITICAL MARKETING RULES:
- NEVER mention losing positions or underwater trades
- NEVER show full portfolio with individual P&L
- Only showcase wins above 15% threshold
- If benchmark comparison is negative, focus on methodology instead
- Celebrate big wins (25%+, 50%+, 100%+) prominently

HANDLING ZERO SIGNALS WEEK:
When there are no PASS/GREEN signals this week:
- This is NORMAL and shows the system's selectivity - NOT a failure
- Focus the newsletter on themes, market analysis, and watchlist stocks
- Skip the "NEW TRADES THIS WEEK" section entirely
- Use subject line: "Week ${WEEK_NUM}: No New Signals | ${THEME_HOOK}"
- Emphasize: "Sometimes the best trade is no trade"
- Highlight watchlist/CONSIDER stocks that almost made it
- Explain what would need to change for them to become GREEN signals

SUBJECT LINE FORMULA:
Week ${WEEK_NUM}: ${NEW_SIGNALS} GREEN Signals | ${HOOK_PHRASE}
Example: "Week 4: 3 GREEN Signals | Why Power Grid is 2026's Winning Theme"
Focus on new signals and hot themes, not P&L.

FORMAT:
- Use markdown formatting
- Keep it scannable with headers and bullets
- Use tables for data comparison
- Target 1,500-2,500 words
- 8-12 minute read time
- Show ALL GREEN signals (not limited to 1)"""

COMPILATION_PROMPT = '''Compile the weekly Sterling Signals newsletter from these inputs:

## MARKET CONTEXT
{market_context}

## SCANNER BRIEFING (Themes & Signals)
{scanner_briefing}

## THEME DETAILS (Sub-Scores)
{theme_details}

## DUE DILIGENCE RESULTS
{dd_results}

## WIN HIGHLIGHTS (only show if we have winners above 15%)
{portfolio_status}

## PERFORMANCE VS BENCHMARK
{benchmark_comparison}

---

## REQUIRED SECTIONS

**1. TITLE & HOOK**
- Compelling title capturing this week's key theme
- Subtitle/hook in one line

**2. MARKET CONTEXT**
- Use the market context provided (light editing only)

**3. HOT THEMES THIS WEEK** 🔥
- PRIME and INVESTABLE themes with scores
- Why each theme is hot NOW
- Key stocks benefiting

**4. COLD THEMES** ❄️
- SELECTIVE and AVOID themes
- Why these are cooling off

**5. NEW TRADES THIS WEEK** 🎯
(SKIP THIS SECTION if no PASS signals - see below for themes-only format)
For each DD-PASS signal, include ALL available DD fields:
- Ticker & company name
- DD Verdict (GREEN signal / GREEN signal speculative)
- **The Pitch:** elevator pitch for why this stock (from dd_elevator_pitch)
- **Why Now:** catalyst timing and urgency (from dd_why_now)
- **The Math:** path to 50%+ return with specific numbers (from dd_the_math)
- **Bear Case:** the bear thesis AND why it's wrong (from dd_bear_case)
- **Risk to Monitor:** the single biggest risk to watch (from dd_risk_to_monitor)
- **Action:** entry recommendation (from dd_action)
- Entry price, position size, conviction
- [CHART: TICKER] placeholder

**5-ALT. NO NEW SIGNALS THIS WEEK** 🎯
(USE THIS SECTION ONLY if there are zero PASS signals)
- Explain this shows the system's selectivity
- "Sometimes the best trade is no trade"
- Highlight what the system filtered out and why
- Focus on patience and discipline

**6. SIGNALS THAT FAILED DD** ⚠️
For each NO GO:
- Ticker and why it failed
- Fatal flaw identified
- What would change our mind

**7. WATCHLIST** (CONSIDER signals)
- Stocks worth watching
- Why waiting
- What triggers entry

**8. WIN HIGHLIGHTS** (conditional - only if we have winners above 15%)
- Showcase closed trades with gains above 15%
- Celebrate big wins (25%+, 50%+, 100%+)
- DO NOT mention any losing positions or current P&L
- Focus on the system working, not individual losses

**9. LOOKING AHEAD**
- Next week's catalysts
- Key events to watch

**10. FOOTER**
- Disclaimer
- Next scan date: Friday after market close
- Subscribe link

---

Generate the complete newsletter in markdown, ready for Substack.'''


def compile_newsletter_llm(
    market_context: str,
    scanner_briefing: str,
    dd_results: str,
    portfolio_status: str,
    benchmark_comparison: str = "",
    theme_details: str = ""
) -> str:
    """Use Claude to compile the full newsletter."""
    if anthropic is None:
        return None

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("  ⚠️ ANTHROPIC_API_KEY not set - skipping LLM compilation")
        return None

    client = anthropic.Anthropic(api_key=api_key)

    prompt = COMPILATION_PROMPT.format(
        market_context=market_context or "[No market context available]",
        scanner_briefing=scanner_briefing or "[No scanner briefing available]",
        theme_details=theme_details or "[No theme sub-score data available]",
        dd_results=dd_results or "[No DD results available]",
        portfolio_status=portfolio_status or "[No portfolio data available]",
        benchmark_comparison=benchmark_comparison or "[No benchmark data available]"
    )

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=6000,
            system=COMPILATION_SYSTEM,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text

    except Exception as e:
        print(f"  ⚠️ LLM compilation error: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════════

def load_market_analysis() -> str:
    """Load the market analysis file."""
    # Try current/ folder first, then legacy location
    if OUTPUT_PATHS_AVAILABLE:
        current_dir = get_current_dir()
        market_file = current_dir / "market_analysis.md"
        if market_file.exists():
            with open(market_file, 'r') as f:
                content = f.read()
                if "## 📊 Market Context" in content:
                    return content[content.index("## 📊 Market Context"):]
                return content

    # Fallback to trades/current/
    market_file = TRADES_DIR / "current" / "market_analysis.md"
    if market_file.exists():
        with open(market_file, 'r') as f:
            content = f.read()
            if "## 📊 Market Context" in content:
                return content[content.index("## 📊 Market Context"):]
            return content
    return ""


def load_scanner_briefing() -> str:
    """Load the scanner briefing file."""
    # Try current/ folder first, then legacy location
    if OUTPUT_PATHS_AVAILABLE:
        current_dir = get_current_dir()
        briefing_file = current_dir / "newsletter_briefing.md"
        if briefing_file.exists():
            with open(briefing_file, 'r') as f:
                return f.read()

    # Fallback to legacy location (trades/current/)
    briefing_file = TRADES_DIR / "current" / "newsletter_briefing.md"
    if briefing_file.exists():
        with open(briefing_file, 'r') as f:
            return f.read()
    return ""


def load_dd_results() -> tuple[str, int]:
    """Load DD results from signals.json.

    Returns:
        tuple: (dd_results_text, pass_signal_count)
    """
    # Try current/ folder first
    signals_file = None
    if OUTPUT_PATHS_AVAILABLE:
        current_dir = get_current_dir()
        signals_file = current_dir / "signals.json"
        if not signals_file.exists():
            signals_file = None

    # Fallback to legacy location
    if signals_file is None:
        signals_file = TRADES_DIR / "signals.json"

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
        current_dir = get_current_dir()
        signals_file = current_dir / "signals.json"
        if not signals_file.exists():
            signals_file = None

    if signals_file is None:
        signals_file = TRADES_DIR / "signals.json"

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


def load_portfolio_status() -> str:
    """Load WIN HIGHLIGHTS only (no portfolio display per marketing overhaul).

    Per marketing safeguards:
    - NEVER show losing positions publicly
    - Only show closed trades with gains above 15%
    - Focus on wins, not current portfolio status
    """
    portfolio_file = TRADES_DIR / "portfolio.csv"
    if not portfolio_file.exists():
        return ""

    import csv

    # Import threshold from config
    try:
        from config import MARKETING_THRESHOLDS
        min_win = MARKETING_THRESHOLDS.get('min_win_to_highlight', 15.0)
    except ImportError:
        min_win = 15.0

    # Find closed trades with positive P&L above threshold
    winners = []

    with open(portfolio_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('status') in ['CLOSED', 'STOPPED']:
                try:
                    entry = float(row.get('entry_price') or 0)
                    exit_price = float(row.get('exit_price') or 0)
                    if entry > 0 and exit_price > 0:
                        pnl_pct = ((exit_price / entry) - 1) * 100
                        if pnl_pct >= min_win:
                            winners.append({
                                'ticker': row['ticker'],
                                'pnl_pct': pnl_pct,
                                'theme': row.get('theme', 'N/A'),
                                'exit_date': row.get('exit_date', '')
                            })
                except (ValueError, TypeError):
                    pass

    if not winners:
        return ""  # No win highlights to show

    # Sort by P&L descending and take top 5
    winners = sorted(winners, key=lambda x: x['pnl_pct'], reverse=True)[:5]

    lines = ["### Win Highlights", ""]
    lines.append("Recent closed trades above 15% gain:")
    lines.append("")
    lines.append("| Ticker | Return | Theme |")
    lines.append("|--------|--------|-------|")

    for w in winners:
        lines.append(f"| ${w['ticker']} | +{w['pnl_pct']:.1f}% | {w['theme']} |")

    lines.append("")
    lines.append("*Our 5-gate system identifies momentum opportunities.*")

    return "\n".join(lines)


# get_spy_ytd_return imported from portfolio_manager (canonical implementation)


def calculate_portfolio_ytd_return() -> float:
    """Calculate portfolio YTD return from portfolio.csv."""
    portfolio_file = TRADES_DIR / "portfolio.csv"
    if not portfolio_file.exists():
        return 0.0

    try:
        import csv
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
        from core.portfolio_manager import PortfolioManager
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
    spy_return = get_spy_ytd_return()
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


def load_chart_manifest() -> Dict[str, str]:
    """Load the chart manifest."""
    # Try current/ folder first
    if OUTPUT_PATHS_AVAILABLE:
        current_dir = get_current_dir()
        manifest_file = current_dir / "charts" / "chart_manifest.json"
        if manifest_file.exists():
            with open(manifest_file, 'r') as f:
                data = json.load(f)
                return data.get("charts", {})

    # Fallback to legacy location
    manifest_file = CHARTS_DIR / "chart_manifest.json"
    if manifest_file.exists():
        with open(manifest_file, 'r') as f:
            data = json.load(f)
            return data.get("charts", {})
    return {}


# ═══════════════════════════════════════════════════════════════════════════════
# MARKDOWN TO HTML CONVERSION
# ═══════════════════════════════════════════════════════════════════════════════

def get_chart_as_base64(ticker: str, chart_manifest: Dict[str, str]) -> Optional[str]:
    """Get chart image as base64 for embedding."""
    if ticker not in chart_manifest:
        return None

    chart_path = Path(chart_manifest[ticker])
    if not chart_path.exists():
        # Try relative to CHARTS_DIR
        chart_path = CHARTS_DIR / chart_path.name
        if not chart_path.exists():
            return None

    with open(chart_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def markdown_to_html(md_content: str, chart_manifest: Dict[str, str] = None) -> str:
    """Convert markdown to Substack-friendly HTML with embedded charts."""
    html = md_content
    chart_manifest = chart_manifest or {}

    # Remove the disclaimer section (we add it in template)
    html = re.sub(r'## 📝 Disclaimer.*?(?=---|\Z)', '', html, flags=re.DOTALL)

    # Remove the generated timestamp line
    html = re.sub(r'\*Generated:.*?\*', '', html)

    # Convert headers
    html = re.sub(r'^#### (.+)$', r'<h4>\1</h4>', html, flags=re.MULTILINE)
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)

    # Convert horizontal rules
    html = re.sub(r'^---+$', '<hr>', html, flags=re.MULTILINE)

    # Convert bold
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)

    # Convert italic
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)

    # Convert blockquotes (multi-line)
    def convert_blockquote(match):
        content = match.group(0)
        lines = content.split('\n')
        clean_lines = [re.sub(r'^>\s*', '', line) for line in lines]
        return '<blockquote>' + '<br>\n'.join(clean_lines) + '</blockquote>'

    html = re.sub(r'(?:^>.*$\n?)+', convert_blockquote, html, flags=re.MULTILINE)

    # Convert tables
    def convert_table(match):
        table_text = match.group(0)
        lines = [l.strip() for l in table_text.strip().split('\n') if l.strip()]

        if len(lines) < 2:
            return table_text

        # Parse header
        header_cells = [c.strip() for c in lines[0].split('|') if c.strip()]

        # Skip separator line and parse body
        body_rows = []
        for line in lines[2:]:  # Skip header and separator
            cells = [c.strip() for c in line.split('|') if c.strip()]
            if cells:
                body_rows.append(cells)

        # Build HTML table
        html_table = '<table>\n<thead><tr>'
        for cell in header_cells:
            html_table += f'<th>{cell}</th>'
        html_table += '</tr></thead>\n<tbody>'

        for row in body_rows:
            html_table += '<tr>'
            for cell in row:
                html_table += f'<td>{cell}</td>'
            html_table += '</tr>\n'

        html_table += '</tbody></table>'
        return html_table

    # Match markdown tables
    html = re.sub(r'(?:^\|.+\|$\n?)+', convert_table, html, flags=re.MULTILINE)

    # Convert unordered lists
    def convert_list(match):
        items = match.group(0)
        lines = items.strip().split('\n')
        html_list = '<ul>\n'
        for line in lines:
            item = re.sub(r'^[-*]\s+', '', line.strip())
            if item:
                html_list += f'<li>{item}</li>\n'
        html_list += '</ul>'
        return html_list

    html = re.sub(r'(?:^[-*]\s+.+$\n?)+', convert_list, html, flags=re.MULTILINE)

    # Convert chart placeholders to embedded images or placeholder boxes
    def convert_chart(match):
        ticker = match.group(1)
        chart_base64 = get_chart_as_base64(ticker, chart_manifest)

        if chart_base64:
            return f'''
<div style="margin: 20px 0;">
    <p><strong>📊 {ticker} Chart</strong></p>
    <img src="data:image/png;base64,{chart_base64}" alt="{ticker} Chart" style="max-width: 100%; border-radius: 8px; border: 1px solid #ddd;">
</div>'''
        else:
            # Check if chart file exists but not in manifest
            chart_files = list(CHARTS_DIR.glob(f"{ticker}_*.png")) if CHARTS_DIR.exists() else []
            if chart_files:
                latest_chart = sorted(chart_files)[-1]
                try:
                    with open(latest_chart, 'rb') as f:
                        chart_data = base64.b64encode(f.read()).decode('utf-8')
                    return f'''
<div style="margin: 20px 0;">
    <p><strong>📊 {ticker} Chart</strong></p>
    <img src="data:image/png;base64,{chart_data}" alt="{ticker} Chart" style="max-width: 100%; border-radius: 8px; border: 1px solid #ddd;">
</div>'''
                except (OSError, ValueError):
                    pass

            return f'''
<div style="background: #f0f0f0; border: 2px dashed #ccc; padding: 40px; text-align: center; margin: 20px 0; border-radius: 8px;">
    <strong>📊 {ticker} Chart</strong><br>
    <em>Chart image will be added here</em>
</div>'''

    # Match various chart placeholder formats
    html = re.sub(r'\[CHART:\s*([A-Z]+)\]', convert_chart, html)
    html = re.sub(r'📸\s*\*?\*?\[CHART:\s*([A-Z]+)\]\*?\*?.*', convert_chart, html)

    # Convert placeholder markers to callout boxes
    html = re.sub(
        r'\[PLACEHOLDER.*?\]',
        '<em>[Add content here]</em>',
        html
    )

    # Wrap paragraphs
    paragraphs = html.split('\n\n')
    wrapped = []
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        # Don't wrap if already an HTML element
        if p.startswith('<') or p.startswith('|'):
            wrapped.append(p)
        else:
            # Wrap plain text in <p> tags
            lines = p.split('\n')
            wrapped.append('<p>' + '<br>\n'.join(lines) + '</p>')

    html = '\n\n'.join(wrapped)

    # Clean up extra whitespace
    html = re.sub(r'\n{3,}', '\n\n', html)

    return html


# ═══════════════════════════════════════════════════════════════════════════════
# HTML TEMPLATE
# ═══════════════════════════════════════════════════════════════════════════════

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Sterling Signals - Weekly Newsletter</title>
    <style>
        /* These styles are for preview only - Substack uses its own */
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 680px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
            color: #333;
        }}
        h1 {{ color: #1a1a1a; border-bottom: 2px solid #333; padding-bottom: 10px; }}
        h2 {{ color: #333; margin-top: 30px; }}
        h3 {{ color: #444; }}
        h4 {{ color: #555; margin-top: 25px; }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 15px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 10px;
            text-align: left;
        }}
        th {{ background-color: #f5f5f5; font-weight: 600; }}
        blockquote {{
            border-left: 4px solid #333;
            margin: 20px 0;
            padding: 10px 20px;
            background: #f9f9f9;
            font-style: italic;
        }}
        .pass {{ color: #16a34a; font-weight: bold; }}
        .caution {{ color: #ca8a04; font-weight: bold; }}
        .fail {{ color: #dc2626; font-weight: bold; }}
        .bullish {{ color: #16a34a; }}
        .risk {{ color: #dc2626; }}
        hr {{ border: none; border-top: 1px solid #ddd; margin: 30px 0; }}
        ul {{ padding-left: 25px; }}
        li {{ margin: 8px 0; }}
        .chart-placeholder {{
            background: #f0f0f0;
            border: 2px dashed #ccc;
            padding: 40px;
            text-align: center;
            margin: 20px 0;
            border-radius: 8px;
        }}
        .chart-img {{
            max-width: 100%;
            border-radius: 8px;
            margin: 20px 0;
        }}
        img {{
            max-width: 100%;
            height: auto;
        }}
        .action-box {{
            background: #f0fdf4;
            border: 1px solid #16a34a;
            border-radius: 8px;
            padding: 15px;
            margin: 15px 0;
        }}
        .caution-box {{
            background: #fefce8;
            border: 1px solid #ca8a04;
            border-radius: 8px;
            padding: 15px;
            margin: 15px 0;
        }}
    </style>
</head>
<body>
{content}

<hr>
<p style="text-align: center; color: #666; font-size: 14px;">
    <em>This newsletter is for informational purposes only and does not constitute financial advice.</em><br>
    <em>All investment decisions should be made based on your own research and risk tolerance.</em><br><br>
    <strong>Subscribe for free:</strong> <a href="{substack_url}">{substack_url}</a>
</p>
</body>
</html>
"""


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN COMPILATION
# ═══════════════════════════════════════════════════════════════════════════════

def compile_newsletter(full_mode: bool = False, preview: bool = False) -> Path:
    """Compile the newsletter briefing to HTML."""

    print(f"\n{'═' * 60}")
    print(f"  NEWSLETTER COMPILER - Sterling Signals")
    print(f"{'═' * 60}")

    chart_manifest = load_chart_manifest()
    print(f"  📊 Charts available: {len(chart_manifest)}")

    if full_mode:
        # Full automated pipeline
        print("\n  🔄 Running full automated compilation...")

        # Step 1: Generate market analysis
        print("\n  Step 1: Market Analysis")
        market_analysis = load_market_analysis()
        if not market_analysis:
            print("    Generating market context via Claude...")
            try:
                from content.market_analyzer import run_market_analysis, save_market_analysis
                result = run_market_analysis()
                if result.success():
                    save_market_analysis(result.analysis)
                    market_analysis = result.analysis
                    print(f"    ✅ Generated (cost: ${result.cost:.3f})")
                else:
                    print(f"    ⚠️ Failed: {result.error}")
            except ImportError:
                print("    ⚠️ market_analyzer.py not found")
        else:
            print("    ✅ Loaded from file")

        # Step 2: Load scanner briefing
        print("\n  Step 2: Scanner Briefing")
        scanner_briefing = load_scanner_briefing()
        if scanner_briefing:
            print("    ✅ Loaded from file")
        else:
            print("    ⚠️ No briefing found - run scanner first")

        # Step 3: Load DD results
        print("\n  Step 3: Due Diligence Results")
        dd_results, pass_count = load_dd_results()
        if pass_count == 0:
            print("    ℹ️ No PASS signals this week - generating themes-only newsletter")
        elif dd_results and dd_results != "[DD not yet run]":
            print(f"    ✅ Loaded from signals.json ({pass_count} PASS signals)")
        else:
            print("    ⚠️ No DD results - run scanner with --web-search")

        # Step 4: Load portfolio status
        print("\n  Step 4: Portfolio Status")
        portfolio_status = load_portfolio_status()
        if portfolio_status:
            print("    ✅ Loaded from portfolio.csv")
        else:
            print("    ⚠️ No portfolio data")

        # Step 4b: Generate benchmark comparison
        print("\n  Step 4b: Benchmark Comparison (Portfolio vs SPY/QQQ)")
        benchmark_comparison = generate_benchmark_comparison()
        if benchmark_comparison:
            print("    ✅ Generated SPY + NASDAQ comparison")
        else:
            print("    ⚠️ No benchmark data")

        # Step 4c: Load theme sub-scores
        print("\n  Step 4c: Theme Sub-Scores")
        theme_details = load_theme_details()
        if theme_details:
            print("    ✅ Loaded theme sub-scores from signals.json")
        else:
            print("    ⚠️ No theme data available")

        # Step 5: LLM compilation
        print("\n  Step 5: LLM Newsletter Compilation")
        compiled_newsletter = compile_newsletter_llm(
            market_analysis,
            scanner_briefing,
            dd_results,
            portfolio_status,
            benchmark_comparison,
            theme_details
        )

        if compiled_newsletter:
            print("    ✅ Newsletter compiled via Claude")
            print("    🔍 Checking LLM output for negative P&L leakage...")
            md_content = compiled_newsletter
        else:
            print("    ⚠️ LLM compilation failed - using raw briefing")
            md_content = scanner_briefing

    else:
        # Simple mode - just convert briefing to HTML
        if OUTPUT_PATHS_AVAILABLE:
            briefing_path = get_current_dir() / "newsletter_briefing.md"
        else:
            briefing_path = TRADES_DIR / "current" / "newsletter_briefing.md"

        if not briefing_path.exists():
            print(f"  ❌ Briefing not found: {briefing_path}")
            print("     Run the scanner first: python -m core.scanner --web-search")
            return None

        print(f"  📄 Reading briefing: {briefing_path}")

        with open(briefing_path, 'r') as f:
            md_content = f.read()

    # Check for negative P&L — in --full mode this checks LLM output (should be clean);
    # in simple mode this checks the raw briefing (will contain P&L as expected)
    import re as _re
    negative_pnl_matches = _re.findall(r'-\d+\.?\d*%', md_content)
    stopped_mentions = _re.findall(r'\bSTOPPED\b', md_content)
    if negative_pnl_matches:
        print(f"\n  ⚠️ WARNING: Negative P&L found in newsletter: {negative_pnl_matches}")
        print("     Review before publishing — losses should not appear in public content.")
    if stopped_mentions:
        print(f"\n  ⚠️ WARNING: STOPPED positions mentioned in newsletter ({len(stopped_mentions)}x)")
        print("     Review before publishing — stopped positions should not be showcased.")

    # Validate content for banned marketing terms
    if MARKETING_VOCABULARY_AVAILABLE:
        print("\n  🔍 Validating content for banned terms...")
        is_valid, violations = validate_content(md_content)
        if not is_valid:
            print(f"  ⚠️ WARNING: Newsletter contains banned terms: {violations}")
            print("     Review recommended before publishing.")
        else:
            print("  ✅ Content passed vocabulary validation")

    # Convert to HTML
    print("\n  🔄 Converting to HTML...")
    html_content = markdown_to_html(md_content, chart_manifest)

    # Wrap in template
    full_html = HTML_TEMPLATE.format(
        content=html_content,
        substack_url=SUBSTACK_URL
    )

    # Save to current/ and weekly archive if available
    if OUTPUT_PATHS_AVAILABLE:
        current_dir, week_dir = ensure_output_structure()

        # Save to current/
        current_html = current_dir / "newsletter.html"
        with open(current_html, 'w') as f:
            f.write(full_html)

        # Save to weekly archive
        archive_html = week_dir / "newsletter.html"
        with open(archive_html, 'w') as f:
            f.write(full_html)

        print(f"\n  ✅ Newsletter compiled:")
        print(f"     • {get_relative_path(current_html)} (current)")
        print(f"     • {get_relative_path(archive_html)} (archived)")

    if not OUTPUT_PATHS_AVAILABLE:
        # Fallback: write to trades root if output_paths not available
        output_path = TRADES_DIR / "newsletter.html"
        with open(output_path, 'w') as f:
            f.write(full_html)
        print(f"\n  ✅ Newsletter compiled: {output_path}")

    # List embedded vs missing charts
    embedded_charts = [t for t in chart_manifest.keys()]
    if embedded_charts:
        print(f"\n  📊 Charts embedded: {', '.join(embedded_charts)}")

    # Check for chart placeholders that weren't filled
    missing_charts = re.findall(r'\[CHART:\s*([A-Z]+)\]', md_content)
    missing_charts = [t for t in missing_charts if t not in chart_manifest]
    if missing_charts:
        print(f"  ⚠️ Charts missing: {', '.join(missing_charts)}")
        print(f"     Run: python chart_capture.py --ticker {' '.join(missing_charts)}")

    print(f"\n  📋 Next steps:")
    print(f"     1. Open {output_path} in browser")
    print(f"     2. Copy the content (Cmd+A, Cmd+C)")
    print(f"     3. Paste into Substack editor")
    print(f"     4. Preview and publish!")

    if preview:
        print(f"\n  🌐 Opening preview in browser...")
        webbrowser.open(f"file://{output_path.absolute()}")

    print(f"\n{'═' * 60}\n")

    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compile newsletter briefing to HTML for Substack"
    )
    parser.add_argument(
        '--full', '-f',
        action='store_true',
        help='Full automated pipeline (market analysis + LLM compilation)'
    )
    parser.add_argument(
        '--preview', '-p',
        action='store_true',
        help='Open HTML in browser for preview'
    )

    args = parser.parse_args()
    compile_newsletter(full_mode=args.full, preview=args.preview)


if __name__ == "__main__":
    main()
