#!/usr/bin/env python3
"""
Sterling Grid V6 — Merge Decisions
====================================
Bridge between Claude.ai chat analysis and downstream automation.

Reads:
  - scanner/output/signals.json       (from scanner, as technical base)
  - scanner/output/current/decisions.json     (from Claude.ai Prompt 7 export)

Produces:
  - scanner/output/signals.json       (merged, same format downstream expects)
  - scanner/output/current/content_schedule.json  (scan metadata for reference)
  - Updates portfolio manager with new positions and exits

Usage:
  python -m scanner.merge_decisions
  python -m scanner.merge_decisions --dry-run         # Preview without saving
  python -m scanner.merge_decisions --no-portfolio     # Skip portfolio updates
  python -m scanner.merge_decisions --decisions FILE   # Custom decisions.json path
"""

import json
import sys
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional


# ═══════════════════════════════════════════════════════════════════════════════
# PATHS
# ═══════════════════════════════════════════════════════════════════════════════

# Try to import project paths, fall back to defaults
try:
    from config.output_paths import (
        SCANNER_OUTPUT, SIGNALS_FILE, SIGNALS_TECH_FILE,
        get_scanner_current_dir, get_scanner_archive_dir,
    )
    CURRENT_DIR = get_scanner_current_dir()
except ImportError:
    SCANNER_OUTPUT = Path("scanner/output")
    CURRENT_DIR = SCANNER_OUTPUT / "current"
    SIGNALS_FILE = SCANNER_OUTPUT / "signals.json"
    SIGNALS_TECH_FILE = SCANNER_OUTPUT / "signals_technical.json"

    def get_scanner_archive_dir(dt=None):
        from datetime import datetime as _dt
        d = dt or _dt.now()
        iso = d.isocalendar()
        return SCANNER_OUTPUT / "archive" / f"{iso[0]}-W{iso[1]:02d}"

SIGNALS_TECH = SIGNALS_TECH_FILE
DECISIONS_DEFAULT = SCANNER_OUTPUT / "decisions.json"
SIGNALS_OUT = SIGNALS_FILE  # Write to canonical location
CONTENT_OUT = CURRENT_DIR / "content_schedule.json"


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def load_json(path: Path, required: bool = True) -> dict:
    """Load JSON file with error handling."""
    if not path.exists():
        if required:
            print(f"  ✗ Required file not found: {path}")
            return {}
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"  ✗ Invalid JSON in {path}: {e}")
        return {}


def save_json(data: dict, path: Path) -> bool:
    """Save JSON file, creating parent dirs if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"  ✗ Error saving {path}: {e}")
        return False


def get_weekly_archive_dir() -> Path:
    """Get the weekly archive directory (scanner/output/archive/YYYY-WNN/)."""
    week_dir = get_scanner_archive_dir()
    week_dir.mkdir(parents=True, exist_ok=True)
    return week_dir


# ═══════════════════════════════════════════════════════════════════════════════
# CORE: MERGE TECHNICAL + DECISIONS → SIGNALS.JSON
# ═══════════════════════════════════════════════════════════════════════════════

def merge_signals(tech: dict, decisions: dict) -> dict:
    """
    Merge scanner technical data with Claude.ai chat decisions.

    Produces signals.json in the EXACT format that downstream systems
    (newsletter_compiler, live_tweet_generator)
    already consume.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Build ticker lookup from ALL technical signal arrays (BUG-4 fix)
    tech_lookup: Dict[str, dict] = {}
    for key in ("buy_signals", "pass_signals", "consider_signals"):
        for sig in tech.get(key, []):
            sym = sig.get("symbol", "")
            if sym and sym not in tech_lookup:  # first match wins
                tech_lookup[sym] = sig

    # Start with technical base structure
    merged = {
        "timestamp": timestamp,
        "timeframe": "WEEKLY",
        "entry_criteria": tech.get("entry_criteria",
            "Sterling Grid V6: HMA pivot + (UC rising OR MACD cross-up)"),
        "exit_criteria": tech.get("exit_criteria",
            "ExD compound exit + tiered profit lock"),
        "stats": tech.get("stats", {}),

        # Market context (from Claude.ai decisions)
        "market_context_summary": decisions.get("market_context_summary", ""),
        "market_regime": decisions.get("market_regime", ""),

        # These are the arrays downstream systems read
        "themes": [],
        "pass_signals": [],
        "consider_signals": [],
        "buy_signals": [],          # Legacy: union of pass + consider
        "sell_signals": [],
        "assessed_signals": [],

        # Historical tracking (pass through from scanner)
        "historical_winners": tech.get("historical_winners", []),
        "big_wins": tech.get("big_wins", []),
        "home_runs": tech.get("home_runs", []),
    }

    # ── Map themes ──────────────────────────────────────────────────────────
    for theme in decisions.get("themes_this_week", []):
        merged["themes"].append({
            "name": theme.get("name", ""),
            "classification": theme.get("classification", ""),
            "composite_score": theme.get("composite_score", 0),
            "catalyst_score": theme.get("catalyst_score", 0),
            "momentum_score": theme.get("momentum_score", 0),
            "crowding_score": theme.get("crowding_score", 0),
            "runway_score": theme.get("runway_score", 0),
            "thesis_summary": theme.get("thesis_summary", ""),
            "why_now": theme.get("why_now", ""),
            "key_catalysts": theme.get("key_catalysts", []),
            "primary_risks": theme.get("primary_risks", []),
            "valuation_regime": theme.get("valuation_regime", ""),
            "lifecycle_stage": theme.get("lifecycle_stage", ""),
            # Downstream compat fields
            "theme_type": "TREND",
            "position_sizing_recommendation": "",
            "primary_etfs": theme.get("primary_etfs", []),
            "crowding_indicator": theme.get("crowding_indicator", ""),
        })

    # ── Map new positions → pass_signals / consider_signals ─────────────────
    unmatched_tickers = []  # Track tickers missing from technical data

    for pos in decisions.get("new_positions", []):
        symbol = pos.get("symbol", "")
        tech_data = tech_lookup.get(symbol, {})

        if not tech_data:
            unmatched_tickers.append(symbol)

        # Determine final_decision from verdict
        verdict = pos.get("verdict", pos.get("dd_verdict", ""))
        if verdict in ("STRONG BUY", "STRONG_BUY"):
            final_decision = "PASS"
        elif verdict in ("SPEC BUY", "SPEC_BUY", "SPECULATIVE BUY"):
            final_decision = "CONSIDER"
        else:
            final_decision = "CONSIDER"

        # Build bullish_factors from DD data, filtering empty strings
        bullish_factors = pos.get("bullish_factors", [
            pos.get("variant_perception", ""),
            pos.get("dd_why_now", ""),
            pos.get("dd_key_catalyst", ""),
        ])
        bullish_factors = [f for f in bullish_factors if f]

        # Build risk_factors from DD data, filtering empty strings
        risk_factors = pos.get("risk_factors", [
            pos.get("dd_bear_case", ""),
            pos.get("dd_risk_to_monitor", ""),
            pos.get("kill_switch", ""),
        ])
        risk_factors = [f for f in risk_factors if f]

        signal = {
            # ── Technical data (from scanner) ──
            # BUG-2 fix: All defaults are False/0 — never fabricate confirmation
            "symbol": symbol,
            "price": pos.get("price", tech_data.get("price", 0)),
            "tier": pos.get("tier", tech_data.get("tier", "")),
            "quality_tier": pos.get("quality_tier", tech_data.get("quality_tier", 0)),
            "beta": tech_data.get("beta", 0),
            "uc": tech_data.get("uc", 0),
            "uc_rising": tech_data.get("uc_rising", False),
            "rsi14": tech_data.get("rsi14", 0),
            "macd_cross_up": tech_data.get("macd_cross_up", False),
            "hma_pivot_low": tech_data.get("hma_pivot_low", False),
            "hma_pivot_high": tech_data.get("hma_pivot_high", False),
            "hma_slope_rising": tech_data.get("hma_slope_rising", False),
            "buy_signal": tech_data.get("buy_signal", False),
            "exd_signal": tech_data.get("exd_signal", False),
            "return_20d": tech_data.get("return_20d", 0),
            # Legacy compat keys
            "banker": tech_data.get("uc", tech_data.get("banker", 0)),
            "uc_rising_above": tech_data.get("uc_rising_above", False),

            # ── Theme data (from Claude.ai) ──
            "theme": pos.get("theme", ""),
            "theme_score": pos.get("theme_score", 0),
            "pure_play_score": pos.get("theme_score", 0),  # Legacy alias
            "theme_verdict": pos.get("theme_verdict", "STRONG FIT"),
            "theme_classification": pos.get("theme_classification", ""),
            "valuation_regime": pos.get("valuation_regime", ""),

            # ── Gate data (from Claude.ai) ──
            "final_decision": final_decision,
            "conviction": pos.get("dd_conviction", pos.get("conviction", 0)),
            "gate_verdict": pos.get("gate_verdict", verdict.replace(" ", "_")),
            "gate_conviction": pos.get("gate_conviction", pos.get("conviction", 0)),
            "gate_catalyst": pos.get("catalyst_summary", ""),
            "gate_bear_case": pos.get("gate_bear_case", ""),
            "gate_math": pos.get("gate_math", ""),
            "sector_status": "",
            "upside_potential": pos.get("dd_the_math", ""),
            "bullish_factors": bullish_factors,
            "risk_factors": risk_factors,
            "reasoning": pos.get("dd_elevator_pitch", ""),

            # ── Position sizing ──
            "position_size_pct": pos.get("position_size_pct", 0),
            "position_dollars": 0,  # Calculated by portfolio manager
            "position_tier": pos.get("tier", ""),

            # ── Deep DD data (from Claude.ai) ──
            "dd_verdict": pos.get("dd_verdict", verdict),
            "dd_conviction": pos.get("dd_conviction", pos.get("conviction", 0)),
            "dd_position_size": pos.get("position_size", ""),
            "dd_elevator_pitch": pos.get("dd_elevator_pitch", ""),
            "dd_why_now": pos.get("dd_why_now", ""),
            "dd_the_math": pos.get("dd_the_math", ""),
            "dd_bear_case": pos.get("dd_bear_case", ""),
            "dd_risk_to_monitor": pos.get("dd_risk_to_monitor", ""),
            "dd_action": pos.get("dd_action", ""),
            "dd_key_catalyst": pos.get("dd_key_catalyst", pos.get("catalyst_summary", "")),
            "dd_fatal_flaw": pos.get("dd_fatal_flaw", ""),

            # ── Action ──
            "action": pos.get("dd_action", "Enter Monday at market open"),

            # ── Downstream compat aliases ──
            "catalyst_summary": pos.get("catalyst_summary", pos.get("dd_key_catalyst", "")),
        }

        # Derive position_size_pct from tier if not explicitly set
        if signal["position_size_pct"] == 0 and signal.get("tier"):
            tier_pcts = {"T1": 0.20, "T2": 0.10, "T3": 0.05}
            signal["position_size_pct"] = tier_pcts.get(signal["tier"], 0.10)

        if final_decision == "PASS":
            merged["pass_signals"].append(signal)
        else:
            merged["consider_signals"].append(signal)

        # buy_signals is the legacy union of both
        merged["buy_signals"].append(signal)

    # ── Warn about unmatched tickers ──────────────────────────────────────
    if unmatched_tickers:
        print(f"  ⚠ {len(unmatched_tickers)} ticker(s) in decisions.json not found in "
              f"signals_technical.json: {', '.join(unmatched_tickers)}")
        print(f"    Technical fields will be empty for these tickers")

    # ── Map sell signals ────────────────────────────────────────────────────
    # Start with scanner's sell signals (ExD, trailing stops)
    for sell in tech.get("sell_signals", []):
        merged["sell_signals"].append(sell)

    # Add exits from Claude.ai decisions (thesis broken, target reached, etc.)
    for exit_sig in decisions.get("exits", []):
        # Avoid duplicates (scanner may have flagged same ticker)
        existing_symbols = {s.get("symbol") for s in merged["sell_signals"]}
        if exit_sig.get("symbol") not in existing_symbols:
            merged["sell_signals"].append({
                "symbol": exit_sig.get("symbol", ""),
                "price": exit_sig.get("exit_price", 0),
                "reason": exit_sig.get("reason", ""),
                "entry_price": exit_sig.get("entry_price", 0),
                "highest_close": 0,
                "drawdown_pct": 0,
                "pnl_pct": exit_sig.get("pnl_pct", 0),
            })

    # ── Map rejected stocks → assessed_signals ──────────────────────────────
    for nogo in decisions.get("no_go", []):
        symbol = nogo.get("symbol", "")
        tech_data = tech_lookup.get(symbol, {})
        merged["assessed_signals"].append({
            "symbol": symbol,
            "price": tech_data.get("price", 0),
            "theme": "",
            "theme_score": 0,
            "theme_verdict": "WEAK FIT",
            "final_decision": "REJECTED",
            "tier": tech_data.get("tier", ""),
        })

    # ── Map watchlist → assessed_signals ─────────────────────────────────────
    for watch in decisions.get("watchlist", []):
        symbol = watch.get("symbol", "")
        tech_data = tech_lookup.get(symbol, {})
        merged["assessed_signals"].append({
            "symbol": symbol,
            "price": watch.get("price_at_scan", tech_data.get("price", 0)),
            "theme": watch.get("theme", ""),
            "theme_score": 0,
            "theme_verdict": "GOOD FIT",
            "final_decision": "WATCHLIST",
            "tier": tech_data.get("tier", ""),
        })

    # Defensive alias for any consumer reading exit_signals instead of sell_signals
    merged["exit_signals"] = merged["sell_signals"]

    return merged


# ═══════════════════════════════════════════════════════════════════════════════
# CONTENT SCHEDULE GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

def build_content_schedule(decisions: dict) -> dict:
    """
    Build minimal content metadata from decisions.json.

    The actual content scheduling is done by content_production_guide.py
    from repo data (portfolio, themes, signals). This just records scan
    metadata for reference.
    """
    scan_date = decisions.get("scan_date", datetime.now().strftime("%Y-%m-%d"))
    market_ctx = decisions.get("market_context_summary", "")

    try:
        base_date = datetime.strptime(scan_date, "%Y-%m-%d")
    except (ValueError, TypeError):
        base_date = datetime.now()

    return {
        "generated": datetime.now().isoformat(),
        "scan_date": scan_date,
        "week_start": (base_date + timedelta(days=1)).strftime("%Y-%m-%d"),
        "week_end": (base_date + timedelta(days=7)).strftime("%Y-%m-%d"),
        "market_context": market_ctx,
        "new_positions": [
            {"symbol": p.get("symbol", ""), "theme": p.get("theme", "")}
            for p in decisions.get("new_positions", [])
        ],
        "has_newsletter": (DECISIONS_DEFAULT.parent / "newsletter.html").exists(),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# PORTFOLIO UPDATES
# ═══════════════════════════════════════════════════════════════════════════════

def update_portfolio(decisions: dict, dry_run: bool = False):
    """Update portfolio manager with new positions and exits from decisions."""
    new_positions = decisions.get("new_positions", [])
    exits = decisions.get("exits", [])

    if not new_positions and not exits:
        print("  No portfolio changes")
        return

    if dry_run:
        if new_positions:
            print(f"  Would add {len(new_positions)} position(s):")
            for p in new_positions:
                print(f"    + {p['symbol']} at ${p.get('price', 0):.2f} ({p.get('tier', '?')})")
        if exits:
            print(f"  Would close {len(exits)} position(s):")
            for e in exits:
                print(f"    - {e['symbol']} at ${e.get('exit_price', 0):.2f} ({e.get('pnl_pct', 0):+.1f}%)")
        return

    try:
        from portfolio.manager import PortfolioManager
        pm = PortfolioManager()

        for pos in new_positions:
            try:
                pm.add_trade(
                    ticker=pos["symbol"],
                    entry_price=pos.get("price", 0),
                    theme=pos.get("theme", ""),
                    tier=pos.get("tier", "T2"),
                    signal_type="PASS",
                    conviction=pos.get("dd_conviction", pos.get("conviction", 0)),
                    notes=pos.get("dd_elevator_pitch", ""),
                    position_size_pct=pos.get("position_size_pct", 0.0),
                    sizing_gear=pos.get("sizing_gear", ""),
                )
                psize = pos.get("position_size", "UNKNOWN")
                print(f"  ✓ Added {pos['symbol']} at ${pos.get('price', 0):.2f} "
                      f"({pos.get('tier', '?')}, {psize})")
            except Exception as e:
                print(f"  ✗ Error adding {pos.get('symbol', '?')}: {e}")

        for exit_sig in exits:
            try:
                pm.flag_exit(
                    ticker=exit_sig["symbol"],
                    exit_price=exit_sig.get("exit_price", 0),
                    reason=exit_sig.get("reason", "Manual exit"),
                )
                pnl = exit_sig.get("pnl_pct", 0)
                emoji = "🟢" if pnl >= 0 else "🔴"
                print(f"  {emoji} Closed {exit_sig['symbol']} at "
                      f"${exit_sig.get('exit_price', 0):.2f} ({pnl:+.1f}%)")
            except Exception as e:
                print(f"  ✗ Error closing {exit_sig.get('symbol', '?')}: {e}")

        # Update live prices on all open positions
        try:
            pm.update_prices()
            print(f"\n  ✓ Live prices updated")
        except Exception:
            pass

        # Export for Google Sheets
        try:
            sheets_file = pm.export_for_google_sheets()
            print(f"  ✓ Google Sheets export: {sheets_file}")
        except Exception:
            pass

    except ImportError:
        print("  ⚠ Portfolio manager not available")
        print("  Update positions manually in your portfolio tracker")
    except Exception as e:
        print(f"  ⚠ Portfolio update error: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

def validate_decisions(decisions: dict) -> List[str]:
    """Validate decisions.json structure. Returns list of warnings."""
    warnings = []

    if not decisions:
        warnings.append("decisions.json is empty")
        return warnings

    # Required top-level fields (content_angles excluded — handled by repo automation)
    for field in ["scan_date", "market_regime", "new_positions", "themes_this_week"]:
        if field not in decisions:
            warnings.append(f"Missing required field: {field}")

    # Validate scan_date format
    scan_date = decisions.get("scan_date", "")
    if scan_date:
        try:
            datetime.strptime(scan_date, "%Y-%m-%d")
        except ValueError:
            warnings.append(f"scan_date '{scan_date}' is not YYYY-MM-DD format")

    # Validate market_regime
    valid_regimes = {"risk_on", "risk_off", "selective"}
    regime = decisions.get("market_regime", "")
    if regime and regime not in valid_regimes:
        warnings.append(f"market_regime '{regime}' not in {valid_regimes}")

    # Validate new positions
    for i, pos in enumerate(decisions.get("new_positions", [])):
        prefix = f"new_positions[{i}] ({pos.get('symbol', '?')})"
        if not pos.get("symbol"):
            warnings.append(f"{prefix}: missing symbol")
        if not pos.get("verdict"):
            warnings.append(f"{prefix}: missing verdict")
        if not pos.get("dd_elevator_pitch"):
            warnings.append(f"{prefix}: missing dd_elevator_pitch (newsletter needs this)")
        if pos.get("conviction", 0) == 0 and pos.get("dd_conviction", 0) == 0:
            warnings.append(f"{prefix}: conviction is 0")
        if pos.get("tier", "") not in ("T1", "T2", "T3"):
            warnings.append(f"{prefix}: tier '{pos.get('tier')}' not in T1/T2/T3")
        if pos.get("price", 0) <= 0:
            warnings.append(f"{prefix}: price is {pos.get('price', 0)}")

    # Validate themes have names
    for i, theme in enumerate(decisions.get("themes_this_week", [])):
        if not theme.get("name"):
            warnings.append(f"themes_this_week[{i}]: missing name")

    # Validate exits have required fields
    for i, ex in enumerate(decisions.get("exits", [])):
        prefix = f"exits[{i}] ({ex.get('symbol', '?')})"
        if not ex.get("symbol"):
            warnings.append(f"{prefix}: missing symbol")
        if ex.get("exit_price", 0) <= 0:
            warnings.append(f"{prefix}: exit_price is {ex.get('exit_price', 0)}")

    # Validate theme sub-scores are numeric
    for i, theme in enumerate(decisions.get("themes_this_week", [])):
        prefix = f"themes_this_week[{i}]"
        for score_field in ["composite_score", "catalyst_score", "momentum_score",
                            "crowding_score", "runway_score"]:
            val = theme.get(score_field)
            if val is not None and not isinstance(val, (int, float)):
                warnings.append(f"{prefix}: {score_field} is {type(val).__name__}, expected number")

    return warnings


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Merge Claude.ai decisions with scanner technical data")
    parser.add_argument("--dry-run", action="store_true",
        help="Preview merge without saving files or updating portfolio")
    parser.add_argument("--no-portfolio", action="store_true",
        help="Skip portfolio updates (just merge files)")
    parser.add_argument("--decisions", type=Path, default=DECISIONS_DEFAULT,
        help=f"Path to decisions.json (default: {DECISIONS_DEFAULT})")
    parser.add_argument("--technical", type=Path, default=SIGNALS_TECH,
        help=f"Path to signals_technical.json (default: {SIGNALS_TECH})")
    args = parser.parse_args()

    print()
    print("  ╔══════════════════════════════════════════════════╗")
    print("  ║  STERLING GRID — MERGE DECISIONS                ║")
    print("  ║  Chat Analysis → Downstream Automation          ║")
    print("  ╚══════════════════════════════════════════════════╝")
    print()

    # ── Load inputs ─────────────────────────────────────────────────────────
    tech = load_json(args.technical, required=False)
    decisions = load_json(args.decisions, required=True)

    if not decisions:
        print("  ✗ Cannot proceed without decisions.json")
        print(f"    Expected at: {args.decisions}")
        print()
        print("  To create decisions.json:")
        print("  1. Run analysis in Claude.ai using Prompt 1")
        print("  2. Use Prompt 7 to generate structured export")
        print("  3. Copy the JSON output to decisions.json")
        print(f"  4. Save to: {args.decisions}")
        return 1

    if not tech:
        print("  ⚠ No signals_technical.json found — using decisions-only mode")
        print(f"    (Expected at: {args.technical})")
        print("    Technical fields will be empty in merged output")
        tech = {"buy_signals": [], "sell_signals": [], "stats": {}}

    # ── Validate ────────────────────────────────────────────────────────────
    warnings = validate_decisions(decisions)
    if warnings:
        print(f"  ⚠ {len(warnings)} validation warning(s):")
        for w in warnings:
            print(f"    • {w}")
        print()

    # ── Merge ───────────────────────────────────────────────────────────────
    merged = merge_signals(tech, decisions)
    schedule = build_content_schedule(decisions)

    # ── Summary ─────────────────────────────────────────────────────────────
    n_tech = len(tech.get("buy_signals", []))
    n_new = len(decisions.get("new_positions", []))
    n_nogo = len(decisions.get("no_go", []))
    n_exits = len(decisions.get("exits", []))
    n_watch = len(decisions.get("watchlist", []))
    n_pass = len(merged["pass_signals"])
    n_consider = len(merged["consider_signals"])
    n_sell = len(merged["sell_signals"])
    n_themes = len(merged["themes"])

    print("  INPUTS:")
    print(f"    Technical signals: {n_tech} stocks")
    print(f"    Chat decisions:   {n_new} buys, {n_nogo} no-go, "
          f"{n_exits} exits, {n_watch} watchlist")
    print()
    print("  MERGED OUTPUT:")
    print(f"    🟢 PASS signals:    {n_pass}")
    print(f"    🟡 CONSIDER signals: {n_consider}")
    print(f"    🔴 SELL signals:     {n_sell}")
    print(f"    📊 Themes:           {n_themes}")

    if args.dry_run:
        print("\n  ── DRY RUN ──")
        print()
        for sig in merged["pass_signals"]:
            print(f"  🟢 {sig['symbol']} — {sig['dd_verdict']} ({sig['dd_conviction']}/10) "
                  f"| {sig['theme']}")
        for sig in merged["consider_signals"]:
            print(f"  🟡 {sig['symbol']} — {sig['dd_verdict']} ({sig['dd_conviction']}/10) "
                  f"| {sig['theme']}")
        for sig in merged["sell_signals"]:
            print(f"  🔴 {sig['symbol']} — {sig.get('reason', 'Exit')}")

        print()
        print("  Portfolio changes (preview):")
        update_portfolio(decisions, dry_run=True)

        print("\n  No files written (--dry-run)")
        return 0

    # ── Save outputs ────────────────────────────────────────────────────────
    print("\n  SAVING:")

    if save_json(merged, SIGNALS_OUT):
        print(f"  ✓ {SIGNALS_OUT}")

    # Also save to current/ for consumers that read from there
    current_signals = CURRENT_DIR / "signals.json"
    if current_signals != SIGNALS_OUT:
        if save_json(merged, current_signals):
            print(f"  ✓ {current_signals}")

    if save_json(schedule, CONTENT_OUT):
        print(f"  ✓ {CONTENT_OUT}")

    # Archive to weekly folder
    week_dir = get_weekly_archive_dir()
    save_json(merged, week_dir / "signals.json")
    save_json(schedule, week_dir / "content_schedule.json")
    save_json(decisions, week_dir / "decisions.json")

    print(f"  ✓ Archived to {week_dir}/")

    # ── Portfolio updates ───────────────────────────────────────────────────
    if not args.no_portfolio:
        print("\n  PORTFOLIO:")
        update_portfolio(decisions)

    # ── Done ────────────────────────────────────────────────────────────────
    print()
    print("  ══════════════════════════════════════════════════")
    print("  ✓ Merge complete. Downstream systems ready.")
    print()
    print("  Next steps:")
    print("    • Run content_production_guide.py for weekly schedule")
    print("    • Publish newsletter to Substack")
    print("    • signal_tracker reads signals.json for win tracking")
    print("  ══════════════════════════════════════════════════")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
