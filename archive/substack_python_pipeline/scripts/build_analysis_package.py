#!/usr/bin/env python3
"""
BUILD ANALYSIS PACKAGE — Saturday Session Data Compiler
========================================================

Pre-formats all data needed for the 8-prompt Sterling Signals analysis pipeline.
Generates an HTML email with copy-to-clipboard buttons for each prompt section.

Zero LLM cost — pure data formatting and delivery.

Usage:
    python3 -m scripts.build_analysis_package
    python3 -m scripts.build_analysis_package --dry-run    # Preview without saving
    python3 -m scripts.build_analysis_package --skip-email  # Save HTML only
"""

import argparse
import csv
import io
import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.output_paths import (
    ANALYSIS_PACKAGE_FILE,
    DECISIONS_FILE,
    PORTFOLIO_FILE,
    SCANNER_OUTPUT,
    SIGNAL_HISTORY_FILE,
    SIGNALS_TECH_FILE,
    get_scanner_current_dir,
    list_weekly_archives,
    save_to_scanner_current_and_archive,
)


# ═══════════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════════

def load_signals() -> Dict[str, Any]:
    """Load this week's scanner output from signals_technical.json."""
    if not SIGNALS_TECH_FILE.exists():
        print(f"  ⚠ signals_technical.json not found: {SIGNALS_TECH_FILE}")
        return {}
    try:
        with open(SIGNALS_TECH_FILE) as f:
            data = json.load(f)
        buy_count = len(data.get("buy_signals", []))
        sell_count = len(data.get("sell_signals", []))
        print(f"  ✓ Loaded signals: {buy_count} buy, {sell_count} sell")
        return data
    except (json.JSONDecodeError, OSError) as e:
        print(f"  ✗ Error reading signals: {e}")
        return {}


def load_portfolio() -> List[Dict[str, str]]:
    """Load current open positions from portfolio CSV."""
    if not PORTFOLIO_FILE.exists():
        print(f"  ⚠ portfolio.csv not found: {PORTFOLIO_FILE}")
        return []
    try:
        with open(PORTFOLIO_FILE, newline="") as f:
            reader = csv.DictReader(f)
            positions = [row for row in reader if row.get("status") == "OPEN"]
        print(f"  ✓ Loaded portfolio: {len(positions)} open positions")
        return positions
    except (csv.Error, OSError) as e:
        print(f"  ✗ Error reading portfolio: {e}")
        return []


def load_recent_decisions(weeks: int = 4) -> List[Dict[str, Any]]:
    """Load decisions.json from current and recent archives."""
    decisions = []

    # Current decisions.json
    if DECISIONS_FILE.exists():
        try:
            with open(DECISIONS_FILE) as f:
                data = json.load(f)
            decisions.append(data)
            print(f"  ✓ Loaded current decisions.json (scan_date: {data.get('scan_date', '?')})")
        except (json.JSONDecodeError, OSError) as e:
            print(f"  ✗ Error reading current decisions.json: {e}")

    # Check archives for older decisions.json files
    archives = list_weekly_archives("scanner")
    for week_id in sorted(archives, reverse=True)[:weeks]:
        archive_decisions = SCANNER_OUTPUT / "archive" / week_id / "decisions.json"
        if archive_decisions.exists():
            try:
                with open(archive_decisions) as f:
                    data = json.load(f)
                # Skip if same scan_date as current (avoid duplicates)
                if decisions and data.get("scan_date") == decisions[0].get("scan_date"):
                    continue
                decisions.append(data)
                print(f"  ✓ Loaded archived decisions: {week_id}")
            except (json.JSONDecodeError, OSError):
                pass

    if not decisions:
        print("  ⚠ No decisions.json found (current or archived)")
    return decisions


def load_signal_history() -> Tuple[str, List[Dict[str, str]]]:
    """Load signal history CSV as raw string and parsed rows."""
    if not SIGNAL_HISTORY_FILE.exists():
        print(f"  ⚠ signal_history_rows.csv not found: {SIGNAL_HISTORY_FILE}")
        return "", []
    try:
        raw = SIGNAL_HISTORY_FILE.read_text().strip()
        lines = raw.split("\n")

        # Parse with csv.DictReader
        reader = csv.DictReader(io.StringIO(raw))
        rows = list(reader)
        print(f"  ✓ Loaded signal history: {len(rows)} rows")
        return raw, rows
    except (csv.Error, OSError) as e:
        print(f"  ✗ Error reading signal history: {e}")
        return "", []


def load_prompt_templates() -> Dict[str, str]:
    """Extract prompt texts from sterling_prompt_library.md."""
    library_path = Path(__file__).resolve().parent.parent / "sterling_prompt_library.md"
    if not library_path.exists():
        print(f"  ⚠ sterling_prompt_library.md not found: {library_path}")
        return {}

    content = library_path.read_text()
    templates = {}

    # Extract main prompts: # PROMPT N: TITLE
    # Pattern: heading, optional blockquote guidance, then ``` delimited content
    prompt_pattern = re.compile(
        r'^# PROMPT (\w+):\s*(.+?)$',
        re.MULTILINE
    )

    matches = list(prompt_pattern.finditer(content))
    for i, match in enumerate(matches):
        prompt_id = match.group(1)  # R, 0, 1, 2, 3, 3B, 4, 5, 6, 7, 8
        # Find the first ``` block after this heading
        search_start = match.end()
        # Limit search to next prompt heading (or end of file)
        search_end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        section = content[search_start:search_end]

        # Extract content between first pair of ``` delimiters
        code_match = re.search(r'```\n(.*?)```', section, re.DOTALL)
        if code_match:
            templates[prompt_id] = code_match.group(1).strip()

    # Extract challenge prompts
    challenges = {}
    challenge_section_match = re.search(
        r'^# CHALLENGE PROMPTS\b.*?(?=^# (?!CHALLENGE))',
        content,
        re.MULTILINE | re.DOTALL
    )
    if challenge_section_match:
        challenge_text = challenge_section_match.group(0)
        # Find ## headings that are NOT struck through
        challenge_pattern = re.compile(
            r'^## (?!~~)(.+?)$',
            re.MULTILINE
        )
        c_matches = list(challenge_pattern.finditer(challenge_text))
        for j, cm in enumerate(c_matches):
            name = cm.group(1).strip()
            # Skip headings with parenthetical notes like "(use after Prompt 1)"
            clean_name = re.sub(r'\s*\(.*?\)\s*$', '', name)
            c_start = cm.end()
            c_end = c_matches[j + 1].start() if j + 1 < len(c_matches) else len(challenge_text)
            c_section = challenge_text[c_start:c_end]
            c_code = re.search(r'```\n(.*?)```', c_section, re.DOTALL)
            if c_code:
                challenges[clean_name] = c_code.group(1).strip()

    templates["challenges"] = challenges

    prompt_count = len([k for k in templates if k != "challenges"])
    challenge_count = len(challenges)
    print(f"  ✓ Loaded prompt templates: {prompt_count} prompts, {challenge_count} challenges")
    return templates


# ═══════════════════════════════════════════════════════════════════════════════
# PROMPT BUILDERS
# ═══════════════════════════════════════════════════════════════════════════════

def _enrich_portfolio_prices(
    portfolio: List[Dict[str, str]],
    signals: Dict[str, Any],
) -> List[Dict[str, str]]:
    """Add current_price and pnl_pct to portfolio positions from signals data."""
    # Build lookup from historical_winners in signals_technical.json
    price_lookup = {}
    for winner in signals.get("historical_winners", []):
        price_lookup[winner["ticker"]] = {
            "current_price": winner.get("current_price"),
            "pnl_pct": winner.get("pnl_pct"),
        }

    for pos in portfolio:
        ticker = pos.get("ticker", "")
        if ticker in price_lookup:
            pos["current_price"] = str(price_lookup[ticker]["current_price"] or "")
            pos["pnl_pct"] = str(price_lookup[ticker]["pnl_pct"] or "")
        else:
            # Try to calculate from highest_close as a rough proxy
            try:
                entry = float(pos.get("entry_price", 0))
                highest = float(pos.get("highest_close", 0))
                if entry > 0 and highest > 0:
                    pos["current_price"] = str(highest)
                    pos["pnl_pct"] = str(round((highest / entry - 1) * 100, 1))
            except (ValueError, ZeroDivisionError):
                pass
    return portfolio


def build_prompt_r(
    portfolio: List[Dict[str, str]],
    decisions: List[Dict[str, Any]],
    signal_history_raw: str,
    templates: Dict[str, str],
) -> str:
    """Build Prompt R with pre-filled data blocks."""
    template = templates.get("R", "")
    if not template:
        # Build data-only version without template wrapper
        return _build_prompt_r_data_only(portfolio, decisions, signal_history_raw)

    # --- 1. Open positions ---
    if portfolio:
        open_lines = []
        for pos in portfolio:
            ticker = pos.get("ticker", "?")
            entry_date = pos.get("entry_date", "?")
            entry_price = pos.get("entry_price", "?")
            current = pos.get("current_price", "N/A")
            pnl = pos.get("pnl_pct", "N/A")
            theme = pos.get("theme", "?")

            # Format P&L
            try:
                pnl_val = float(pnl)
                pnl_str = f"{pnl_val:+.1f}%"
            except (ValueError, TypeError):
                pnl_str = "N/A"

            try:
                current_str = f"${float(current):.2f}"
            except (ValueError, TypeError):
                current_str = "N/A"

            open_lines.append(
                f"${ticker}: entered {entry_date}, entry ${entry_price}, "
                f"current {current_str}, {pnl_str}, thesis: {theme}"
            )
        open_block = "\n".join(open_lines)
    else:
        open_block = "No open positions"

    # --- 2. Recently closed ---
    closed_lines = []
    # Check portfolio for CLOSED/STOPPED positions in last 4 weeks
    cutoff = (datetime.now() - timedelta(weeks=4)).strftime("%Y-%m-%d")
    # Also check decisions.json exits
    for d in decisions:
        for exit_item in d.get("exits", []):
            ticker = exit_item.get("symbol", exit_item.get("ticker", "?"))
            reason = exit_item.get("reason", exit_item.get("exit_reason", "?"))
            closed_lines.append(f"${ticker}: {reason}")

    if not closed_lines:
        closed_block = "No recent closes"
    else:
        closed_block = "\n".join(closed_lines)

    # --- 3. Notable filtered ---
    filtered_lines = []
    if decisions:
        latest = decisions[0]
        no_go = latest.get("no_go", [])
        # Sort by rejection stage priority
        stage_priority = {"review_gate": 0, "dd": 1, "gate": 2, "thematic": 3}
        sorted_nogo = sorted(
            no_go,
            key=lambda x: stage_priority.get(x.get("stage_rejected", ""), 99)
        )
        for item in sorted_nogo[:5]:
            ticker = item.get("symbol", "?")
            stage = item.get("stage_rejected", "?")
            reason = item.get("rejection_reason", "?")
            # Truncate long reasons
            if len(reason) > 120:
                reason = reason[:117] + "..."
            filtered_lines.append(f"${ticker}: filtered at {stage} — {reason}")

    if not filtered_lines:
        filtered_block = "First session — no prior data"
    else:
        filtered_block = "\n".join(filtered_lines)

    # --- 4. Signal history ---
    if signal_history_raw:
        lines = signal_history_raw.strip().split("\n")
        # Include header + last 30 data rows
        if len(lines) > 31:
            history_block = lines[0] + "\n" + "\n".join(lines[-30:])
        else:
            history_block = signal_history_raw.strip()
    else:
        history_block = "No signal history — first session"

    # --- 5. Calibration notes ---
    calibration_block = ""
    if decisions:
        latest = decisions[0]
        retro = latest.get("retrospective", {})
        cal_notes = retro.get("calibration_notes", [])
        scan_date = latest.get("scan_date", "unknown")
        if cal_notes:
            calibration_block = f"\nPREVIOUS CALIBRATION NOTES (from session {scan_date}):\n"
            for note in cal_notes:
                calibration_block += f"- {note}\n"

    # --- Replace placeholders in template ---
    result = template

    # Replace [PASTE: ticker, entry date, entry price, current price, P&L %, original thesis]
    result = re.sub(
        r'\[PASTE: ticker, entry date, entry price.*?\]',
        open_block,
        result,
        count=1,
    )

    # Replace [PASTE: ticker, entry date, exit date, P&L %, reason for exit]
    result = re.sub(
        r'\[PASTE: ticker, entry date, exit date.*?\]',
        closed_block,
        result,
        count=1,
    )

    # Replace [PASTE: 3-5 notable filtered tickers...]
    result = re.sub(
        r'\[PASTE: 3-5 notable filtered tickers.*?\]',
        filtered_block,
        result,
        flags=re.DOTALL,
        count=1,
    )

    # Replace [PASTE or ATTACH: signal_history.csv...]
    result = re.sub(
        r'\[PASTE or ATTACH: signal_history\.csv.*?\]',
        history_block,
        result,
        flags=re.DOTALL,
        count=1,
    )

    # Append calibration notes before the closing instruction
    if calibration_block:
        # Insert before "Present:" line
        result = result.replace(
            "Present:\n",
            calibration_block + "\nPresent:\n",
        )

    return result


def _build_prompt_r_data_only(
    portfolio: List[Dict[str, str]],
    decisions: List[Dict[str, Any]],
    signal_history_raw: str,
) -> str:
    """Fallback: build data blocks without the prompt template."""
    lines = ["[Prompt R template not found — data blocks only]\n"]
    lines.append("OPEN POSITIONS:")
    if portfolio:
        for pos in portfolio:
            lines.append(
                f"  ${pos.get('ticker', '?')}: entry ${pos.get('entry_price', '?')}, "
                f"current ${pos.get('current_price', 'N/A')}, theme: {pos.get('theme', '?')}"
            )
    else:
        lines.append("  No open positions")

    lines.append("\nSIGNAL HISTORY:")
    if signal_history_raw:
        lines.append(signal_history_raw.strip())
    else:
        lines.append("  No signal history")

    return "\n".join(lines)


def _format_signal_table(signals: Dict[str, Any]) -> str:
    """Format buy signals as a pipe-delimited table for Prompt 1."""
    buy_signals = signals.get("buy_signals", [])
    if not buy_signals:
        return "(Scanner produced 0 signals this week)"

    header = "Ticker | Price    | Tier | UC    | RSI  | MACD | 4W Mom% | Beta"
    separator = "-------|----------|------|-------|------|------|---------|-----"
    rows = [header, separator]

    for sig in buy_signals:
        ticker = sig.get("symbol", "?")
        price = sig.get("price", 0)
        tier = sig.get("tier", "?")
        uc = sig.get("uc", 0)
        rsi = sig.get("rsi14", 0)
        macd = "YES" if sig.get("macd_cross_up") else "no"
        mom = sig.get("momentum_4w", 0)
        beta = sig.get("beta", 0)

        rows.append(
            f"{ticker:<6} | ${price:<7.2f} | {tier:<4} | {uc:<5.1f} | {rsi:<4.0f} | {macd:<4} | {mom:+.1f}%{'':<2} | {beta:.2f}"
        )

    return "\n".join(rows)


def _format_portfolio_context(portfolio: List[Dict[str, str]]) -> str:
    """Format portfolio summary for Prompt 1 context section."""
    if not portfolio:
        return "No open positions"

    parts = []
    for pos in portfolio:
        ticker = pos.get("ticker", "?")
        theme = pos.get("theme", "?")
        pnl = pos.get("pnl_pct", "N/A")
        try:
            pnl_str = f"{float(pnl):+.1f}%"
        except (ValueError, TypeError):
            pnl_str = "N/A"
        parts.append(f"${ticker}: {pnl_str} ({theme})")

    return "\n".join(parts)


def build_prompt_1(
    signals: Dict[str, Any],
    portfolio: List[Dict[str, str]],
    signal_history_raw: str,
    templates: Dict[str, str],
) -> List[str]:
    """Build Prompt 1 section(s), auto-splitting if >15 signals."""
    template = templates.get("1", "")
    buy_signals = signals.get("buy_signals", [])
    total = len(buy_signals)

    portfolio_context = _format_portfolio_context(portfolio)

    # Determine batching
    if total <= 15:
        batches = [buy_signals]
    else:
        batch_size = 8
        batches = [
            buy_signals[i:i + batch_size]
            for i in range(0, total, batch_size)
        ]

    # Signal history context for D1 Theme Clustering Check (last 4 weeks)
    history_context = ""
    if signal_history_raw:
        lines = signal_history_raw.strip().split("\n")
        if len(lines) > 1:
            history_context = (
                "\n\nSIGNAL HISTORY (last 4 weeks, for cross-session theme tracking):\n"
                + signal_history_raw.strip()
            )

    results = []
    for batch_idx, batch in enumerate(batches):
        # Build signal table for this batch
        batch_signals = {**signals, "buy_signals": batch}
        signal_table = _format_signal_table(batch_signals)

        if not template:
            # Fallback: data only
            text = f"[Prompt 1 template not found — data block only]\n\n"
            text += f"SIGNAL TABLE ({len(batch)} of {total} signals):\n{signal_table}\n\n"
            text += f"PORTFOLIO CONTEXT:\n{portfolio_context}"
            if history_context:
                text += history_context
            results.append(text)
            continue

        # Fill template
        text = template

        # Replace portfolio context placeholder
        text = re.sub(
            r'\[PASTE CURRENT OPEN POSITIONS WITH P&L.*?\]',
            portfolio_context,
            text,
            count=1,
        )

        # Replace scanner output placeholder
        table_with_context = signal_table
        if history_context:
            table_with_context += history_context

        text = re.sub(
            r'\[PASTE YOUR SCANNER OUTPUT TABLE HERE\]',
            table_with_context,
            text,
            count=1,
        )

        # Add batch header if multi-batch
        if len(batches) > 1:
            if batch_idx == 0:
                batch_note = (
                    f"\n[NOTE: {total} signals auto-split into {len(batches)} batches of ~8. "
                    f"This is batch 1 of {len(batches)}.]\n\n"
                )
            else:
                batch_note = (
                    f"\nContinue thematic analysis with batch {batch_idx + 1} of {len(batches)} "
                    f"({len(batch)} signals). Apply the same framework from batch 1.\n\n"
                )
                # For batch 2+, just the signal table (no full template repeat)
                text = batch_note + signal_table
                if history_context and batch_idx == 1:
                    text += history_context
                results.append(text)
                continue

            text = batch_note + text

        results.append(text)

    if not results:
        results.append(
            "Scanner produced 0 signals this week. Consider running Prompt 0 for market "
            "context and then deciding whether to wait for next week."
        )

    return results


def build_prompt_8_prefill(signals: Dict[str, Any]) -> str:
    """Pre-fill scan metadata for Prompt 8."""
    stats = signals.get("stats", {})
    timestamp = signals.get("timestamp", "")

    # Parse date from timestamp
    scan_date = ""
    if timestamp:
        try:
            dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
            scan_date = dt.strftime("%Y-%m-%d")
        except ValueError:
            scan_date = timestamp[:10] if len(timestamp) >= 10 else ""

    prefill = f"""Pre-filled scan metadata (verify and adjust):
  scan_date: "{scan_date}"
  scan_week_ending: "{scan_date}"
  stats:
    tickers_loaded: {stats.get('tickers_loaded', '?')}
    technical_signals: {stats.get('technical_signals', '?')}
    tier_t1: {stats.get('tier_t1', '?')}
    tier_t2: {stats.get('tier_t2', '?')}
    tier_t3: {stats.get('tier_t3', '?')}"""

    return prefill


# ═══════════════════════════════════════════════════════════════════════════════
# HTML RENDERER
# ═══════════════════════════════════════════════════════════════════════════════

def _html_escape(text: str) -> str:
    """Escape HTML special characters in text content."""
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_html(
    sections: List[Dict[str, str]],
    stats: Dict[str, Any],
) -> str:
    """Generate self-contained HTML email with copy buttons for each prompt."""
    week_ending = stats.get("week_ending", "?")
    signal_count = stats.get("signal_count", 0)
    tier_summary = stats.get("tier_summary", "")
    portfolio_count = stats.get("portfolio_count", 0)

    # Build section HTML
    sections_html = ""
    for sec in sections:
        sid = sec["id"]
        title = _html_escape(sec["title"])
        content = _html_escape(sec["content"])
        note = _html_escape(sec.get("note", ""))
        is_open = sec.get("open", False)
        open_attr = " open" if is_open else ""

        note_html = f'<p class="note">{note}</p>' if note else ""

        sections_html += f"""
    <details{open_attr} class="prompt-section">
      <summary>
        <span class="section-title">{title}</span>
        <button class="copy-btn" onclick="copySection('{sid}')">COPY</button>
      </summary>
      {note_html}
      <pre id="content-{sid}" class="prompt-content">{content}</pre>
    </details>
"""

    # Build challenge prompts section
    challenges_html = ""
    challenge_sections = [s for s in sections if s.get("is_challenge")]
    if challenge_sections:
        challenge_items = ""
        for cs in challenge_sections:
            cid = cs["id"]
            ctitle = _html_escape(cs["title"])
            ccontent = _html_escape(cs["content"])
            challenge_items += f"""
      <details class="challenge-item">
        <summary>
          <span>{ctitle}</span>
          <button class="copy-btn" onclick="copySection('{cid}')">COPY</button>
        </summary>
        <pre id="content-{cid}" class="prompt-content">{ccontent}</pre>
      </details>
"""
        challenges_html = f"""
    <details class="prompt-section challenges-section">
      <summary><span class="section-title">Challenge Prompts (optional)</span></summary>
      {challenge_items}
    </details>
"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sterling Signals Analysis Package — Week ending {week_ending}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    background: #1a1a2e; color: #e0e0e0; font-family: -apple-system, BlinkMacSystemFont,
    'Segoe UI', Roboto, monospace; padding: 20px; max-width: 900px; margin: 0 auto;
    line-height: 1.5;
  }}
  .header {{
    border-bottom: 2px solid #16213e; padding-bottom: 16px; margin-bottom: 20px;
  }}
  .header h1 {{ color: #00d4aa; font-size: 1.4em; margin-bottom: 8px; }}
  .stats-banner {{
    background: #16213e; padding: 12px 16px; border-radius: 6px;
    font-size: 0.9em; color: #a0a0c0; margin-bottom: 12px;
  }}
  .stats-banner strong {{ color: #00d4aa; }}
  .workflow {{
    background: #0f3460; padding: 14px 16px; border-radius: 6px;
    font-size: 0.85em; margin-bottom: 20px; border-left: 3px solid #00d4aa;
  }}
  .workflow h3 {{ color: #00d4aa; margin-bottom: 8px; font-size: 0.95em; }}
  .workflow ol {{ padding-left: 20px; }}
  .workflow li {{ margin-bottom: 4px; color: #b0b0d0; }}
  .prompt-section {{
    background: #16213e; border-radius: 6px; margin-bottom: 10px;
    border: 1px solid #1a1a3e;
  }}
  .prompt-section > summary {{
    padding: 12px 16px; cursor: pointer; display: flex;
    justify-content: space-between; align-items: center;
    list-style: none; user-select: none;
  }}
  .prompt-section > summary::-webkit-details-marker {{ display: none; }}
  .prompt-section > summary::before {{
    content: '▶'; margin-right: 8px; font-size: 0.7em; color: #606080;
    transition: transform 0.2s;
  }}
  .prompt-section[open] > summary::before {{ transform: rotate(90deg); }}
  .section-title {{ font-weight: 600; color: #e0e0e0; }}
  .copy-btn {{
    background: #00d4aa; color: #1a1a2e; border: none; padding: 4px 12px;
    border-radius: 4px; cursor: pointer; font-size: 0.8em; font-weight: 600;
    flex-shrink: 0;
  }}
  .copy-btn:hover {{ background: #00f0c0; }}
  .copy-btn.copied {{ background: #606080; color: #a0a0a0; }}
  .note {{
    padding: 8px 16px; font-size: 0.85em; color: #808090;
    border-top: 1px solid #1a1a3e;
  }}
  .prompt-content {{
    padding: 16px; font-family: 'SF Mono', Monaco, 'Courier New', monospace;
    font-size: 0.82em; white-space: pre-wrap; word-wrap: break-word;
    color: #c8c8d8; background: #0f0f1e; border-top: 1px solid #1a1a3e;
    max-height: 600px; overflow-y: auto; line-height: 1.4;
  }}
  .challenges-section {{ border-color: #2a2a4e; }}
  .challenge-item {{
    margin: 4px 12px; background: #0f0f1e; border-radius: 4px;
  }}
  .challenge-item > summary {{
    padding: 8px 12px; cursor: pointer; display: flex;
    justify-content: space-between; align-items: center;
    font-size: 0.9em; color: #a0a0c0;
  }}
  .after-session {{
    background: #1e1e3e; padding: 16px; border-radius: 6px;
    margin-top: 20px; border-left: 3px solid #ff6b6b;
  }}
  .after-session h3 {{ color: #ff6b6b; margin-bottom: 8px; }}
  .after-session ol {{ padding-left: 20px; }}
  .after-session li {{ margin-bottom: 4px; color: #b0b0d0; }}
  .after-session code {{ background: #16213e; padding: 2px 6px; border-radius: 3px; }}
</style>
</head>
<body>

<div class="header">
  <h1>Sterling Signals Analysis Package</h1>
  <div class="stats-banner">
    <strong>{signal_count}</strong> signals ({tier_summary}) |
    <strong>{portfolio_count}</strong> open positions |
    Week ending <strong>{week_ending}</strong> |
    Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}
  </div>
</div>

<div class="workflow">
  <h3>Session Workflow</h3>
  <ol>
    <li>Open Claude.ai → Opus 4.6 + Extended Thinking + Web Search</li>
    <li>Copy <strong>Prompt R</strong> → paste → review → confirm calibration</li>
    <li>Copy <strong>Prompt 0</strong> → paste → review → confirm regime</li>
    <li>Copy <strong>Prompt 1</strong> → paste → review → decide which advance</li>
    <li>Copy <strong>Prompt 2</strong> → per ticker → review</li>
    <li>Copy <strong>Prompt 3</strong> → per ticker (one at a time) → review</li>
    <li>Copy <strong>Prompt 4</strong> → review → finalize</li>
    <li>Copy <strong>Prompt 5</strong> → get newsletter HTML</li>
    <li>Copy <strong>Prompt 8</strong> → get decisions.json → save to repo</li>
  </ol>
</div>

{sections_html}

{challenges_html}

<div class="after-session">
  <h3>After Session</h3>
  <ol>
    <li>Copy the decisions.json output from Prompt 8</li>
    <li>Save to <code>scanner/output/decisions.json</code></li>
    <li>Copy signal_history rows from Prompt 8 output</li>
    <li>Run: <code>python3 -m scripts.append_signal_history --interactive</code></li>
    <li>Save newsletter.html from Prompt 5 alongside decisions.json</li>
    <li>Run: <code>python3 -m scanner.saturday_workflow</code></li>
  </ol>
</div>

<script>
function copySection(id) {{
  const el = document.getElementById('content-' + id);
  if (!el) return;
  const text = el.textContent;
  const btn = el.closest('.prompt-section, .challenge-item').querySelector('.copy-btn');

  if (navigator.clipboard && navigator.clipboard.writeText) {{
    navigator.clipboard.writeText(text).then(() => {{
      if (btn) {{ btn.textContent = 'COPIED'; btn.classList.add('copied'); }}
      setTimeout(() => {{
        if (btn) {{ btn.textContent = 'COPY'; btn.classList.remove('copied'); }}
      }}, 2000);
    }}).catch(() => fallbackCopy(el, btn));
  }} else {{
    fallbackCopy(el, btn);
  }}
}}

function fallbackCopy(el, btn) {{
  const range = document.createRange();
  range.selectNodeContents(el);
  const sel = window.getSelection();
  sel.removeAllRanges();
  sel.addRange(range);
  try {{
    document.execCommand('copy');
    if (btn) {{ btn.textContent = 'COPIED'; btn.classList.add('copied'); }}
    setTimeout(() => {{
      if (btn) {{ btn.textContent = 'COPY'; btn.classList.remove('copied'); }}
    }}, 2000);
  }} catch(e) {{
    if (btn) {{ btn.textContent = 'SELECT & COPY'; }}
  }}
  sel.removeAllRanges();
}}
</script>

</body>
</html>"""

    return html


# ═══════════════════════════════════════════════════════════════════════════════
# SAVE & SEND
# ═══════════════════════════════════════════════════════════════════════════════

def save_package(html: str) -> Path:
    """Save HTML package to scanner/output/current/ and archive."""
    current_path, archive_path = save_to_scanner_current_and_archive(
        html, "analysis_package.html"
    )
    print(f"  ✓ Saved: {current_path}")
    print(f"  ✓ Archived: {archive_path}")
    return current_path


def send_email(html: str, stats: Dict[str, Any], skip: bool = False) -> bool:
    """Send via SendGrid. Graceful failure if no API key."""
    if skip:
        print("  ⚠ Email sending skipped (--skip-email)")
        return False

    api_key = os.environ.get("SENDGRID_API_KEY")
    if not api_key:
        print("  ⚠ SENDGRID_API_KEY not set — email not sent")
        return False

    to_email = os.environ.get("STERLING_EMAIL_TO")
    from_email = os.environ.get("STERLING_EMAIL_FROM", "signals@sterlingsignals.com")
    if not to_email:
        print("  ⚠ STERLING_EMAIL_TO not set — email not sent")
        return False

    week_ending = stats.get("week_ending", "?")
    signal_count = stats.get("signal_count", 0)
    subject = f"Sterling Signals Analysis Package — {signal_count} signals — Week ending {week_ending}"

    try:
        # Import sendgrid only when needed
        import sendgrid
        from sendgrid.helpers.mail import Content, Email, Mail, To

        sg = sendgrid.SendGridAPIClient(api_key=api_key)
        message = Mail(
            from_email=Email(from_email),
            to_emails=To(to_email),
            subject=subject,
            html_content=Content("text/html", html),
        )
        response = sg.client.mail.send.post(request_body=message.get())
        print(f"  ✓ Email sent (status: {response.status_code})")
        return True
    except ImportError:
        print("  ⚠ sendgrid package not installed — email not sent")
        return False
    except Exception as e:
        print(f"  ✗ Email send failed: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> int:
    """Build the analysis package."""
    parser = argparse.ArgumentParser(
        description="Build Saturday analysis package for Claude.ai session"
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without saving")
    parser.add_argument("--skip-email", action="store_true", help="Save HTML only, don't email")
    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("  STERLING SIGNALS — ANALYSIS PACKAGE BUILDER")
    print("=" * 70 + "\n")

    # --- Load all data ---
    print("Loading data...")
    signals = load_signals()
    portfolio = load_portfolio()
    decisions = load_recent_decisions()
    signal_history_raw, signal_history_rows = load_signal_history()
    templates = load_prompt_templates()

    # Enrich portfolio with current prices
    if portfolio and signals:
        portfolio = _enrich_portfolio_prices(portfolio, signals)

    # --- Compute stats ---
    buy_signals = signals.get("buy_signals", [])
    stats_data = signals.get("stats", {})
    timestamp = signals.get("timestamp", "")
    scan_date = ""
    if timestamp:
        try:
            dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
            scan_date = dt.strftime("%Y-%m-%d")
        except ValueError:
            scan_date = timestamp[:10] if len(timestamp) >= 10 else ""

    tier_t1 = stats_data.get("tier_t1", 0)
    tier_t2 = stats_data.get("tier_t2", 0)
    tier_t3 = stats_data.get("tier_t3", 0)

    stats = {
        "signal_count": len(buy_signals),
        "tier_summary": f"T1: {tier_t1}, T2: {tier_t2}, T3: {tier_t3}",
        "portfolio_count": len(portfolio),
        "week_ending": scan_date,
    }

    # --- Build prompt sections ---
    print("\nBuilding prompt sections...")

    sections = []

    # Prompt R — Retrospective (open by default)
    prompt_r_text = build_prompt_r(portfolio, decisions, signal_history_raw, templates)
    sections.append({
        "id": "R",
        "title": "Prompt R — Retrospective",
        "content": prompt_r_text,
        "note": "Paste first. Contains pre-formatted portfolio and signal history data.",
        "open": True,
    })

    # Prompt 0 — Market Context
    prompt_0_text = templates.get("0", "[Prompt 0 template not found]")
    sections.append({
        "id": "0",
        "title": "Prompt 0 — Market Context",
        "content": prompt_0_text,
        "note": "No data needed — Claude uses web search.",
        "open": False,
    })

    # Prompt 1 — Thematic Analysis (open by default, may have multiple batches)
    prompt_1_texts = build_prompt_1(signals, portfolio, signal_history_raw, templates)
    if len(prompt_1_texts) == 1:
        sections.append({
            "id": "1",
            "title": f"Prompt 1 — Thematic Analysis ({len(buy_signals)} signals)",
            "content": prompt_1_texts[0],
            "note": f"{len(buy_signals)} signals in single batch.",
            "open": True,
        })
    else:
        for idx, text in enumerate(prompt_1_texts):
            batch_label = f"Batch {idx + 1} of {len(prompt_1_texts)}"
            sections.append({
                "id": f"1{chr(97 + idx)}",  # 1a, 1b, 1c...
                "title": f"Prompt 1 — Thematic Analysis ({batch_label})",
                "content": text,
                "note": f"{len(buy_signals)} signals, auto-split into {len(prompt_1_texts)} batches.",
                "open": idx == 0,
            })

    # Prompt 2 — Investment Gate
    prompt_2_text = templates.get("2", "[Prompt 2 template not found]")
    sections.append({
        "id": "2",
        "title": "Prompt 2 — Investment Gate",
        "content": prompt_2_text,
        "note": "Run per ticker after Prompt 1 review.",
        "open": False,
    })

    # Prompt 3 — Deep DD
    prompt_3_text = templates.get("3", "[Prompt 3 template not found]")
    sections.append({
        "id": "3",
        "title": "Prompt 3 — Deep Due Diligence",
        "content": prompt_3_text,
        "note": "Run per ticker. One at a time for best quality.",
        "open": False,
    })

    # Prompt 4 — Portfolio Review Gate
    prompt_4_text = templates.get("4", "[Prompt 4 template not found]")
    sections.append({
        "id": "4",
        "title": "Prompt 4 — Portfolio Review Gate",
        "content": prompt_4_text,
        "note": "Run ONCE after all DD is complete. Do not skip.",
        "open": False,
    })

    # Prompt 5 — Newsletter
    prompt_5_text = templates.get("5", "[Prompt 5 template not found]")
    sections.append({
        "id": "5",
        "title": "Prompt 5 — Newsletter",
        "content": prompt_5_text,
        "note": "",
        "open": False,
    })

    # Prompt 8 — Decisions Export
    prompt_8_text = templates.get("8", "[Prompt 8 template not found]")
    prefill = build_prompt_8_prefill(signals)
    prompt_8_combined = f"{prefill}\n\n---\n\n{prompt_8_text}" if prompt_8_text else prefill
    sections.append({
        "id": "8",
        "title": "Prompt 8 — Decisions Export",
        "content": prompt_8_combined,
        "note": "Run LAST. Pre-filled scan metadata at top.",
        "open": False,
    })

    # Challenge prompts
    challenge_sections = []
    challenges = templates.get("challenges", {})
    for name, text in challenges.items():
        cid = re.sub(r'[^a-z0-9]', '_', name.lower())
        challenge_sections.append({
            "id": f"c_{cid}",
            "title": name,
            "content": text,
            "is_challenge": True,
        })

    print(f"  Built {len(sections)} prompt sections + {len(challenge_sections)} challenges")

    # --- Render HTML ---
    print("\nRendering HTML...")
    all_sections = sections + challenge_sections
    html = render_html(all_sections, stats)
    print(f"  HTML size: {len(html):,} bytes")

    # --- Save and send ---
    if args.dry_run:
        print("\n  [DRY RUN] Would save to:")
        print(f"    {ANALYSIS_PACKAGE_FILE}")
        print(f"\n  Preview stats: {stats}")
    else:
        print("\nSaving...")
        save_package(html)
        send_email(html, stats, skip=args.skip_email)

    # --- Summary ---
    print("\n" + "=" * 70)
    print("  ANALYSIS PACKAGE COMPLETE")
    print("=" * 70)
    print(f"  Signals: {stats['signal_count']} ({stats['tier_summary']})")
    print(f"  Portfolio: {stats['portfolio_count']} open positions")
    print(f"  Prompts: {len(sections)} sections + {len(challenge_sections)} challenges")
    print(f"  Week ending: {stats['week_ending']}")
    print("=" * 70 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
