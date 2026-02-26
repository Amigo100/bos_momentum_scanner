#!/usr/bin/env python3
"""
Saturday Workflow — Single command to bridge chat session to automation.

Runs after you've saved decisions.json and optionally newsletter.html
from your Claude.ai analysis session.

Steps:
  1. merge_decisions.py → signals.json
  2. Portfolio manager → add/exit positions, update prices
  3. market_analyzer.py → market_analysis.md (if missing)
  4. daily_context_builder.py → daily context document
  5. Place newsletter.html in output directories (if exists)
  6. Archive everything to weekly folder
  7. Print summary

Usage:
  python -m scanner.saturday_workflow
  python -m scanner.saturday_workflow --dry-run
  python -m scanner.saturday_workflow --skip-market
  python -m scanner.saturday_workflow --skip-guide
"""

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


# ═══════════════════════════════════════════════════════════════════════════════
# PATHS
# ═══════════════════════════════════════════════════════════════════════════════

try:
    from config.output_paths import (
        SCANNER_OUTPUT, SIGNALS_FILE, SIGNALS_TECH_FILE,
        get_scanner_current_dir, get_scanner_archive_dir,
        get_substack_current_dir, get_substack_archive_dir,
        get_week_identifier,
    )
    CURRENT_DIR = get_scanner_current_dir()
    SUBSTACK_CURRENT = get_substack_current_dir()
except ImportError:
    SCANNER_OUTPUT = Path("scanner/output")
    CURRENT_DIR = SCANNER_OUTPUT / "current"
    SIGNALS_FILE = SCANNER_OUTPUT / "signals.json"
    SIGNALS_TECH_FILE = SCANNER_OUTPUT / "signals_technical.json"
    SUBSTACK_CURRENT = Path("substack/output/current")

    def get_week_identifier(dt=None):
        if dt is None:
            dt = datetime.now()
        iso = dt.isocalendar()
        return f"{iso.year}-W{iso.week:02d}"

    def get_scanner_archive_dir(dt=None):
        return SCANNER_OUTPUT / "archive" / get_week_identifier(dt)

    def get_substack_archive_dir(dt=None):
        return Path("substack/output/archive") / get_week_identifier(dt)

DECISIONS_DEFAULT = SCANNER_OUTPUT / "decisions.json"


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def load_json(path: Path, required: bool = True) -> dict:
    """Load JSON file with error handling."""
    if not path.exists():
        if required:
            print(f"  ✗ Required file not found: {path}")
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"  ✗ Invalid JSON in {path}: {e}")
        return {}


def get_weekly_archive_dir() -> Path:
    """Get scanner archive directory for this week."""
    week_dir = get_scanner_archive_dir()
    week_dir.mkdir(parents=True, exist_ok=True)
    return week_dir


# ═══════════════════════════════════════════════════════════════════════════════
# PREFLIGHT VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

def preflight_check(decisions_path: Path) -> bool:
    """Validate inputs before running workflow."""
    ok = True

    # Check decisions.json exists
    if not decisions_path.exists():
        print(f"  ✗ decisions.json not found: {decisions_path}")
        print(f"    Run Claude.ai analysis and save Prompt 7 output here")
        ok = False

    # Check signals_technical.json exists (warning only, not fatal)
    if not SIGNALS_TECH_FILE.exists():
        alt = CURRENT_DIR / "signals_technical.json"
        if not alt.exists():
            print(f"  ⚠ signals_technical.json not found — merge will use decisions-only mode")

    # Check decisions.json is valid JSON with scan_date
    if decisions_path.exists():
        try:
            with open(decisions_path) as f:
                data = json.load(f)
            if not data.get("scan_date"):
                print(f"  ⚠ decisions.json missing scan_date")
        except json.JSONDecodeError as e:
            print(f"  ✗ decisions.json is not valid JSON: {e}")
            ok = False

    return ok


# ═══════════════════════════════════════════════════════════════════════════════
# WORKFLOW STEPS
# ═══════════════════════════════════════════════════════════════════════════════

def step_merge(decisions_path: Path, dry_run: bool = False) -> Optional[dict]:
    """Step 1: Merge decisions with technical data → signals.json."""
    print("─" * 60)
    print("  STEP 1: Merge Decisions → signals.json")
    print("─" * 60)

    # Load tech data from signals_technical.json (BUG-1 fix: was reading merged signals.json)
    tech = load_json(SIGNALS_TECH_FILE, required=False)
    if not tech:
        # Fallback: try current/ directory
        tech_alt = CURRENT_DIR / "signals_technical.json"
        tech = load_json(tech_alt, required=False)
    if not tech:
        print("  ⚠ No signals_technical.json found — decisions-only mode")
        tech = {"buy_signals": [], "sell_signals": [], "stats": {}}
    else:
        n = len(tech.get("buy_signals", []))
        print(f"  ✓ Loaded technical base ({n} signals)")

    # Load decisions
    decisions = load_json(decisions_path, required=True)
    if not decisions:
        print(f"  ✗ Cannot proceed without decisions.json at {decisions_path}")
        return None

    n_new = len(decisions.get("new_positions", []))
    n_exits = len(decisions.get("exits", []))
    n_themes = len(decisions.get("themes_this_week", []))
    print(f"  ✓ Loaded decisions ({n_new} buys, {n_exits} exits, {n_themes} themes)")

    # Merge
    from scanner.merge_decisions import merge_signals, build_content_schedule, save_json
    merged = merge_signals(tech, decisions)
    schedule = build_content_schedule(decisions)

    if dry_run:
        print(f"  [DRY RUN] Would write {len(merged['buy_signals'])} signals to {SIGNALS_FILE}")
        return decisions

    # Save merged signals
    if save_json(merged, SIGNALS_FILE):
        print(f"  ✓ Saved {SIGNALS_FILE}")

    # Also save to current/
    current_signals = CURRENT_DIR / "signals.json"
    if current_signals != SIGNALS_FILE:
        if save_json(merged, current_signals):
            print(f"  ✓ Saved {current_signals}")

    # Save content schedule
    content_out = CURRENT_DIR / "content_schedule.json"
    if save_json(schedule, content_out):
        print(f"  ✓ Saved {content_out}")

    print()
    return decisions


def step_portfolio(decisions: dict, dry_run: bool = False):
    """Step 2: Update portfolio with new positions and exits."""
    print("─" * 60)
    print("  STEP 2: Portfolio Updates")
    print("─" * 60)

    from scanner.merge_decisions import update_portfolio
    update_portfolio(decisions, dry_run=dry_run)
    print()


def step_market_analysis(dry_run: bool = False, skip: bool = False):
    """Step 3: Generate market analysis if missing."""
    print("─" * 60)
    print("  STEP 3: Market Analysis")
    print("─" * 60)

    if skip:
        print("  ⏭ Skipped (--skip-market)")
        print()
        return

    market_file = CURRENT_DIR / "market_analysis.md"
    if market_file.exists():
        print(f"  ✓ market_analysis.md already exists")
        print()
        return

    if dry_run:
        print("  [DRY RUN] Would generate market_analysis.md")
        print()
        return

    try:
        from substack.market_analyzer import run_market_analysis
        print("  Generating market analysis (this calls the LLM)...")
        run_market_analysis()
        print("  ✓ market_analysis.md generated")
    except ImportError:
        print("  ⚠ market_analyzer not available")
        print("    (Market context from decisions.json is sufficient)")
    except Exception as e:
        print(f"  ⚠ Market analyzer failed: {e}")
        print("    (Market context from decisions.json is sufficient)")
    print()


def step_content_guide(dry_run: bool = False, skip: bool = False):
    """Step 4: Generate daily context document."""
    print("─" * 60)
    print("  STEP 4: Daily Context Builder")
    print("─" * 60)

    if skip:
        print("  ⏭ Skipped (--skip-guide)")
        print()
        return

    if dry_run:
        print("  [DRY RUN] Would generate daily_context.md")
        print()
        return

    try:
        from substack.daily_context_builder import main as dcb_main
        dcb_main()
        print("  ✓ daily_context.md generated")
    except ImportError:
        print("  ⚠ daily_context_builder not available")
    except Exception as e:
        print(f"  ⚠ Daily context builder failed: {e}")
    print()


def step_newsletter(decisions_path: Path, dry_run: bool = False):
    """Step 5: Place newsletter.html in output directories."""
    print("─" * 60)
    print("  STEP 5: Newsletter Distribution")
    print("─" * 60)

    # BUG-5 fix: Look for newsletter alongside decisions.json first,
    # then fall back to scanner output root
    newsletter_src = decisions_path.parent / "newsletter.html"
    if not newsletter_src.exists():
        newsletter_src = SCANNER_OUTPUT / "newsletter.html"
    if not newsletter_src.exists():
        # Check if it's already in the target location
        if (SUBSTACK_CURRENT / "newsletter.html").exists():
            print(f"  ✓ newsletter.html already in {SUBSTACK_CURRENT}")
            print()
            return
        print(f"  ⚠ No newsletter.html found")
        print(f"    Save Prompt 4 output as newsletter.html alongside decisions.json")
        print()
        return

    targets = [
        SUBSTACK_CURRENT / "newsletter.html",
    ]

    if dry_run:
        print(f"  [DRY RUN] Would copy newsletter.html to {len(targets)} location(s)")
        print()
        return

    for target in targets:
        if target.resolve() == newsletter_src.resolve():
            continue  # Skip self-copy
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(newsletter_src, target)
        print(f"  ✓ Copied to {target}")

    print()


def step_archive(decisions_path: Path, dry_run: bool = False):
    """Step 6: Archive everything to weekly folder."""
    print("─" * 60)
    print("  STEP 6: Archive to Weekly Folder")
    print("─" * 60)

    week_dir = get_weekly_archive_dir()

    files_to_archive = [
        (decisions_path, "decisions.json"),
        (SIGNALS_FILE, "signals.json"),
        (CURRENT_DIR / "content_schedule.json", "content_schedule.json"),
    ]

    # Newsletter from substack output
    newsletter_src = SUBSTACK_CURRENT / "newsletter.html"
    if newsletter_src.exists():
        files_to_archive.append((newsletter_src, "newsletter.html"))

    if dry_run:
        print(f"  [DRY RUN] Would archive to {week_dir}/")
        for src, name in files_to_archive:
            exists = "✓" if src.exists() else "✗"
            print(f"    {exists} {name}")
        print()
        return

    for src, name in files_to_archive:
        if src.exists():
            shutil.copy2(src, week_dir / name)
            print(f"  ✓ {name} → {week_dir.name}/")
        else:
            print(f"  ⏭ {name} (not found)")

    # Also archive to substack archive
    try:
        substack_archive = get_substack_archive_dir()
        substack_archive.mkdir(parents=True, exist_ok=True)
        newsletter_src_arch = SUBSTACK_CURRENT / "newsletter.html"
        if newsletter_src_arch.exists():
            shutil.copy2(newsletter_src_arch, substack_archive / "newsletter.html")
            print(f"  ✓ newsletter.html → substack archive")
    except Exception:
        pass

    print()


def step_summary(decisions: dict, dry_run: bool = False):
    """Step 7: Print summary with next steps."""
    print("═" * 60)
    print("  SATURDAY WORKFLOW COMPLETE")
    print("═" * 60)
    print()

    n_new = len(decisions.get("new_positions", []))
    n_exits = len(decisions.get("exits", []))
    n_themes = len(decisions.get("themes_this_week", []))
    regime = decisions.get("market_regime", "unknown")

    if dry_run:
        print("  [DRY RUN] No files were written.")
        print()

    print(f"  Market regime: {regime}")
    print(f"  New positions: {n_new}")
    print(f"  Exits:         {n_exits}")
    print(f"  Themes:        {n_themes}")
    print()

    if n_new > 0:
        print("  New buys:")
        for p in decisions.get("new_positions", []):
            print(f"    🟢 {p['symbol']} — {p.get('theme', '')} "
                  f"(${p.get('price', 0):.2f}, {p.get('verdict', '')})")
        print()

    print("  NEXT STEPS:")
    print("  ─────────────────────────────────────────")
    step = 1

    newsletter_exists = (SUBSTACK_CURRENT / "newsletter.html").exists()
    if newsletter_exists:
        print(f"  {step}. Publish newsletter to Substack")
        step += 1
    else:
        print(f"  {step}. Generate newsletter in Claude.ai (Prompt 4) and re-run workflow")
        step += 1

    guide_exists = (SUBSTACK_CURRENT / "daily_context.md").exists()
    if guide_exists:
        print(f"  {step}. Attach daily_context.md to Claude.ai for daily posts")
        step += 1

    print(f"  {step}. Post 3 Substack notes for today")
    print("  ─────────────────────────────────────────")
    print()


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Saturday workflow: bridge chat session to automation")
    parser.add_argument("--dry-run", action="store_true",
        help="Preview without writing files or updating portfolio")
    parser.add_argument("--skip-market", action="store_true",
        help="Skip market_analyzer.py API call")
    parser.add_argument("--skip-guide", action="store_true",
        help="Skip daily_context_builder.py")
    parser.add_argument("--decisions", type=Path, default=DECISIONS_DEFAULT,
        help=f"Path to decisions.json (default: {DECISIONS_DEFAULT})")
    parser.add_argument("--decisions-dir", type=Path, default=None,
        help="Directory containing decisions.json and newsletter.html")
    args = parser.parse_args()

    # Resolve decisions path from --decisions-dir if provided
    if args.decisions_dir:
        args.decisions = args.decisions_dir / "decisions.json"

    print()
    print("  ╔══════════════════════════════════════════════════╗")
    print("  ║  SATURDAY WORKFLOW                               ║")
    print("  ║  Chat Session → Downstream Automation            ║")
    print("  ╚══════════════════════════════════════════════════╝")
    print()

    if args.dry_run:
        print("  🔍 DRY RUN MODE — no files will be written")
        print()

    # Preflight validation
    if not preflight_check(args.decisions):
        print("\n  ✗ Preflight check failed. Fix the issues above and re-run.")
        return 1
    print()

    # Step 1: Merge decisions → signals.json
    decisions = step_merge(args.decisions, dry_run=args.dry_run)
    if decisions is None:
        return 1

    # Step 2: Update portfolio
    step_portfolio(decisions, dry_run=args.dry_run)

    # Step 3: Market analysis (optional)
    step_market_analysis(dry_run=args.dry_run, skip=args.skip_market)

    # Step 4: Content production guide (optional)
    step_content_guide(dry_run=args.dry_run, skip=args.skip_guide)

    # Step 5: Newsletter distribution
    step_newsletter(args.decisions, dry_run=args.dry_run)

    # Step 6: Archive
    step_archive(args.decisions, dry_run=args.dry_run)

    # Step 7: Summary
    step_summary(decisions, dry_run=args.dry_run)

    return 0


if __name__ == "__main__":
    sys.exit(main())
