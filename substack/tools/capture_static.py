#!/usr/bin/env python3
"""
Capture a static HTML file as a PNG screenshot.

Unlike capture.py (which records animations frame-by-frame), this script
takes a single screenshot for static data graphics that accompany Substack
notes.

Usage:
  python capture_static.py input.html [--width 680] [--format png]
  python capture_static.py substack/output/current/notes/*_graphic_*.html --batch
"""

import argparse, asyncio, glob, os, sys
from pathlib import Path


async def capture_screenshot(html_path, width=680, output_path=None):
    """Take a single PNG screenshot of an HTML file."""
    from playwright.async_api import async_playwright

    url = f"file://{os.path.abspath(html_path)}"
    if output_path is None:
        output_path = str(Path(html_path).with_suffix('.png'))

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": width, "height": 1})

        await page.goto(url)
        # Wait for fonts to load
        await page.wait_for_timeout(1500)

        # Get the actual content height
        height = await page.evaluate("""
            () => {
                const body = document.body;
                const html = document.documentElement;
                return Math.max(
                    body.scrollHeight, body.offsetHeight,
                    html.clientHeight, html.scrollHeight, html.offsetHeight
                );
            }
        """)

        # Resize viewport to full content height, then screenshot
        await page.set_viewport_size({"width": width, "height": height})
        await page.wait_for_timeout(200)

        await page.screenshot(path=output_path, full_page=True)
        await browser.close()

    size_kb = os.path.getsize(output_path) / 1024
    print(f"  ✓ {output_path} ({size_kb:.0f} KB, {width}×{height})")
    return output_path


async def main():
    parser = argparse.ArgumentParser(description="Screenshot static HTML → PNG")
    parser.add_argument("html", nargs="+", help="HTML file(s) or glob pattern")
    parser.add_argument("--width", type=int, default=680,
                        help="Viewport width (default: 680 — matches Substack)")
    parser.add_argument("--format", choices=["png"], default="png",
                        help="Output format (only PNG supported)")
    parser.add_argument("--batch", action="store_true",
                        help="Process multiple files")
    args = parser.parse_args()

    # Expand globs
    files = []
    for pattern in args.html:
        expanded = glob.glob(pattern)
        files.extend(expanded if expanded else [pattern])

    if not files:
        print("No files found.")
        sys.exit(1)

    print(f"Capturing {len(files)} file(s) at {args.width}px width...")
    for html_file in files:
        if not os.path.exists(html_file):
            print(f"  ⚠ Skipping (not found): {html_file}")
            continue
        await capture_screenshot(html_file, width=args.width)

    print(f"\nDone — {len(files)} PNG(s) generated.")


if __name__ == "__main__":
    asyncio.run(main())
