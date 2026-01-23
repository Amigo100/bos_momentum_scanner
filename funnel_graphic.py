#!/usr/bin/env python3
"""
Funnel Graphic Generator
========================

Generates a professional visual funnel showing the 5-gate stock filtering process.
Output: 1200x675 pixel image (Twitter/X card ratio)

Usage:
    python funnel_graphic.py                           # Use signals.json data
    python funnel_graphic.py --test                    # Generate with sample data
    python funnel_graphic.py --output custom_path.png  # Custom output path
    python funnel_graphic.py --style dark              # Dark theme (default)
    python funnel_graphic.py --style light             # Light theme

The funnel shows the 5-Gate Filtering System:
    1. Universe: 1,817 stocks scanned
    2. Volatility Expansion: Beta ≥ 1.5 filter
    3. Institutional Accumulation: Smart money signals
    4. Theme Alignment: Sector flow confirmation
    5. Forensic Audit: Final PASS signals

Integration:
    - Used by tweet_generator.py for funnel_graphic content type
    - Charts saved to trades/charts/funnel_graphic.png
    - Automatically updates chart_manifest.json
"""

import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Tuple

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("Warning: PIL/Pillow not installed. Run: pip install Pillow")

# =============================================================================
# CONFIGURATION
# =============================================================================

# Output paths
TRADES_DIR = Path(__file__).parent / "trades"
CHARTS_DIR = TRADES_DIR / "charts"
DEFAULT_OUTPUT = CHARTS_DIR / "funnel_graphic.png"
MANIFEST_FILE = CHARTS_DIR / "chart_manifest.json"

# Image dimensions (Twitter/X card ratio 1.91:1)
IMAGE_WIDTH = 1200
IMAGE_HEIGHT = 675

# Color themes
THEMES = {
    'dark': {
        'background': '#0d1117',
        'background_gradient': '#161b22',
        'text_primary': '#ffffff',
        'text_secondary': '#8b949e',
        'text_accent': '#58a6ff',
        'text_highlight': '#7ee787',
        'border': '#30363d',
        'glow': '#238636',
    },
    'light': {
        'background': '#ffffff',
        'background_gradient': '#f6f8fa',
        'text_primary': '#24292f',
        'text_secondary': '#57606a',
        'text_accent': '#0969da',
        'text_highlight': '#1a7f37',
        'border': '#d0d7de',
        'glow': '#1a7f37',
    }
}

# Stage colors (gradient progression)
STAGE_COLORS = [
    ('#238636', '#2ea043'),  # Universe - Green
    ('#1f6feb', '#388bfd'),  # Volatility - Blue
    ('#8957e5', '#a371f7'),  # Institutional - Purple
    ('#f78166', '#ffa198'),  # Theme - Orange/Coral
    ('#f0883e', '#ffc107'),  # Final - Gold
]

# Stage configuration
STAGES_CONFIG = [
    {
        'key': 'universe',
        'name': 'Universe',
        'icon': '📊',
        'description': 'US Equities Scanned',
        'marketing_name': 'Market Universe',
    },
    {
        'key': 'volatility',
        'name': 'Volatility Expansion',
        'icon': '📈',
        'description': 'Volatility Expansion Criteria',
        'marketing_name': 'Volatility Filter',
    },
    {
        'key': 'institutional',
        'name': 'Institutional Signals',
        'icon': '🔍',
        'description': 'Institutional Accumulation Divergence',
        'marketing_name': 'Smart Money Detection',
    },
    {
        'key': 'theme',
        'name': 'Theme Alignment',
        'icon': '🎯',
        'description': 'Sector Flow Analysis Confirmed',
        'marketing_name': 'Theme Confirmation',
    },
    {
        'key': 'final',
        'name': 'Forensic Audit',
        'icon': '✅',
        'description': 'The 5th Gate: PASS',
        'marketing_name': 'Final Signals',
    },
]


# =============================================================================
# DATA LOADING
# =============================================================================

def load_signals_data(signals_path: Optional[Path] = None) -> Dict:
    """Load stats from signals.json or return sample data."""
    if signals_path is None:
        signals_path = TRADES_DIR / "signals.json"

    if signals_path.exists():
        try:
            with open(signals_path) as f:
                data = json.load(f)
            stats = data.get('stats', {})

            # Extract date from timestamp
            timestamp = data.get('timestamp', '')
            if timestamp:
                try:
                    date_str = datetime.strptime(timestamp.split()[0], "%Y-%m-%d").strftime("%B %d, %Y")
                except:
                    date_str = datetime.now().strftime("%B %d, %Y")
            else:
                date_str = datetime.now().strftime("%B %d, %Y")

            return {
                'universe': stats.get('tickers_loaded', 1817),
                'volatility': stats.get('beta_gte_1_5', 485),
                'institutional': stats.get('weekly_bos_up', 48),
                'theme': stats.get('theme_confirmed', 17),
                'final': stats.get('final_trade', 6),
                'timestamp': date_str,
                'raw_timestamp': timestamp,
            }
        except Exception as e:
            print(f"  Warning: Error loading signals.json: {e}")

    return get_sample_data()


def get_sample_data() -> Dict:
    """Return sample data for testing."""
    return {
        'universe': 1817,
        'volatility': 485,
        'institutional': 48,
        'theme': 17,
        'final': 6,
        'timestamp': datetime.now().strftime("%B %d, %Y"),
        'raw_timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


# =============================================================================
# FONT HANDLING
# =============================================================================

def get_font(size: int, bold: bool = False, mono: bool = False) -> ImageFont.FreeTypeFont:
    """Get font with fallback chain for cross-platform support."""

    if mono:
        font_paths = [
            '/System/Library/Fonts/SFNSMono.ttf',
            '/System/Library/Fonts/Monaco.dfont',
            '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',
            '/usr/share/fonts/TTF/DejaVuSansMono.ttf',
            'C:\\Windows\\Fonts\\consola.ttf',
        ]
    elif bold:
        font_paths = [
            '/System/Library/Fonts/SFNSDisplay-Bold.otf',
            '/System/Library/Fonts/Helvetica.ttc',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
            '/usr/share/fonts/TTF/DejaVuSans-Bold.ttf',
            'C:\\Windows\\Fonts\\arialbd.ttf',
        ]
    else:
        font_paths = [
            '/System/Library/Fonts/SFNSDisplay.otf',
            '/System/Library/Fonts/Helvetica.ttc',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/TTF/DejaVuSans.ttf',
            'C:\\Windows\\Fonts\\arial.ttf',
        ]

    for font_path in font_paths:
        try:
            return ImageFont.truetype(font_path, size)
        except (IOError, OSError):
            continue

    # Fallback to default
    try:
        return ImageFont.load_default()
    except:
        return None


def get_text_dimensions(draw: ImageDraw, text: str, font: ImageFont) -> Tuple[int, int]:
    """Get text width and height."""
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


# =============================================================================
# DRAWING HELPERS
# =============================================================================

def create_gradient_background(width: int, height: int, color1: str, color2: str) -> Image:
    """Create a vertical gradient background."""
    img = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(img)

    # Parse colors
    r1, g1, b1 = int(color1[1:3], 16), int(color1[3:5], 16), int(color1[5:7], 16)
    r2, g2, b2 = int(color2[1:3], 16), int(color2[3:5], 16), int(color2[5:7], 16)

    for y in range(height):
        ratio = y / height
        r = int(r1 + (r2 - r1) * ratio)
        g = int(g1 + (g2 - g1) * ratio)
        b = int(b1 + (b2 - b1) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    return img


def draw_rounded_trapezoid(
    draw: ImageDraw,
    y_top: int,
    width_top: int,
    width_bottom: int,
    height: int,
    color: str,
    center_x: int,
    border_color: Optional[str] = None,
    border_width: int = 0
) -> int:
    """Draw a trapezoid shape with optional border."""
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

    # Draw border if specified
    if border_color and border_width > 0:
        draw.polygon(points, fill=color, outline=border_color, width=border_width)
    else:
        draw.polygon(points, fill=color)

    return y_bottom


def draw_gradient_trapezoid(
    img: Image,
    y_top: int,
    width_top: int,
    width_bottom: int,
    height: int,
    color1: str,
    color2: str,
    center_x: int
) -> int:
    """Draw a trapezoid with horizontal gradient fill."""
    draw = ImageDraw.Draw(img)

    # Parse colors
    r1, g1, b1 = int(color1[1:3], 16), int(color1[3:5], 16), int(color1[5:7], 16)
    r2, g2, b2 = int(color2[1:3], 16), int(color2[3:5], 16), int(color2[5:7], 16)

    for row in range(height):
        ratio = row / height
        # Interpolate width
        current_width = width_top - (width_top - width_bottom) * ratio
        x1 = center_x - current_width / 2
        x2 = center_x + current_width / 2
        y = y_top + row

        # Interpolate color
        r = int(r1 + (r2 - r1) * ratio)
        g = int(g1 + (g2 - g1) * ratio)
        b = int(b1 + (b2 - b1) * ratio)

        draw.line([(x1, y), (x2, y)], fill=(r, g, b))

    return y_top + height


# =============================================================================
# MAIN GRAPHIC GENERATION
# =============================================================================

def generate_funnel_graphic(
    data: Dict,
    output_path: Optional[Path] = None,
    theme: str = 'dark'
) -> Path:
    """
    Generate the funnel visualization image.

    Args:
        data: Dict with keys: universe, volatility, institutional, theme, final, timestamp
        output_path: Output file path (default: trades/charts/funnel_graphic.png)
        theme: Color theme ('dark' or 'light')

    Returns:
        Path to generated image
    """
    if not PIL_AVAILABLE:
        raise RuntimeError("PIL/Pillow required. Install with: pip install Pillow")

    if output_path is None:
        output_path = DEFAULT_OUTPUT

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Get theme colors
    colors = THEMES.get(theme, THEMES['dark'])

    # Create gradient background
    img = create_gradient_background(
        IMAGE_WIDTH, IMAGE_HEIGHT,
        colors['background'],
        colors['background_gradient']
    )
    draw = ImageDraw.Draw(img)

    # Fonts
    font_title = get_font(42, bold=True)
    font_subtitle = get_font(18)
    font_stage_name = get_font(16, bold=True)
    font_stage_count = get_font(32, bold=True)
    font_pct = get_font(14)
    font_desc = get_font(13)
    font_footer = get_font(14)
    font_conversion = get_font(20, bold=True)

    # =========================================================================
    # HEADER
    # =========================================================================

    # Title
    title = "The 5-Gate Filtering System"
    title_w, title_h = get_text_dimensions(draw, title, font_title)
    draw.text(
        ((IMAGE_WIDTH - title_w) // 2, 28),
        title,
        fill=colors['text_primary'],
        font=font_title
    )

    # Subtitle with date
    subtitle = f"Weekly Scan • {data['timestamp']}"
    subtitle_w, _ = get_text_dimensions(draw, subtitle, font_subtitle)
    draw.text(
        ((IMAGE_WIDTH - subtitle_w) // 2, 78),
        subtitle,
        fill=colors['text_secondary'],
        font=font_subtitle
    )

    # =========================================================================
    # FUNNEL STAGES
    # =========================================================================

    # Funnel layout configuration
    funnel_top = 120
    funnel_center_x = IMAGE_WIDTH // 2 + 50  # Offset right to make room for labels
    funnel_width_start = 520
    funnel_width_end = 100
    stage_height = 78
    stage_gap = 6
    label_margin = 180  # Space for left labels

    # Calculate width reduction per stage
    num_stages = len(STAGES_CONFIG)
    width_reduction = (funnel_width_start - funnel_width_end) / (num_stages - 1)

    # Get data values
    stage_values = [
        data['universe'],
        data['volatility'],
        data['institutional'],
        data['theme'],
        data['final'],
    ]

    # Draw funnel stages
    y = funnel_top
    prev_value = data['universe']

    for i, (stage, value) in enumerate(zip(STAGES_CONFIG, stage_values)):
        current_width = int(funnel_width_start - (width_reduction * i))
        next_width = int(funnel_width_start - (width_reduction * (i + 1))) if i < num_stages - 1 else funnel_width_end

        color1, color2 = STAGE_COLORS[i]

        # Draw stage trapezoid with gradient
        y_bottom = draw_gradient_trapezoid(
            img,
            y_top=y,
            width_top=current_width,
            width_bottom=next_width,
            height=stage_height,
            color1=color1,
            color2=color2,
            center_x=funnel_center_x
        )

        # Redraw the draw object after modifying image
        draw = ImageDraw.Draw(img)

        # Left side: Stage name and icon
        stage_y_center = y + stage_height // 2

        # Icon
        icon_x = funnel_center_x - current_width // 2 - label_margin + 10
        draw.text(
            (icon_x, stage_y_center - 12),
            stage['icon'],
            fill=colors['text_primary'],
            font=font_stage_name
        )

        # Stage name
        name_x = icon_x + 30
        draw.text(
            (name_x, stage_y_center - 10),
            stage['name'],
            fill=colors['text_primary'],
            font=font_stage_name
        )

        # Count in center of stage
        count_text = f"{value:,}"
        count_w, count_h = get_text_dimensions(draw, count_text, font_stage_count)
        draw.text(
            (funnel_center_x - count_w // 2, stage_y_center - count_h // 2 - 2),
            count_text,
            fill='#ffffff',
            font=font_stage_count
        )

        # Right side: Description and conversion percentage
        right_x = funnel_center_x + current_width // 2 + 25

        # Description
        draw.text(
            (right_x, stage_y_center - 18),
            stage['description'],
            fill=colors['text_secondary'],
            font=font_desc
        )

        # Conversion percentage (except for first stage)
        if i > 0 and prev_value > 0:
            pct = (value / prev_value) * 100
            pct_text = f"↓ {pct:.1f}% pass rate"
            draw.text(
                (right_x, stage_y_center + 2),
                pct_text,
                fill=colors['text_accent'],
                font=font_pct
            )

        prev_value = value
        y = y_bottom + stage_gap

    # =========================================================================
    # CONVERSION SUMMARY
    # =========================================================================

    summary_y = y + 15

    # Overall conversion
    if data['universe'] > 0:
        overall_pct = (data['final'] / data['universe']) * 100
        conversion_text = f"Final Result: {data['universe']:,} stocks → {data['final']} actionable signals ({overall_pct:.2f}%)"
    else:
        conversion_text = f"Final Result: {data['universe']:,} → {data['final']} signals"

    conv_w, _ = get_text_dimensions(draw, conversion_text, font_conversion)
    draw.text(
        ((IMAGE_WIDTH - conv_w) // 2, summary_y),
        conversion_text,
        fill=colors['text_highlight'],
        font=font_conversion
    )

    # =========================================================================
    # FOOTER
    # =========================================================================

    # Brand footer
    footer_text = "Sterling Signals • sterlingsignals.substack.com"
    footer_w, _ = get_text_dimensions(draw, footer_text, font_footer)
    draw.text(
        ((IMAGE_WIDTH - footer_w) // 2, IMAGE_HEIGHT - 40),
        footer_text,
        fill=colors['text_secondary'],
        font=font_footer
    )

    # Decorative line above footer
    line_y = IMAGE_HEIGHT - 55
    line_width = 400
    draw.line(
        [(IMAGE_WIDTH // 2 - line_width // 2, line_y),
         (IMAGE_WIDTH // 2 + line_width // 2, line_y)],
        fill=colors['border'],
        width=1
    )

    # =========================================================================
    # SAVE
    # =========================================================================

    img.save(output_path, 'PNG', quality=95, optimize=True)
    print(f"  ✅ Funnel graphic saved: {output_path}")

    # Update chart manifest
    update_chart_manifest(output_path, data)

    return output_path


def update_chart_manifest(output_path: Path, data: Dict):
    """Update the chart manifest with the new funnel graphic."""
    try:
        if MANIFEST_FILE.exists():
            with open(MANIFEST_FILE) as f:
                manifest = json.load(f)
        else:
            manifest = {'charts': {}}

        manifest['charts']['funnel_graphic'] = {
            'path': str(output_path),
            'generated': datetime.now().isoformat(),
            'data': {
                'universe': data['universe'],
                'final': data['final'],
                'timestamp': data['timestamp'],
            }
        }

        with open(MANIFEST_FILE, 'w') as f:
            json.dump(manifest, f, indent=2)

    except Exception as e:
        print(f"  Warning: Could not update manifest: {e}")


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Generate funnel visualization for the 5-Gate Filtering System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python funnel_graphic.py                    # Use signals.json data
    python funnel_graphic.py --test             # Generate with sample data
    python funnel_graphic.py --style light      # Light theme
    python funnel_graphic.py -o custom.png      # Custom output path
        """
    )
    parser.add_argument(
        '--test', '-t',
        action='store_true',
        help='Generate with sample data for testing'
    )
    parser.add_argument(
        '--signals', '-s',
        type=str,
        help='Path to signals.json file'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Output path for image'
    )
    parser.add_argument(
        '--style',
        choices=['dark', 'light'],
        default='dark',
        help='Color theme (default: dark)'
    )

    args = parser.parse_args()

    if not PIL_AVAILABLE:
        print("ERROR: PIL/Pillow not installed.")
        print("Install with: pip install Pillow")
        return 1

    # Load data
    print("\n" + "=" * 60)
    print("  FUNNEL GRAPHIC GENERATOR")
    print("=" * 60 + "\n")

    if args.test:
        data = get_sample_data()
        print("  Using sample data for testing...")
    elif args.signals:
        data = load_signals_data(Path(args.signals))
    else:
        data = load_signals_data()

    print(f"\n  📊 Scan Data:")
    print(f"     Universe:     {data['universe']:,} stocks")
    print(f"     Volatility:   {data['volatility']:,} passed")
    print(f"     Institutional: {data['institutional']:,} signals")
    print(f"     Theme:        {data['theme']:,} confirmed")
    print(f"     Final:        {data['final']} PASS signals")
    print(f"     Date:         {data['timestamp']}")
    print()

    # Generate
    output_path = Path(args.output) if args.output else None
    generate_funnel_graphic(data, output_path, theme=args.style)

    print("\n" + "=" * 60 + "\n")
    return 0


if __name__ == "__main__":
    exit(main())
