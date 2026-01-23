#!/usr/bin/env python3
"""
DATA MODELS - Unified Dataclass Definitions
============================================

Central repository for all dataclasses used across the codebase.
Provides inheritance hierarchies and consistent field naming.

Usage:
    from src.common.data_models import (
        Stock, Trade, Theme, SellSignal,
        GatekeeperResult, DDResult, TweetContent,
        TradeStatus, GateDecision, ThemeClassification
    )
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional, Any

from .config import TRAILING_STOP_PCT, STOP_WARNING_PCT, BETA_THRESHOLD, BANKER_TIER3


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
    PRIME = "PRIME"           # Highest conviction (score >= 7.5)
    INVESTABLE = "INVESTABLE" # Good opportunities (score >= 6.0)
    SELECTIVE = "SELECTIVE"   # Mixed signals (score >= 4.5)
    AVOID = "AVOID"           # Stay away (score < 4.5)


class ThemeFit(Enum):
    """Theme fit assessment for stocks."""
    STRONG = "STRONG FIT"
    GOOD = "GOOD FIT"
    MODERATE = "MODERATE FIT"
    POOR = "POOR FIT"


class ThemeType(Enum):
    """Theme type classification."""
    TREND = "TREND"           # Secular growth with strong momentum
    BOTTLENECK = "BOTTLENECK" # Supply/capacity constraints
    CONTRARIAN = "CONTRARIAN" # Oversold/overlooked with reversal catalyst


class RedFlagLevel(Enum):
    """Red flag severity levels."""
    CLEAN = "CLEAN"
    MINOR = "MINOR"
    SEVERE = "SEVERE"


# ═══════════════════════════════════════════════════════════════════════════════
# BASE CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class BaseResult:
    """Base class for analysis results with common fields."""
    ticker: str
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
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
    4. Due Diligence (dd_verdict, dd_conviction, dd_summary)

    Example:
        stock = Stock(symbol="AAPL", price=150.0, beta=1.8, banker=65.5)
        if stock.passes_technical():
            # Proceed to thematic analysis
    """
    # ─────────────────────────────────────────────────────────────────────────
    # Core Identity
    # ─────────────────────────────────────────────────────────────────────────
    symbol: str
    price: float = 0.0

    # ─────────────────────────────────────────────────────────────────────────
    # Technical Indicators (Step 3-4)
    # ─────────────────────────────────────────────────────────────────────────
    beta: float = 0.0
    banker: float = 0.0
    bos_bullish: bool = False
    bos_bearish: bool = False
    bos_debug: Dict = field(default_factory=dict)
    return_20d: float = 0.0
    momentum_4w: float = 0.0
    tier: str = ""  # TIER1, TIER2, TIER3

    # ─────────────────────────────────────────────────────────────────────────
    # Thematic Analyzer Fields (Step 5)
    # ─────────────────────────────────────────────────────────────────────────
    theme: str = ""
    theme_score: float = 0.0
    pure_play_score: int = 0  # 0-100%
    theme_verdict: str = ""   # STRONG FIT, GOOD FIT, MODERATE FIT, POOR FIT

    # ─────────────────────────────────────────────────────────────────────────
    # Gatekeeper Fields (Step 6)
    # ─────────────────────────────────────────────────────────────────────────
    final_decision: str = ""  # PASS, CAUTION, FAIL
    conviction: int = 0       # 1-5
    catalyst_summary: str = ""
    red_flag_level: str = ""  # CLEAN, MINOR, SEVERE
    action: str = ""          # Recommended action
    bullish_factors: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)
    reasoning: str = ""

    # ─────────────────────────────────────────────────────────────────────────
    # Due Diligence Fields (Optional)
    # ─────────────────────────────────────────────────────────────────────────
    dd_verdict: str = ""
    dd_conviction: int = 0
    dd_summary: str = ""

    def passes_technical(self) -> bool:
        """
        Check if stock passes technical gate.

        Criteria: Weekly BoS Up + Beta >= 1.5 + Banker >= 55
        """
        return (
            self.bos_bullish and
            self.beta >= BETA_THRESHOLD and
            self.banker >= BANKER_TIER3
        )

    def passes_theme(self) -> bool:
        """Check if stock passes theme gate (STRONG or GOOD fit)."""
        return self.theme_verdict in [ThemeFit.STRONG.value, ThemeFit.GOOD.value]

    def is_tradeable(self) -> bool:
        """Check if stock is ready to trade (PASS decision)."""
        return self.final_decision == GateDecision.PASS.value

    def get_tier(self) -> str:
        """Determine tier based on Banker value."""
        if self.banker >= 70:
            return "TIER1"
        elif self.banker >= 60:
            return "TIER2"
        elif self.banker >= 55:
            return "TIER3"
        return ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════
# TRADE DATA
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Trade:
    """
    Represents a trade (open or closed) in the portfolio.

    Stored fields are persisted to CSV.
    Calculated fields are computed on load.

    Example:
        trade = Trade.from_stock(stock)
        trade.calculate_metrics(current_price=165.00)
        print(f"P&L: {trade.pnl_pct:.1f}%")
    """
    # ─────────────────────────────────────────────────────────────────────────
    # Stored Fields (in CSV)
    # ─────────────────────────────────────────────────────────────────────────
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

    # ─────────────────────────────────────────────────────────────────────────
    # Calculated Fields (not stored)
    # ─────────────────────────────────────────────────────────────────────────
    current_price: float = 0.0
    pnl_pct: float = 0.0
    pnl_usd: float = 0.0
    stop_level: float = 0.0
    days_held: int = 0
    distance_to_stop_pct: float = 0.0
    stop_alert: bool = False

    def __post_init__(self):
        """Initialize defaults after creation."""
        if not self.entry_date:
            self.entry_date = datetime.now().strftime("%Y-%m-%d")
        if self.highest_close == 0 and self.entry_price > 0:
            self.highest_close = self.entry_price

    def calculate_metrics(
        self,
        current_price: Optional[float] = None,
        stop_pct: float = None,
        warning_pct: float = None
    ) -> None:
        """
        Calculate all derived metrics.

        Args:
            current_price: Current market price (optional)
            stop_pct: Trailing stop percentage (default from config)
            warning_pct: Stop warning threshold (default from config)
        """
        stop_pct = stop_pct or TRAILING_STOP_PCT
        warning_pct = warning_pct or STOP_WARNING_PCT

        if current_price is not None:
            self.current_price = current_price

            # Update highest close for open positions
            if self.status == TradeStatus.OPEN.value and current_price > self.highest_close:
                self.highest_close = current_price

        # Use exit price for closed trades, current price for open
        price_for_calc = self.exit_price if self.status != TradeStatus.OPEN.value else self.current_price

        if self.entry_price > 0 and price_for_calc > 0:
            self.pnl_pct = ((price_for_calc / self.entry_price) - 1) * 100
            self.pnl_usd = (price_for_calc - self.entry_price) * 100  # Assumes 100 shares

        # Stop level
        if self.highest_close > 0:
            self.stop_level = self.highest_close * (1 - stop_pct / 100)

        # Distance to stop
        if self.status == TradeStatus.OPEN.value and self.current_price > 0 and self.stop_level > 0:
            self.distance_to_stop_pct = ((self.current_price - self.stop_level) / self.current_price) * 100
            self.stop_alert = self.distance_to_stop_pct <= warning_pct

        # Days held
        self._calculate_days_held()

    def _calculate_days_held(self) -> None:
        """Calculate days held from entry date."""
        if self.entry_date:
            try:
                entry = datetime.strptime(self.entry_date, "%Y-%m-%d")
                if self.status == TradeStatus.OPEN.value:
                    self.days_held = (datetime.now() - entry).days
                elif self.exit_date:
                    exit_dt = datetime.strptime(self.exit_date, "%Y-%m-%d")
                    self.days_held = (exit_dt - entry).days
            except ValueError:
                pass

    def to_csv_row(self) -> Dict[str, str]:
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
    def from_csv_row(cls, row: Dict[str, str]) -> 'Trade':
        """Create Trade from CSV row."""
        return cls(
            ticker=row.get('ticker', '').upper(),
            status=row.get('status', 'OPEN'),
            entry_date=row.get('entry_date', ''),
            entry_price=safe_float(row.get('entry_price')),
            exit_date=row.get('exit_date', ''),
            exit_price=safe_float(row.get('exit_price')),
            highest_close=safe_float(row.get('highest_close')),
            theme=row.get('theme', ''),
            tier=row.get('tier', ''),
            signal_type=row.get('signal_type', 'PASS'),
            conviction=safe_int(row.get('conviction')),
            notes=row.get('notes', '')
        )

    @classmethod
    def from_stock(cls, stock: Stock) -> 'Trade':
        """Create Trade from Stock object."""
        return cls(
            ticker=stock.symbol,
            status=TradeStatus.OPEN.value,
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

    Example:
        theme = Theme(name="AI Infrastructure", classification="PRIME", composite_score=8.5)
        if theme.is_investable():
            # Theme is PRIME or INVESTABLE
    """
    rank: int = 0
    name: str = ""
    classification: str = "INVESTABLE"  # PRIME, INVESTABLE, SELECTIVE, AVOID
    theme_type: str = "TREND"           # TREND, BOTTLENECK, CONTRARIAN
    composite_score: float = 0.0        # 0-10 scale

    # ─────────────────────────────────────────────────────────────────────────
    # Component Scores
    # ─────────────────────────────────────────────────────────────────────────
    catalyst_score: float = 0.0
    momentum_score: float = 0.0
    crowding_score: float = 0.0
    runway_score: float = 0.0

    # ─────────────────────────────────────────────────────────────────────────
    # Details
    # ─────────────────────────────────────────────────────────────────────────
    thesis_summary: str = ""
    key_catalysts: List[str] = field(default_factory=list)
    primary_etfs: List[str] = field(default_factory=list)
    crowding_indicator: str = "Moderate"  # Low, Moderate, High

    def is_investable(self) -> bool:
        """Check if theme is worth investing in (PRIME or INVESTABLE)."""
        return self.classification in [
            ThemeClassification.PRIME.value,
            ThemeClassification.INVESTABLE.value
        ]

    def is_prime(self) -> bool:
        """Check if theme is highest conviction."""
        return self.classification == ThemeClassification.PRIME.value

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════
# ANALYSIS RESULTS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class GatekeeperResult(BaseAnalysisResult):
    """
    Result from the Gatekeeper analysis gate.

    Example:
        result = GatekeeperResult(
            ticker="AAPL",
            decision="PASS",
            conviction=4,
            catalyst_summary="Earnings Feb 15"
        )
    """
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
        return self.decision == GateDecision.PASS.value


@dataclass
class DDResult(BaseAnalysisResult):
    """
    Result from automated due diligence analysis.

    Example:
        result = DDResult(
            ticker="AAPL",
            dd_verdict="STRONG BUY",
            dd_conviction=8,
            dd_key_catalyst="Product launch Q2"
        )
    """
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
    """
    Signal to exit a position.

    Example:
        signal = SellSignal(
            symbol="AAPL",
            price=145.00,
            reason="Weekly BoS Down",
            entry_price=150.00,
            pnl_pct=-3.3
        )
    """
    symbol: str
    price: float
    reason: str           # "Weekly BoS Down" or "Trailing Stop Hit"
    entry_price: float
    highest_close: float
    pnl_pct: float
    action: str = ""      # Recommended action

    def to_dict(self) -> Dict[str, Any]:
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

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'TweetContent':
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
    slot: int = 0                    # 1-5
    category: str = ""               # theme_hot, buy_signal, etc.
    prompt_text: str = ""            # Full prompt for Grok
    ticker: str = ""                 # Primary ticker (if applicable)
    visual_suggestion: str = ""      # Chart/image suggestion

    def to_dict(self) -> Dict[str, Any]:
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

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def safe_float(value: Any, default: float = 0.0) -> float:
    """
    Safely convert a value to float.

    Handles strings like 'N/A', '19.1%', commas, etc.

    Args:
        value: Value to convert
        default: Default if conversion fails

    Returns:
        Float value or default
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
    """
    Safely convert a value to int.

    Args:
        value: Value to convert
        default: Default if conversion fails

    Returns:
        Int value or default
    """
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
    print(f"\n  Stock: {stock.symbol}")
    print(f"    Passes technical: {stock.passes_technical()}")
    print(f"    Passes theme: {stock.passes_theme()}")
    print(f"    Is tradeable: {stock.is_tradeable()}")

    # Test Trade
    trade = Trade.from_stock(stock)
    trade.calculate_metrics(current_price=165.00)
    print(f"\n  Trade: {trade.ticker}")
    print(f"    Entry: ${trade.entry_price:.2f}")
    print(f"    Current: ${trade.current_price:.2f}")
    print(f"    P&L: {trade.pnl_pct:.1f}%")
    print(f"    Stop Level: ${trade.stop_level:.2f}")

    # Test Theme
    theme = Theme(
        rank=1,
        name="AI Infrastructure",
        classification="PRIME",
        composite_score=8.5,
        thesis_summary="Data center buildout accelerating"
    )
    print(f"\n  Theme: {theme.name}")
    print(f"    Classification: {theme.classification}")
    print(f"    Investable: {theme.is_investable()}")

    # Test utility functions
    print(f"\n  safe_float('19.5%'): {safe_float('19.5%')}")
    print(f"  safe_float('N/A'): {safe_float('N/A')}")
    print(f"  safe_int('42'): {safe_int('42')}")

    print("\n  ✓ All models working correctly")
