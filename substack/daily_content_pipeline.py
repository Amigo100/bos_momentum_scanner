#!/usr/bin/env python3
"""
DAILY CONTENT PIPELINE — Sterling Signals
==========================================

Orchestrates the daily content generation workflow:
1. Market analysis (cached if fails)
2. Daily context builder (critical)
3. Daily notes generator (non-blocking)
4. Email notification (sends whatever was produced)

Each step is independent — a failure in one step doesn't block the others.

Usage:
    python -m substack.daily_content_pipeline                    # Full daily run
    python -m substack.daily_content_pipeline --skip-notes       # Context doc only
    python -m substack.daily_content_pipeline --skip-email       # No email notification
    python -m substack.daily_content_pipeline --day wednesday    # Override day detection
    python -m substack.daily_content_pipeline --dry-run          # Preview without LLM/email
    python -m substack.daily_content_pipeline --email-only       # Just send email for existing outputs
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from config.output_paths import get_substack_current_dir


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 1: MARKET ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

def run_step_market_analysis(dry_run: bool = False) -> Optional[str]:
    """Run market analysis or load cached version.

    Returns market analysis text or None.
    """
    if dry_run:
        print("  ℹ Market analysis: skipped (dry-run)")
        return _load_cached_market_analysis()

    try:
        from substack.market_analyzer import run_market_analysis, save_market_analysis

        print("  Running market analysis...")
        result = run_market_analysis()

        if result.error:
            print(f"  ⚠ Market analysis error: {result.error} — using cached version")
            return _load_cached_market_analysis()

        # Save the result
        save_market_analysis(result.analysis)
        print(f"  ✓ Market analysis saved (${result.cost:.4f})")
        return result.analysis

    except Exception as e:
        print(f"  ⚠ Market analysis failed: {e} — using cached version")
        return _load_cached_market_analysis()


def _load_cached_market_analysis() -> Optional[str]:
    """Load cached market analysis from current/market_analysis.md."""
    path = get_substack_current_dir() / "market_analysis.md"
    if not path.exists():
        # Try scanner current dir
        from config.output_paths import get_scanner_current_dir
        path = get_scanner_current_dir() / "market_analysis.md"

    if path.exists():
        try:
            content = path.read_text()
            print(f"  ✓ Using cached market analysis ({len(content):,} chars)")
            return content
        except IOError:
            pass

    print("  ℹ No cached market analysis available")
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 2: DAILY CONTEXT BUILDER
# ═══════════════════════════════════════════════════════════════════════════════

def run_step_context_builder(day: str, dry_run: bool = False) -> Dict:
    """Run the daily context builder.

    Returns dict with:
        - filepath: path to saved daily_context.md (or None)
        - post_assignment: dict with category, topic, theme (or None)
        - notes_context: the notes context JSON dict (or None)
    """
    result = {"filepath": None, "post_assignment": None, "notes_context": None}

    try:
        from substack.content_utils import build_content_context
        from substack.daily_context_builder import (
            PostAssignment,
            build_daily_context,
            build_notes_context_json,
            determine_todays_post,
            load_full_portfolio,
            load_live_market_data,
            load_portfolio_snapshot,
        )
        from config.output_paths import (
            get_substack_current_dir,
            get_substack_archive_dir,
        )

        # Load data
        print("  Loading scanner data...")
        ctx = build_content_context()
        portfolio = load_full_portfolio()
        snapshot = load_portfolio_snapshot()

        print(f"    Signals: {ctx.scan_stats.get('tickers_loaded', 0):,} scanned, {ctx.pass_count} GREEN")
        print(f"    Portfolio: {len(portfolio)} open positions")
        print(f"    Themes: {len(ctx.themes)}")

        # Live market data
        if dry_run:
            market_data = {}
        else:
            market_data = load_live_market_data()

        # Determine today's post
        assignment = determine_todays_post(day, ctx, portfolio, snapshot)

        if assignment:
            result["post_assignment"] = {
                "category": assignment.category,
                "topic": assignment.topic,
                "theme": assignment.theme,
                "reason": assignment.reason,
                "override_type": assignment.override_type,
            }
            print(f"  ✓ Post: {assignment.category} — {assignment.topic}")
        else:
            print(f"  ✓ No post today ({day.capitalize()}) — notes only")

        # Build outputs
        context_md = build_daily_context(day, ctx, portfolio, assignment, market_data)
        notes_json = build_notes_context_json(day, ctx, portfolio, market_data)
        result["notes_context"] = notes_json

        if dry_run:
            print(f"  ✓ Context doc: {len(context_md):,} chars (dry-run, not saved)")
            return result

        # Save
        current_dir = get_substack_current_dir()
        current_dir.mkdir(parents=True, exist_ok=True)

        context_path = current_dir / "daily_context.md"
        context_path.write_text(context_md)
        result["filepath"] = str(context_path)

        json_path = current_dir / "daily_notes_context.json"
        json_path.write_text(json.dumps(notes_json, indent=2))

        # Archive
        try:
            archive_dir = get_substack_archive_dir()
            archive_dir.mkdir(parents=True, exist_ok=True)
            (archive_dir / "daily_context.md").write_text(context_md)
            (archive_dir / "daily_notes_context.json").write_text(json.dumps(notes_json, indent=2))
        except Exception:
            pass  # Archive failure is non-critical

        print(f"  ✓ Context doc saved: {context_path}")

    except Exception as e:
        print(f"  ❌ Context builder failed: {e}")
        import traceback
        traceback.print_exc()

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 3: DAILY NOTES GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

def run_step_notes_generator(
    day: str,
    notes_context: Optional[Dict] = None,
    dry_run: bool = False,
) -> List[Dict]:
    """Run the daily notes generator.

    Returns list of note dicts with type, slot, filepath, text.
    """
    try:
        from substack.daily_notes_generator import generate_daily_notes

        print("  Generating notes...")
        notes = generate_daily_notes(
            day=day,
            context=notes_context,
            dry_run=dry_run,
        )
        print(f"  ✓ {len(notes)} notes generated")
        return notes

    except Exception as e:
        print(f"  ⚠ Notes generation failed: {e}")
        import traceback
        traceback.print_exc()
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 4: EMAIL NOTIFICATION (spec Section 12)
# ═══════════════════════════════════════════════════════════════════════════════

def format_email_body(
    day: str,
    post_assignment: Optional[Dict],
    notes: List[Dict],
    market_analysis: Optional[str],
) -> str:
    """Format the daily content email body per spec Section 12.1."""
    now = datetime.now()
    lines = []

    lines.append("STERLING SIGNALS — DAILY CONTENT BRIEF")
    lines.append(f"{day.capitalize()}, {now.strftime('%B %d, %Y')}")
    lines.append("")
    lines.append("━" * 40)
    lines.append("")

    # Today's post
    if post_assignment:
        category = post_assignment.get("category", "Unknown")
        topic = post_assignment.get("topic", category)
        lines.append(f"TODAY'S POST: {category} — {topic}")
    else:
        lines.append("No long-form post today — notes only")
    lines.append("")

    # Market snapshot (extract from analysis if available)
    if market_analysis:
        # Take first 200 chars as a quick snapshot
        snippet = market_analysis[:200].replace("\n", " ").strip()
        lines.append("MARKET SNAPSHOT")
        lines.append(snippet)
        lines.append("")

    # Notes summary
    if notes:
        lines.append(f"TODAY'S NOTES ({len(notes)} ready — paste to Substack)")
        for note in notes:
            note_type = note.get("type", "UNKNOWN")
            text = note.get("text", "")
            # First 60 chars of note text as preview
            preview = text[:60].replace("\n", " ").strip()
            if len(text) > 60:
                preview += "..."
            lines.append(f"  {note.get('slot', '?')}. {note_type}: \"{preview}\"")
        lines.append("")

    lines.append("━" * 40)
    lines.append("")
    lines.append("ATTACHMENTS")
    lines.append("- daily_context.md — attach to Claude.ai for today's post")
    if notes:
        lines.append(f"- {len(notes)}x note HTML files — paste directly to Substack Notes")
    lines.append("")
    lines.append("The full daily_context.md is also in the repo:")
    lines.append("substack/output/current/daily_context.md")

    return "\n".join(lines)


def send_daily_email(day: str, results: Dict) -> bool:
    """Send the daily content brief via email.

    Returns True if sent successfully.
    """
    try:
        from utils.email_notifier import send_email
    except ImportError:
        print("  ⚠ Email notifier not available")
        return False

    post = results.get("context_doc", {}).get("post_assignment")
    notes = results.get("notes", [])

    # Build subject
    subject = f"Sterling Signals — {day.capitalize()}: "
    if post:
        subject += post.get("topic", post.get("category", "Content Ready"))
    else:
        subject += "Notes Only"

    # Build body
    body = format_email_body(
        day=day,
        post_assignment=post,
        notes=notes,
        market_analysis=results.get("market_analysis"),
    )

    # Note: current email_notifier.send_email takes (subject, body).
    # Attachments are listed in the body text for the user to find in the repo.
    try:
        success = send_email(subject=subject, body=body)
    except RuntimeError as e:
        print(f"  ⚠ Email not configured: {e}")
        return False
    except Exception as e:
        print(f"  ⚠ Email send error: {e}")
        return False

    if success:
        print(f"  ✓ Email sent: {subject}")
    else:
        print(f"  ⚠ Email send failed (returned False)")

    return success


# ═══════════════════════════════════════════════════════════════════════════════
# EMAIL-ONLY MODE
# ═══════════════════════════════════════════════════════════════════════════════

def run_email_only(day: str) -> bool:
    """Send email using existing outputs (no regeneration).

    Reads whatever files exist in substack/output/current/ and sends them.
    """
    current_dir = get_substack_current_dir()

    # Load existing context doc info
    context_doc = {"filepath": None, "post_assignment": None}
    context_path = current_dir / "daily_context.md"
    if context_path.exists():
        context_doc["filepath"] = str(context_path)

    # Try to determine post assignment from daily_notes_context.json
    json_path = current_dir / "daily_notes_context.json"
    if json_path.exists():
        try:
            data = json.loads(json_path.read_text())
            # Extract post info if available
            post_cat = data.get("post_category")
            post_topic = data.get("post_topic")
            if post_cat:
                context_doc["post_assignment"] = {
                    "category": post_cat,
                    "topic": post_topic or post_cat,
                }
        except (json.JSONDecodeError, IOError):
            pass

    # Load existing notes
    notes = []
    notes_dir = current_dir / "notes"
    if notes_dir.exists():
        for html_file in sorted(notes_dir.glob("note_*.html")):
            # Parse note type from filename: note_{slot}_{type}_{date}.html
            parts = html_file.stem.split("_")
            if len(parts) >= 3:
                slot = parts[1] if parts[1].isdigit() else "?"
                note_type = "_".join(parts[2:-1]).upper() if len(parts) > 3 else parts[2].upper()
                notes.append({
                    "type": note_type,
                    "slot": int(slot) if slot.isdigit() else 0,
                    "filepath": str(html_file),
                    "text": html_file.read_text()[:200],  # Preview only
                })

    # Load cached market analysis
    market_analysis = _load_cached_market_analysis()

    results = {
        "market_analysis": market_analysis,
        "context_doc": context_doc,
        "notes": notes,
    }

    return send_daily_email(day, results)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════

def run_daily_pipeline(
    day: str,
    dry_run: bool = False,
    skip_notes: bool = False,
    skip_email: bool = False,
) -> Dict:
    """Run the full daily content pipeline.

    Each step is independent — a failure in one doesn't block the others.

    Args:
        day: Day of the week (e.g. "monday").
        dry_run: Preview without LLM calls or saving.
        skip_notes: Skip note generation.
        skip_email: Skip email notification.

    Returns:
        Results dict with status of each step.
    """
    results = {
        "portfolio_refresh": None,
        "portfolio_dashboard": None,
        "market_analysis": None,
        "context_doc": {"filepath": None, "post_assignment": None, "notes_context": None},
        "notes": [],
        "email_sent": False,
    }

    # Step 0: Portfolio price refresh (non-blocking)
    print("\n─── Step 0: Portfolio Price Refresh ──────────────────────")
    try:
        if not dry_run:
            from portfolio.manager import refresh_daily_prices
            snapshot = refresh_daily_prices()
            positions = snapshot.get("summary", {}).get("open_positions", 0)
            print(f"  ✓ Portfolio refreshed — {positions} positions updated")
            results["portfolio_refresh"] = True
        else:
            print("  ℹ Portfolio refresh: skipped (dry-run)")
            results["portfolio_refresh"] = False
    except Exception as e:
        print(f"  ⚠ Portfolio refresh failed: {e} — continuing with stale prices")
        results["portfolio_refresh"] = False

    # Step 0.5: Portfolio dashboard (non-blocking)
    print("\n─── Step 0.5: Portfolio Dashboard ───────────────────────")
    try:
        if not dry_run and results.get("portfolio_refresh"):
            from substack.portfolio_visual import generate_daily_dashboard
            dash = generate_daily_dashboard()
            print(f"  ✓ Dashboard: {dash['html_path'].name}")
            print(f"  ✓ Summary:   {dash['png_path'].name}")
            results["portfolio_dashboard"] = True
        else:
            print("  ℹ Dashboard: skipped (dry-run or no refresh)")
            results["portfolio_dashboard"] = False
    except Exception as e:
        print(f"  ⚠ Dashboard failed: {e} — continuing")
        results["portfolio_dashboard"] = False

    # Step 1: Market analysis (non-blocking — use cached if fails)
    print("\n─── Step 1: Market Analysis ─────────────────────────────")
    results["market_analysis"] = run_step_market_analysis(dry_run=dry_run)

    # Step 2: Daily context doc (critical — always attempt)
    print("\n─── Step 2: Daily Context Builder ───────────────────────")
    results["context_doc"] = run_step_context_builder(day=day, dry_run=dry_run)

    # Step 3: Notes (non-blocking — failure doesn't stop email)
    if not skip_notes:
        print("\n─── Step 3: Daily Notes Generator ───────────────────────")
        notes_context = results["context_doc"].get("notes_context")
        results["notes"] = run_step_notes_generator(
            day=day,
            notes_context=notes_context,
            dry_run=dry_run,
        )
    else:
        print("\n─── Step 3: Notes — SKIPPED ─────────────────────────────")

    # Step 4: Email (sends whatever we have)
    if not skip_email and not dry_run:
        print("\n─── Step 4: Email Notification ──────────────────────────")
        try:
            results["email_sent"] = send_daily_email(day, results)
        except Exception as e:
            print(f"  ⚠ Email failed: {e}")
    elif dry_run:
        print("\n─── Step 4: Email — SKIPPED (dry-run) ──────────────────")
    else:
        print("\n─── Step 4: Email — SKIPPED ─────────────────────────────")

    return results


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Daily Content Pipeline — Sterling Signals")
    parser.add_argument("--day", type=str, default=None,
                        help="Override day (e.g., wednesday)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without LLM calls or saving")
    parser.add_argument("--skip-notes", action="store_true",
                        help="Skip note generation (context doc only)")
    parser.add_argument("--skip-email", action="store_true",
                        help="Skip email notification")
    parser.add_argument("--email-only", action="store_true",
                        help="Just send email for existing outputs")

    args = parser.parse_args()

    # Determine day
    if args.day:
        day = args.day.lower()
    else:
        day = datetime.now().strftime("%A").lower()

    now = datetime.now()
    day_title = day.capitalize()

    print("\n" + "=" * 70)
    print("  STERLING SIGNALS — DAILY CONTENT PIPELINE")
    print(f"  {day_title} {now.strftime('%B %d, %Y')}")
    if args.dry_run:
        print("  Mode: DRY RUN")
    elif args.email_only:
        print("  Mode: EMAIL ONLY")
    print("=" * 70)

    # Email-only mode
    if args.email_only:
        print("\n  Sending email for existing outputs...")
        success = run_email_only(day)
        return 0 if success else 1

    # Full pipeline
    results = run_daily_pipeline(
        day=day,
        dry_run=args.dry_run,
        skip_notes=args.skip_notes,
        skip_email=args.skip_email,
    )

    # Summary
    print("\n" + "=" * 70)
    print("  PIPELINE SUMMARY")
    print("=" * 70)

    steps = [
        ("Market Analysis", "✓" if results["market_analysis"] else "⚠ cached/unavailable"),
        ("Context Doc", "✓" if results["context_doc"].get("filepath") else ("✓ dry-run" if args.dry_run else "❌ failed")),
        ("Notes", f"✓ {len(results['notes'])} generated" if results["notes"] else ("skipped" if args.skip_notes else "⚠ none")),
        ("Email", "✓ sent" if results["email_sent"] else ("skipped" if args.skip_email or args.dry_run else "⚠ not sent")),
    ]

    for step_name, status in steps:
        print(f"  {step_name:20s} {status}")

    post = results["context_doc"].get("post_assignment")
    if post:
        print(f"\n  Today's post: {post.get('category', '?')} — {post.get('topic', '?')}")
    else:
        print(f"\n  No long-form post today ({day_title})")

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
