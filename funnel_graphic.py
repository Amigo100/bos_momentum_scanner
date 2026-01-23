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

The funnel shows:
    1. Universe: 1,817 stocks
    2. Volatility Expansion Criteria: X passed
    3. Institutional Accumulation: X showed signals
    4. Theme Alignment: X confirmed
    5. Forensic Audit: X final PASS
"""

import json
import argparse
from pathlib import Path
from datetime import datetime

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("Warning: PIL/Pillow not installed. Run: pip install Pillow")

# Output paths
TRADES_DIR = Path(__file__).parent / "trades"
CHARTS_DIR = TRADES_DIR / "charts"
DEFAULT_OUTPUT = CHARTS_DIR / "funnel_graphic.png"

# Color scheme (dark theme matching Sterling Signals brand)
COLORS = {
    'background': '#0d1117',      # Dark background
    'funnel_top': '#238636',      # Green (universe)
    'funnel_mid1': '#1f6feb',     # Blue (volatility)
    'funnel_mid2': '#8957e5',     # Purple (institutional)
    'funnel_mid3': '#f78166',     # Orange (theme)
    'funnel_bottom': '#f0883e',   # Gold (final)
    'text_primary': '#ffffff',    # White text
    'text_secondary': '#8b949e',  # Gray text
    'text_accent': '#58a6ff',     # Blue accent
    'border': '#30363d',          # Border color
}

# Stage colors (gradient from green to gold)
STAGE_COLORS = [
    '#238636',  # Universe - Green
    '#1f6feb',  # Volatility - Blue
    '#8957e5',  # Institutional - Purple
    '#f78166',  # Theme - Orange
    '#f0883e',  # Final - Gold
]


def load_signals_data(signals_path: Path = None) -> dict:
    """Load stats from signals.json or return sample data."""
    if signals_path is None:
        signals_path = TRADES_DIR / "signals.json"

    if signals_path.exists():
        try:
            with open(signals_path) as f:
                data = json.load(f)
            stats = data.get('stats', {})
            return {
                'universe': stats.get('tickers_loaded', 1817),
                'volatility': stats.get('beta_gte_1_5', 485),
                'institutional': stats.get('weekly_bos_up', 48),
                'theme': stats.get('theme_confirmed', 17),
                'final': stats.get('final_trade', 6),
                'timestamp': data.get('timestamp', datetime.now().strftime("%Y-%m-%d")),
            }
        except Exception as e:
            print(f"Error loading signals.json: {e}")

    # Return sample data if file not found
    return get_sample_data()


def get_sample_data() -> dict:
    """Return sample data for testing."""
    return {
        'universe': 1817,
        'volatility': 485,
        'institutional': 48,
        'theme': 17,
        'final': 6,
        'timestamp': datetime.now().strftime("%Y-%m-%d"),
    }


def get_font(size: int, bold: bool = False):
    """Get font, falling back to default if custom fonts unavailable."""
    # Try common system fonts
    font_names = [
        '/System/Library/Fonts/SFNSMono.ttf',  # macOS
        '/System/Library/Fonts/Helvetica.ttc',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',  # Linux
        '/usr/share/fonts/TTF/DejaVuSans.ttf',
        'C:\\Windows\\Fonts\\arial.ttf',  # Windows
    ]

    if bold:
        font_names = [
            '/System/Library/Fonts/SFNSMono.ttf',
            '/System/Library/Fonts/Helvetica.ttc',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
            'C:\\Windows\\Fonts\\arialbd.ttf',
        ] + font_names

    for font_path in font_names:
        try:
            return ImageFont.truetype(font_path, size)
        except (IOError, OSError):
            continue

    # Fallback to default
    return ImageFont.load_default()


def draw_funnel_stage(
    draw: ImageDraw,
    y_top: int,
    width_top: int,
    width_bottom: int,
    height: int,
    color: str,
    center_x: int
):
    """Draw a single funnel stage (trapezoid shape)."""
    x1_top = center_x - width_top // 2
    x2_top = center_x + width_top // 2
    x1_bottom = center_x - width_bottom // 2
    x2_bottom = center_x + width_bottom // 2
    y_bottom = y_top + height

    # Draw trapezoid
    points = [
        (x1_top, y_top),
        (x2_top, y_top),
        (x2_bottom, y_bottom),
        (x1_bottom, y_bottom),
    ]
    draw.polygon(points, fill=color)

    return y_bottom


def generate_funnel_graphic(data: dict, output_path: Path = None) -> Path:
    """
    Generate funnel visualization image.

    Args:
        data: Dict with keys: universe, volatility, institutional, theme, final
        output_path: Output file path (default: trades/charts/funnel_graphic.png)

    Returns:
        Path to generated image
    """
    if not PIL_AVAILABLE:
        raise RuntimeError("PIL/Pillow required. Install with: pip install Pillow")

    if output_path is None:
        output_path = DEFAULT_OUTPUT

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Image dimensions (Twitter card ratio 1.91:1, also works for most social)
    width = 1200
    height = 675

    # Create image
    img = Image.new('RGB', (width, height), color=COLORS['background'])
    draw = ImageDraw.Draw(img)

    # Fonts
    font_title = get_font(36, bold=True)
    font_stage_name = get_font(18)
    font_stage_count = get_font(28, bold=True)
    font_pct = get_font(14)
    font_footer = get_font(14)

    # Title
    title = "The 5-Gate Filtering System"
    title_bbox = draw.textbbox((0, 0), title, font=font_title)
    title_width = title_bbox[2] - title_bbox[0]
    draw.text(
        ((width - title_width) // 2, 25),
        title,
        fill=COLORS['text_primary'],
        font=font_title
    )

    # Subtitle
    subtitle = f"Week of {data['timestamp']}"
    subtitle_bbox = draw.textbbox((0, 0), subtitle, font=font_footer)
    subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
    draw.text(
        ((width - subtitle_width) // 2, 70),
        subtitle,
        fill=COLORS['text_secondary'],
        font=font_footer
    )

    # Funnel stages data
    stages = [
        ("Universe", data['universe'], "US Equities Scanned"),
        ("Volatility Expansion", data['volatility'], "Beta ≥ 1.5 Filter"),
        ("Institutional Signals", data['institutional'], "Smart Money Accumulation"),
        ("Theme Alignment", data['theme'], "Sector Flow Confirmed"),
        ("Forensic Audit", data['final'], "Final PASS Signals"),
    ]

    # Funnel dimensions
    funnel_top = 110
    funnel_left_margin = 120
    funnel_width_start = 700
    funnel_width_end = 120
    stage_height = 85
    stage_gap = 8
    center_x = width // 2

    # Calculate width reduction per stage
    width_reduction = (funnel_width_start - funnel_width_end) / (len(stages) - 1)

    # Draw funnel stages
    y = funnel_top
    prev_count = data['universe']

    for i, (name, count, description) in enumerate(stages):
        current_width = int(funnel_width_start - (width_reduction * i))
        next_width = int(funnel_width_start - (width_reduction * (i + 1))) if i < len(stages) - 1 else funnel_width_end

        # Draw stage
        y_bottom = draw_funnel_stage(
            draw,
            y_top=y,
            width_top=current_width,
            width_bottom=next_width,
            height=stage_height,
            color=STAGE_COLORS[i],
            center_x=center_x
        )

        # Stage name (left side)
        name_x = center_x - current_width // 2 - 10
        name_y = y + stage_height // 2 - 10
        draw.text(
            (funnel_left_margin - 100, name_y),
            name,
            fill=COLORS['text_primary'],
            font=font_stage_name,
            anchor="rm"
        )

        # Count (center of stage)
        count_text = f"{count:,}"
        count_bbox = draw.textbbox((0, 0), count_text, font=font_stage_count)
        count_width = count_bbox[2] - count_bbox[0]
        draw.text(
            (center_x - count_width // 2, y + stage_height // 2 - 15),
            count_text,
            fill=COLORS['text_primary'],
            font=font_stage_count
        )

        # Percentage (right side) - except for first stage
        if i > 0:
            pct = (count / prev_count * 100) if prev_count > 0 else 0
            pct_text = f"→ {pct:.1f}%"
            pct_x = center_x + current_width // 2 + 20
            draw.text(
                (pct_x, name_y),
                pct_text,
                fill=COLORS['text_accent'],
                font=font_pct
            )

        # Description (right side, below percentage)
        desc_x = center_x + current_width // 2 + 20
        draw.text(
            (desc_x, name_y + 18),
            description,
            fill=COLORS['text_secondary'],
            font=font_pct
        )

        prev_count = count
        y = y_bottom + stage_gap

    # Overall conversion rate
    if data['universe'] > 0:
        overall_pct = data['final'] / data['universe'] * 100
        conversion_text = f"Overall: {data['universe']:,} → {data['final']} ({overall_pct:.2f}%)"
    else:
        conversion_text = f"Overall: {data['universe']:,} → {data['final']}"

    conv_bbox = draw.textbbox((0, 0), conversion_text, font=font_stage_name)
    conv_width = conv_bbox[2] - conv_bbox[0]
    draw.text(
        ((width - conv_width) // 2, y + 20),
        conversion_text,
        fill=COLORS['text_accent'],
        font=font_stage_name
    )

    # Footer
    footer_text = "Sterling Signals | sterlingsignals.substack.com"
    footer_bbox = draw.textbbox((0, 0), footer_text, font=font_footer)
    footer_width = footer_bbox[2] - footer_bbox[0]
    draw.text(
        ((width - footer_width) // 2, height - 35),
        footer_text,
        fill=COLORS['text_secondary'],
        font=font_footer
    )

    # Save image
    img.save(output_path, 'PNG', quality=95)
    print(f"Funnel graphic saved: {output_path}")

    return output_path


def main():
    parser = argparse.ArgumentParser(description="Generate funnel visualization graphic")
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

    print(f"Generating funnel graphic...")
    print(f"  Universe: {data['universe']:,}")
    print(f"  Volatility: {data['volatility']:,}")
    print(f"  Institutional: {data['institutional']:,}")
    print(f"  Theme: {data['theme']:,}")
    print(f"  Final: {data['final']}")

    # Generate
    output_path = Path(args.output) if args.output else None
    generate_funnel_graphic(data, output_path)

    return 0


if __name__ == "__main__":
    exit(main())
