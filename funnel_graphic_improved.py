#!/usr/bin/env python3
"""
Funnel Graphic Generator
========================

Generates a visual funnel showing the stock filtering process.
Output: 1200x675 pixel image (Twitter card ratio)

Usage:
    python funnel_graphic.py                           # Use signals.json data
    python funnel_graphic.py --test                    # Generate with sample data
    python funnel_graphic.py --output custom_path.png  # Custom output path
    python funnel_graphic.py --with-tweet              # Also output tweet text

The funnel shows the 5-Gate System:
    1. Universe: 1,817 stocks analyzed
    2. Volatility Expansion Criteria: X passed
    3. Institutional Accumulation Divergence: X showed signals
    4. Theme Momentum Alignment: X confirmed
    5. Forensic Audit: X final PASS

IMPORTANT: All terminology follows MARKETING_GUIDE.md approved vocabulary.
           NO internal terms (Beta, BoS, Banker, etc.) appear on the graphic.
"""

import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple
import sys

try:
    from PIL import Image, ImageDraw, ImageFont
    import PIL
    PIL_AVAILABLE = True
    PIL_VERSION = tuple(map(int, PIL.__version__.split('.')[:2]))
    ANCHOR_SUPPORTED = PIL_VERSION >= (8, 0)
except ImportError:
    PIL_AVAILABLE = False
    ANCHOR_SUPPORTED = False
    print("Warning: PIL/Pillow not installed. Run: pip install Pillow")

# Output paths
TRADES_DIR = Path(__file__).parent / "trades"
CHARTS_DIR = TRADES_DIR / "charts"
DEFAULT_OUTPUT = CHARTS_DIR / "funnel_graphic.png"
MANIFEST_PATH = CHARTS_DIR / "chart_manifest.json"

# =============================================================================
# MARKETING-APPROVED TERMINOLOGY (from MARKETING_GUIDE.md)
# =============================================================================
# These are the ONLY terms that should appear on the graphic.
# Internal terms like "Beta >= 1.5", "BoS", "Banker" are BANNED.

STAGE_LABELS = {
    'universe': {
        'name': 'Universe',
        'description': 'US Stocks Analyzed',
    },
    'volatility': {
        'name': 'Gate 1',
        'description': 'Volatility Expansion Criteria',
    },
    'institutional': {
        'name': 'Gate 2',
        'description': 'Institutional Accumulation Divergence',
    },
    'theme': {
        'name': 'Gate 3',
        'description': 'Theme Momentum Alignment',
    },
    'final': {
        'name': 'Gate 4-5',
        'description': 'Forensic Audit: PASS',
    },
}

# =============================================================================
# COLOR SCHEME (Dark theme - Sterling Signals brand)
# =============================================================================

COLORS = {
    'background': '#0d1117',
    'text_primary': '#ffffff',
    'text_secondary': '#8b949e',
    'text_accent': '#58a6ff',
    'text_gold': '#f0883e',
    'border': '#30363d',
}

# Stage colors (gradient from green to gold) - tested for contrast
STAGE_COLORS = [
    '#2ea043',  # Universe - Bright Green (improved contrast)
    '#1f6feb',  # Gate 1 - Blue
    '#a371f7',  # Gate 2 - Light Purple (improved from #8957e5)
    '#f78166',  # Gate 3 - Orange
    '#f0883e',  # Gate 4-5 - Gold
]


def load_signals_data(signals_path: Path = None) -> dict:
    """
    Load stats from signals.json or return sample data.
    
    Handles multiple possible key names from signals.json to map
    to our standard data structure.
    """
    if signals_path is None:
        signals_path = TRADES_DIR / "signals.json"

    if signals_path.exists():
        try:
            with open(signals_path) as f:
                data = json.load(f)
            
            stats = data.get('stats', {})
            
            # Map various possible key names to our standard structure
            # This handles different versions of signals.json
            return {
                'universe': (
                    stats.get('tickers_loaded') or 
                    stats.get('universe') or 
                    stats.get('total_scanned') or 
                    1817
                ),
                'volatility': (
                    stats.get('volatility_pass') or
                    stats.get('beta_gte_1_5') or  # Legacy key
                    stats.get('gate_1_pass') or
                    485
                ),
                'institutional': (
                    stats.get('institutional_pass') or
                    stats.get('weekly_bos_up') or  # Legacy key
                    stats.get('gate_2_pass') or
                    48
                ),
                'theme': (
                    stats.get('theme_pass') or
                    stats.get('theme_confirmed') or  # Legacy key
                    stats.get('gate_3_pass') or
                    17
                ),
                'final': (
                    stats.get('final_pass') or
                    stats.get('final_trade') or  # Legacy key
                    stats.get('pass_signals') or
                    6
                ),
                'final_tickers': (
                    stats.get('pass_tickers') or
                    data.get('pass_signals', [])
                ),
                'timestamp': data.get('timestamp', datetime.now().strftime("%Y-%m-%d")),
                'week_number': data.get('week_number', datetime.now().isocalendar()[1]),
            }
        except Exception as e:
            print(f"Warning: Error loading signals.json: {e}")
            print("Using sample data instead.")

    return get_sample_data()


def get_sample_data() -> dict:
    """Return sample data for testing."""
    return {
        'universe': 1817,
        'volatility': 485,
        'institutional': 48,
        'theme': 17,
        'final': 6,
        'final_tickers': ['OKLO', 'RCAT', 'LUNR', 'QBTS', 'RGTI', 'IONQ'],
        'timestamp': datetime.now().strftime("%Y-%m-%d"),
        'week_number': datetime.now().isocalendar()[1],
    }


def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Get font, falling back to default if custom fonts unavailable."""
    font_paths = []
    
    if bold:
        font_paths = [
            # macOS
            '/System/Library/Fonts/Supplemental/Arial Bold.ttf',
            '/System/Library/Fonts/SFNSDisplay-Bold.otf',
            # Linux
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
            '/usr/share/fonts/TTF/DejaVuSans-Bold.ttf',
            # Windows
            'C:\\Windows\\Fonts\\arialbd.ttf',
        ]
    
    font_paths += [
        # macOS
        '/System/Library/Fonts/Supplemental/Arial.ttf',
        '/System/Library/Fonts/SFNSDisplay.otf',
        '/System/Library/Fonts/Helvetica.ttc',
        # Linux
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/TTF/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
        # Windows
        'C:\\Windows\\Fonts\\arial.ttf',
    ]

    for font_path in font_paths:
        try:
            return ImageFont.truetype(font_path, size)
        except (IOError, OSError):
            continue

    # Fallback to default (will be small but functional)
    try:
        return ImageFont.load_default()
    except:
        return None


def draw_text_safe(
    draw: ImageDraw,
    position: Tuple[int, int],
    text: str,
    font: ImageFont,
    fill: str,
    anchor: str = None
) -> None:
    """
    Draw text with safe anchor handling for older Pillow versions.
    """
    if anchor and ANCHOR_SUPPORTED:
        draw.text(position, text, fill=fill, font=font, anchor=anchor)
    else:
        # Manual anchor calculation for older Pillow
        if anchor and anchor in ('rm', 'mm', 'lm'):
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x, y = position
            if anchor.startswith('r'):
                x -= text_width
            elif anchor.startswith('m'):
                x -= text_width // 2
            
            if anchor.endswith('m'):
                y -= text_height // 2
            
            position = (x, y)
        
        draw.text(position, text, fill=fill, font=font)


def draw_funnel_stage(
    draw: ImageDraw,
    y_top: int,
    width_top: int,
    width_bottom: int,
    height: int,
    color: str,
    center_x: int
) -> int:
    """Draw a single funnel stage (trapezoid shape)."""
    x1_top = center_x - width_top // 2
    x2_top = center_x + width_top // 2
    x1_bottom = center_x - width_bottom // 2
    x2_bottom = center_x + width_bottom // 2
    y_bottom = y_top + height

    points = [
        (x1_top, y_top),
        (x2_top, y_top),
        (x2_bottom, y_bottom),
        (x1_bottom, y_bottom),
    ]
    draw.polygon(points, fill=color)

    return y_bottom


def generate_funnel_graphic(
    data: dict,
    output_path: Path = None,
    update_manifest: bool = True
) -> Tuple[Path, str]:
    """
    Generate funnel visualization image.

    Args:
        data: Dict with keys: universe, volatility, institutional, theme, final
        output_path: Output file path (default: trades/charts/funnel_graphic.png)
        update_manifest: Whether to update chart_manifest.json

    Returns:
        Tuple of (path to generated image, suggested tweet text)
    """
    if not PIL_AVAILABLE:
        raise RuntimeError("PIL/Pillow required. Install with: pip install Pillow")

    if output_path is None:
        output_path = DEFAULT_OUTPUT

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Image dimensions (Twitter card ratio ~1.91:1)
    width = 1200
    height = 675

    # Create image
    img = Image.new('RGB', (width, height), color=COLORS['background'])
    draw = ImageDraw.Draw(img)

    # Fonts
    font_title = get_font(42, bold=True)
    font_subtitle = get_font(16)
    font_stage_name = get_font(16, bold=True)
    font_stage_desc = get_font(14)
    font_stage_count = get_font(26, bold=True)
    font_pct = get_font(13)
    font_footer = get_font(13)
    font_callout = get_font(18, bold=True)

    # === HEADER ===
    title = "The 5-Gate Screening System"
    title_bbox = draw.textbbox((0, 0), title, font=font_title)
    title_width = title_bbox[2] - title_bbox[0]
    draw.text(
        ((width - title_width) // 2, 20),
        title,
        fill=COLORS['text_primary'],
        font=font_title
    )

    # Subtitle with week number
    week_num = data.get('week_number', datetime.now().isocalendar()[1])
    subtitle = f"Week {week_num} • {data['timestamp']}"
    subtitle_bbox = draw.textbbox((0, 0), subtitle, font=font_subtitle)
    subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
    draw.text(
        ((width - subtitle_width) // 2, 68),
        subtitle,
        fill=COLORS['text_secondary'],
        font=font_subtitle
    )

    # === FUNNEL ===
    stages = [
        ('universe', data['universe']),
        ('volatility', data['volatility']),
        ('institutional', data['institutional']),
        ('theme', data['theme']),
        ('final', data['final']),
    ]

    funnel_top = 100
    funnel_width_start = 650
    funnel_width_end = 130
    stage_height = 80
    stage_gap = 6
    center_x = width // 2 + 50  # Offset right to make room for labels

    width_reduction = (funnel_width_start - funnel_width_end) / (len(stages) - 1)

    y = funnel_top
    prev_count = data['universe']
    left_label_x = 80

    for i, (stage_key, count) in enumerate(stages):
        stage_info = STAGE_LABELS[stage_key]
        current_width = int(funnel_width_start - (width_reduction * i))
        next_width = int(funnel_width_start - (width_reduction * (i + 1))) if i < len(stages) - 1 else funnel_width_end

        # Draw trapezoid
        y_bottom = draw_funnel_stage(
            draw,
            y_top=y,
            width_top=current_width,
            width_bottom=next_width,
            height=stage_height,
            color=STAGE_COLORS[i],
            center_x=center_x
        )

        # Left side: Stage name
        name_y = y + stage_height // 2 - 20
        draw.text(
            (left_label_x, name_y),
            stage_info['name'],
            fill=COLORS['text_primary'],
            font=font_stage_name
        )
        
        # Left side: Description (below name)
        draw.text(
            (left_label_x, name_y + 20),
            stage_info['description'],
            fill=COLORS['text_secondary'],
            font=font_stage_desc
        )

        # Center: Count
        count_text = f"{count:,}"
        count_bbox = draw.textbbox((0, 0), count_text, font=font_stage_count)
        count_width = count_bbox[2] - count_bbox[0]
        draw.text(
            (center_x - count_width // 2, y + stage_height // 2 - 13),
            count_text,
            fill=COLORS['text_primary'],
            font=font_stage_count
        )

        # Right side: Pass rate (except first stage)
        if i > 0 and prev_count > 0:
            pct = count / prev_count * 100
            pct_text = f"→ {pct:.1f}% pass"
            right_x = center_x + current_width // 2 + 25
            draw.text(
                (right_x, y + stage_height // 2 - 8),
                pct_text,
                fill=COLORS['text_accent'],
                font=font_pct
            )

        prev_count = count
        y = y_bottom + stage_gap

    # === BOTTOM CALLOUT ===
    # Overall conversion
    if data['universe'] > 0:
        overall_pct = data['final'] / data['universe'] * 100
        conversion_text = f"{data['universe']:,} stocks → {data['final']} actionable signals ({overall_pct:.3f}%)"
    else:
        conversion_text = f"{data['universe']:,} stocks → {data['final']} actionable signals"

    conv_bbox = draw.textbbox((0, 0), conversion_text, font=font_callout)
    conv_width = conv_bbox[2] - conv_bbox[0]
    draw.text(
        ((width - conv_width) // 2, y + 15),
        conversion_text,
        fill=COLORS['text_gold'],
        font=font_callout
    )

    # === FOOTER ===
    footer_left = "Sterling Signals"
    footer_right = "@SterlingSignals • sterlingsignals.substack.com"
    
    draw.text(
        (30, height - 35),
        footer_left,
        fill=COLORS['text_secondary'],
        font=font_footer
    )
    
    footer_right_bbox = draw.textbbox((0, 0), footer_right, font=font_footer)
    footer_right_width = footer_right_bbox[2] - footer_right_bbox[0]
    draw.text(
        (width - footer_right_width - 30, height - 35),
        footer_right,
        fill=COLORS['text_secondary'],
        font=font_footer
    )

    # Save image
    img.save(output_path, 'PNG', quality=95, optimize=True)
    print(f"✓ Funnel graphic saved: {output_path}")

    # Update manifest
    if update_manifest:
        update_chart_manifest(output_path, data)

    # Generate tweet text (MARKETING_GUIDE.md Section 2.4 template)
    tweet_text = generate_tweet_text(data)

    return output_path, tweet_text


def generate_tweet_text(data: dict) -> str:
    """
    Generate tweet text following MARKETING_GUIDE.md Section 2.4 template.
    """
    tweet = f"""This week's scan:

📊 {data['universe']:,} stocks analyzed
📉 {data['volatility']:,} passed Volatility Expansion Criteria
🔍 {data['institutional']:,} showed Institutional Accumulation
🎯 {data['theme']:,} aligned with hot themes
✅ {data['final']} cleared the Forensic Audit

{data['final']} actionable signals. Full breakdown in the newsletter."""

    return tweet


def update_chart_manifest(image_path: Path, data: dict) -> None:
    """Update chart_manifest.json with the new funnel graphic."""
    manifest = {}
    
    if MANIFEST_PATH.exists():
        try:
            with open(MANIFEST_PATH) as f:
                manifest = json.load(f)
        except:
            pass
    
    manifest['funnel_graphic'] = {
        'path': str(image_path),
        'generated_at': datetime.now().isoformat(),
        'data': {
            'universe': data['universe'],
            'final': data['final'],
            'week': data.get('week_number'),
        },
        'type': 'funnel',
    }
    
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"✓ Manifest updated: {MANIFEST_PATH}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate funnel visualization graphic",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python funnel_graphic.py                    # Use signals.json
  python funnel_graphic.py --test             # Sample data
  python funnel_graphic.py --with-tweet       # Output tweet text
  python funnel_graphic.py -o my_funnel.png   # Custom output
        """
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Generate with sample data'
    )
    parser.add_argument(
        '--signals',
        type=str,
        help='Path to signals.json file'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Output path for image'
    )
    parser.add_argument(
        '--with-tweet',
        action='store_true',
        help='Also output the suggested tweet text'
    )
    parser.add_argument(
        '--no-manifest',
        action='store_true',
        help='Skip updating chart_manifest.json'
    )

    args = parser.parse_args()

    if not PIL_AVAILABLE:
        print("ERROR: PIL/Pillow not installed.")
        print("Install with: pip install Pillow")
        return 1

    # Load data
    if args.test:
        data = get_sample_data()
        print("Using sample data for testing...")
    elif args.signals:
        data = load_signals_data(Path(args.signals))
    else:
        data = load_signals_data()

    print(f"\nGenerating funnel graphic...")
    print(f"  Universe:      {data['universe']:,}")
    print(f"  Gate 1 Pass:   {data['volatility']:,}")
    print(f"  Gate 2 Pass:   {data['institutional']:,}")
    print(f"  Gate 3 Pass:   {data['theme']:,}")
    print(f"  Final PASS:    {data['final']}")
    print()

    # Generate
    output_path = Path(args.output) if args.output else None
    image_path, tweet_text = generate_funnel_graphic(
        data,
        output_path,
        update_manifest=not args.no_manifest
    )

    if args.with_tweet:
        print("\n" + "=" * 60)
        print("SUGGESTED TWEET (MARKETING_GUIDE.md Section 2.4)")
        print("=" * 60)
        print(tweet_text)
        print("=" * 60)
        
        # Also save tweet to file
        tweet_path = image_path.parent / "funnel_tweet.txt"
        with open(tweet_path, 'w') as f:
            f.write(tweet_text)
        print(f"✓ Tweet text saved: {tweet_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
