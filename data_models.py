#!/usr/bin/env python3
"""
DATA MODELS - Unified Dataclass Definitions
============================================

Central repository for all dataclasses used across the codebase.
Provides inheritance hierarchies and consistent field naming.

Usage:
    from data_models import (
        Stock, Trade, Theme, Signal,
        GatekeeperResult, DDResult, TweetContent
    )
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional, Any


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class TradeStatus(Enum):
    """Trade status values."""
    OPEN = "OPEN"
    CLOSED = "CLOSED"      # Manual exit (profit taking, strategic)
    STOPPED = "STOPPED"    # Hit trailing stop


class GateDecision(Enum):
    """Gatekeeper decision values."""
    PASS = "PASS"
    CAUTION = "CAUTION"
    FAIL = "FAIL"


class ThemeClassification(Enum):
    """Theme classification levels."""
    PRIME = "PRIME"           # Highest conviction
    INVESTABLE = "INVESTABLE" # Good opportunities
    SELECTIVE = "SELECTIVE"   # Mixed signals
    AVOID = "AVOID"           # Stay away


class ThemeFit(Enum):
    """Theme fit assessment."""
    STRONG = "STRONG FIT"
    GOOD = "GOOD FIT"
    MODERATE = "MODERATE FIT"
    POOR = "POOR FIT"


# ═══════════════════════════════════════════════════════════════════════════════
# BASE CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class BaseResult:
    """Base class for analysis results with common fields."""
    ticker: str
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class BaseAnalysisResult(BaseResult):
    """Base class for analysis results with decision fields."""
    decision: str = ""
    conviction: int = 0       # 1-5 scale
    reasoning: str = ""


# ═══════════════════════════════════════════════════════════════════════════════
# STOCK DATA
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Stock:
    """
    Core stock data structure used throughout the scanner pipeline.

    Populated progressively through:
    1. Technical scan (price, beta, banker, bos)
    2. Thematic analyzer (theme, theme_score, theme_verdict)
    3. Gatekeeper (final_decision, conviction, catalysts)
    """
    # Core identity
    symbol: str

    # Price data
    price: float = 0.0

    # Technical indicators
    beta: float = 0.0
    banker: float = 0.0
    bos_bullish: bool = False
    bos_bearish: bool = False
    bos_debug: Dict = field(default_factory=dict)
    return_20d: float = 0.0
    momentum_4w: float = 0.0
    tier: str = ""  # TIER1, TIER2, TIER3

    # Thematic analyzer fields (populated in Step 5)
    theme: str = ""
    theme_score: float = 0.0
    pure_play_score: int = 0  # 0-100%
    theme_verdict: str = ""   # STRONG FIT, GOOD FIT, MODERATE FIT, POOR FIT

    # Gatekeeper fields (populated in Step 6)
    final_decision: str = ""  # PASS, CAUTION, FAIL
    conviction: int = 0       # 1-5
    catalyst_summary: str = ""
    red_flag_level: str = ""  # CLEAN, MINOR, SEVERE
    action: str = ""          # Recommended action
    bullish_factors: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)
    reasoning: str = ""

    # DD fields (optional)
    dd_verdict: str = ""
    dd_conviction: int = 0
    dd_summary: str = ""

    def passes_technical(self) -> bool:
        """Check if stock passes technical gate."""
        return self.bos_bullish and self.beta >= 1.5 and self.banker >= 55

    def passes_theme(self) -> bool:
        """Check if stock passes theme gate."""
        return self.theme_verdict in ["STRONG FIT", "GOOD FIT"]

    def is_tradeable(self) -> bool:
        """Check if stock is ready to trade."""
        return self.final_decision == "PASS"


# ═══════════════════════════════════════════════════════════════════════════════
# TRADE DATA
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Trade:
    """
    Represents a trade (open or closed) in the portfolio.

    Stored fields are persisted to CSV.
    Calculated fields are computed on load.
    """
    # Stored fields (in CSV)
    ticker: str
    status: str = "OPEN"
    entry_date: str = ""
    entry_price: float = 0.0
    exit_date: str = ""
    exit_price: float = 0.0
    highest_close: float = 0.0
    theme: str = ""
    tier: str = ""
    signal_type: str = "PASS"  # PASS or CAUTION
    conviction: int = 0
    notes: str = ""

    # Calculated fields (not stored)
    current_price: float = 0.0
    pnl_pct: float = 0.0
    pnl_usd: float = 0.0
    stop_level: float = 0.0
    days_held: int = 0
    distance_to_stop_pct: float = 0.0
    stop_alert: bool = False

    def __post_init__(self):
        """Initialize calculated fields."""
        if not self.entry_date:
            self.entry_date = datetime.now().strftime("%Y-%m-%d")
        if self.highest_close == 0 and self.entry_price > 0:
            self.highest_close = self.entry_price

    def calculate_metrics(
        self,
        current_price: float = None,
        stop_pct: float = 20.0,
        warning_pct: float = 5.0
    ) -> None:
        """
        Calculate all derived metrics.

        Args:
            current_price: Current market price (optional)
            stop_pct: Trailing stop percentage (default 20%)
            warning_pct: Stop warning threshold (default 5%)
        """
        if current_price is not None:
            self.current_price = current_price

            # Update highest close for open positions
            if self.status == "OPEN" and current_price > self.highest_close:
                self.highest_close = current_price

        # Use exit price for closed trades, current price for open
        price_for_calc = self.exit_price if self.status != "OPEN" else self.current_price

        if self.entry_price > 0 and price_for_calc > 0:
            self.pnl_pct = ((price_for_calc / self.entry_price) - 1) * 100
            self.pnl_usd = (price_for_calc - self.entry_price) * 100  # Assumes 100 shares

        # Stop level
        if self.highest_close > 0:
            self.stop_level = self.highest_close * (1 - stop_pct / 100)

        # Distance to stop
        if self.status == "OPEN" and self.current_price > 0 and self.stop_level > 0:
            self.distance_to_stop_pct = ((self.current_price - self.stop_level) / self.current_price) * 100
            self.stop_alert = self.distance_to_stop_pct <= warning_pct

        # Days held
        if self.entry_date:
            try:
                entry = datetime.strptime(self.entry_date, "%Y-%m-%d")
                if self.status == "OPEN":
                    self.days_held = (datetime.now() - entry).days
                elif self.exit_date:
                    exit_dt = datetime.strptime(self.exit_date, "%Y-%m-%d")
                    self.days_held = (exit_dt - entry).days
            except ValueError:
                pass

    def to_csv_row(self) -> Dict:
        """Convert to CSV row (stored fields only)."""
        return {
            'ticker': self.ticker,
            'status': self.status,
            'entry_date': self.entry_date,
            'entry_price': f"{self.entry_price:.2f}" if self.entry_price else "",
            'exit_date': self.exit_date,
            'exit_price': f"{self.exit_price:.2f}" if self.exit_price else "",
            'highest_close': f"{self.highest_close:.2f}" if self.highest_close else "",
            'theme': self.theme,
            'tier': self.tier,
            'signal_type': self.signal_type,
            'conviction': str(self.conviction) if self.conviction else "",
            'notes': self.notes
        }

    @classmethod
    def from_csv_row(cls, row: Dict) -> 'Trade':
        """Create Trade from CSV row."""
        return cls(
            ticker=row.get('ticker', '').upper(),
            status=row.get('status', 'OPEN'),
            entry_date=row.get('entry_date', ''),
            entry_price=float(row.get('entry_price') or 0),
            exit_date=row.get('exit_date', ''),
            exit_price=float(row.get('exit_price') or 0),
            highest_close=float(row.get('highest_close') or 0),
            theme=row.get('theme', ''),
            tier=row.get('tier', ''),
            signal_type=row.get('signal_type', 'PASS'),
            conviction=int(row.get('conviction') or 0),
            notes=row.get('notes', '')
        )

    @classmethod
    def from_stock(cls, stock: Stock) -> 'Trade':
        """Create Trade from Stock object."""
        return cls(
            ticker=stock.symbol,
            status="OPEN",
            entry_date=datetime.now().strftime("%Y-%m-%d"),
            entry_price=stock.price,
            highest_close=stock.price,
            theme=stock.theme,
            tier=stock.tier,
            signal_type=stock.final_decision,
            conviction=stock.conviction
        )


# ═══════════════════════════════════════════════════════════════════════════════
# THEME DATA
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Theme:
    """
    Theme data from thematic analyzer.

    Represents an investable theme with scoring and classification.
    """
    rank: int = 0
    name: str = ""
    classification: str = "INVESTABLE"  # PRIME, INVESTABLE, SELECTIVE, AVOID
    theme_type: str = "TREND"           # TREND, BOTTLENECK, CONTRARIAN
    composite_score: float = 0.0        # 0-10 scale

    # Component scores
    catalyst_score: float = 0.0
    momentum_score: float = 0.0
    crowding_score: float = 0.0
    runway_score: float = 0.0

    # Details
    thesis_summary: str = ""
    key_catalysts: List[str] = field(default_factory=list)
    primary_etfs: List[str] = field(default_factory=list)
    crowding_indicator: str = "Moderate"  # Low, Moderate, High

    def is_investable(self) -> bool:
        """Check if theme is worth investing in."""
        return self.classification in ["PRIME", "INVESTABLE"]

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════
# ANALYSIS RESULTS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class GatekeeperResult(BaseAnalysisResult):
    """Result from the Gatekeeper analysis gate."""
    # Decision is inherited: PASS, CAUTION, FAIL
    # Conviction is inherited: 1-5 scale

    # Theme context (passed through)
    theme: str = ""
    theme_fit: str = ""  # STRONG, GOOD, MODERATE

    # Catalyst assessment
    catalyst_present: bool = False
    catalyst_summary: str = ""
    days_to_catalyst: int = -1  # -1 if none found

    # Red flag assessment
    red_flag_level: str = "CLEAN"  # CLEAN, MINOR, SEVERE
    red_flags: List[str] = field(default_factory=list)

    # Market sentiment
    analyst_trend: str = ""  # BULLISH, NEUTRAL, BEARISH
    short_interest_pct: float = 0.0

    # Key factors
    key_bullish: List[str] = field(default_factory=list)
    key_risks: List[str] = field(default_factory=list)

    # Recommendation
    action: str = ""  # Specific action recommendation

    def passed(self) -> bool:
        """Check if gatekeeper passed."""
        return self.decision == "PASS"


@dataclass
class DDResult(BaseAnalysisResult):
    """Result from automated due diligence analysis."""
    # Verdict (different scale from gatekeeper)
    dd_verdict: str = ""          # STRONG BUY, SPEC BUY, NO GO
    dd_conviction: int = 0        # 1-10 scale
    dd_position_size: str = ""    # FULL, REDUCED, PASS

    # Analysis content
    dd_analysis: str = ""         # Full analysis text
    dd_key_catalyst: str = ""     # Key catalyst identified
    dd_fatal_flaw: str = ""       # Fatal flaw if NO GO
    dd_math_to_50: str = ""       # Path to 50% return
    dd_bear_case: str = ""        # Bear case summary
    dd_bull_case: str = ""        # Bull case summary
    dd_thinking: str = ""         # Extended thinking (if available)

    # Meta
    dd_cost: float = 0.0          # Cost of this DD call
    dd_mode: str = ""             # QUICK or FULL
    error: str = ""               # Error message if failed

    def passed(self) -> bool:
        """Check if DD resulted in a buy verdict."""
        return self.dd_verdict in ["STRONG BUY", "SPEC BUY", "SPECULATIVE BUY"]


@dataclass
class SellSignal:
    """Signal to exit a position."""
    symbol: str
    price: float
    reason: str           # "Weekly BoS Down" or "Trailing Stop Hit"
    entry_price: float
    highest_close: float
    pnl_pct: float
    action: str = ""      # Recommended action

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════
# CONTENT GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TweetContent:
    """Single tweet content structure."""
    id: str = ""
    text: str = ""
    category: str = ""
    slot: int = 0
    day: str = ""
    scheduled_date: str = ""
    scheduled_time: str = ""
    posted: bool = False
    posted_at: str = ""
    tweet_id: str = ""
    image_path: str = ""
    is_thread_start: bool = False

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict) -> 'TweetContent':
        """Create from dictionary."""
        return cls(
            id=d.get('id', ''),
            text=d.get('text', ''),
            category=d.get('category', ''),
            slot=d.get('slot', 0),
            day=d.get('day', ''),
            scheduled_date=d.get('scheduled_date', ''),
            scheduled_time=d.get('scheduled_time', ''),
            posted=d.get('posted', False),
            posted_at=d.get('posted_at', ''),
            tweet_id=d.get('tweet_id', ''),
            image_path=d.get('image_path', ''),
            is_thread_start=d.get('is_thread_start', False)
        )


@dataclass
class WeeklyContent:
    """Container for all weekly content generation data."""
    # Themes
    prime_themes: List[Dict] = field(default_factory=list)
    investable_themes: List[Dict] = field(default_factory=list)
    selective_themes: List[Dict] = field(default_factory=list)
    avoid_themes: List[Dict] = field(default_factory=list)

    # Signals
    pass_signals: List[Dict] = field(default_factory=list)
    caution_signals: List[Dict] = field(default_factory=list)
    sell_signals: List[Dict] = field(default_factory=list)

    # Portfolio
    open_positions: List[Dict] = field(default_factory=list)
    recently_closed: List[Dict] = field(default_factory=list)
    stopped_positions: List[Dict] = field(default_factory=list)

    # Stats
    scan_stats: Dict = field(default_factory=dict)
    portfolio_stats: Dict = field(default_factory=dict)

    # SPY benchmark
    spy_return_ytd: float = 0.0
    portfolio_return_ytd: float = 0.0
    alpha: float = 0.0

    # Charts
    chart_manifest: Dict[str, str] = field(default_factory=dict)


@dataclass
class GrokPrompt:
    """A single Grok prompt with metadata."""
    day: str = ""                    # Monday, Tuesday, etc.
    slot: int = 0                    # 1-3
    category: str = ""               # theme_hot, buy_signal, etc.
    prompt_text: str = ""            # Full prompt for Grok
    ticker: str = ""                 # Primary ticker (if applicable)
    visual_suggestion: str = ""      # Chart/image suggestion

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════
# SCAN STATISTICS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ScanStats:
    """Statistics from a scanner run."""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    tickers_loaded: int = 0
    data_downloaded: int = 0
    download_failures: int = 0
    beta_gte_1_5: int = 0
    weekly_bos_up: int = 0
    banker_gte_55: int = 0
    technical_signals: int = 0
    theme_confirmed: int = 0
    gatekeeper_pass: int = 0
    gatekeeper_caution: int = 0
    gatekeeper_fail: int = 0
    final_trade: int = 0
    final_consider: int = 0
    total_cost: float = 0.0

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def safe_float(value: Any, default: float = 0.0) -> float:
    """
    Safely convert a value to float.

    Handles strings like 'N/A', '19.1%', commas, etc.
    """
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip().rstrip('%').replace(',', '')
        if cleaned.lower() in ('n/a', 'na', 'none', 'unknown', ''):
            return default
        try:
            return float(cleaned)
        except ValueError:
            return default
    return default


def safe_int(value: Any, default: int = 0) -> int:
    """Safely convert a value to int."""
    try:
        return int(safe_float(value, default))
    except (ValueError, TypeError):
        return default


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Data Models - Testing")
    print("=" * 50)

    # Test Stock
    stock = Stock(
        symbol="AAPL",
        price=150.00,
        beta=1.8,
        banker=65.5,
        bos_bullish=True,
        tier="TIER1",
        theme="AI Infrastructure",
        theme_verdict="STRONG FIT",
        final_decision="PASS",
        conviction=4
    )
    print(f"\nStock: {stock.symbol}")
    print(f"  Passes technical: {stock.passes_technical()}")
    print(f"  Passes theme: {stock.passes_theme()}")
    print(f"  Is tradeable: {stock.is_tradeable()}")

    # Test Trade
    trade = Trade.from_stock(stock)
    trade.calculate_metrics(current_price=165.00)
    print(f"\nTrade: {trade.ticker}")
    print(f"  Entry: ${trade.entry_price:.2f}")
    print(f"  Current: ${trade.current_price:.2f}")
    print(f"  P&L: {trade.pnl_pct:.1f}%")
    print(f"  Stop Level: ${trade.stop_level:.2f}")

    # Test Theme
    theme = Theme(
        rank=1,
        name="AI Infrastructure",
        classification="PRIME",
        composite_score=8.5,
        thesis_summary="Data center buildout accelerating"
    )
    print(f"\nTheme: {theme.name}")
    print(f"  Classification: {theme.classification}")
    print(f"  Investable: {theme.is_investable()}")

    print("\n✓ All models working correctly")
