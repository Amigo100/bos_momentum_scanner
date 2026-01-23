#!/usr/bin/env python3
"""
Card Generator
==============

Generates visual cards for trades and portfolio performance.
Output: 1200x675 pixel images (Twitter/X card ratio)

Card Types:
    1. Post-Mortem Card: Stopped-out position with entry/exit and lesson
    2. Win Card: Profitable exit celebration with gain %
    3. Alpha Card: Portfolio vs SPY performance comparison

Usage:
    python card_generator.py post_mortem TICKER --entry 10.50 --exit 8.40 --loss 20
    python card_generator.py win TICKER --entry 10.50 --exit 15.75 --gain 50 --days 45
    python card_generator.py alpha --portfolio 15.5 --spy 8.2 --period YTD
    python card_generator.py --test  # Generate all sample cards

Integration:
    - Used by tweet_generator.py for post_mortem, win_card, alpha_card content types
    - Cards saved to trades/charts/
    - Automatically updates chart_manifest.json
"""

import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Tuple

try:
    from PIL import Image, ImageDraw, ImageFont
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
        'text_muted': '#6e7681',
        'border': '#30363d',
        'green': '#7ee787',
        'green_bg': '#238636',
        'red': '#f85149',
        'red_bg': '#da3633',
        'gold': '#f0883e',
        'blue': '#58a6ff',
        'accent': '#a371f7',
    },
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


def draw_rounded_rectangle(
    draw: ImageDraw,
    xy: Tuple[int, int, int, int],
    radius: int,
    fill: str,
    outline: Optional[str] = None,
    width: int = 1
):
    """Draw a rounded rectangle."""
    x1, y1, x2, y2 = xy

    # Draw rounded rectangle using multiple shapes
    draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill)
    draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill)

    # Corners
    draw.pieslice([x1, y1, x1 + 2 * radius, y1 + 2 * radius], 180, 270, fill=fill)
    draw.pieslice([x2 - 2 * radius, y1, x2, y1 + 2 * radius], 270, 360, fill=fill)
    draw.pieslice([x1, y2 - 2 * radius, x1 + 2 * radius, y2], 90, 180, fill=fill)
    draw.pieslice([x2 - 2 * radius, y2 - 2 * radius, x2, y2], 0, 90, fill=fill)

    # Outline if specified
    if outline:
        draw.arc([x1, y1, x1 + 2 * radius, y1 + 2 * radius], 180, 270, fill=outline, width=width)
        draw.arc([x2 - 2 * radius, y1, x2, y1 + 2 * radius], 270, 360, fill=outline, width=width)
        draw.arc([x1, y2 - 2 * radius, x1 + 2 * radius, y2], 90, 180, fill=outline, width=width)
        draw.arc([x2 - 2 * radius, y2 - 2 * radius, x2, y2], 0, 90, fill=outline, width=width)
        draw.line([x1 + radius, y1, x2 - radius, y1], fill=outline, width=width)
        draw.line([x1 + radius, y2, x2 - radius, y2], fill=outline, width=width)
        draw.line([x1, y1 + radius, x1, y2 - radius], fill=outline, width=width)
        draw.line([x2, y1 + radius, x2, y2 - radius], fill=outline, width=width)


# =============================================================================
# POST-MORTEM CARD
# =============================================================================

def generate_post_mortem_card(
    ticker: str,
    entry_price: float,
    exit_price: float,
    loss_pct: float,
    theme: str = "",
    lesson: str = "",
    output_path: Optional[Path] = None
) -> Path:
    """
    Generate Post-Mortem Card for stopped-out position.

    Args:
        ticker: Stock symbol
        entry_price: Entry price
        exit_price: Exit price (stop hit)
        loss_pct: Loss percentage (positive number, e.g., 20 for -20%)
        theme: Investment theme (optional)
        lesson: Brief lesson learned (optional)
        output_path: Output file path

    Returns:
        Path to generated image
    """
    if not PIL_AVAILABLE:
        raise RuntimeError("PIL/Pillow required. Install with: pip install Pillow")

    if output_path is None:
        output_path = CHARTS_DIR / f"post_mortem_{ticker}_{datetime.now():%Y%m%d}.png"

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    colors = THEMES['dark']

    # Create background
    img = create_gradient_background(
        IMAGE_WIDTH, IMAGE_HEIGHT,
        colors['background'],
        colors['background_gradient']
    )
    draw = ImageDraw.Draw(img)

    # Fonts
    font_icon = get_font(80, bold=True)
    font_ticker = get_font(72, bold=True)
    font_label = get_font(24)
    font_value = get_font(36, bold=True)
    font_pct = get_font(48, bold=True)
    font_lesson = get_font(22)
    font_footer = get_font(16)
    font_quote = get_font(20)

    center_x = IMAGE_WIDTH // 2

    # =========================================================================
    # HEADER - Red X icon
    # =========================================================================

    icon = "X"
    icon_w, icon_h = get_text_dimensions(draw, icon, font_icon)
    draw.text(
        (center_x - icon_w // 2, 40),
        icon,
        fill=colors['red'],
        font=font_icon
    )

    # Ticker
    ticker_text = f"${ticker}"
    ticker_w, _ = get_text_dimensions(draw, ticker_text, font_ticker)
    draw.text(
        (center_x - ticker_w // 2, 130),
        ticker_text,
        fill=colors['text_primary'],
        font=font_ticker
    )

    # "Stopped Out" label
    label = "STOPPED OUT"
    label_w, _ = get_text_dimensions(draw, label, font_label)
    draw.text(
        (center_x - label_w // 2, 205),
        label,
        fill=colors['red'],
        font=font_label
    )

    # =========================================================================
    # PRICE INFO BOX
    # =========================================================================

    box_y = 260
    box_height = 130
    box_width = 600
    box_x = center_x - box_width // 2

    draw_rounded_rectangle(
        draw,
        (box_x, box_y, box_x + box_width, box_y + box_height),
        radius=15,
        fill='#1c2128',
        outline=colors['border'],
        width=2
    )

    # Entry / Exit / Loss columns
    col_width = box_width // 3

    # Entry
    entry_x = box_x + col_width // 2
    draw.text((entry_x - 30, box_y + 20), "Entry", fill=colors['text_secondary'], font=font_label)
    entry_val = f"${entry_price:.2f}"
    entry_w, _ = get_text_dimensions(draw, entry_val, font_value)
    draw.text((entry_x - entry_w // 2, box_y + 55), entry_val, fill=colors['text_primary'], font=font_value)

    # Exit
    exit_x = box_x + col_width + col_width // 2
    draw.text((exit_x - 25, box_y + 20), "Exit", fill=colors['text_secondary'], font=font_label)
    exit_val = f"${exit_price:.2f}"
    exit_w, _ = get_text_dimensions(draw, exit_val, font_value)
    draw.text((exit_x - exit_w // 2, box_y + 55), exit_val, fill=colors['text_primary'], font=font_value)

    # Loss
    loss_x = box_x + 2 * col_width + col_width // 2
    draw.text((loss_x - 25, box_y + 20), "Loss", fill=colors['text_secondary'], font=font_label)
    loss_val = f"-{loss_pct:.1f}%"
    loss_w, _ = get_text_dimensions(draw, loss_val, font_pct)
    draw.text((loss_x - loss_w // 2, box_y + 50), loss_val, fill=colors['red'], font=font_pct)

    # =========================================================================
    # DISCIPLINE QUOTE
    # =========================================================================

    quote = "Capital Preservation Protocol executed."
    quote_w, _ = get_text_dimensions(draw, quote, font_quote)
    draw.text(
        (center_x - quote_w // 2, 420),
        quote,
        fill=colors['text_secondary'],
        font=font_quote
    )

    subquote = "No ego, just execution."
    subquote_w, _ = get_text_dimensions(draw, subquote, font_quote)
    draw.text(
        (center_x - subquote_w // 2, 455),
        subquote,
        fill=colors['text_muted'],
        font=font_quote
    )

    # =========================================================================
    # LESSON (if provided)
    # =========================================================================

    if lesson:
        lesson_text = f"Lesson: {lesson}"
        if len(lesson_text) > 80:
            lesson_text = lesson_text[:77] + "..."
        lesson_w, _ = get_text_dimensions(draw, lesson_text, font_lesson)
        draw.text(
            (center_x - lesson_w // 2, 510),
            lesson_text,
            fill=colors['gold'],
            font=font_lesson
        )

    # =========================================================================
    # FOOTER
    # =========================================================================

    footer = "Sterling Signals • sterlingsignals.substack.com"
    footer_w, _ = get_text_dimensions(draw, footer, font_footer)
    draw.text(
        (center_x - footer_w // 2, IMAGE_HEIGHT - 45),
        footer,
        fill=colors['text_muted'],
        font=font_footer
    )

    # Decorative line
    line_width = 400
    draw.line(
        [(center_x - line_width // 2, IMAGE_HEIGHT - 60),
         (center_x + line_width // 2, IMAGE_HEIGHT - 60)],
        fill=colors['border'],
        width=1
    )

    # Save
    img.save(output_path, 'PNG', quality=95, optimize=True)
    print(f"  Post-mortem card saved: {output_path}")

    update_chart_manifest('post_mortem', output_path, {
        'ticker': ticker,
        'entry': entry_price,
        'exit': exit_price,
        'loss_pct': loss_pct
    })

    return output_path


# =============================================================================
# WIN CARD
# =============================================================================

def generate_win_card(
    ticker: str,
    entry_price: float,
    exit_price: float,
    gain_pct: float,
    days_held: int = 0,
    theme: str = "",
    output_path: Optional[Path] = None
) -> Path:
    """
    Generate Win Card for profitable exit.

    Args:
        ticker: Stock symbol
        entry_price: Entry price
        exit_price: Exit price
        gain_pct: Gain percentage
        days_held: Days position was held
        theme: Investment theme (optional)
        output_path: Output file path

    Returns:
        Path to generated image
    """
    if not PIL_AVAILABLE:
        raise RuntimeError("PIL/Pillow required. Install with: pip install Pillow")

    if output_path is None:
        output_path = CHARTS_DIR / f"win_card_{ticker}_{datetime.now():%Y%m%d}.png"

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    colors = THEMES['dark']

    # Create background
    img = create_gradient_background(
        IMAGE_WIDTH, IMAGE_HEIGHT,
        colors['background'],
        colors['background_gradient']
    )
    draw = ImageDraw.Draw(img)

    # Fonts
    font_icon = get_font(80, bold=True)
    font_ticker = get_font(72, bold=True)
    font_label = get_font(24)
    font_value = get_font(36, bold=True)
    font_pct = get_font(64, bold=True)
    font_days = get_font(22)
    font_footer = get_font(16)
    font_quote = get_font(20)

    center_x = IMAGE_WIDTH // 2

    # =========================================================================
    # HEADER - Checkmark icon
    # =========================================================================

    icon = "+"
    icon_w, icon_h = get_text_dimensions(draw, icon, font_icon)
    draw.text(
        (center_x - icon_w // 2, 30),
        icon,
        fill=colors['green'],
        font=font_icon
    )

    # Ticker
    ticker_text = f"${ticker}"
    ticker_w, _ = get_text_dimensions(draw, ticker_text, font_ticker)
    draw.text(
        (center_x - ticker_w // 2, 110),
        ticker_text,
        fill=colors['text_primary'],
        font=font_ticker
    )

    # "Winner!" label
    label = "PROFITABLE EXIT"
    label_w, _ = get_text_dimensions(draw, label, font_label)
    draw.text(
        (center_x - label_w // 2, 185),
        label,
        fill=colors['green'],
        font=font_label
    )

    # =========================================================================
    # LARGE GAIN PERCENTAGE
    # =========================================================================

    gain_text = f"+{gain_pct:.1f}%"
    gain_w, gain_h = get_text_dimensions(draw, gain_text, font_pct)
    draw.text(
        (center_x - gain_w // 2, 230),
        gain_text,
        fill=colors['green'],
        font=font_pct
    )

    # =========================================================================
    # PRICE INFO BOX
    # =========================================================================

    box_y = 320
    box_height = 100
    box_width = 500
    box_x = center_x - box_width // 2

    draw_rounded_rectangle(
        draw,
        (box_x, box_y, box_x + box_width, box_y + box_height),
        radius=15,
        fill='#1c2128',
        outline=colors['border'],
        width=2
    )

    # Entry / Exit columns
    col_width = box_width // 2

    # Entry
    entry_x = box_x + col_width // 2
    draw.text((entry_x - 30, box_y + 15), "Entry", fill=colors['text_secondary'], font=font_label)
    entry_val = f"${entry_price:.2f}"
    entry_w, _ = get_text_dimensions(draw, entry_val, font_value)
    draw.text((entry_x - entry_w // 2, box_y + 50), entry_val, fill=colors['text_primary'], font=font_value)

    # Exit
    exit_x = box_x + col_width + col_width // 2
    draw.text((exit_x - 25, box_y + 15), "Exit", fill=colors['text_secondary'], font=font_label)
    exit_val = f"${exit_price:.2f}"
    exit_w, _ = get_text_dimensions(draw, exit_val, font_value)
    draw.text((exit_x - exit_w // 2, box_y + 50), exit_val, fill=colors['green'], font=font_value)

    # =========================================================================
    # DAYS HELD
    # =========================================================================

    if days_held > 0:
        days_text = f"Position held: {days_held} days"
        days_w, _ = get_text_dimensions(draw, days_text, font_days)
        draw.text(
            (center_x - days_w // 2, 440),
            days_text,
            fill=colors['text_secondary'],
            font=font_days
        )

    # =========================================================================
    # QUOTE
    # =========================================================================

    quote = "Systematic process. Disciplined execution."
    quote_w, _ = get_text_dimensions(draw, quote, font_quote)
    draw.text(
        (center_x - quote_w // 2, 490),
        quote,
        fill=colors['text_muted'],
        font=font_quote
    )

    # =========================================================================
    # FOOTER
    # =========================================================================

    footer = "Sterling Signals • sterlingsignals.substack.com"
    footer_w, _ = get_text_dimensions(draw, footer, font_footer)
    draw.text(
        (center_x - footer_w // 2, IMAGE_HEIGHT - 45),
        footer,
        fill=colors['text_muted'],
        font=font_footer
    )

    # Decorative line
    line_width = 400
    draw.line(
        [(center_x - line_width // 2, IMAGE_HEIGHT - 60),
         (center_x + line_width // 2, IMAGE_HEIGHT - 60)],
        fill=colors['border'],
        width=1
    )

    # Save
    img.save(output_path, 'PNG', quality=95, optimize=True)
    print(f"  Win card saved: {output_path}")

    update_chart_manifest('win_card', output_path, {
        'ticker': ticker,
        'entry': entry_price,
        'exit': exit_price,
        'gain_pct': gain_pct,
        'days_held': days_held
    })

    return output_path


# =============================================================================
# ALPHA CARD
# =============================================================================

def generate_alpha_card(
    portfolio_return: float,
    spy_return: float,
    period: str = "YTD",
    output_path: Optional[Path] = None
) -> Path:
    """
    Generate Alpha Card showing portfolio vs SPY performance.

    Args:
        portfolio_return: Portfolio return percentage
        spy_return: SPY return percentage
        period: Time period (e.g., "YTD", "MTD", "QTD")
        output_path: Output file path

    Returns:
        Path to generated image
    """
    if not PIL_AVAILABLE:
        raise RuntimeError("PIL/Pillow required. Install with: pip install Pillow")

    if output_path is None:
        output_path = CHARTS_DIR / f"alpha_card_{period.lower()}_{datetime.now():%Y%m%d}.png"

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    colors = THEMES['dark']
    alpha = portfolio_return - spy_return
    is_outperforming = alpha > 0

    # Create background
    img = create_gradient_background(
        IMAGE_WIDTH, IMAGE_HEIGHT,
        colors['background'],
        colors['background_gradient']
    )
    draw = ImageDraw.Draw(img)

    # Fonts
    font_title = get_font(42, bold=True)
    font_period = get_font(24)
    font_label = get_font(28)
    font_value = get_font(56, bold=True)
    font_alpha = get_font(72, bold=True)
    font_alpha_label = get_font(28, bold=True)
    font_footer = get_font(16)
    font_bar_label = get_font(18)

    center_x = IMAGE_WIDTH // 2

    # =========================================================================
    # HEADER
    # =========================================================================

    title = "Performance vs Benchmark"
    title_w, _ = get_text_dimensions(draw, title, font_title)
    draw.text(
        (center_x - title_w // 2, 35),
        title,
        fill=colors['text_primary'],
        font=font_title
    )

    period_text = f"{period} Performance"
    period_w, _ = get_text_dimensions(draw, period_text, font_period)
    draw.text(
        (center_x - period_w // 2, 85),
        period_text,
        fill=colors['text_secondary'],
        font=font_period
    )

    # =========================================================================
    # COMPARISON BARS
    # =========================================================================

    bar_area_top = 150
    bar_height = 60
    bar_gap = 30
    bar_max_width = 500
    label_width = 150
    value_width = 150
    bar_x_start = 200

    # Normalize bar widths
    max_return = max(abs(portfolio_return), abs(spy_return), 1)

    # Portfolio bar
    portfolio_bar_width = int((abs(portfolio_return) / max_return) * bar_max_width) if max_return > 0 else 0
    portfolio_bar_width = max(portfolio_bar_width, 20)  # Minimum width

    # Portfolio label
    draw.text(
        (bar_x_start - 140, bar_area_top + 15),
        "Portfolio",
        fill=colors['text_primary'],
        font=font_label
    )

    # Portfolio bar
    bar_color = colors['green'] if portfolio_return >= 0 else colors['red']
    draw_rounded_rectangle(
        draw,
        (bar_x_start, bar_area_top, bar_x_start + portfolio_bar_width, bar_area_top + bar_height),
        radius=8,
        fill=bar_color
    )

    # Portfolio value
    portfolio_text = f"{portfolio_return:+.1f}%"
    draw.text(
        (bar_x_start + portfolio_bar_width + 20, bar_area_top + 10),
        portfolio_text,
        fill=bar_color,
        font=font_value
    )

    # SPY bar
    spy_bar_top = bar_area_top + bar_height + bar_gap
    spy_bar_width = int((abs(spy_return) / max_return) * bar_max_width) if max_return > 0 else 0
    spy_bar_width = max(spy_bar_width, 20)

    # SPY label
    draw.text(
        (bar_x_start - 140, spy_bar_top + 15),
        "SPY",
        fill=colors['text_primary'],
        font=font_label
    )

    # SPY bar (always blue for benchmark)
    draw_rounded_rectangle(
        draw,
        (bar_x_start, spy_bar_top, bar_x_start + spy_bar_width, spy_bar_top + bar_height),
        radius=8,
        fill=colors['blue']
    )

    # SPY value
    spy_text = f"{spy_return:+.1f}%"
    draw.text(
        (bar_x_start + spy_bar_width + 20, spy_bar_top + 10),
        spy_text,
        fill=colors['blue'],
        font=font_value
    )

    # =========================================================================
    # ALPHA SECTION
    # =========================================================================

    alpha_section_top = spy_bar_top + bar_height + 50

    # Alpha box
    alpha_box_width = 400
    alpha_box_height = 140
    alpha_box_x = center_x - alpha_box_width // 2

    box_border_color = colors['green'] if is_outperforming else colors['red']
    draw_rounded_rectangle(
        draw,
        (alpha_box_x, alpha_section_top, alpha_box_x + alpha_box_width, alpha_section_top + alpha_box_height),
        radius=15,
        fill='#1c2128',
        outline=box_border_color,
        width=3
    )

    # Alpha label
    alpha_label = "Alpha"
    alpha_label_w, _ = get_text_dimensions(draw, alpha_label, font_alpha_label)
    draw.text(
        (center_x - alpha_label_w // 2, alpha_section_top + 20),
        alpha_label,
        fill=colors['text_secondary'],
        font=font_alpha_label
    )

    # Alpha value
    alpha_text = f"{alpha:+.1f}%"
    alpha_w, _ = get_text_dimensions(draw, alpha_text, font_alpha)
    alpha_color = colors['green'] if is_outperforming else colors['red']
    draw.text(
        (center_x - alpha_w // 2, alpha_section_top + 55),
        alpha_text,
        fill=alpha_color,
        font=font_alpha
    )

    # =========================================================================
    # BOTTOM MESSAGE
    # =========================================================================

    if is_outperforming:
        message = "Outperforming the market through systematic selection."
    else:
        message = "Staying disciplined. Process over short-term results."

    message_font = get_font(18)
    message_w, _ = get_text_dimensions(draw, message, message_font)
    draw.text(
        (center_x - message_w // 2, alpha_section_top + alpha_box_height + 25),
        message,
        fill=colors['text_muted'],
        font=message_font
    )

    # =========================================================================
    # FOOTER
    # =========================================================================

    footer = "Sterling Signals • sterlingsignals.substack.com"
    footer_w, _ = get_text_dimensions(draw, footer, font_footer)
    draw.text(
        (center_x - footer_w // 2, IMAGE_HEIGHT - 45),
        footer,
        fill=colors['text_muted'],
        font=font_footer
    )

    # Decorative line
    line_width = 400
    draw.line(
        [(center_x - line_width // 2, IMAGE_HEIGHT - 60),
         (center_x + line_width // 2, IMAGE_HEIGHT - 60)],
        fill=colors['border'],
        width=1
    )

    # Save
    img.save(output_path, 'PNG', quality=95, optimize=True)
    print(f"  Alpha card saved: {output_path}")

    update_chart_manifest('alpha_card', output_path, {
        'portfolio_return': portfolio_return,
        'spy_return': spy_return,
        'alpha': alpha,
        'period': period
    })

    return output_path


# =============================================================================
# MANIFEST UPDATE
# =============================================================================

def update_chart_manifest(card_type: str, output_path: Path, data: Dict):
    """Update the chart manifest with the new card."""
    try:
        if MANIFEST_FILE.exists():
            with open(MANIFEST_FILE) as f:
                manifest = json.load(f)
        else:
            manifest = {'charts': {}}

        manifest['charts'][card_type] = {
            'path': str(output_path),
            'generated': datetime.now().isoformat(),
            'data': data
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
        description="Generate visual cards for trades and portfolio performance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python card_generator.py post_mortem AAPL --entry 150.00 --exit 120.00 --loss 20
    python card_generator.py win NVDA --entry 400.00 --exit 600.00 --gain 50 --days 30
    python card_generator.py alpha --portfolio 15.5 --spy 8.2 --period YTD
    python card_generator.py --test
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Card type')

    # Post-mortem subcommand
    post_mortem = subparsers.add_parser('post_mortem', help='Generate post-mortem card for stopped position')
    post_mortem.add_argument('ticker', type=str, help='Stock ticker symbol')
    post_mortem.add_argument('--entry', type=float, required=True, help='Entry price')
    post_mortem.add_argument('--exit', type=float, required=True, help='Exit price')
    post_mortem.add_argument('--loss', type=float, required=True, help='Loss percentage (positive number)')
    post_mortem.add_argument('--theme', type=str, default='', help='Investment theme')
    post_mortem.add_argument('--lesson', type=str, default='', help='Lesson learned')
    post_mortem.add_argument('--output', '-o', type=str, help='Output path')

    # Win card subcommand
    win = subparsers.add_parser('win', help='Generate win card for profitable exit')
    win.add_argument('ticker', type=str, help='Stock ticker symbol')
    win.add_argument('--entry', type=float, required=True, help='Entry price')
    win.add_argument('--exit', type=float, required=True, help='Exit price')
    win.add_argument('--gain', type=float, required=True, help='Gain percentage')
    win.add_argument('--days', type=int, default=0, help='Days held')
    win.add_argument('--theme', type=str, default='', help='Investment theme')
    win.add_argument('--output', '-o', type=str, help='Output path')

    # Alpha card subcommand
    alpha = subparsers.add_parser('alpha', help='Generate alpha card showing portfolio vs SPY')
    alpha.add_argument('--portfolio', type=float, required=True, help='Portfolio return percentage')
    alpha.add_argument('--spy', type=float, required=True, help='SPY return percentage')
    alpha.add_argument('--period', type=str, default='YTD', help='Time period (e.g., YTD, MTD)')
    alpha.add_argument('--output', '-o', type=str, help='Output path')

    # Test mode
    parser.add_argument('--test', '-t', action='store_true', help='Generate all sample cards')

    args = parser.parse_args()

    if not PIL_AVAILABLE:
        print("ERROR: PIL/Pillow not installed.")
        print("Install with: pip install Pillow")
        return 1

    print("\n" + "=" * 60)
    print("  CARD GENERATOR")
    print("=" * 60 + "\n")

    if args.test:
        # Generate sample cards
        print("  Generating sample cards...\n")

        generate_post_mortem_card(
            ticker="SMCI",
            entry_price=45.00,
            exit_price=36.00,
            loss_pct=20.0,
            lesson="Extended moves can reverse quickly"
        )

        generate_win_card(
            ticker="NVDA",
            entry_price=450.00,
            exit_price=720.00,
            gain_pct=60.0,
            days_held=45
        )

        generate_alpha_card(
            portfolio_return=18.5,
            spy_return=8.2,
            period="YTD"
        )

        print("\n  All sample cards generated!")

    elif args.command == 'post_mortem':
        output = Path(args.output) if args.output else None
        generate_post_mortem_card(
            ticker=args.ticker.upper(),
            entry_price=args.entry,
            exit_price=args.exit,
            loss_pct=args.loss,
            theme=args.theme,
            lesson=args.lesson,
            output_path=output
        )

    elif args.command == 'win':
        output = Path(args.output) if args.output else None
        generate_win_card(
            ticker=args.ticker.upper(),
            entry_price=args.entry,
            exit_price=args.exit,
            gain_pct=args.gain,
            days_held=args.days,
            theme=args.theme,
            output_path=output
        )

    elif args.command == 'alpha':
        output = Path(args.output) if args.output else None
        generate_alpha_card(
            portfolio_return=args.portfolio,
            spy_return=args.spy,
            period=args.period,
            output_path=output
        )

    else:
        parser.print_help()
        return 1

    print("\n" + "=" * 60 + "\n")
    return 0


if __name__ == "__main__":
    exit(main())
