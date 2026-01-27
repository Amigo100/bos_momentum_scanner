#!/usr/bin/env python3
"""
GROK PROMPTS GENERATOR - 21 Weekly X/Twitter Prompts
====================================================

Generates 21 contextual Grok prompts (3 per day) based on your scanner outputs.
These prompts are designed to build your Sterling Signals audience on X/Twitter.

The prompts cover:
  - Hot themes (PRIME/INVESTABLE) and why
  - Sub-par themes (SELECTIVE/AVOID) and why
  - Stocks flagged as buys (PASS signals) and catalysts
  - Stocks the gatekeeper passed on (CAUTION/FAIL) and reasoning
  - Open positions and updates
  - Sell signals and risk management

Usage:
    python grok_prompts_generator.py                    # Uses latest_newsletter_briefing.md
    python grok_prompts_generator.py --briefing PATH    # Use specific briefing file
    python grok_prompts_generator.py --output prompts/  # Custom output directory

Output:
    - grok_prompts_YYYYMMDD.md - All 21 prompts in one file
    - Individual day files for easy access
"""

import os
import sys
import json
import csv
import re
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).resolve().parent
TRADES_DIR = BASE_DIR / "trades"
OUTPUT_DIR = TRADES_DIR / "grok_prompts"  # Consistent with scanner.py location
GROK_OUTPUT_DIR = OUTPUT_DIR  # Alias for import compatibility

# Sterling Signals branding
SUBSTACK_URL = "https://sterlingsignals.substack.com"
ACCOUNT_HANDLE = "@SterlingSignals"

# Days of the week for scheduling
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# Import marketing vocabulary for validation
try:
    from marketing_vocabulary import validate_content, BANNED_TERMS
    MARKETING_VOCABULARY_AVAILABLE = True
except ImportError:
    MARKETING_VOCABULARY_AVAILABLE = False
    BANNED_TERMS = []


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class PortfolioData:
    """Container for all portfolio data extracted from scanner outputs."""
    # Themes
    prime_themes: List[Dict] = field(default_factory=list)      # PRIME themes
    investable_themes: List[Dict] = field(default_factory=list) # INVESTABLE themes
    selective_themes: List[Dict] = field(default_factory=list)  # SELECTIVE themes
    avoid_themes: List[Dict] = field(default_factory=list)      # AVOID themes
    
    # Signals
    pass_signals: List[Dict] = field(default_factory=list)      # PASS from gatekeeper
    caution_signals: List[Dict] = field(default_factory=list)   # CAUTION from gatekeeper
    fail_signals: List[Dict] = field(default_factory=list)      # FAIL from gatekeeper
    technical_only: List[Dict] = field(default_factory=list)    # Passed technical, pending DD
    
    # Portfolio
    open_positions: List[Dict] = field(default_factory=list)
    sell_signals: List[Dict] = field(default_factory=list)
    
    # Stats
    scan_stats: Dict = field(default_factory=dict)
    scan_date: str = ""


@dataclass
class GrokPrompt:
    """A single Grok prompt with metadata."""
    day: str                    # Monday, Tuesday, etc.
    slot: int                   # 1, 2, or 3 (morning, midday, evening)
    category: str               # theme_hot, theme_cold, buy_signal, etc.
    title: str                  # Short descriptive title
    prompt: str                 # The actual prompt text
    visual_suggestion: str      # Suggested visual to accompany post
    ticker: str = ""            # If prompt is about a specific ticker
    theme: str = ""             # If prompt is about a specific theme


# ═══════════════════════════════════════════════════════════════════════════════
# DATA EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_live_prices_for_positions(positions: List[Dict]) -> List[Dict]:
    """Fetch live prices via yfinance and calculate accurate P&L.

    Args:
        positions: List of position dicts with 'ticker' and 'entry_price' keys

    Returns:
        Updated positions list with current_price and pnl fields
    """
    if not positions:
        return positions

    try:
        import yfinance as yf
        tickers = [p.get('ticker', p.get('symbol', '')) for p in positions if p.get('ticker') or p.get('symbol')]
        tickers = [t for t in tickers if t]  # Remove empty strings

        if not tickers:
            return positions

        print(f"  📈 Fetching live prices for {len(tickers)} positions...")
        data = yf.download(tickers, period="1d", progress=False)

        if data.empty:
            print("  ⚠ No price data returned")
            return positions

        for pos in positions:
            ticker = pos.get('ticker', pos.get('symbol', ''))
            entry_price = float(pos.get('entry_price', 0) or 0)

            if not ticker or entry_price <= 0:
                continue

            try:
                if len(tickers) == 1:
                    current_price = float(data['Close'].iloc[-1])
                else:
                    current_price = float(data['Close'][ticker].iloc[-1])

                pos['current_price'] = current_price

                pnl_pct = ((current_price / entry_price) - 1) * 100
                pos['pnl'] = f"{pnl_pct:+.1f}%"

                # Update highest close if current is higher
                highest = float(pos.get('highest_close', entry_price) or entry_price)
                if current_price > highest:
                    pos['highest_close'] = current_price

            except (KeyError, IndexError) as e:
                # Keep original values if lookup fails
                pass

    except ImportError:
        print("  ⚠ yfinance not available for live prices")
    except Exception as e:
        print(f"  ⚠ Error fetching live prices: {e}")

    return positions


def parse_briefing_markdown(briefing_path: Path) -> PortfolioData:
    """Parse the newsletter briefing markdown to extract portfolio data."""

    data = PortfolioData()

    if not briefing_path.exists():
        print(f"  ⚠ Briefing file not found: {briefing_path}")
        return data

    with open(briefing_path, 'r') as f:
        content = f.read()
    
    # Extract scan date
    date_match = re.search(r'\*\*Scan Date:\*\* (.+)', content)
    if date_match:
        data.scan_date = date_match.group(1)
    
    # Extract themes - try multiple formats

    # Format 1: "## 🔥 Hot Themes This Week" with "### PRIME Themes" subsections
    hot_themes_section = re.search(r'## 🔥 Hot Themes This Week(.*?)(?=\n---|\n## )', content, re.DOTALL)
    if hot_themes_section:
        themes_text = hot_themes_section.group(1)

        # Parse PRIME Themes section - format: **Theme Name** (TYPE)
        prime_section = re.search(r'### PRIME Themes.*?\n(.*?)(?=### INVESTABLE|### SELECTIVE|### AVOID|\Z)', themes_text, re.DOTALL)
        if prime_section:
            # Match **Theme Name** at start of line
            for match in re.finditer(r'\*\*([^*]+)\*\*\s*\(', prime_section.group(1)):
                theme_name = match.group(1).strip()
                if theme_name:
                    data.prime_themes.append({'name': theme_name, 'classification': 'PRIME'})

        # Parse INVESTABLE Themes section - format: - **Theme Name** (TYPE) - Score
        investable_section = re.search(r'### INVESTABLE Themes.*?\n(.*?)(?=### SELECTIVE|### AVOID|\Z)', themes_text, re.DOTALL)
        if investable_section:
            for match in re.finditer(r'\*\*([^*]+)\*\*\s*\(', investable_section.group(1)):
                theme_name = match.group(1).strip()
                if theme_name:
                    data.investable_themes.append({'name': theme_name, 'classification': 'INVESTABLE'})

    # Format 2 (legacy): "## 🎯 Theme Rankings" with **PRIME**/**INVESTABLE** markers
    if not data.prime_themes:
        themes_section = re.search(r'## 🎯 Theme Rankings(.*?)(?=##|\Z)', content, re.DOTALL)
        if themes_section:
            themes_text = themes_section.group(1)

            # Parse PRIME themes
            prime_match = re.search(r'\*\*PRIME.*?\*\*(.+?)(?:\*\*INVESTABLE|\*\*SELECTIVE|\*\*AVOID|$)', themes_text, re.DOTALL)
            if prime_match:
                for line in prime_match.group(1).split('\n'):
                    if line.strip().startswith('-'):
                        theme_name = line.strip('- ').split('|')[0].strip()
                        if theme_name and not theme_name.startswith('*'):
                            data.prime_themes.append({'name': theme_name, 'classification': 'PRIME'})

            # Parse INVESTABLE themes
            inv_match = re.search(r'\*\*INVESTABLE.*?\*\*(.+?)(?:\*\*SELECTIVE|\*\*AVOID|$)', themes_text, re.DOTALL)
            if inv_match:
                for line in inv_match.group(1).split('\n'):
                    if line.strip().startswith('-'):
                        theme_name = line.strip('- ').split('|')[0].strip()
                        if theme_name and not theme_name.startswith('*'):
                            data.investable_themes.append({'name': theme_name, 'classification': 'INVESTABLE'})

            # Parse SELECTIVE themes
            sel_match = re.search(r'\*\*SELECTIVE.*?\*\*(.+?)(?:\*\*AVOID|$)', themes_text, re.DOTALL)
            if sel_match:
                for line in sel_match.group(1).split('\n'):
                    if line.strip().startswith('-'):
                        theme_name = line.strip('- ').split('|')[0].strip()
                        if theme_name and not theme_name.startswith('*'):
                            data.selective_themes.append({'name': theme_name, 'classification': 'SELECTIVE'})

            # Parse AVOID themes
            avoid_match = re.search(r'\*\*AVOID.*?\*\*(.+?)(?=\n##|\Z)', themes_text, re.DOTALL)
            if avoid_match:
                for line in avoid_match.group(1).split('\n'):
                    if line.strip().startswith('-'):
                        theme_name = line.strip('- ').split('|')[0].strip()
                        if theme_name and not theme_name.startswith('*'):
                            data.avoid_themes.append({'name': theme_name, 'classification': 'AVOID'})
    
    # Extract PASS signals (🟢) - handle both "Entry Signals" and "Ready for Entry" formats
    pass_section = re.search(r'### 🟢 PASS - (?:Entry Signals|Ready for Entry)(.*?)(?=### 🟡|### ⚠|## 📈|## 📋|\Z)', content, re.DOTALL)
    if pass_section:
        # Look for ticker blocks - use \n---\n or \n#### as delimiter
        ticker_blocks = re.findall(r'#### ([A-Z]{2,5})\n(.*?)(?=\n---\n|\n####|\Z)', pass_section.group(1), re.DOTALL)
        for ticker, block in ticker_blocks:
            # Skip "Due Diligence" sections
            if "Due Diligence" in ticker or "Due Diligence" in block[:50]:
                continue
            signal = {'ticker': ticker}

            # Extract price from table format: | **Price** | $31.90 |
            price_match = re.search(r'\*\*Price\*\*\s*\|\s*\$?([\d.]+)', block)
            if price_match:
                signal['price'] = float(price_match.group(1))

            # Extract theme from table format: | **Theme** | value |
            theme_match = re.search(r'\*\*Theme\*\*\s*\|\s*(.+?)\s*\|', block)
            if theme_match:
                signal['theme'] = theme_match.group(1).strip()

            # Extract catalyst from table format: | **Catalyst** | value |
            catalyst_match = re.search(r'\*\*Catalyst\*\*\s*\|\s*(.+?)\s*\|', block)
            if catalyst_match:
                signal['catalyst'] = catalyst_match.group(1).strip()

            # Extract analysis/reasoning
            analysis_match = re.search(r'\*\*Analysis:\*\*\s*>\s*(.+)', block)
            if analysis_match:
                signal['reasoning'] = analysis_match.group(1).strip()

            # Extract conviction from table: | **Conviction** | ★★★★☆ |
            conviction_match = re.search(r'\*\*Conviction\*\*\s*\|\s*([★☆]+)', block)
            if conviction_match:
                stars = conviction_match.group(1).count('★')
                signal['conviction'] = stars

            data.pass_signals.append(signal)
    
    # Extract CAUTION signals (🟡) - handle both "Watchlist" and "Wait or Size Down" formats
    caution_section = re.search(r'### 🟡 CAUTION - (?:Watchlist|Wait or Size Down)(.*?)(?=## 📈|## 📋|\Z)', content, re.DOTALL)
    if caution_section:
        # Look for ticker blocks - use \n---\n or \n#### as delimiter
        ticker_blocks = re.findall(r'#### ([A-Z]{2,5})\n(.*?)(?=\n---\n|\n####|\Z)', caution_section.group(1), re.DOTALL)
        for ticker, block in ticker_blocks:
            # Skip "Due Diligence" sections
            if "Due Diligence" in ticker or "Due Diligence" in block[:50]:
                continue
            signal = {'ticker': ticker}

            # Extract price from table format: | **Price** | $14.53 |
            price_match = re.search(r'\*\*Price\*\*\s*\|\s*\$?([\d.]+)', block)
            if price_match:
                signal['price'] = float(price_match.group(1))

            # Extract theme from table format: | **Theme** | value |
            theme_match = re.search(r'\*\*Theme\*\*\s*\|\s*(.+?)\s*\|', block)
            if theme_match:
                signal['theme'] = theme_match.group(1).strip()

            # Look for concerns/risks
            concerns = re.findall(r'^- (.+)$', block, re.MULTILINE)
            if concerns:
                signal['concerns'] = concerns
            
            analysis_match = re.search(r'\*\*Analysis:\*\*\s*>\s*(.+)', block)
            if analysis_match:
                signal['reasoning'] = analysis_match.group(1).strip()
            
            data.caution_signals.append(signal)
    
    # Extract sell signals
    sell_section = re.search(r'### ⚠️ Caution Signals \(Consider Tightening Stops\)(.*?)(?=###|##|\Z)', content, re.DOTALL)
    if sell_section:
        # Parse table rows
        rows = re.findall(r'\| (\w+) \| \$([\d.]+) \| (.+?) \| \$([\d.]+) \| \$([\d.]+) \| ([+-]?[\d.]+%?) \|', sell_section.group(1))
        for row in rows:
            data.sell_signals.append({
                'ticker': row[0],
                'price': float(row[1]),
                'reason': row[2].strip(),
                'entry_price': float(row[3]),
                'highest_close': float(row[4]),
                'pnl': row[5]
            })
    
    # Extract open positions
    positions_section = re.search(r'### 📊 Open Positions(.*?)(?=###|##|\Z)', content, re.DOTALL)
    if positions_section:
        rows = re.findall(r'\| (\w+) \| ([\d-]+) \| \$([\d.]+) \| (.+?) \| (\w+) \| ([+-]?[\d.]+%?) \|', positions_section.group(1))
        for row in rows:
            entry_date = row[1]
            # Calculate days held
            days_held = 0
            if entry_date:
                try:
                    entry_dt = datetime.strptime(entry_date, "%Y-%m-%d")
                    days_held = (datetime.now() - entry_dt).days
                except ValueError:
                    pass
            data.open_positions.append({
                'ticker': row[0],
                'entry_date': entry_date,
                'entry_price': float(row[2]),
                'theme': row[3].strip(),
                'tier': row[4],
                'pnl': row[5],
                'days_held': days_held
            })
    
    # Extract scan stats
    stats_match = re.search(r'Tickers scanned: (\d+)', content)
    if stats_match:
        data.scan_stats['tickers_scanned'] = int(stats_match.group(1))
    
    bos_match = re.search(r'Weekly BoS Up: (\d+)', content)
    if bos_match:
        data.scan_stats['bos_bullish'] = int(bos_match.group(1))
    
    tech_match = re.search(r'Technical signals: (\d+)', content)
    if tech_match:
        data.scan_stats['technical_signals'] = int(tech_match.group(1))
    
    theme_match = re.search(r'Theme confirmed: (\d+)', content)
    if theme_match:
        data.scan_stats['theme_confirmed'] = int(theme_match.group(1))
    
    return data


def load_open_positions_csv(trades_dir: Path, fetch_live_prices: bool = True) -> List[Dict]:
    """Load open positions from CSV file with optional live price fetching.

    Checks portfolio.csv first (unified format), falls back to open_positions.csv (legacy).

    Args:
        trades_dir: Directory containing portfolio files
        fetch_live_prices: If True, fetch current prices via yfinance for accurate P&L
    """
    positions = []

    # Try unified portfolio.csv first
    portfolio_file = trades_dir / "portfolio.csv"
    if portfolio_file.exists():
        try:
            with open(portfolio_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Only include OPEN positions
                    if row.get('status', 'OPEN').upper() == 'OPEN':
                        entry_price = float(row.get('entry_price', 0) or 0)
                        highest_close = float(row.get('highest_close', entry_price) or entry_price)
                        entry_date = row.get('entry_date', '')

                        # Calculate days held
                        days_held = 0
                        if entry_date:
                            try:
                                entry_dt = datetime.strptime(entry_date, "%Y-%m-%d")
                                days_held = (datetime.now() - entry_dt).days
                            except ValueError:
                                pass

                        # Map portfolio.csv fields to expected format
                        positions.append({
                            'symbol': row.get('ticker', ''),
                            'ticker': row.get('ticker', ''),
                            'entry_date': entry_date,
                            'entry_price': entry_price,
                            'highest_close': highest_close,
                            'tier': row.get('tier', ''),
                            'theme': row.get('theme', ''),
                            'decision': row.get('signal_type', 'PASS'),
                            'conviction': row.get('conviction', '0'),
                            'current_price': 0,  # Will be updated below
                            'pnl': '+0.0%',  # Will be calculated below
                            'days_held': days_held,
                            'drawdown_pct': row.get('drawdown_pct', '0'),
                            'notes': row.get('notes', '')
                        })

            # Fetch live prices if requested
            if positions and fetch_live_prices:
                try:
                    import yfinance as yf
                    tickers = [p['ticker'] for p in positions if p['ticker']]
                    if tickers:
                        print(f"  📈 Fetching live prices for {len(tickers)} positions...")
                        data = yf.download(tickers, period="1d", progress=False)

                        for pos in positions:
                            ticker = pos['ticker']
                            entry_price = pos['entry_price']
                            try:
                                if len(tickers) == 1:
                                    current_price = float(data['Close'].iloc[-1])
                                else:
                                    current_price = float(data['Close'][ticker].iloc[-1])

                                pos['current_price'] = current_price

                                if entry_price > 0:
                                    pnl_pct = ((current_price / entry_price) - 1) * 100
                                    pos['pnl'] = f"{pnl_pct:+.1f}%"

                                    # Update highest close if current is higher
                                    if current_price > pos['highest_close']:
                                        pos['highest_close'] = current_price
                            except (KeyError, IndexError):
                                pos['current_price'] = entry_price
                                pos['pnl'] = '+0.0%'
                except ImportError:
                    print("  ⚠ yfinance not available for live prices")
                except Exception as e:
                    print(f"  ⚠ Error fetching live prices: {e}")

            if positions:
                return positions
        except Exception as e:
            print(f"  ⚠ Error loading portfolio.csv: {e}")
    
    # Fall back to legacy open_positions.csv
    positions_file = trades_dir / "open_positions.csv"
    if positions_file.exists():
        try:
            with open(positions_file, 'r') as f:
                reader = csv.DictReader(f)
                positions = list(reader)
        except Exception as e:
            print(f"  ⚠ Error loading open_positions.csv: {e}")
    
    return positions


def load_themes_cache(base_dir: Path) -> List[Dict]:
    """Load themes from cache file."""
    themes_file = base_dir / "themes_cache.json"
    themes = []
    
    if themes_file.exists():
        try:
            with open(themes_file, 'r') as f:
                data = json.load(f)
                themes = data.get('themes', [])
        except Exception as e:
            print(f"  ⚠ Error loading themes cache: {e}")
    
    return themes


# ═══════════════════════════════════════════════════════════════════════════════
# PROMPT TEMPLATES
# ═══════════════════════════════════════════════════════════════════════════════

def create_hot_theme_prompt(theme: Dict, data: PortfolioData) -> GrokPrompt:
    """Create a prompt about a hot (PRIME/INVESTABLE) theme."""
    theme_name = theme.get('name', 'Unknown Theme')
    classification = theme.get('classification', 'INVESTABLE')
    
    prompt = f"""SCANNER OUTPUT:
{classification}: {theme_name}

---

You are drafting an X post for {ACCOUNT_HANDLE}, a momentum stock newsletter.

Using the theme above:
1. Search for the LATEST news/developments in {theme_name} (last 7 days)
2. Find a specific catalyst, data point, or news event that's driving momentum
3. Draft a visually engaging X post (under 280 characters) that:
   - Opens with a compelling hook about why this theme matters NOW
   - Uses the specific recent data point or catalyst you found
   - Shows this is a {classification} theme in my systematic scanner
   - Teases that I have specific stock picks in this theme
   - Ends with CTA: {SUBSTACK_URL}

Make it accessible to readers who don't follow this sector closely.

IMPORTANT: Search for CURRENT news - don't rely on old knowledge. The post should feel timely and informed.
"""
    
    return GrokPrompt(
        day="",
        slot=0,
        category="theme_hot",
        title=f"Hot Theme: {theme_name}",
        prompt=prompt,
        visual_suggestion=f"Theme infographic or sector ETF momentum chart for {theme_name}",
        theme=theme_name
    )


def create_cold_theme_prompt(theme: Dict, data: PortfolioData) -> GrokPrompt:
    """Create a prompt about a cold (SELECTIVE/AVOID) theme."""
    theme_name = theme.get('name', 'Unknown Theme')
    classification = theme.get('classification', 'SELECTIVE')
    
    prompt = f"""SCANNER OUTPUT:
{classification}: {theme_name}

---

You are drafting an X post for {ACCOUNT_HANDLE}.

Using the theme above:
1. Search for recent news explaining headwinds/challenges in {theme_name}
2. Find a specific reason why momentum has faded or risks have increased
3. Draft a visually engaging X post (under 280 characters) that:
   - States what theme I'm avoiding or being selective on
   - Gives ONE specific, current reason from your search
   - Shows disciplined capital allocation ("I could chase, but...")
   - Pivots to what themes I AM focused on instead
   - Ends with CTA: {SUBSTACK_URL}

Be contrarian but not dismissive. Show that avoiding bad trades IS a trading edge.
"""
    
    return GrokPrompt(
        day="",
        slot=0,
        category="theme_cold",
        title=f"Avoiding: {theme_name}",
        prompt=prompt,
        visual_suggestion=f"Sector underperformance chart or '{classification} ⚠️' graphic",
        theme=theme_name
    )


def create_buy_signal_prompt(signal: Dict, data: PortfolioData) -> GrokPrompt:
    """Create a prompt about a PASS buy signal."""
    ticker = signal.get('ticker', 'UNKNOWN')
    theme = signal.get('theme', 'Unknown')
    catalyst = signal.get('catalyst', '')
    price = signal.get('price', 0)
    
    prompt = f"""SCANNER OUTPUT:
PASS: {ticker} | Theme: {theme} | Price: ${price:.2f}
Catalyst: {catalyst if catalyst else 'TBD'}

---

You are drafting an X post for {ACCOUNT_HANDLE}, a momentum stock newsletter.

Using the scanner output above:
1. Search for the LATEST news on ${ticker} (last 7 days)
2. Find upcoming catalysts (earnings, product launches, contracts, etc.)
3. Draft a visually engaging X post (under 280 characters) that:
   - Opens with an attention-grabbing hook that stops the scroll
   - Highlights this PASSED a proprietary 3-gate screening system (technical, thematic, fundamental)
   - Teases the opportunity WITHOUT revealing my entry level
   - Creates urgency ("This just triggered..." or "Fresh signal...")
   - Ends with CTA: {SUBSTACK_URL}

Make it punchy and impossible to scroll past. This is a RARE signal - we scan 1800+ stocks weekly.
"""
    
    return GrokPrompt(
        day="",
        slot=0,
        category="buy_signal",
        title=f"BUY Signal: {ticker}",
        prompt=prompt,
        visual_suggestion=f"Weekly chart with breakout + '🎯 SCANNER SIGNAL' overlay for {ticker}",
        ticker=ticker,
        theme=theme
    )


def create_watchlist_prompt(signal: Dict, data: PortfolioData) -> GrokPrompt:
    """Create a prompt about a CAUTION watchlist stock."""
    ticker = signal.get('ticker', 'UNKNOWN')
    theme = signal.get('theme', 'Unknown')
    price = signal.get('price', 0)
    concerns = signal.get('concerns', [])
    reasoning = signal.get('reasoning', '')
    
    concern_text = concerns[0] if concerns else reasoning[:50] if reasoning else "timing concerns"
    
    prompt = f"""SCANNER OUTPUT:
CAUTION: {ticker} | Theme: {theme} | Price: ${price:.2f}
Reason: {concern_text}

---

You are drafting an X post for {ACCOUNT_HANDLE}.

Using the scanner output above:
1. Search for recent news on ${ticker}
2. Draft a visually engaging X post (under 280 characters) that:
   - Shows this stock caught my attention (it's on radar)
   - Explains specifically WHY it's not actionable YET (use the reason above)
   - Shows disciplined patience, NOT indecision ("I could FOMO, but...")
   - References my proprietary 3-gate screening system
   - Ends with CTA to see what DID pass: {SUBSTACK_URL}

Educational and compelling. Show that waiting IS a strategy.
"""
    
    return GrokPrompt(
        day="",
        slot=0,
        category="watchlist",
        title=f"Watching: {ticker}",
        prompt=prompt,
        visual_suggestion=f"Chart with key level marked + 'WATCHING 👀' overlay for {ticker}",
        ticker=ticker,
        theme=theme
    )


def create_position_update_prompt(position: Dict, data: PortfolioData) -> GrokPrompt:
    """Create a prompt about an open position update.

    Note: P&L is calculated at generation time but the prompt instructs Grok
    to look up CURRENT price, so the tweet reflects real-time data.
    """
    ticker = position.get('ticker', position.get('symbol', 'UNKNOWN'))
    entry_price = float(position.get('entry_price', 0))
    entry_date = position.get('entry_date', 'N/A')
    theme = position.get('theme', 'Unknown')
    tier = position.get('tier', 'N/A')
    days_held = position.get('days_held', 0)

    # Include snapshot P&L for context, but prompt asks for LIVE data
    pnl = position.get('pnl', '+0%')

    # CRIT-12.4: Entry prices are PRIVATE - do not expose in public prompts
    prompt = f"""POSITION CONTEXT (may be outdated - look up current price):
Ticker: ${ticker}
Theme: {theme} | Tier: {tier}
Held: ~{days_held} days (entry price private)
Snapshot P&L: {pnl} (verify with current price)

---

You are drafting an X post for {ACCOUNT_HANDLE}.

IMPORTANT: The P&L above may be stale. Before drafting:
1. Look up the CURRENT price and recent performance of ${ticker}
2. Use the snapshot P&L as a reference, but verify current performance

Then draft a visually engaging X post (under 280 characters) that:
   - States the position with CURRENT P&L (not the snapshot above)
   - Notes current status based on price action (uptrend, consolidating, pullback)
   - Search for any recent news on ${ticker} (last 7 days)
   - Shows active, systematic portfolio management
   - Builds credibility through real-time transparency
   - Ends with CTA for full portfolio: {SUBSTACK_URL}

Example format: "${ticker} update: +XX.X% since entry ({days_held} days held). [Recent development]. Full portfolio → [link]"

Transparent and timely. Real P&L builds trust.
"""

    return GrokPrompt(
        day="",
        slot=0,
        category="position_update",
        title=f"Position Update: {ticker}",
        prompt=prompt,
        # CRIT-12.4: Removed entry price from visual suggestion
        visual_suggestion=f"Position card showing {ticker}, live P&L%, {days_held} days held, chart thumbnail",
        ticker=ticker,
        theme=theme
    )


def create_sell_signal_prompt(signal: Dict, data: PortfolioData) -> GrokPrompt:
    """Create a prompt about a sell/caution signal."""
    ticker = signal.get('ticker', 'UNKNOWN')
    price = signal.get('price', 0)
    reason = signal.get('reason', 'Technical deterioration')
    pnl = signal.get('pnl', '+0%')
    # CRIT-12.4: entry_price is PRIVATE - do not expose in public prompts

    prompt = f"""CAUTION SIGNAL:
{ticker}: Sell signal triggered | Current: ${price:.2f} | P&L: {pnl}
Reason: {reason}

---

You are drafting an X post for {ACCOUNT_HANDLE}.

Using the signal above:
1. Search for any recent news that might explain ${ticker}'s weakness
2. Draft a visually engaging X post (under 280 characters) that:
   - Acknowledges the caution signal transparently
   - Explains what triggered it (Capital Preservation Protocol, structural break, etc.)
   - Shows active risk management in action
   - Frames this as discipline, not defeat ("This is why we use systematic exits...")
   - Ends with CTA: {SUBSTACK_URL}

Risk management in action builds more credibility than only showing winners.
"""
    
    return GrokPrompt(
        day="",
        slot=0,
        category="sell_signal",
        title=f"Caution: {ticker}",
        prompt=prompt,
        visual_suggestion=f"Chart showing the sell signal trigger point for {ticker}",
        ticker=ticker
    )


def create_scanner_stats_prompt(data: PortfolioData) -> GrokPrompt:
    """Create a prompt about weekly scanner statistics."""
    stats = data.scan_stats
    tickers_scanned = stats.get('tickers_scanned', 1800)
    bos_bullish = stats.get('bos_bullish', 50)
    technical = stats.get('technical_signals', 15)
    theme_confirmed = stats.get('theme_confirmed', 5)
    passes = len(data.pass_signals)
    
    prompt = f"""SCANNER STATS:
Scanned: {tickers_scanned} | BoS Up: {bos_bullish} | Technical Pass: {technical} | Theme Fit: {theme_confirmed} | Final PASS: {passes}

---

You are drafting an X post for {ACCOUNT_HANDLE}.

Using the stats above:
1. Draft a visually engaging X post (under 280 characters) that:
   - Leads with the filtering ratio (e.g., "{tickers_scanned} stocks → {passes} signals")
   - Emphasizes the rigorous 3-gate screening process
   - Creates CURIOSITY about what made the cut
   - Builds FOMO for non-subscribers
   - Strong CTA: {SUBSTACK_URL}

This is the "proof of work" post. Make readers feel they're missing out if not subscribed.
"""
    
    return GrokPrompt(
        day="",
        slot=0,
        category="scanner_stats",
        title="Weekly Scanner Stats",
        prompt=prompt,
        visual_suggestion="Funnel graphic: 1800+ → X → Y → Z → PASS"
    )


def create_why_passed_prompt(signal: Dict, data: PortfolioData) -> GrokPrompt:
    """Create a prompt explaining why a stock FAILED the gates."""
    ticker = signal.get('ticker', 'UNKNOWN')
    concerns = signal.get('concerns', [])
    reasoning = signal.get('reasoning', 'Did not meet all criteria')
    theme = signal.get('theme', 'Unknown')
    
    main_concern = concerns[0] if concerns else reasoning[:60]
    
    prompt = f"""SCANNER OUTPUT:
EXCLUDED: {ticker} | Theme: {theme}
Reason: {main_concern}

---

You are drafting an X post for {ACCOUNT_HANDLE}.

Using the scanner output above:
1. Search for why ${ticker} might be getting attention/hype right now
2. Draft a visually engaging X post (under 280 characters) that:
   - Acknowledges the buzz WITHOUT being dismissive ("I see the hype...")
   - States specifically which gate it failed (technical, thematic, or quality)
   - Shows disciplined process over FOMO
   - References the proprietary 3-gate system
   - Ends with: "What DID pass → {SUBSTACK_URL}"

Show process, not arrogance. This builds trust.
"""
    
    return GrokPrompt(
        day="",
        slot=0,
        category="why_passed",
        title=f"Why I Passed: {ticker}",
        prompt=prompt,
        visual_suggestion="Gate Check graphic (Technical ✓/✗ | Theme ✓/✗ | Quality ✓/✗)",
        ticker=ticker,
        theme=theme
    )


def create_theme_comparison_prompt(hot_theme: Dict, cold_theme: Dict) -> GrokPrompt:
    """Create a prompt comparing two themes."""
    hot_name = hot_theme.get('name', 'Hot Theme')
    cold_name = cold_theme.get('name', 'Cold Theme')
    
    prompt = f"""THEME COMPARISON:
HOT: {hot_name}
COLD: {cold_name}

---

You are drafting an X post for {ACCOUNT_HANDLE}.

1. Search for recent performance/momentum of both themes
2. Draft a visually engaging X post (under 280 characters) that:
   - Compares the two themes fairly (don't strawman the cold one)
   - States which has stronger momentum RIGHT NOW
   - Shows systematic theme analysis
   - Implies I have specific picks in the winning theme
   - Ends with CTA: {SUBSTACK_URL}

Balanced but decisive. Capital flows matter.
"""
    
    return GrokPrompt(
        day="",
        slot=0,
        category="theme_comparison",
        title=f"{hot_name} vs {cold_name}",
        prompt=prompt,
        visual_suggestion="Side-by-side comparison chart or graphic"
    )


def create_trading_lesson_prompt() -> GrokPrompt:
    """Create an educational trading lesson prompt."""
    
    lessons = [
        "Entry timing matters more than stock selection",
        "Fresh trends outperform extended trends",
        "Trailing stops protect gains better than fixed targets",
        "The best trade is often the one you don't make",
        "Position sizing determines survival, not returns",
        "Weekly timeframes filter out noise",
        "Theme alignment multiplies momentum",
    ]
    
    import random
    lesson = random.choice(lessons)
    
    prompt = f"""TRADING LESSON:
Topic: {lesson}

---

You are drafting an X post for {ACCOUNT_HANDLE}.

1. Pick a practical way to illustrate this lesson
2. Draft a visually engaging X post (under 280 characters) that:
   - States the lesson clearly
   - Gives ONE practical application
   - Shows experienced, systematic perspective
   - Doesn't preach - share as hard-won wisdom
   - Ends with CTA: {SUBSTACK_URL}

Educational and actionable. Make them think "I should follow this person."
"""
    
    return GrokPrompt(
        day="",
        slot=0,
        category="trading_lesson",
        title=f"Lesson: {lesson[:40]}...",
        prompt=prompt,
        visual_suggestion="Rule graphic or annotated chart example"
    )


def create_market_pulse_prompt() -> GrokPrompt:
    """Create a market pulse/reaction prompt."""
    
    prompt = f"""You are drafting an X post for {ACCOUNT_HANDLE}, a momentum stock newsletter.

1. Search for TODAY's market performance:
   - S&P 500, NASDAQ, Russell 2000 moves
   - What sectors are leading/lagging
   - Any notable movers or news

2. Draft a visually engaging X post (under 280 characters) that:
   - Opens with the headline move and specific numbers
   - Notes sector leadership or rotation
   - Connects to implications for momentum/high-beta stocks
   - Shows you're actively watching markets
   - Ends with CTA: {SUBSTACK_URL}

Quick, informed, timely. Show you're in the trenches.
"""
    
    return GrokPrompt(
        day="",
        slot=0,
        category="market_pulse",
        title="Market Pulse",
        prompt=prompt,
        visual_suggestion="Index performance bars or sector heat map"
    )


def create_newsletter_drop_prompt(data: PortfolioData) -> GrokPrompt:
    """Create a newsletter announcement prompt."""
    
    passes = len(data.pass_signals)
    cautions = len(data.caution_signals)
    top_theme = data.prime_themes[0]['name'] if data.prime_themes else (
        data.investable_themes[0]['name'] if data.investable_themes else "Multiple themes"
    )
    
    pass_tickers = [s['ticker'] for s in data.pass_signals[:3]]
    caution_tickers = [s['ticker'] for s in data.caution_signals[:3]]
    
    highlights = f"PASS: {', '.join(pass_tickers) if pass_tickers else 'None'} | CAUTION: {', '.join(caution_tickers) if caution_tickers else 'None'} | Top Theme: {top_theme}"
    
    prompt = f"""NEWSLETTER HIGHLIGHTS:
{highlights}

---

You are drafting an X post for {ACCOUNT_HANDLE}.

This is the MAIN distribution moment for the weekly newsletter.

Draft a visually engaging X post (under 280 characters) that:
- Announces the newsletter is LIVE with energy
- Highlights the most interesting/contrarian element
- Emphasizes the proprietary scanner methodology
- Creates URGENCY to read now
- Direct CTA: {SUBSTACK_URL}

This is the moment. Make it count.
"""
    
    return GrokPrompt(
        day="",
        slot=0,
        category="newsletter_drop",
        title="Newsletter Drop",
        prompt=prompt,
        visual_suggestion="Newsletter header graphic or key insight card"
    )


def create_week_ahead_prompt() -> GrokPrompt:
    """Create a Monday week ahead prompt."""
    
    prompt = f"""You are drafting an X post for {ACCOUNT_HANDLE}.

1. Search for THIS WEEK's key catalysts:
   - Major earnings (big tech, bellwethers)
   - Fed speakers or announcements
   - Economic data releases (CPI, jobs, etc.)
   - Any sector-specific events

2. Draft a visually engaging X post (under 280 characters) that:
   - Sets up the week with energy
   - Notes 2-3 key catalysts with DATES
   - Shows systematic market awareness
   - Builds anticipation
   - Ends with CTA: {SUBSTACK_URL}

Energetic but professional. Monday motivation.
"""
    
    return GrokPrompt(
        day="",
        slot=0,
        category="week_ahead",
        title="Week Ahead Preview",
        prompt=prompt,
        visual_suggestion="'Week Ahead' calendar graphic with key dates"
    )


def create_engagement_prompt() -> GrokPrompt:
    """Create a Sunday engagement prompt (no hard sell)."""
    
    questions = [
        "What's your biggest trading lesson from 2024?",
        "Momentum or value - which camp are you in?",
        "What's on your watchlist this week?",
        "How long do you typically hold positions?",
        "Best trade you passed on this year?",
    ]
    
    import random
    question = random.choice(questions)
    
    prompt = f"""ENGAGEMENT POST (Sunday):
Theme: Community building, light touch

---

You are drafting a light, engagement-focused X post for {ACCOUNT_HANDLE}.

Topic/Question: {question}

Draft a visually engaging X post (under 280 characters) that:
- Is EASY to respond to
- Builds community
- Shows personality without being unprofessional
- NO Substack link (pure engagement)

Light touch, not a hard sell. Build relationships.
"""
    
    return GrokPrompt(
        day="",
        slot=0,
        category="engagement",
        title="Sunday Engagement",
        prompt=prompt,
        visual_suggestion="Optional - question card or simple graphic"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# PROMPT SCHEDULING
# ═══════════════════════════════════════════════════════════════════════════════

def generate_weekly_prompts(data: PortfolioData) -> List[GrokPrompt]:
    """Generate 21 prompts organized by day of week."""
    
    prompts = []
    
    # Collect all available prompt sources
    hot_themes = data.prime_themes + data.investable_themes
    cold_themes = data.selective_themes + data.avoid_themes
    all_positions = data.open_positions
    
    # ═══════════════════════════════════════════════════════════════════════════
    # MONDAY (Week Ahead, Theme Hot, Position Update)
    # ═══════════════════════════════════════════════════════════════════════════
    
    # Slot 1: Week Ahead
    p = create_week_ahead_prompt()
    p.day = "Monday"
    p.slot = 1
    prompts.append(p)
    
    # Slot 2: Hot Theme
    if hot_themes:
        p = create_hot_theme_prompt(hot_themes[0], data)
        p.day = "Monday"
        p.slot = 2
        prompts.append(p)
    else:
        p = create_market_pulse_prompt()
        p.day = "Monday"
        p.slot = 2
        prompts.append(p)
    
    # Slot 3: Position Update or Trading Lesson
    if all_positions:
        p = create_position_update_prompt(all_positions[0], data)
        p.day = "Monday"
        p.slot = 3
        prompts.append(p)
    else:
        p = create_trading_lesson_prompt()
        p.day = "Monday"
        p.slot = 3
        prompts.append(p)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TUESDAY (Buy Signal, Cold Theme, Watchlist)
    # ═══════════════════════════════════════════════════════════════════════════
    
    # Slot 1: Buy Signal or Scanner Stats
    if data.pass_signals:
        p = create_buy_signal_prompt(data.pass_signals[0], data)
        p.day = "Tuesday"
        p.slot = 1
        prompts.append(p)
    else:
        p = create_scanner_stats_prompt(data)
        p.day = "Tuesday"
        p.slot = 1
        prompts.append(p)
    
    # Slot 2: Cold Theme
    if cold_themes:
        p = create_cold_theme_prompt(cold_themes[0], data)
        p.day = "Tuesday"
        p.slot = 2
        prompts.append(p)
    else:
        p = create_trading_lesson_prompt()
        p.day = "Tuesday"
        p.slot = 2
        prompts.append(p)
    
    # Slot 3: Watchlist Stock
    if data.caution_signals:
        p = create_watchlist_prompt(data.caution_signals[0], data)
        p.day = "Tuesday"
        p.slot = 3
        prompts.append(p)
    else:
        p = create_market_pulse_prompt()
        p.day = "Tuesday"
        p.slot = 3
        prompts.append(p)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # WEDNESDAY (Market Pulse, Theme Comparison, Position Update)
    # ═══════════════════════════════════════════════════════════════════════════
    
    # Slot 1: Market Pulse
    p = create_market_pulse_prompt()
    p.day = "Wednesday"
    p.slot = 1
    prompts.append(p)
    
    # Slot 2: Theme Comparison
    if hot_themes and cold_themes:
        p = create_theme_comparison_prompt(hot_themes[0], cold_themes[0])
        p.day = "Wednesday"
        p.slot = 2
        prompts.append(p)
    elif len(hot_themes) >= 2:
        p = create_hot_theme_prompt(hot_themes[1], data)
        p.day = "Wednesday"
        p.slot = 2
        prompts.append(p)
    else:
        p = create_trading_lesson_prompt()
        p.day = "Wednesday"
        p.slot = 2
        prompts.append(p)
    
    # Slot 3: Position Update or Sell Signal
    if data.sell_signals:
        p = create_sell_signal_prompt(data.sell_signals[0], data)
        p.day = "Wednesday"
        p.slot = 3
        prompts.append(p)
    elif len(all_positions) > 1:
        p = create_position_update_prompt(all_positions[1], data)
        p.day = "Wednesday"
        p.slot = 3
        prompts.append(p)
    else:
        p = create_trading_lesson_prompt()
        p.day = "Wednesday"
        p.slot = 3
        prompts.append(p)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # THURSDAY (Buy Signal 2, Why Passed, Hot Theme 2)
    # ═══════════════════════════════════════════════════════════════════════════
    
    # Slot 1: Second Buy Signal or Why Passed
    if len(data.pass_signals) > 1:
        p = create_buy_signal_prompt(data.pass_signals[1], data)
        p.day = "Thursday"
        p.slot = 1
        prompts.append(p)
    elif data.caution_signals:
        p = create_why_passed_prompt(data.caution_signals[0], data)
        p.day = "Thursday"
        p.slot = 1
        prompts.append(p)
    else:
        p = create_scanner_stats_prompt(data)
        p.day = "Thursday"
        p.slot = 1
        prompts.append(p)
    
    # Slot 2: Hot Theme 2 or Trading Lesson
    if len(hot_themes) > 1:
        p = create_hot_theme_prompt(hot_themes[1], data)
        p.day = "Thursday"
        p.slot = 2
        prompts.append(p)
    else:
        p = create_trading_lesson_prompt()
        p.day = "Thursday"
        p.slot = 2
        prompts.append(p)
    
    # Slot 3: Watchlist 2 or Market Pulse
    if len(data.caution_signals) > 1:
        p = create_watchlist_prompt(data.caution_signals[1], data)
        p.day = "Thursday"
        p.slot = 3
        prompts.append(p)
    else:
        p = create_market_pulse_prompt()
        p.day = "Thursday"
        p.slot = 3
        prompts.append(p)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # FRIDAY (Scanner Stats, Cold Theme 2, Position Update)
    # ═══════════════════════════════════════════════════════════════════════════
    
    # Slot 1: Scanner Stats (teaser for newsletter)
    p = create_scanner_stats_prompt(data)
    p.day = "Friday"
    p.slot = 1
    prompts.append(p)
    
    # Slot 2: Cold Theme 2 or Why Passed
    if len(cold_themes) > 1:
        p = create_cold_theme_prompt(cold_themes[1], data)
        p.day = "Friday"
        p.slot = 2
        prompts.append(p)
    elif len(data.caution_signals) > 1:
        p = create_why_passed_prompt(data.caution_signals[1], data)
        p.day = "Friday"
        p.slot = 2
        prompts.append(p)
    else:
        p = create_trading_lesson_prompt()
        p.day = "Friday"
        p.slot = 2
        prompts.append(p)
    
    # Slot 3: Position Update 3 or Market Pulse
    if len(all_positions) > 2:
        p = create_position_update_prompt(all_positions[2], data)
        p.day = "Friday"
        p.slot = 3
        prompts.append(p)
    else:
        p = create_market_pulse_prompt()
        p.day = "Friday"
        p.slot = 3
        prompts.append(p)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SATURDAY (Newsletter Drop, Buy Signal Deep Dive, Sell Signal)
    # ═══════════════════════════════════════════════════════════════════════════
    
    # Slot 1: Newsletter Drop
    p = create_newsletter_drop_prompt(data)
    p.day = "Saturday"
    p.slot = 1
    prompts.append(p)
    
    # Slot 2: Buy Signal Deep Dive or Hot Theme
    if data.pass_signals:
        p = create_buy_signal_prompt(data.pass_signals[0], data)
        p.title = f"Deep Dive: {data.pass_signals[0]['ticker']}"
        p.day = "Saturday"
        p.slot = 2
        prompts.append(p)
    elif hot_themes:
        p = create_hot_theme_prompt(hot_themes[0], data)
        p.day = "Saturday"
        p.slot = 2
        prompts.append(p)
    else:
        p = create_trading_lesson_prompt()
        p.day = "Saturday"
        p.slot = 2
        prompts.append(p)
    
    # Slot 3: Sell Signal or Why Passed
    if data.sell_signals:
        p = create_sell_signal_prompt(data.sell_signals[0], data)
        p.day = "Saturday"
        p.slot = 3
        prompts.append(p)
    elif data.caution_signals:
        p = create_why_passed_prompt(data.caution_signals[0], data)
        p.day = "Saturday"
        p.slot = 3
        prompts.append(p)
    else:
        p = create_trading_lesson_prompt()
        p.day = "Saturday"
        p.slot = 3
        prompts.append(p)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SUNDAY (Engagement, Trading Lesson, Week Preview)
    # ═══════════════════════════════════════════════════════════════════════════
    
    # Slot 1: Engagement (no hard sell)
    p = create_engagement_prompt()
    p.day = "Sunday"
    p.slot = 1
    prompts.append(p)
    
    # Slot 2: Trading Lesson
    p = create_trading_lesson_prompt()
    p.day = "Sunday"
    p.slot = 2
    prompts.append(p)
    
    # Slot 3: Soft week preview
    p = create_week_ahead_prompt()
    p.title = "Looking Ahead (Soft)"
    p.day = "Sunday"
    p.slot = 3
    prompts.append(p)
    
    return prompts


# ═══════════════════════════════════════════════════════════════════════════════
# OUTPUT GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

def generate_prompts_markdown(prompts: List[GrokPrompt], data: PortfolioData) -> str:
    """Generate the full markdown document with all prompts."""
    
    lines = []
    date_str = datetime.now().strftime("%B %d, %Y")
    
    lines.append("# 📱 GROK PROMPTS - Weekly X/Twitter Content")
    lines.append("")
    lines.append(f"**Generated:** {date_str}")
    lines.append(f"**Account:** {ACCOUNT_HANDLE}")
    lines.append(f"**Substack:** {SUBSTACK_URL}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 📋 Weekly Summary")
    lines.append("")
    lines.append("| Day | Slot 1 (Pre-market) | Slot 2 (Morning) | Slot 3 (Midday) | Slot 4 (Power Hour) | Slot 5 (After-hours) |")
    lines.append("|-----|------------------|-----------------|------------------|")
    
    for day in DAYS:
        day_prompts = [p for p in prompts if p.day == day]
        slots = {p.slot: p.title[:20] for p in day_prompts}
        lines.append(f"| {day} | {slots.get(1, '-')} | {slots.get(2, '-')} | {slots.get(3, '-')} |")
    
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Portfolio context
    lines.append("## 📊 Portfolio Context")
    lines.append("")
    lines.append("**Current State:**")
    if data.pass_signals:
        lines.append(f"- **PASS Signals:** {', '.join([s['ticker'] for s in data.pass_signals])}")
    if data.caution_signals:
        lines.append(f"- **CAUTION Signals:** {', '.join([s['ticker'] for s in data.caution_signals])}")
    if data.open_positions:
        lines.append(f"- **Open Positions:** {', '.join([p.get('ticker', p.get('symbol', '?')) for p in data.open_positions])}")
    if data.sell_signals:
        lines.append(f"- **Sell Signals:** {', '.join([s['ticker'] for s in data.sell_signals])}")
    
    lines.append("")
    lines.append("**Themes:**")
    if data.prime_themes:
        lines.append(f"- **PRIME:** {', '.join([t['name'] for t in data.prime_themes])}")
    if data.investable_themes:
        lines.append(f"- **INVESTABLE:** {', '.join([t['name'] for t in data.investable_themes])}")
    if data.selective_themes:
        lines.append(f"- **SELECTIVE:** {', '.join([t['name'] for t in data.selective_themes])}")
    if data.avoid_themes:
        lines.append(f"- **AVOID:** {', '.join([t['name'] for t in data.avoid_themes])}")
    
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Individual prompts by day
    for day in DAYS:
        day_prompts = [p for p in prompts if p.day == day]
        if not day_prompts:
            continue
        
        lines.append(f"# 📅 {day.upper()}")
        lines.append("")
        
        for p in sorted(day_prompts, key=lambda x: x.slot):
            slot_labels = {1: "🌅 Pre-market (08:00 ET)", 2: "☀️ Morning (10:00 ET)", 3: "🌞 Midday (12:30 ET)", 4: "⚡ Power Hour (15:30 ET)", 5: "🌆 After-hours (18:00 ET)"}
            slot_label = slot_labels.get(p.slot, f"Slot {p.slot}")
            
            lines.append(f"## {slot_label}: {p.title}")
            lines.append("")
            lines.append(f"**Category:** {p.category}")
            if p.ticker:
                lines.append(f"**Ticker:** ${p.ticker}")
            if p.theme:
                lines.append(f"**Theme:** {p.theme}")
            lines.append(f"**Visual:** {p.visual_suggestion}")
            lines.append("")
            lines.append("### Prompt (Copy to Grok)")
            lines.append("")
            lines.append("```")
            lines.append(p.prompt)
            lines.append("```")
            lines.append("")
            lines.append("---")
            lines.append("")
    
    lines.append("## 📝 Usage Notes")
    lines.append("")
    lines.append("1. **Copy each prompt** into Grok (X's AI)")
    lines.append("2. **Review the output** - Grok will search for current news")
    lines.append("3. **Edit as needed** - Add your voice, adjust tone")
    lines.append("4. **Add the visual** - Use TradingView charts, Canva graphics, etc.")
    lines.append("5. **Post at optimal times** - Pre-market (8am ET), Morning (10am ET), Midday (12:30pm ET), Power Hour (3:30pm ET), After-hours (6pm ET)")
    lines.append("")
    lines.append("**Pro Tips:**")
    lines.append("- Pre-market (8am ET) posts capture early traders")
    lines.append("- Power Hour (3:30pm ET) posts are CRITICAL for US market reaction")
    lines.append("- Engagement posts (questions) work best on Sunday")
    lines.append("- Newsletter drops should go Saturday morning (Eastern Time)")
    lines.append("- Real P&L transparency builds trust")
    lines.append("- Compare performance to SPY/QQQ for credibility")
    lines.append("")
    lines.append(f"*Generated by Sterling Signals Grok Prompts Generator*")
    
    return "\n".join(lines)


def save_prompts(prompts: List[GrokPrompt], data: PortfolioData, output_dir: Path):
    """Save prompts to markdown files."""
    
    output_dir.mkdir(exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    
    # Main file with all prompts
    main_content = generate_prompts_markdown(prompts, data)

    # Validate content for banned marketing terms
    if MARKETING_VOCABULARY_AVAILABLE:
        is_valid, violations = validate_content(main_content)
        if not is_valid:
            print(f"  ⚠️ WARNING: Prompts contain banned terms: {violations}")
            print("     Consider reviewing generated prompts.")
        else:
            print("  ✅ Prompts passed vocabulary validation")

    main_file = output_dir / f"grok_prompts_{date_str}.md"
    with open(main_file, 'w') as f:
        f.write(main_content)
    
    # Also save as latest
    latest_file = output_dir / "latest_grok_prompts.md"
    with open(latest_file, 'w') as f:
        f.write(main_content)
    
    # Individual day files for convenience
    for day in DAYS:
        day_prompts = [p for p in prompts if p.day == day]
        if day_prompts:
            day_file = output_dir / f"{day.lower()}_prompts.md"
            
            lines = [f"# {day} Prompts", ""]
            for p in sorted(day_prompts, key=lambda x: x.slot):
                lines.append(f"## Slot {p.slot}: {p.title}")
                lines.append("")
                lines.append("```")
                lines.append(p.prompt)
                lines.append("```")
                lines.append("")
                lines.append(f"**Visual:** {p.visual_suggestion}")
                lines.append("")
                lines.append("---")
                lines.append("")
            
            with open(day_file, 'w') as f:
                f.write("\n".join(lines))
    
    return main_file


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate 21 Grok prompts for weekly X content")
    parser.add_argument("--briefing", type=str, help="Path to newsletter briefing markdown file")
    parser.add_argument("--output", type=str, help="Output directory for prompts")
    parser.add_argument("--trades-dir", type=str, help="Directory containing trade files")
    args = parser.parse_args()
    
    print("\n")
    print("╔" + "═" * 60 + "╗")
    print("║" + " GROK PROMPTS GENERATOR ".center(60) + "║")
    print("║" + " 21 Weekly X/Twitter Prompts ".center(60) + "║")
    print("╚" + "═" * 60 + "╝")
    print("")
    
    # Determine paths
    trades_dir = Path(args.trades_dir) if args.trades_dir else TRADES_DIR
    output_dir = Path(args.output) if args.output else OUTPUT_DIR
    
    if args.briefing:
        briefing_path = Path(args.briefing)
    else:
        briefing_path = trades_dir / "latest_newsletter_briefing.md"
    
    print(f"  📂 Trades directory: {trades_dir}")
    print(f"  📄 Briefing file: {briefing_path}")
    print(f"  📁 Output directory: {output_dir}")
    print("")
    
    # Load portfolio data
    print("  Loading portfolio data...")
    data = parse_briefing_markdown(briefing_path)

    # Also try to load from CSV if briefing parsing was sparse
    if not data.open_positions:
        csv_positions = load_open_positions_csv(trades_dir, fetch_live_prices=True)
        if csv_positions:
            data.open_positions = csv_positions

    # Always fetch live prices for open positions (ensures accurate P&L in prompts)
    if data.open_positions:
        data.open_positions = fetch_live_prices_for_positions(data.open_positions)

    # Load themes from cache if available
    themes_cache = load_themes_cache(BASE_DIR)
    if themes_cache and not data.prime_themes:
        for theme in themes_cache:
            classification = theme.get('classification', 'INVESTABLE')
            if classification == 'PRIME':
                data.prime_themes.append(theme)
            elif classification == 'INVESTABLE':
                data.investable_themes.append(theme)
            elif classification == 'SELECTIVE':
                data.selective_themes.append(theme)
            elif classification == 'AVOID':
                data.avoid_themes.append(theme)
    
    # Summary of loaded data
    print("")
    print("  📊 Data loaded:")
    print(f"     • PRIME themes: {len(data.prime_themes)}")
    print(f"     • INVESTABLE themes: {len(data.investable_themes)}")
    print(f"     • SELECTIVE themes: {len(data.selective_themes)}")
    print(f"     • AVOID themes: {len(data.avoid_themes)}")
    print(f"     • PASS signals: {len(data.pass_signals)}")
    print(f"     • CAUTION signals: {len(data.caution_signals)}")
    print(f"     • Open positions: {len(data.open_positions)}")
    print(f"     • Sell signals: {len(data.sell_signals)}")
    print("")
    
    # Generate prompts
    print("  Generating 21 weekly prompts...")
    prompts = generate_weekly_prompts(data)
    
    # Save output
    main_file = save_prompts(prompts, data, output_dir)
    
    print("")
    print("  ✅ Prompts generated successfully!")
    print("")
    print(f"  📁 Main file: {main_file}")
    print(f"  📁 Latest: {output_dir / 'latest_grok_prompts.md'}")
    print(f"  📁 Day files: {output_dir}/<day>_prompts.md")
    print("")
    print("  " + "─" * 50)
    print("")
    print("  📅 Weekly Schedule:")
    for day in DAYS:
        day_prompts = [p for p in prompts if p.day == day]
        titles = [p.title[:25] for p in sorted(day_prompts, key=lambda x: x.slot)]
        print(f"     {day:10} | {' | '.join(titles)}")
    print("")
    print("═" * 64)


if __name__ == "__main__":
    main()
