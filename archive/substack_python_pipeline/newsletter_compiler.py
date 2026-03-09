#!/usr/bin/env python3
"""
NEWSLETTER COMPILER — Sterling Signals (Simplified)
====================================================
Copies Claude.ai-generated HTML to output directories with validation.
Also provides general post archiving for midweek content.

Usage:
    python -m substack.newsletter_compiler --from-html PATH
    python -m substack.newsletter_compiler --from-html PATH --preview
    python -m substack.newsletter_compiler --from-html PATH --dry-run
    python -m substack.newsletter_compiler --archive-post PATH --filename tuesday_deep_dive.html
"""

import argparse
import sys
import webbrowser
from pathlib import Path
from typing import Optional

from config.output_paths import (
    get_relative_path,
    save_to_substack_current_and_archive,
    get_claude_content_dir,
    get_week_identifier,
)
from config.banned_terms import validate_content


# ═══════════════════════════════════════════════════════════════════════════════
# COMPILE FROM HTML (primary workflow)
# ═══════════════════════════════════════════════════════════════════════════════

def compile_from_html(
    html_path: str,
    dry_run: bool = False,
    preview: bool = False,
) -> Optional[Path]:
    """Copy HTML newsletter from Claude.ai to current/ and archive/ with validation.

    Saves to three locations:
    - substack/output/current/newsletter.html
    - substack/output/archive/YYYY-WXX/newsletter.html
    - substack/output/claude_content/newsletter_YYYY-WXX.html
    """
    html_file = Path(html_path)
    if not html_file.exists():
        print(f"  Error: HTML file not found: {html_file}")
        return None

    print(f"\n{'=' * 60}")
    print(f"  NEWSLETTER COMPILER — From HTML")
    print(f"{'=' * 60}")
    print(f"  Source: {html_file}")

    content = html_file.read_text(encoding="utf-8")
    print(f"  Read {len(content):,} characters")

    # Validate for banned terms
    is_valid, violations = validate_content(content)
    if not is_valid:
        print(f"  ⚠ Banned terms found: {violations}")
        print(f"  Proceeding anyway — review before publishing")
    else:
        print(f"  ✓ Content passed vocabulary validation")

    if dry_run:
        print(f"\n  [DRY RUN] Would save to current/ and archive/")
        print(f"{'=' * 60}\n")
        return html_file

    # Save to current/ + weekly archive/
    current_path, archive_path = save_to_substack_current_and_archive(
        content, "newsletter.html"
    )
    print(f"\n  Newsletter placed:")
    print(f"     Current: {get_relative_path(current_path)}")
    print(f"     Archive: {get_relative_path(archive_path)}")

    # Also save to claude_content/ with week identifier
    claude_dir = get_claude_content_dir()
    week_id = get_week_identifier()
    claude_path = claude_dir / f"newsletter_{week_id}.html"
    claude_path.write_text(content)
    print(f"     Claude:  {get_relative_path(claude_path)}")

    print(f"\n  Next steps:")
    print(f"     1. Open {current_path} in browser")
    print(f"     2. Copy the content (Cmd+A, Cmd+C)")
    print(f"     3. Paste into Substack editor")
    print(f"     4. Preview and publish!")

    if preview:
        print(f"\n  Opening preview in browser...")
        webbrowser.open(f"file://{current_path.absolute()}")

    print(f"\n{'=' * 60}\n")
    return current_path


# ═══════════════════════════════════════════════════════════════════════════════
# ARCHIVE POST (general purpose)
# ═══════════════════════════════════════════════════════════════════════════════

def archive_post(
    html_path: str,
    filename: str,
    dry_run: bool = False,
) -> Optional[Path]:
    """Archive any Substack post HTML to current/ and archive/.

    Use this for midweek content (deep dives, theme posts, etc.)
    that needs to be placed in the standard output directories.
    """
    html_file = Path(html_path)
    if not html_file.exists():
        print(f"  Error: HTML file not found: {html_file}")
        return None

    content = html_file.read_text(encoding="utf-8")
    print(f"  Archiving: {html_file.name} → {filename}")
    print(f"  Size: {len(content):,} characters")

    # Validate for banned terms
    is_valid, violations = validate_content(content)
    if not is_valid:
        print(f"  ⚠ Banned terms found: {violations}")

    if dry_run:
        print(f"  [DRY RUN] Would save to current/ and archive/")
        return html_file

    current_path, archive_path = save_to_substack_current_and_archive(
        content, filename
    )
    print(f"  ✓ Current: {get_relative_path(current_path)}")
    print(f"  ✓ Archive: {get_relative_path(archive_path)}")
    return current_path


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Copy Claude.ai HTML newsletter to output paths, or archive a post"
    )
    parser.add_argument(
        "--from-html", type=str, metavar="PATH",
        help="Path to Claude.ai HTML newsletter file",
    )
    parser.add_argument(
        "--archive-post", type=str, metavar="PATH",
        help="Path to any Substack post HTML to archive",
    )
    parser.add_argument(
        "--filename", type=str, default=None,
        help="Output filename for --archive-post (e.g., tuesday_deep_dive.html)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview without saving files",
    )
    parser.add_argument(
        "--preview", "-p", action="store_true",
        help="Open HTML in browser after saving",
    )

    args = parser.parse_args()

    if args.from_html:
        result = compile_from_html(args.from_html, dry_run=args.dry_run, preview=args.preview)
        return 0 if result else 1

    if args.archive_post:
        if not args.filename:
            print("Error: --filename is required with --archive-post")
            return 1
        result = archive_post(args.archive_post, args.filename, dry_run=args.dry_run)
        return 0 if result else 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
