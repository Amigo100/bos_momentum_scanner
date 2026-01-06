#!/usr/bin/env python3
"""
Thematic Investment Analyzer
============================
A two-step analysis system that:
1. Identifies top investable themes in the current market
2. Maps user tickers to those themes and scores upside potential

Features:
- Claude API with web search for real-time data
- Comprehensive terminal logging
- Trade log CSV for retrospective analysis
- Email notifications
- Rate limit handling with exponential backoff
"""

import os
import sys
import json
import time
import csv
import smtplib
import logging
from datetime import datetime, timedelta
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
import traceback

# Third-party imports
try:
    import anthropic
except ImportError:
    print("ERROR: anthropic package not installed. Run: pip install anthropic --break-system-packages")
    sys.exit(1)

try:
    import yfinance as yf
except ImportError:
    print("ERROR: yfinance package not installed. Run: pip install yfinance --break-system-packages")
    sys.exit(1)


# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class Config:
    """Configuration settings for the analyzer"""
    
    # API Settings
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    model: str = "claude-opus-4-5-20251101"
    max_tokens: int = 16000  # Increased for Opus 4.5 verbose output
    
    # Rate Limiting
    max_retries: int = 8  # Increased from 5
    base_delay: float = 5.0  # Increased from 2.0
    max_delay: float = 180.0  # Increased from 120
    rate_limit_cooldown: float = 90.0  # Increased from 60
    inter_step_delay: float = 30.0  # NEW: Delay between Step 1 and Step 2
    min_request_interval: float = 3.0  # NEW: Minimum seconds between any requests
    
    # Web Search Settings
    # WARNING: Web search costs ~$10/1000 searches. Each API call can make 5-10 searches.
    # Default OFF to control costs. Enable only when you need current news/prices.
    use_web_search: bool = False  # Set True to enable web search (adds ~$0.50-2.00/run)
    
    # File Paths
    tickers_file: str = "LLM_tickers.txt"
    trade_log_file: str = "trade_log.csv"
    analysis_output_dir: str = "analysis_outputs"
    
    # Email Settings (set via environment variables)
    smtp_server: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    email_sender: str = os.getenv("EMAIL_SENDER", "")
    email_password: str = os.getenv("EMAIL_PASSWORD", "")
    email_recipients: List[str] = field(default_factory=lambda: 
        os.getenv("EMAIL_RECIPIENTS", "").split(",") if os.getenv("EMAIL_RECIPIENTS") else [])
    
    # Analysis Settings
    max_tickers_per_batch: int = 5  # Reduced from 10 to be safer with rate limits
    theme_count: int = 5  # Number of top themes to identify
    conservative_rate_limiting: bool = True  # If True, use longer delays


# ============================================================================
# LOGGING SETUP
# ============================================================================

class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for terminal output"""
    
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'
    }
    
    SYMBOLS = {
        'DEBUG': '🔍',
        'INFO': '✓',
        'WARNING': '⚠',
        'ERROR': '✗',
        'CRITICAL': '💀'
    }
    
    def format(self, record):
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        symbol = self.SYMBOLS.get(record.levelname, '')
        reset = self.COLORS['RESET']
        
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
        
        # Build message
        formatted = f"{color}[{timestamp}] {symbol} {record.levelname:<8}{reset} | {record.getMessage()}"
        
        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"
        
        return formatted


def setup_logging(verbose: bool = True) -> logging.Logger:
    """Setup comprehensive logging"""
    
    logger = logging.getLogger("ThematicAnalyzer")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    
    # Clear existing handlers
    logger.handlers = []
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(ColoredFormatter())
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.addHandler(console_handler)
    
    # File handler for persistent logs
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s'
    ))
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    
    return logger


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class Theme:
    """Represents an investable theme with catalyst-focused analysis"""
    rank: int
    name: str
    primary_etfs: List[str]
    composite_score: float
    factor_scores: Dict[str, float]
    key_catalysts: List[str]
    primary_risks: List[str]
    thesis_summary: str = ""
    crowding_indicator: str = "Moderate"  # Low/Moderate/High
    why_now: str = ""
    
    # Theme type classification (NEW - from Gemini insights)
    theme_type: str = "TREND"  # TREND / BOTTLENECK / CONTRARIAN
    theme_type_rationale: str = ""  # Why this classification
    relative_strength_vs_spy: str = ""  # Outperforming / In-line / Underperforming
    
    # Classification fields (derived from composite_score)
    classification: str = "INVESTABLE"  # PRIME / INVESTABLE / SELECTIVE / AVOID
    position_sizing_recommendation: str = "FULL"  # FULL / REDUCED / MINIMAL / NONE
    classification_rationale: str = ""
    
    # Factor analysis details (from new prompt structure)
    catalyst_score: float = 0.0
    catalyst_detail: str = ""
    momentum_score: float = 0.0
    momentum_detail: str = ""
    crowding_score: float = 0.0
    crowding_detail: str = ""
    runway_score: float = 0.0
    runway_detail: str = ""
    
    # Backwards compatibility fields (may be populated or not)
    cycle_stage: str = ""
    fundamental_cycle_score: float = 0.0
    
    def calculate_classification(self):
        """Calculate classification based on composite_score"""
        score = self.composite_score
        
        if score >= 7.5:
            self.classification = "PRIME"
            self.position_sizing_recommendation = "FULL"
            self.classification_rationale = f"High conviction theme ({score:.1f}/10). Strong catalysts + momentum + runway."
        elif score >= 6.0:
            self.classification = "INVESTABLE"
            self.position_sizing_recommendation = "FULL"
            self.classification_rationale = f"Good opportunity ({score:.1f}/10). Solid fundamentals, standard position sizing."
        elif score >= 4.5:
            self.classification = "SELECTIVE"
            self.position_sizing_recommendation = "REDUCED"
            self.classification_rationale = f"Mixed signals ({score:.1f}/10). Only best stocks in this theme."
        else:
            self.classification = "AVOID"
            self.position_sizing_recommendation = "NONE"
            self.classification_rationale = f"Weak setup ({score:.1f}/10). Fading momentum or overcrowded."
    
    def is_investable(self) -> bool:
        """Returns True if theme is PRIME or INVESTABLE"""
        return self.classification in ["PRIME", "INVESTABLE"]
    
    def is_bottleneck_or_contrarian(self) -> bool:
        """Returns True if theme is a second-order or contrarian play (preferred)"""
        return self.theme_type in ["BOTTLENECK", "CONTRARIAN"]
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class TickerAnalysis:
    """Analysis result for a single ticker"""
    ticker: str
    company_name: str
    primary_theme: Optional[str]
    theme_score: Optional[float]
    theme_rank: Optional[int]
    secondary_themes: List[str]
    pure_play_score: int
    market_position: str
    upside_score: float
    upside_rationale: str
    verdict: str
    action: str
    valuation_metric: str
    key_catalysts: List[str]
    risks: List[Dict[str, str]]
    current_price: Optional[float] = None
    sector: Optional[str] = None
    
    # Theme classification fields
    theme_classification: str = "INVESTABLE"  # PRIME / INVESTABLE / SELECTIVE / AVOID
    conviction: str = "Medium"  # High / Medium / Low
    
    # Stock-specific scores (from new prompt)
    theme_fit_score: float = 0.0
    theme_fit_pct: float = 0.0  # % of business tied to theme
    company_position_score: float = 0.0
    company_position: str = ""  # Leader/Challenger/Niche/Laggard
    stock_setup_score: float = 0.0
    stock_setup: str = ""  # Ideal/Good/Fair/Poor
    
    # Risk factors
    earnings_date: str = ""
    earnings_risk: bool = False
    short_interest: str = ""
    red_flags: List[str] = None
    
    def __post_init__(self):
        if self.red_flags is None:
            self.red_flags = []
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def passes_gate(self) -> bool:
        """
        Check if ticker passes the theme gate.
        
        Criteria:
        - Verdict must be STRONG FIT or GOOD FIT
        - Theme must be PRIME or INVESTABLE (not SELECTIVE or AVOID)
        """
        verdict_ok = self.verdict in ["STRONG FIT", "GOOD FIT"]
        theme_ok = self.theme_classification in ["PRIME", "INVESTABLE"]
        return verdict_ok and theme_ok
    
    def passes_gate_relaxed(self) -> bool:
        """
        Relaxed gate - also allows SELECTIVE themes with STRONG FIT.
        Use for broader screening.
        """
        if self.verdict == "STRONG FIT":
            return self.theme_classification in ["PRIME", "INVESTABLE", "SELECTIVE"]
        elif self.verdict == "GOOD FIT":
            return self.theme_classification in ["PRIME", "INVESTABLE"]
        return False
    
    def get_conviction_level(self) -> str:
        """Calculate conviction based on scores"""
        if self.verdict == "STRONG FIT" and self.theme_classification == "PRIME":
            return "High"
        elif self.verdict == "STRONG FIT" and self.theme_classification == "INVESTABLE":
            return "High"
        elif self.verdict == "GOOD FIT" and self.theme_classification in ["PRIME", "INVESTABLE"]:
            return "Medium"
        else:
            return "Low"


@dataclass
class AnalysisResult:
    """Complete analysis result"""
    timestamp: str
    themes: List[Theme]
    ticker_analyses: List[TickerAnalysis]
    summary: Dict[str, Any]
    
    def get_passing_tickers(self) -> List[TickerAnalysis]:
        """Get tickers that pass the theme gate"""
        return [t for t in self.ticker_analyses if t.passes_gate()]


# ============================================================================
# RATE LIMITER
# ============================================================================

class RateLimiter:
    """Handles API rate limiting with exponential backoff"""
    
    def __init__(self, config: Config, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.request_count = 0
        self.last_request_time = 0
        self.consecutive_rate_limits = 0
        self.total_rate_limits = 0  # Track total rate limits hit
        self.last_success_time = 0  # Track when last successful request completed
    
    def wait_if_needed(self):
        """Wait if we're making requests too quickly"""
        elapsed = time.time() - self.last_request_time
        min_interval = self.config.min_request_interval
        
        if elapsed < min_interval:
            sleep_time = min_interval - elapsed
            self.logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s between requests")
            time.sleep(sleep_time)
    
    def handle_rate_limit(self, attempt: int) -> float:
        """Calculate delay after rate limit hit"""
        self.consecutive_rate_limits += 1
        self.total_rate_limits += 1
        
        # Exponential backoff with jitter
        delay = min(
            self.config.base_delay * (2 ** attempt) + (time.time() % 1),
            self.config.max_delay
        )
        
        # Add extra cooldown if we've hit multiple rate limits
        if self.consecutive_rate_limits >= 3:
            delay += self.config.rate_limit_cooldown
            self.logger.warning(
                f"Multiple rate limits hit ({self.consecutive_rate_limits}). "
                f"Adding {self.config.rate_limit_cooldown}s cooldown"
            )
        
        return delay
    
    def record_success(self):
        """Record successful request"""
        self.last_request_time = time.time()
        self.last_success_time = time.time()
        self.request_count += 1
        self.consecutive_rate_limits = 0
    
    def wait_for_inter_step_cooldown(self, step_name: str):
        """Wait between major steps to avoid rate limiting"""
        delay = self.config.inter_step_delay
        
        # If we hit any rate limits, add extra buffer
        if self.total_rate_limits > 0:
            delay += 30.0
            self.logger.info(f"Adding extra buffer due to previous rate limits")
        
        self.logger.info(f"Cooling down {delay:.0f}s before {step_name}...")
        
        # Show countdown for long waits
        if delay > 10:
            for remaining in range(int(delay), 0, -10):
                self.logger.info(f"  {remaining}s remaining...")
                time.sleep(min(10, remaining))
        else:
            time.sleep(delay)
    
    def get_stats(self) -> Dict:
        """Get rate limiter statistics"""
        return {
            "total_requests": self.request_count,
            "consecutive_rate_limits": self.consecutive_rate_limits,
            "total_rate_limits": self.total_rate_limits
        }


# ============================================================================
# PROMPTS
# ============================================================================

STEP_1_PROMPT = """
## IDENTIFY TOP 5-7 INVESTABLE THEMES (6-12 Month Horizon)

You are identifying themes with the **highest probability of strong returns over the next 6-12 months**.

### ═══════════════════════════════════════════════════════════════════════════
### WHAT MAKES A THEME INVESTABLE (NOT just "early cycle")
### ═══════════════════════════════════════════════════════════════════════════

A theme is INVESTABLE if it has:

1. **ACTIVE CATALYSTS** - Specific events/trends driving the theme forward NOW
2. **POSITIVE MOMENTUM** - Theme is gaining strength, not fading
3. **NOT OVERCROWDED** - Room for new money to enter
4. **RUNWAY REMAINING** - Growth story not exhausted

**IMPORTANT:** A mid-cycle theme with strong catalysts can outperform an early-cycle theme without catalysts. Focus on WHAT'S WORKING NOW, not theoretical cycle positioning.

### ═══════════════════════════════════════════════════════════════════════════
### REQUIRED SEARCHES (Do these EXACTLY for consistency)
### ═══════════════════════════════════════════════════════════════════════════

**STEP A: Discover What's Working Now**
Search these EXACT queries:
1. "best performing sector ETFs 2025"
2. "investment themes working 2025"
3. "where is smart money flowing 2025"
4. "sectors with positive earnings revisions 2025"

From Step A, identify the TOP 3-5 TRENDS currently driving markets.

**STEP B: Second-Order Derivative Search (CRITICAL - Find the Bottlenecks)**
The best 6-12 month returns come from SOLVING bottlenecks, not chasing trends.

For EACH major trend identified in Step A, dynamically search:
1. "[trend] bottlenecks 2025" 
2. "[trend] supply constraints"
3. "[trend] infrastructure limitations"
4. "what limits [trend] growth"

Example searches based on Step A findings:
- If AI is hot → search "AI infrastructure bottlenecks 2025", "AI power constraints", "AI cooling limitations"
- If Defense is hot → search "defense supply chain bottlenecks", "defense manufacturing constraints"
- If EVs are hot → search "EV battery supply constraints", "EV charging infrastructure limitations"

Also search these general bottleneck queries:
1. "supply chain constraints 2025" (what's in shortage?)
2. "infrastructure bottlenecks 2025"
3. "pick and shovel plays 2025"

**KEY INSIGHT:** For every first-order trend, ask "What INPUT is constrained?"
- AI trend → Power? Cooling? Cabling? Chips?
- Defense trend → Manufacturing? Cybersecurity? Rare materials?
- EV trend → Batteries? Copper? Charging infrastructure?
- Biotech trend → Manufacturing capacity? Regulatory bandwidth?

The bottleneck is often MORE investable than the trend itself because it's less crowded.

**STEP C: Contrarian Hunt (Improving Fundamentals, Lagging Sentiment)**
Search these EXACT queries:
1. "underperforming sectors positive earnings revisions 2025"
2. "hated sectors improving fundamentals 2025"
3. "sectors with relative strength divergence 2025"

Look for: Underperformed S&P for 12-24 months BUT showing recent accumulation or earnings beats.

**STEP D: Identify Emerging/Accelerating Themes**
Search these EXACT queries:
1. "emerging investment themes 2025"
2. "accelerating trends 2025 investing"
3. "sectors gaining momentum 2025"

**STEP E: Check for Themes to AVOID**
Search these EXACT queries:
1. "overcrowded trades 2025"
2. "sectors losing momentum 2025"
3. "investment themes to avoid 2025"

### ═══════════════════════════════════════════════════════════════════════════
### THEME EVALUATION FRAMEWORK (Simplified for Consistency)
### ═══════════════════════════════════════════════════════════════════════════

For each potential theme, evaluate these 4 criteria:

## 1. CATALYST STRENGTH (40% weight) - Most Important

**What to search:** "[theme] catalysts 2025" and "[theme] upcoming events"

| Rating | Criteria | Score |
|--------|----------|-------|
| STRONG | Multiple specific catalysts in next 6-12 months (earnings, product launches, policy, capex announcements) | 8-10 |
| MODERATE | 1-2 catalysts or general tailwinds | 5-7 |
| WEAK | No specific catalysts, relying on continuation | 2-4 |

**Examples of STRONG catalysts:**
- AI: Hyperscaler capex announcements, new chip launches, enterprise adoption metrics
- Nuclear: New reactor approvals, utility contracts, policy support bills
- Defense: Budget increases, contract awards, geopolitical events

## 2. MOMENTUM DIRECTION (25% weight)

**What to search:** "[theme] ETF performance" and check 1-month, 3-month returns

| Rating | Criteria | Score |
|--------|----------|-------|
| ACCELERATING | 3-month return > 1-month annualized (momentum building) | 8-10 |
| STEADY | Consistent positive returns, healthy trend | 6-7 |
| DECELERATING | Recent underperformance vs prior trend | 3-5 |
| NEGATIVE | Downtrend or sharp reversal | 1-2 |

**Key insight:** We want themes that are WORKING, not themes we hope will work.

## 3. CROWDING LEVEL (20% weight)

**What to search:** "[theme] crowded trade" and "[theme] fund flows"

| Rating | Criteria | Score |
|--------|----------|-------|
| LOW | Under-owned, skepticism remains, short interest elevated | 8-10 |
| MODERATE | Growing interest but not consensus | 5-7 |
| HIGH | Consensus long, magazine covers, record inflows | 2-4 |
| EXTREME | "Can't lose" mentality, retail FOMO | 1 |

**Warning signs of overcrowding:**
- Theme on mainstream magazine covers
- Record ETF inflows in past 3 months
- Universal analyst buy ratings
- "Everyone knows" the theme

## 4. RUNWAY REMAINING (15% weight)

**What to search:** "[theme] market penetration" and "[theme] growth projections"

| Rating | Criteria | Score |
|--------|----------|-------|
| LONG | <40% penetration OR multi-year capex cycle ahead | 8-10 |
| MEDIUM | 40-70% penetration with continued growth | 5-7 |
| SHORT | >70% penetration, mature market | 2-4 |

### ═══════════════════════════════════════════════════════════════════════════
### INVESTABILITY CLASSIFICATION
### ═══════════════════════════════════════════════════════════════════════════

Calculate weighted score:
**COMPOSITE = (Catalyst × 0.40) + (Momentum × 0.25) + (Crowding × 0.20) + (Runway × 0.15)**

| Composite Score | Classification | Action |
|-----------------|----------------|--------|
| 7.5+ | PRIME | High conviction - prioritize stocks in this theme |
| 6.0 - 7.4 | INVESTABLE | Good opportunity - standard position sizing |
| 4.5 - 5.9 | SELECTIVE | Caution - only best stocks in theme |
| < 4.5 | AVOID | Do not invest - theme is fading or overcrowded |

### ═══════════════════════════════════════════════════════════════════════════
### EXPLICIT REJECTION CRITERIA
### ═══════════════════════════════════════════════════════════════════════════

**AUTOMATICALLY REJECT themes that have ANY of these:**

1. **FADING MOMENTUM**: ETF down >10% from recent highs with no catalyst for reversal
2. **EXTREME CROWDING**: On magazine covers + record fund inflows + universal bullishness
3. **CATALYST EXHAUSTION**: Major catalyst already passed (e.g., election play post-election)
4. **STRUCTURAL HEADWINDS**: Regulatory threats, technological disruption, demand destruction

### ═══════════════════════════════════════════════════════════════════════════
### THEME TYPE CLASSIFICATION
### ═══════════════════════════════════════════════════════════════════════════

Classify each theme by HOW you found it:

| Type | Description | Risk Profile | Example |
|------|-------------|--------------|---------|
| **TREND** | First-order, consensus theme | Higher crowding risk | "AI Chips" |
| **BOTTLENECK** | Second-order, solves constraint | Lower crowding, higher asymmetry | "Grid Infrastructure for AI" |
| **CONTRARIAN** | Underperformed but improving | Highest asymmetry if timing is right | "Emerging Markets" |

**Preference order for 6-12 month returns:**
1. BOTTLENECK themes (underappreciated, less crowded)
2. CONTRARIAN themes (improving fundamentals, lagging sentiment) 
3. TREND themes (only if crowding is still low)

**BOTTLENECK example:**
- First-order trend: "AI data centers are growing"
- Second-order bottleneck: "Power grid can't supply enough electricity"
- Investment theme: "Grid Modernization / Transformers / Nuclear SMRs"

**CONTRARIAN example:**
- Observation: "Sector X has underperformed S&P by 30% over 18 months"
- Improving signal: "But earnings revisions turned positive last 60 days"
- Investment thesis: "Fundamentals improving, sentiment hasn't caught up"

### ═══════════════════════════════════════════════════════════════════════════
### OUTPUT FORMAT
### ═══════════════════════════════════════════════════════════════════════════

Respond with ONLY valid JSON (no markdown, no explanation):

{
  "analysis_date": "YYYY-MM-DD",
  "market_context": "Brief description of current market environment",
  "trends_identified_step_a": ["List the 3-5 hot trends found in Step A"],
  "searches_performed": ["List ALL searches performed, including dynamic Step B bottleneck searches"],
  
  "top_themes": [
    {
      "rank": 1,
      "theme": "Specific Theme Name",
      "primary_etfs": ["ETF1", "ETF2"],
      
      "theme_type": "BOTTLENECK/TREND/CONTRARIAN",
      "theme_type_rationale": "Why this classification - e.g., 'Second-order play on AI power demand' or 'Improving fundamentals despite 18-month underperformance'",
      
      "catalyst_analysis": {
        "score": 8,
        "key_catalysts": [
          {"catalyst": "Specific event/trend", "timing": "Q1 2025", "impact": "High/Medium"}
        ],
        "catalyst_evidence": "What search revealed"
      },
      
      "momentum_analysis": {
        "score": 7,
        "etf_1m_return": "+X%",
        "etf_3m_return": "+Y%",
        "trend_direction": "Accelerating/Steady/Decelerating",
        "relative_strength_vs_spy": "Outperforming/In-line/Underperforming",
        "momentum_evidence": "What search revealed"
      },
      
      "crowding_analysis": {
        "score": 7,
        "crowding_level": "Low/Moderate/High",
        "warning_signs": ["Any warning signs found"],
        "crowding_evidence": "What search revealed"
      },
      
      "runway_analysis": {
        "score": 8,
        "penetration_estimate": "X% of addressable market",
        "growth_runway_years": 5,
        "runway_evidence": "What search revealed"
      },
      
      "composite_score": 7.6,
      "classification": "PRIME/INVESTABLE/SELECTIVE/AVOID",
      
      "investment_thesis": "2-3 sentence thesis for why this theme will outperform over next 6-12 months",
      "primary_risks": ["Risk 1", "Risk 2"],
      "what_would_change_view": "What would make you downgrade this theme"
    }
  ],
  
  "themes_rejected": [
    {
      "theme": "Theme Name",
      "rejection_reason": "Specific reason (fading momentum/overcrowded/catalyst exhaustion/headwinds)",
      "evidence": "What search showed"
    }
  ],
  
  "contrarian_watchlist": [
    {
      "theme": "Theme Name",
      "underperformance_period": "X months",
      "improving_signal": "What's improving (earnings revisions, relative strength divergence, etc.)",
      "trigger_to_upgrade": "What would make this investable"
    }
  ],
  
  "theme_watchlist": [
    {
      "theme": "Theme Name", 
      "current_issue": "Why not investable now",
      "trigger_to_upgrade": "What would make this investable"
    }
  ]
}

### ═══════════════════════════════════════════════════════════════════════════
### CONSISTENCY GUIDELINES
### ═══════════════════════════════════════════════════════════════════════════

To ensure consistent results across runs:

1. **Step A searches are EXACT** - Use the specified queries verbatim
2. **Step B searches are DYNAMIC** - Construct bottleneck searches based on trends found in Step A
3. **Score based on EVIDENCE from searches** - Not general knowledge
4. **Apply thresholds strictly** - If ETF is down 10%, momentum score is LOW
5. **Cite specific data points** - "SMH up 12% in past month" not "semiconductors doing well"
6. **Date-stamp your evidence** - Note when data is from

**Dynamic Search Example:**
- Step A finds: AI, Defense, Clean Energy are hot trends
- Step B then searches: "AI bottlenecks 2025", "AI power constraints", "defense supply chain constraints", "clean energy grid limitations", etc.

**Themes should NOT change dramatically week-to-week** unless:
- Major catalyst event occurs
- Significant price breakdown/breakout
- Fundamental shift in outlook (earnings, policy, etc.)

If a theme was INVESTABLE last week, it should remain INVESTABLE unless something specific changed.

**Bottleneck themes may shift** as:
- Original constraint gets solved (e.g., chip shortage eased)
- New constraints emerge (e.g., cooling becomes the new bottleneck)
- This is expected and reflects real market dynamics
"""

STEP_2_PROMPT_TEMPLATE = """
## MAP TICKERS TO THEMES & ASSESS FIT (6-12 Month Horizon)

Given the top themes identified, analyze how well each ticker fits and score its potential.

### TOP THEMES FROM STEP 1:
{themes_json}

### TICKERS TO ANALYZE:
{ticker_list}

### ═══════════════════════════════════════════════════════════════════════════
### TICKER EVALUATION FRAMEWORK
### ═══════════════════════════════════════════════════════════════════════════

For each ticker, determine:

## 1. THEME FIT (Does this stock benefit from the theme?)

**Search:** "[company] business segments" and "[company] revenue breakdown"

| Rating | Criteria | Score |
|--------|----------|-------|
| PURE PLAY | >70% of business directly tied to theme | 9-10 |
| STRONG | 50-70% exposure to theme | 7-8 |
| MODERATE | 30-50% exposure to theme | 5-6 |
| WEAK | <30% exposure, tangential at best | 1-4 |

## 2. COMPANY POSITION (Is this the RIGHT stock for the theme?)

**Search:** "[company] market share" and "[company] vs competitors"

| Rating | Criteria | Score |
|--------|----------|-------|
| LEADER | #1-2 market share, gaining share | 9-10 |
| STRONG CHALLENGER | Top 5, competitive position | 7-8 |
| NICHE | Specialized player, defensible niche | 5-6 |
| LAGGARD | Losing share, weak position | 1-4 |

## 3. STOCK SETUP (Is now a good time to buy?)

**Search:** "[ticker] stock news" and check recent price action

| Rating | Criteria | Score |
|--------|----------|-------|
| IDEAL | Breaking out, not extended, positive momentum | 9-10 |
| GOOD | Healthy uptrend, reasonable entry | 7-8 |
| FAIR | Consolidating, waiting for catalyst | 5-6 |
| POOR | Extended/overbought OR downtrend | 1-4 |

## 4. RISK ASSESSMENT

**Search:** "[company] risks" and "[ticker] short interest"

Identify:
- Upcoming earnings date (risk if within 2 weeks)
- Short interest level
- Any company-specific red flags

### ═══════════════════════════════════════════════════════════════════════════
### VERDICT CRITERIA
### ═══════════════════════════════════════════════════════════════════════════

| Theme Classification | Theme Fit Score | Company Position | Verdict |
|---------------------|-----------------|------------------|---------|
| PRIME | 7+ | Leader/Challenger | **STRONG FIT** |
| PRIME | 5-6 | Any | GOOD FIT |
| INVESTABLE | 7+ | Leader/Challenger | **STRONG FIT** |
| INVESTABLE | 5-6 | Leader/Challenger | GOOD FIT |
| INVESTABLE | 5-6 | Niche/Laggard | MODERATE FIT |
| SELECTIVE | 7+ | Leader only | GOOD FIT |
| SELECTIVE | Any other | Any | MODERATE FIT |
| AVOID | Any | Any | WEAK FIT |

**STRONG FIT** = High conviction, full position
**GOOD FIT** = Solid opportunity, standard position
**MODERATE FIT** = Lower conviction, reduced position or pass
**WEAK FIT** = Do not buy

### ═══════════════════════════════════════════════════════════════════════════
### OUTPUT FORMAT
### ═══════════════════════════════════════════════════════════════════════════

Respond with ONLY valid JSON (no markdown, no explanation):

{{
  "analysis_date": "YYYY-MM-DD",
  
  "ticker_analysis": [
    {{
      "ticker": "SYMBOL",
      "company_name": "Full Company Name",
      "current_price": 123.45,
      "sector": "Technology",
      
      "primary_theme": "Theme Name",
      "theme_classification": "PRIME/INVESTABLE/SELECTIVE/AVOID",
      
      "theme_fit": {{
        "score": 8,
        "exposure_pct": 75,
        "rationale": "Why this % exposure"
      }},
      
      "company_position": {{
        "score": 8,
        "position": "Leader/Challenger/Niche/Laggard",
        "rationale": "Market share and competitive position"
      }},
      
      "stock_setup": {{
        "score": 7,
        "setup": "Ideal/Good/Fair/Poor",
        "rationale": "Current technical/momentum assessment"
      }},
      
      "risk_factors": {{
        "earnings_date": "YYYY-MM-DD or Unknown",
        "earnings_risk": true/false,
        "short_interest": "X%",
        "red_flags": ["Any specific concerns"]
      }},
      
      "verdict": "STRONG FIT/GOOD FIT/MODERATE FIT/WEAK FIT",
      "verdict_rationale": "One sentence explaining verdict",
      
      "upside_score": 8.5,
      "action": "Buy/Accumulate/Hold/Avoid",
      "conviction": "High/Medium/Low"
    }}
  ],
  
  "summary": {{
    "strong_fits": ["TICKER1", "TICKER2"],
    "good_fits": ["TICKER3"],
    "moderate_fits": ["TICKER4"],
    "weak_fits": ["TICKER5"],
    "highest_conviction": {{
      "ticker": "TICKER1",
      "theme": "Theme Name",
      "rationale": "Why this is the top pick"
    }}
  }}
}}
"""


# ============================================================================
# MAIN ANALYZER CLASS
# ============================================================================

class ThematicAnalyzer:
    """Main analyzer class that orchestrates the two-step analysis"""
    
    def __init__(self, config: Optional[Config] = None, verbose: bool = True):
        self.config = config or Config()
        self.logger = setup_logging(verbose)
        self.rate_limiter = RateLimiter(self.config, self.logger)
        
        # Validate API key
        if not self.config.anthropic_api_key:
            self.logger.error("ANTHROPIC_API_KEY environment variable not set")
            raise ValueError("ANTHROPIC_API_KEY is required")
        
        self.client = anthropic.Anthropic(api_key=self.config.anthropic_api_key)
        
        # State
        self.themes: List[Theme] = []
        self.ticker_analyses: List[TickerAnalysis] = []
        
        self._print_banner()
    
    def _print_banner(self):
        """Print startup banner"""
        banner = """
╔══════════════════════════════════════════════════════════════════╗
║           THEMATIC INVESTMENT ANALYZER v2.0                      ║
║                                                                  ║
║   Step 1: Identify Top Themes with FUNDAMENTAL Cycle Analysis   ║
║   Step 2: Map Tickers to Themes & Score Upside                  ║
║                                                                  ║
║   🚀 Enhanced: 4-Factor Cycle Detection Framework               ║
║      • TAM Penetration (40%) - How much market left?            ║
║      • Capex Cycle (30%) - Are companies still investing?       ║
║      • Sentiment (20%) - Is everyone already in?                ║
║      • Valuation/Runway (10%) - Growth ahead vs price?          ║
╚══════════════════════════════════════════════════════════════════╝
        """
        print(banner)
        self.logger.info(f"Initialized with model: {self.config.model}")
        self.logger.info(f"Max retries: {self.config.max_retries}")
    
    def _call_api_with_retry(self, messages: List[Dict], description: str) -> str:
        """Call Claude API with retry logic and rate limiting"""
        
        for attempt in range(self.config.max_retries):
            try:
                self.rate_limiter.wait_if_needed()
                
                self.logger.info(f"API call: {description} (attempt {attempt + 1}/{self.config.max_retries})")
                
                # Build API call parameters
                api_params = {
                    "model": self.config.model,
                    "max_tokens": self.config.max_tokens,
                    "messages": messages
                }
                
                # Only add web search if enabled (costs ~$10/1000 searches)
                if self.config.use_web_search:
                    api_params["tools"] = [{
                        "type": "web_search_20250305",
                        "name": "web_search"
                    }]
                    self.logger.debug("Web search ENABLED for this call")
                
                response = self.client.messages.create(**api_params)
                
                self.rate_limiter.record_success()
                
                # Extract text content
                text_content = ""
                for block in response.content:
                    if hasattr(block, 'text'):
                        text_content += block.text
                
                self.logger.debug(f"Response received: {len(text_content)} chars")
                return text_content
                
            except anthropic.RateLimitError as e:
                # Try to extract retry-after from the error
                retry_after = None
                try:
                    # Check if headers are available
                    if hasattr(e, 'response') and e.response is not None:
                        retry_after = e.response.headers.get('retry-after')
                        if retry_after:
                            retry_after = float(retry_after)
                except:
                    pass
                
                if retry_after and retry_after > 0:
                    delay = retry_after + 5  # Add 5s buffer
                    self.logger.warning(f"Rate limit hit. Server says wait {retry_after}s. Waiting {delay:.1f}s...")
                else:
                    delay = self.rate_limiter.handle_rate_limit(attempt)
                    self.logger.warning(f"Rate limit hit. Waiting {delay:.1f}s before retry...")
                
                time.sleep(delay)
                
            except anthropic.APIConnectionError as e:
                delay = self.config.base_delay * (2 ** attempt)
                self.logger.warning(f"Connection error: {e}. Retrying in {delay:.1f}s...")
                time.sleep(delay)
            
            except anthropic.BadRequestError as e:
                error_str = str(e).lower()
                # Check for billing/credit errors - fail immediately
                if "credit balance" in error_str or "billing" in error_str:
                    self.logger.error(f"BILLING ERROR: {e}")
                    raise RuntimeError(f"BILLING_ERROR: Your API credit balance is too low. Please add credits at https://console.anthropic.com/settings/billing")
                # Other bad request errors - don't retry
                self.logger.error(f"Bad request error: {e}")
                raise
                
            except anthropic.APIStatusError as e:
                error_str = str(e).lower()
                
                # Check for billing/credit errors - fail immediately
                if "credit balance" in error_str or "billing" in error_str:
                    self.logger.error(f"BILLING ERROR: {e}")
                    raise RuntimeError(f"BILLING_ERROR: Your API credit balance is too low. Please add credits at https://console.anthropic.com/settings/billing")
                
                if e.status_code >= 500:
                    delay = self.config.base_delay * (2 ** attempt)
                    self.logger.warning(f"Server error ({e.status_code}). Retrying in {delay:.1f}s...")
                    time.sleep(delay)
                elif e.status_code == 529:  # Overloaded
                    delay = self.config.rate_limit_cooldown
                    self.logger.warning(f"API overloaded. Waiting {delay:.1f}s...")
                    time.sleep(delay)
                else:
                    self.logger.error(f"API error: {e}")
                    raise
        
        raise Exception(f"Failed after {self.config.max_retries} attempts: {description}")
    
    def _extract_json(self, text: str) -> Dict:
        """Extract JSON from response text - handles Opus verbose output"""
        import re

        text = text.strip()

        # Expected keys that indicate this is the main response object
        expected_outer_keys = {"top_themes", "themes_rejected", "analysis_date", "market_context"}
        expected_ticker_keys = {"ticker_analyses", "analyses", "tickers"}

        def has_expected_structure(obj):
            """Check if JSON object has expected response structure"""
            if not isinstance(obj, dict):
                return False
            keys = set(obj.keys())
            # Check for theme response structure
            if keys & expected_outer_keys:
                return True
            # Check for ticker analysis response structure
            if keys & expected_ticker_keys:
                return True
            return False

        # Strategy 1: Try to find JSON in markdown code blocks first
        # Use greedy match to get the full JSON block, not just until first }
        json_block_pattern = r'```(?:json)?\s*(\{[\s\S]+\})\s*```'
        matches = re.findall(json_block_pattern, text)
        for match in matches:
            # The match might include extra content, so find valid JSON within it
            try:
                parsed = json.loads(match)
                if has_expected_structure(parsed):
                    return parsed
            except json.JSONDecodeError:
                # Try to find valid JSON within the match using brace counting
                brace_count = 0
                in_string = False
                escape_next = False
                start_idx = match.find('{')
                if start_idx == -1:
                    continue
                for i, char in enumerate(match[start_idx:], start_idx):
                    if escape_next:
                        escape_next = False
                        continue
                    if char == '\\' and in_string:
                        escape_next = True
                        continue
                    if char == '"' and not escape_next:
                        in_string = not in_string
                        continue
                    if not in_string:
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                try:
                                    parsed = json.loads(match[start_idx:i+1])
                                    if has_expected_structure(parsed):
                                        return parsed
                                except json.JSONDecodeError:
                                    pass
                                break

        # Strategy 2: Find ALL valid JSON objects and prefer ones with expected structure
        start_positions = [i for i, c in enumerate(text) if c == '{']

        candidates = []
        for start_idx in start_positions:
            # Find matching closing brace (accounting for strings)
            brace_count = 0
            in_string = False
            escape_next = False
            end_idx = start_idx

            for i, char in enumerate(text[start_idx:], start_idx):
                if escape_next:
                    escape_next = False
                    continue
                if char == '\\' and in_string:
                    escape_next = True
                    continue
                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue
                if not in_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_idx = i + 1
                            break

            if end_idx > start_idx:
                json_str = text[start_idx:end_idx]
                try:
                    parsed = json.loads(json_str)
                    candidates.append((parsed, len(json_str), start_idx))
                except json.JSONDecodeError:
                    continue

        # First, try to find a candidate with expected structure
        for parsed, length, pos in candidates:
            if has_expected_structure(parsed):
                return parsed

        # If no expected structure found, return the largest JSON (likely the main response)
        if candidates:
            # Sort by length descending, return largest
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0]

        # Strategy 3: Last resort - find first { to last }
        first_brace = text.find('{')
        last_brace = text.rfind('}')

        if first_brace != -1 and last_brace > first_brace:
            json_str = text[first_brace:last_brace + 1]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                self.logger.error(f"JSON parse error: {e}")
                self.logger.debug(f"Attempted to parse: {json_str[:500]}...")
                raise

        raise ValueError("No valid JSON object found in response")
    
    def _fetch_price_data(self, tickers: List[str]) -> Dict[str, Dict]:
        """Fetch current price and sector data using yfinance with graceful fallback"""
        
        self.logger.info(f"Fetching price data for {len(tickers)} tickers...")
        
        price_data = {}
        yfinance_available = True
        
        for ticker in tickers:
            if yfinance_available:
                try:
                    self.logger.debug(f"Fetching data for {ticker}")
                    stock = yf.Ticker(ticker)
                    
                    # Try to get info with a short timeout approach
                    info = stock.info
                    
                    # Get last close price
                    hist = stock.history(period="2d")
                    if not hist.empty:
                        last_close = hist['Close'].iloc[-1]
                    else:
                        last_close = info.get('previousClose', info.get('regularMarketPrice'))
                    
                    price_data[ticker] = {
                        'price': last_close,
                        'sector': info.get('sector', 'Unknown'),
                        'industry': info.get('industry', 'Unknown'),
                        'name': info.get('shortName', info.get('longName', ticker))
                    }
                    
                    self.logger.debug(f"  {ticker}: ${last_close:.2f} | {info.get('sector', 'Unknown')}")
                    
                except Exception as e:
                    error_str = str(e).lower()
                    
                    # Check if this is a network/proxy error that affects all requests
                    if any(x in error_str for x in ['proxy', 'connect', 'tunnel', 'network', '403', 'curl']):
                        self.logger.warning(f"yfinance network blocked - will use LLM for price data")
                        yfinance_available = False
                        price_data[ticker] = {
                            'price': None,
                            'sector': 'Unknown',
                            'industry': 'Unknown',
                            'name': ticker
                        }
                    else:
                        self.logger.warning(f"Failed to fetch data for {ticker}: {e}")
                        price_data[ticker] = {
                            'price': None,
                            'sector': 'Unknown',
                            'industry': 'Unknown',
                            'name': ticker
                        }
            else:
                # yfinance not available, use placeholder
                price_data[ticker] = {
                    'price': None,
                    'sector': 'Unknown',
                    'industry': 'Unknown',
                    'name': ticker
                }
        
        if not yfinance_available:
            self.logger.info("Price data will be fetched via web search in the analysis")
        
        return price_data
    
    def _fetch_etf_momentum_data(self) -> str:
        """
        Fetch REAL momentum data for sector ETFs to provide quantitative context.
        
        IMPORTANT: This is PRICE MOMENTUM data, not fundamental cycle stage.
        - Price momentum tells you what HAS happened
        - Fundamental cycle (penetration, capex, sentiment) tells you what's COMING
        
        A sector can have strong price momentum AND still be early fundamental cycle
        (e.g., AI chips up 80% but only 15% penetration)
        """
        etfs = {
            # Major Sectors
            'XLK': 'Technology', 'XLF': 'Financials', 'XLE': 'Energy', 
            'XLV': 'Healthcare', 'XLI': 'Industrials', 'XLY': 'Consumer Disc',
            'XLP': 'Consumer Staples', 'XLU': 'Utilities', 'XLB': 'Materials',
            'XLRE': 'Real Estate', 'XLC': 'Communications',
            # Thematic
            'SMH': 'Semiconductors', 'SOXX': 'Semiconductors', 'XBI': 'Biotech',
            'IBB': 'Biotech', 'ITA': 'Defense/Aero', 'GDX': 'Gold Miners',
            'URA': 'Uranium/Nuclear', 'ICLN': 'Clean Energy', 'TAN': 'Solar',
            'ARKK': 'Innovation', 'KRE': 'Regional Banks', 'OIH': 'Oil Services',
            'BITO': 'Bitcoin/Crypto', 'PAVE': 'Infrastructure', 'JETS': 'Airlines',
            'HACK': 'Cybersecurity', 'BOTZ': 'Robotics/AI', 'LIT': 'Lithium/Battery'
        }
        
        self.logger.info("Fetching ETF momentum data for context...")
        
        results = []
        
        for symbol, theme in etfs.items():
            try:
                etf = yf.Ticker(symbol)
                hist = etf.history(period="6mo")
                
                if len(hist) < 20:
                    continue
                
                current = hist['Close'].iloc[-1]
                
                # Calculate returns
                ret_1w = ((current / hist['Close'].iloc[-5]) - 1) * 100 if len(hist) >= 5 else 0
                ret_1m = ((current / hist['Close'].iloc[-21]) - 1) * 100 if len(hist) >= 21 else 0
                ret_3m = ((current / hist['Close'].iloc[-63]) - 1) * 100 if len(hist) >= 63 else 0
                ret_6m = ((current / hist['Close'].iloc[0]) - 1) * 100
                
                # Distance from 52-week high
                high_52w = hist['High'].max()
                pct_from_high = ((current / high_52w) - 1) * 100
                
                # Price momentum status (NOT fundamental cycle!)
                if pct_from_high > -5 and ret_6m > 30:
                    momentum_status = "EXTENDED"  # Near highs after big run
                elif pct_from_high > -10 and ret_3m > 10:
                    momentum_status = "STRONG"   # Healthy uptrend
                elif ret_1m > 5:
                    momentum_status = "IMPROVING" # Recent strength
                elif pct_from_high < -20:
                    momentum_status = "WEAK"     # Well off highs
                else:
                    momentum_status = "NEUTRAL"
                
                results.append({
                    'symbol': symbol,
                    'theme': theme,
                    'price': round(current, 2),
                    'ret_1w': round(ret_1w, 1),
                    'ret_1m': round(ret_1m, 1),
                    'ret_3m': round(ret_3m, 1),
                    'ret_6m': round(ret_6m, 1),
                    'pct_from_high': round(pct_from_high, 1),
                    'momentum_status': momentum_status
                })
                
            except Exception as e:
                self.logger.debug(f"Failed to fetch {symbol}: {e}")
                continue
        
        if not results:
            self.logger.warning("Could not fetch ETF data - will rely on web search")
            return ""
        
        # Sort by 1-month return
        results.sort(key=lambda x: x['ret_1m'], reverse=True)
        
        # Format as text
        lines = [
            "\n### REAL-TIME ETF PRICE MOMENTUM (for context only):",
            "",
            "⚠️ IMPORTANT: This is PRICE momentum, NOT fundamental cycle stage!",
            "   - A sector can be EXTENDED in price but EARLY in fundamentals",
            "   - Use this data for context, but determine cycle from fundamentals",
            "",
            "| ETF | Theme | 1M% | 3M% | 6M% | From High | Momentum |",
            "|-----|-------|-----|-----|-----|-----------|----------|"
        ]
        
        for r in results:
            lines.append(
                f"| {r['symbol']} | {r['theme']} | {r['ret_1m']:+.1f}% | "
                f"{r['ret_3m']:+.1f}% | {r['ret_6m']:+.1f}% | {r['pct_from_high']:.1f}% | {r['momentum_status']} |"
            )
        
        # Highlight sectors to investigate for fundamental cycle analysis
        extended = [r for r in results if r['momentum_status'] == 'EXTENDED']
        improving = [r for r in results if r['momentum_status'] == 'IMPROVING']
        weak = [r for r in results if r['momentum_status'] == 'WEAK']
        
        lines.append("")
        lines.append("### SECTORS REQUIRING FUNDAMENTAL CYCLE ANALYSIS:")
        lines.append("")
        
        if extended:
            lines.append("🔍 EXTENDED PRICE - Check if late or early fundamental cycle:")
            for r in extended:
                lines.append(f"   • {r['symbol']} ({r['theme']}): +{r['ret_6m']:.0f}% in 6M - IS the theme saturated or still growing?")
        
        if improving:
            lines.append("")
            lines.append("🔍 IMPROVING MOMENTUM - Potential rotation opportunity:")
            for r in improving[:5]:
                lines.append(f"   • {r['symbol']} ({r['theme']}): +{r['ret_1m']:.0f}% this month - SEARCH for why")
        
        if weak:
            lines.append("")
            lines.append("🔍 WEAK MOMENTUM - Check for contrarian opportunity:")
            for r in weak[:5]:
                lines.append(f"   • {r['symbol']} ({r['theme']}): {r['pct_from_high']:.0f}% from high - Are fundamentals turning?")
        
        self.logger.info(f"Fetched momentum data for {len(results)} ETFs")
        
        return "\n".join(lines)
    
    def run_step_1(self) -> List[Theme]:
        """Step 1: Identify top investable themes"""
        
        self.logger.info("=" * 60)
        self.logger.info("STEP 1: IDENTIFYING TOP INVESTABLE THEMES")
        self.logger.info("=" * 60)
        
        # Fetch real ETF momentum data to prevent training data bias
        etf_data = self._fetch_etf_momentum_data()
        
        # Combine prompt with real data
        full_prompt = STEP_1_PROMPT
        if etf_data:
            full_prompt += "\n\n" + etf_data
        
        messages = [{"role": "user", "content": full_prompt}]
        
        response_text = self._call_api_with_retry(messages, "Step 1 - Theme Identification")

        # Debug: save raw response for inspection
        debug_file = Path("logs/opus_raw_response.txt")
        debug_file.parent.mkdir(exist_ok=True)
        debug_file.write_text(response_text)
        self.logger.debug(f"Raw response saved to {debug_file}")

        # Parse response
        data = self._extract_json(response_text)

        # Debug: log what keys were returned
        self.logger.debug(f"Parsed JSON keys: {list(data.keys())}")
        if "top_themes" not in data:
            # Try alternative key names Opus might use
            alt_keys = ["themes", "investment_themes", "thematic_analysis", "results"]
            for key in alt_keys:
                if key in data and isinstance(data[key], list):
                    self.logger.info(f"Found themes under '{key}' instead of 'top_themes'")
                    data["top_themes"] = data[key]
                    break
            if "top_themes" not in data:
                self.logger.warning(f"No 'top_themes' found. Available keys: {list(data.keys())}")

        # Convert to Theme objects with catalyst-focused analysis
        self.themes = []
        for theme_data in data.get("top_themes", []):
            # Try new structure first (catalyst_analysis, momentum_analysis, etc.)
            catalyst_analysis = theme_data.get("catalyst_analysis", {})
            momentum_analysis = theme_data.get("momentum_analysis", {})
            crowding_analysis = theme_data.get("crowding_analysis", {})
            runway_analysis = theme_data.get("runway_analysis", {})
            
            # Fall back to old structure (fundamental_cycle_analysis) if new not present
            fca = theme_data.get("fundamental_cycle_analysis", {})
            
            # Determine if using new or old structure
            using_new_structure = bool(catalyst_analysis)
            
            if using_new_structure:
                # New structure parsing
                theme = Theme(
                    rank=theme_data.get("rank", 0),
                    name=theme_data.get("theme", "Unknown"),
                    primary_etfs=theme_data.get("primary_etfs", []),
                    composite_score=theme_data.get("composite_score", 0),
                    factor_scores=theme_data.get("factor_scores", {}),
                    key_catalysts=[c.get("catalyst", c) if isinstance(c, dict) else c 
                                   for c in catalyst_analysis.get("key_catalysts", theme_data.get("key_catalysts", []))],
                    primary_risks=theme_data.get("primary_risks", []),
                    thesis_summary=theme_data.get("investment_thesis", theme_data.get("why_now", "")),
                    crowding_indicator=crowding_analysis.get("crowding_level", "Moderate"),
                    why_now=theme_data.get("investment_thesis", ""),
                    
                    # Theme type classification (NEW)
                    theme_type=theme_data.get("theme_type", "TREND"),
                    theme_type_rationale=theme_data.get("theme_type_rationale", ""),
                    relative_strength_vs_spy=momentum_analysis.get("relative_strength_vs_spy", ""),
                    
                    # New analysis scores
                    catalyst_score=catalyst_analysis.get("score", 0.0),
                    catalyst_detail=catalyst_analysis.get("catalyst_evidence", ""),
                    momentum_score=momentum_analysis.get("score", 0.0),
                    momentum_detail=f"{momentum_analysis.get('trend_direction', '')} - {momentum_analysis.get('momentum_evidence', '')}",
                    crowding_score=crowding_analysis.get("score", 0.0),
                    crowding_detail=crowding_analysis.get("crowding_evidence", ""),
                    runway_score=runway_analysis.get("score", 0.0),
                    runway_detail=f"{runway_analysis.get('penetration_estimate', '')} - {runway_analysis.get('runway_evidence', '')}",
                    
                    # Get classification from response or calculate
                    classification=theme_data.get("classification", "INVESTABLE")
                )
            else:
                # Old structure parsing (backwards compatibility)
                pen_analysis = fca.get("penetration_analysis", {})
                capex_analysis = fca.get("capex_cycle_analysis", {})
                sent_analysis = fca.get("sentiment_analysis", {})
                val_analysis = fca.get("valuation_runway", {})
                
                theme = Theme(
                    rank=theme_data.get("rank", 0),
                    name=theme_data.get("theme", "Unknown"),
                    primary_etfs=theme_data.get("primary_etfs", []),
                    composite_score=theme_data.get("composite_score", 0),
                    factor_scores=theme_data.get("factor_scores", {}),
                    key_catalysts=theme_data.get("key_catalysts", []),
                    primary_risks=theme_data.get("primary_risks", []),
                    thesis_summary=theme_data.get("thesis_summary", theme_data.get("why_now", "")),
                    cycle_stage=fca.get("cycle_stage", theme_data.get("cycle_stage", "MID")),
                    crowding_indicator=sent_analysis.get("crowding_level", theme_data.get("crowding_indicator", "Moderate")),
                    why_now=theme_data.get("why_now", ""),
                    fundamental_cycle_score=fca.get("fundamental_cycle_score", 0.0),
                )
            
            # Calculate classification based on composite_score
            theme.calculate_classification()
            
            self.themes.append(theme)
        
        # =====================================================================
        # COMPREHENSIVE THEME OUTPUT (NO TRUNCATION)
        # =====================================================================
        
        def wrap_text(text: str, prefix: str = "       ", width: int = 90) -> List[str]:
            """Word-wrap text to specified width with prefix."""
            if not text:
                return []
            words = text.split()
            lines = []
            line = prefix
            for word in words:
                if len(line) + len(word) + 1 > width:
                    lines.append(line)
                    line = prefix + word
                else:
                    line = line + " " + word if line != prefix else prefix + word
            if line != prefix:
                lines.append(line)
            return lines
        
        print("\n")
        print("  ╔" + "═" * 88 + "╗")
        print("  ║" + " TOP INVESTMENT THEMES IDENTIFIED ".center(88) + "║")
        print("  ║" + " (6-12 Month Investment Horizon) ".center(88) + "║")
        print("  ╚" + "═" * 88 + "╝")
        
        for theme in self.themes:
            class_emoji = {"PRIME": "🟢", "INVESTABLE": "🟡", "SELECTIVE": "🟠", "AVOID": "🔴"}.get(theme.classification, "⚪")
            type_emoji = {"BOTTLENECK": "🔧", "CONTRARIAN": "🔄", "TREND": "📈"}.get(theme.theme_type, "📊")
            crowd_emoji = {"Low": "🟢", "Moderate": "🟡", "High": "🔴"}.get(theme.crowding_indicator, "")
            
            print(f"\n  ┌{'─' * 88}┐")
            print(f"  │  #{theme.rank} {theme.name}")
            print(f"  ├{'─' * 88}┤")
            
            # Classification & Score
            print(f"  │  {class_emoji} Classification: {theme.classification:<12}  │  Composite Score: {theme.composite_score:.1f}/10")
            print(f"  │  {type_emoji} Theme Type: {theme.theme_type:<15}  │  Crowding: {crowd_emoji} {theme.crowding_indicator}")
            print(f"  │  📊 Position Sizing: {theme.position_sizing_recommendation}")
            
            # Factor Score Breakdown
            if theme.catalyst_score > 0 or theme.momentum_score > 0:
                print(f"  │")
                print(f"  │  FACTOR SCORES (Weighted Components):")
                print(f"  │    • Catalyst Strength (40%):  {theme.catalyst_score:.1f}/10")
                print(f"  │    • Momentum Direction (25%): {theme.momentum_score:.1f}/10")
                print(f"  │    • Crowding Level (20%):     {theme.crowding_score:.1f}/10")
                print(f"  │    • Runway Remaining (15%):   {theme.runway_score:.1f}/10")
            
            # Factor Details (FULL - no truncation)
            if theme.catalyst_detail or theme.momentum_detail:
                print(f"  │")
                print(f"  │  FACTOR ANALYSIS:")
                if theme.catalyst_detail:
                    for line in wrap_text(f"Catalyst: {theme.catalyst_detail}", "  │    "):
                        print(line)
                if theme.momentum_detail:
                    for line in wrap_text(f"Momentum: {theme.momentum_detail}", "  │    "):
                        print(line)
                if theme.crowding_detail:
                    for line in wrap_text(f"Crowding: {theme.crowding_detail}", "  │    "):
                        print(line)
                if theme.runway_detail:
                    for line in wrap_text(f"Runway: {theme.runway_detail}", "  │    "):
                        print(line)
            
            # Theme Type Rationale (FULL)
            if theme.theme_type_rationale:
                print(f"  │")
                print(f"  │  WHY {theme.theme_type}:")
                for line in wrap_text(theme.theme_type_rationale, "  │    "):
                    print(line)
            
            # Investment Thesis (FULL)
            if theme.thesis_summary:
                print(f"  │")
                print(f"  │  INVESTMENT THESIS:")
                for line in wrap_text(theme.thesis_summary, "  │    "):
                    print(line)
            
            # Why Now (FULL)
            if theme.why_now:
                print(f"  │")
                print(f"  │  WHY NOW:")
                for line in wrap_text(theme.why_now, "  │    "):
                    print(line)
            
            # ALL Key Catalysts (FULL - no truncation, no limit)
            if theme.key_catalysts:
                print(f"  │")
                print(f"  │  KEY CATALYSTS:")
                for i, catalyst in enumerate(theme.key_catalysts, 1):
                    for line in wrap_text(f"{i}. {catalyst}", "  │    "):
                        print(line)
            
            # ALL Primary Risks (FULL)
            if theme.primary_risks:
                print(f"  │")
                print(f"  │  ⚠️  PRIMARY RISKS:")
                for i, risk in enumerate(theme.primary_risks, 1):
                    for line in wrap_text(f"{i}. {risk}", "  │    "):
                        print(line)
            
            # Reference ETFs
            if theme.primary_etfs:
                print(f"  │")
                print(f"  │  REFERENCE ETFs: {', '.join(theme.primary_etfs)}")
            
            # Classification Rationale
            if theme.classification_rationale:
                print(f"  │")
                print(f"  │  CLASSIFICATION RATIONALE:")
                for line in wrap_text(theme.classification_rationale, "  │    "):
                    print(line)
            
            print(f"  └{'─' * 88}┘")
        
        # Summary
        print(f"\n  {'═' * 90}")
        print(f"  THEME SUMMARY")
        print(f"  {'─' * 90}")
        print(f"    Total Themes: {len(self.themes)}")
        print(f"    By Classification:  PRIME: {sum(1 for t in self.themes if t.classification == 'PRIME')}  |  " +
              f"INVESTABLE: {sum(1 for t in self.themes if t.classification == 'INVESTABLE')}  |  " +
              f"SELECTIVE: {sum(1 for t in self.themes if t.classification == 'SELECTIVE')}")
        print(f"    By Type (preference order):  BOTTLENECK: {sum(1 for t in self.themes if t.theme_type == 'BOTTLENECK')}  |  " +
              f"CONTRARIAN: {sum(1 for t in self.themes if t.theme_type == 'CONTRARIAN')}  |  " +
              f"TREND: {sum(1 for t in self.themes if t.theme_type == 'TREND')}")
        
        # Rejected themes (FULL)
        rejected = data.get("themes_rejected", [])
        if rejected:
            print(f"\n    THEMES REJECTED:")
            for r in rejected:
                theme_name = r.get('theme', 'Unknown')
                reason = r.get('rejection_reason', 'N/A')
                print(f"      ❌ {theme_name}: {reason}")
        
        # Contrarian opportunities (FULL)
        contrarian = data.get("contrarian_opportunities", "")
        if contrarian:
            print(f"\n    👀 CONTRARIAN WATCH:")
            for line in wrap_text(contrarian, "       "):
                print(line)
        
        print(f"  {'═' * 90}\n")
        
        return self.themes
    
    def run_step_2(self, tickers: List[str]) -> List[TickerAnalysis]:
        """Step 2: Map tickers to themes and score upside"""
        
        if not self.themes:
            raise ValueError("Must run Step 1 first to identify themes")
        
        self.logger.info("")
        self.logger.info("=" * 60)
        self.logger.info("STEP 2: MAPPING TICKERS TO THEMES")
        self.logger.info("=" * 60)
        self.logger.info(f"Analyzing {len(tickers)} tickers: {', '.join(tickers)}")
        
        # Prepare themes JSON for prompt
        themes_json = json.dumps([t.to_dict() for t in self.themes], indent=2)
        
        prompt = STEP_2_PROMPT_TEMPLATE.format(
            themes_json=themes_json,
            ticker_list=", ".join(tickers)
        )
        
        messages = [{"role": "user", "content": prompt}]
        
        response_text = self._call_api_with_retry(messages, "Step 2 - Ticker Analysis")
        
        # Parse response
        data = self._extract_json(response_text)
        
        # Try to fetch price data via yfinance (may fail in some environments)
        price_data = self._fetch_price_data(tickers)
        
        # Convert to TickerAnalysis objects
        self.ticker_analyses = []
        for analysis in data.get("ticker_analysis", []):
            ticker = analysis.get("ticker", "")
            
            # Use yfinance data if available, otherwise use LLM-provided data
            yf_data = price_data.get(ticker, {})
            
            # Prefer yfinance price if available, otherwise use LLM price
            price = yf_data.get('price')
            if price is None:
                price = analysis.get('current_price')
            
            # Prefer yfinance sector if available and not 'Unknown', otherwise use LLM sector
            sector = yf_data.get('sector')
            if not sector or sector == 'Unknown':
                sector = analysis.get('sector', 'Unknown')
            
            # Extract new structure fields if present
            theme_fit = analysis.get("theme_fit", {})
            company_pos = analysis.get("company_position", {})
            stock_setup = analysis.get("stock_setup", {})
            risk_factors = analysis.get("risk_factors", {})
            
            # Handle pure_play_score - could be in theme_fit.exposure_pct or top-level
            pure_play = theme_fit.get("exposure_pct", analysis.get("pure_play_score", 0))
            if isinstance(pure_play, str):
                # Handle "75%" -> 75
                pure_play = int(pure_play.replace("%", "").strip()) if pure_play else 0
            
            # Look up theme classification from our themes list
            primary_theme_name = analysis.get("primary_theme")
            theme_classification = "INVESTABLE"  # Default
            for theme in self.themes:
                if theme.name == primary_theme_name:
                    theme_classification = theme.classification
                    break
            
            ticker_analysis = TickerAnalysis(
                ticker=ticker,
                company_name=analysis.get("company_name", ticker),
                primary_theme=primary_theme_name,
                theme_score=analysis.get("theme_score"),
                theme_rank=analysis.get("theme_rank"),
                secondary_themes=analysis.get("secondary_themes", []),
                pure_play_score=int(pure_play),
                market_position=company_pos.get("position", analysis.get("market_position", "Unknown")),
                upside_score=analysis.get("upside_score", 0),
                upside_rationale=analysis.get("upside_rationale", analysis.get("verdict_rationale", "")),
                verdict=analysis.get("verdict", "Unknown"),
                action=analysis.get("action", ""),
                valuation_metric=analysis.get("valuation_metric", ""),
                key_catalysts=analysis.get("key_catalysts", []),
                risks=analysis.get("risks", []),
                current_price=price,
                sector=sector,
                
                # New fields from refined prompt
                theme_classification=analysis.get("theme_classification", theme_classification),
                conviction=analysis.get("conviction", "Medium"),
                theme_fit_score=theme_fit.get("score", 0),
                theme_fit_pct=theme_fit.get("exposure_pct", 0) if isinstance(theme_fit.get("exposure_pct", 0), (int, float)) else 0,
                company_position_score=company_pos.get("score", 0),
                company_position=company_pos.get("position", ""),
                stock_setup_score=stock_setup.get("score", 0),
                stock_setup=stock_setup.get("setup", ""),
                earnings_date=risk_factors.get("earnings_date", ""),
                earnings_risk=risk_factors.get("earnings_risk", False),
                short_interest=str(risk_factors.get("short_interest", "")),
                red_flags=risk_factors.get("red_flags", [])
            )
            
            # Calculate conviction if not provided
            if not analysis.get("conviction"):
                ticker_analysis.conviction = ticker_analysis.get_conviction_level()
            
            self.ticker_analyses.append(ticker_analysis)
        
        # =====================================================================
        # COMPREHENSIVE TICKER ANALYSIS OUTPUT (NO TRUNCATION)
        # =====================================================================
        
        def wrap_text(text: str, prefix: str = "  │    ", width: int = 90) -> list:
            """Word-wrap text to specified width with prefix."""
            if not text:
                return []
            words = str(text).split()
            lines = []
            line = prefix
            for word in words:
                if len(line) + len(word) + 1 > width:
                    lines.append(line)
                    line = prefix + word
                else:
                    line = line + " " + word if line != prefix else prefix + word
            if line != prefix:
                lines.append(line)
            return lines
        
        print("\n")
        print("  ╔" + "═" * 88 + "╗")
        print("  ║" + " TICKER-TO-THEME MAPPING RESULTS ".center(88) + "║")
        print("  ╚" + "═" * 88 + "╝")
        
        # Group by verdict for clearer output
        passing = [t for t in self.ticker_analyses if t.passes_gate()]
        marginal = [t for t in self.ticker_analyses if t.verdict in ["STRONG FIT", "GOOD FIT"] and not t.passes_gate()]
        rejected = [t for t in self.ticker_analyses if t.verdict not in ["STRONG FIT", "GOOD FIT"]]
        
        # Show PASSING tickers with full details
        if passing:
            print(f"\n  ✅ PASSING THEMATIC GATE ({len(passing)} stocks)")
            print(f"  {'─' * 88}")
            
            for t in passing:
                verdict_emoji = "🟢" if t.verdict == "STRONG FIT" else "🟡"
                
                print(f"\n  ┌{'─' * 86}┐")
                print(f"  │  {verdict_emoji} {t.ticker} - {t.company_name}")
                print(f"  ├{'─' * 86}┤")
                
                # Basic info
                price_str = f"${t.current_price:.2f}" if t.current_price else "N/A"
                print(f"  │  Price: {price_str:<12}  │  Sector: {t.sector or 'Unknown'}")
                print(f"  │  Theme: {t.primary_theme or 'N/A'}")
                print(f"  │  Theme Classification: {t.theme_classification}  │  Theme Rank: #{t.theme_rank or 'N/A'}")
                
                # Fit assessment
                print(f"  │")
                print(f"  │  THEME FIT ASSESSMENT:")
                print(f"  │    Verdict: {t.verdict}  │  Pure Play: {t.pure_play_score}%")
                print(f"  │    Conviction: {t.conviction}  │  Market Position: {t.market_position}")
                
                # Upside rationale (FULL)
                if t.upside_rationale:
                    print(f"  │")
                    print(f"  │  UPSIDE RATIONALE:")
                    for line in wrap_text(t.upside_rationale):
                        print(line)
                
                # ALL Key Catalysts (FULL)
                if t.key_catalysts:
                    print(f"  │")
                    print(f"  │  KEY CATALYSTS:")
                    for i, catalyst in enumerate(t.key_catalysts, 1):
                        for line in wrap_text(f"{i}. {catalyst}"):
                            print(line)
                
                # ALL Risks (FULL)
                if t.risks:
                    print(f"  │")
                    print(f"  │  ⚠️  RISKS:")
                    for i, risk in enumerate(t.risks, 1):
                        if isinstance(risk, dict):
                            risk_text = risk.get('risk', str(risk))
                            severity = risk.get('severity', '')
                            if severity:
                                risk_text = f"[{severity}] {risk_text}"
                        else:
                            risk_text = str(risk)
                        for line in wrap_text(f"{i}. {risk_text}"):
                            print(line)
                
                # Red flags if any
                if t.red_flags:
                    print(f"  │")
                    print(f"  │  🚨 RED FLAGS:")
                    for flag in t.red_flags:
                        for line in wrap_text(f"• {flag}"):
                            print(line)
                
                # Earnings risk
                if t.earnings_date:
                    print(f"  │")
                    earnings_warning = "⚠️ EARNINGS RISK" if t.earnings_risk else ""
                    print(f"  │  📅 Earnings Date: {t.earnings_date} {earnings_warning}")
                
                # Short interest
                if t.short_interest:
                    print(f"  │  📊 Short Interest: {t.short_interest}")
                
                # Valuation
                if t.valuation_metric:
                    print(f"  │  💰 Valuation: {t.valuation_metric}")
                
                # Action recommendation
                if t.action:
                    print(f"  │")
                    print(f"  │  📋 ACTION:")
                    for line in wrap_text(t.action):
                        print(line)
                
                print(f"  └{'─' * 86}┘")
        
        # Show MARGINAL tickers (passed fit but not theme classification)
        if marginal:
            print(f"\n  ⚠️  MARGINAL - Good Fit but Theme Classification Issue ({len(marginal)} stocks)")
            print(f"  {'─' * 88}")
            
            for t in marginal:
                print(f"\n  ┌{'─' * 86}┐")
                print(f"  │  ⚠️  {t.ticker} - {t.company_name}")
                print(f"  │  Theme: {t.primary_theme or 'N/A'} ({t.theme_classification})")
                print(f"  │  Verdict: {t.verdict}  │  Pure Play: {t.pure_play_score}%")
                print(f"  │  Issue: Theme is {t.theme_classification} - not PRIME/INVESTABLE")
                if t.upside_rationale:
                    print(f"  │  Rationale: {t.upside_rationale}")
                print(f"  └{'─' * 86}┘")
        
        # Show REJECTED tickers (brief - they didn't pass)
        if rejected:
            print(f"\n  ❌ REJECTED - No Theme Fit ({len(rejected)} stocks)")
            print(f"  {'─' * 88}")
            
            for t in rejected:
                reason = t.action if t.action else "No matching theme or weak exposure"
                print(f"    {t.ticker:<8} │ {t.verdict:<15} │ {t.primary_theme or 'No Theme':<25} │ {reason[:40]}")
        
        # Final Summary
        print(f"\n  {'═' * 90}")
        print(f"  TICKER ANALYSIS SUMMARY")
        print(f"  {'─' * 90}")
        print(f"    Total Analyzed: {len(self.ticker_analyses)}")
        print(f"    ✅ Passing Gate: {len(passing)}")
        if passing:
            print(f"       Tickers: {', '.join(t.ticker for t in passing)}")
        print(f"    ⚠️  Marginal: {len(marginal)}")
        print(f"    ❌ Rejected: {len(rejected)}")
        print(f"  {'═' * 90}\n")
        
        return self.ticker_analyses
    
    def save_trade_log(self, filepath: Optional[str] = None) -> str:
        """Save passing tickers to trade log CSV"""
        
        filepath = filepath or self.config.trade_log_file
        passing_tickers = [t for t in self.ticker_analyses if t.passes_gate()]
        
        if not passing_tickers:
            self.logger.warning("No tickers passed the gate - nothing to log")
            return filepath
        
        self.logger.info(f"Saving {len(passing_tickers)} tickers to trade log: {filepath}")
        
        # Check if file exists to determine if we need headers
        file_exists = Path(filepath).exists()
        
        with open(filepath, 'a', newline='') as f:
            writer = csv.writer(f)
            
            # Write header if new file
            if not file_exists:
                writer.writerow([
                    'Timestamp',
                    'Ticker',
                    'Company',
                    'Price',
                    'Sector',
                    'Primary_Theme',
                    'Theme_Score',
                    'Theme_Rank',
                    'Pure_Play_Score',
                    'Upside_Score',
                    'Verdict',
                    'Market_Position',
                    'Valuation',
                    'Key_Catalysts',
                    'Risks',
                    'Action'
                ])
            
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            for t in passing_tickers:
                writer.writerow([
                    timestamp,
                    t.ticker,
                    t.company_name,
                    f"${t.current_price:.2f}" if t.current_price else "N/A",
                    t.sector or "Unknown",
                    t.primary_theme or "N/A",
                    t.theme_score,
                    t.theme_rank,
                    f"{t.pure_play_score}%",
                    t.upside_score,
                    t.verdict,
                    t.market_position,
                    t.valuation_metric,
                    " | ".join(t.key_catalysts[:3]),
                    " | ".join([r.get('risk', '') for r in t.risks[:2]]),
                    t.action
                ])
        
        self.logger.info(f"Trade log updated: {filepath}")
        return filepath
    
    def save_full_analysis(self, output_dir: Optional[str] = None) -> str:
        """Save complete analysis to JSON file"""
        
        output_dir = Path(output_dir or self.config.analysis_output_dir)
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = output_dir / f"analysis_{timestamp}.json"
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "themes": [t.to_dict() for t in self.themes],
            "ticker_analyses": [t.to_dict() for t in self.ticker_analyses],
            "summary": {
                "total_tickers": len(self.ticker_analyses),
                "passing_gate": len([t for t in self.ticker_analyses if t.passes_gate()]),
                "strong_fits": [t.ticker for t in self.ticker_analyses if t.verdict == "STRONG FIT"],
                "good_fits": [t.ticker for t in self.ticker_analyses if t.verdict == "GOOD FIT"],
                "no_theme_fit": [t.ticker for t in self.ticker_analyses if t.verdict == "NO THEME FIT"]
            },
            "rate_limiter_stats": self.rate_limiter.get_stats()
        }
        
        with open(filepath, 'w') as f:
            json.dump(result, f, indent=2)
        
        self.logger.info(f"Full analysis saved: {filepath}")
        return str(filepath)
    
    def send_email_notification(self, subject: Optional[str] = None) -> bool:
        """Send email notification with analysis results"""
        
        if not all([
            self.config.email_sender,
            self.config.email_password,
            self.config.email_recipients
        ]):
            self.logger.warning("Email not configured - skipping notification")
            return False
        
        self.logger.info("Sending email notification...")
        
        passing_tickers = [t for t in self.ticker_analyses if t.passes_gate()]
        
        # Build email content
        subject = subject or f"Thematic Analysis Results - {datetime.now().strftime('%Y-%m-%d')}"
        
        # Plain text version
        text_content = self._build_email_text(passing_tickers)
        
        # HTML version
        html_content = self._build_email_html(passing_tickers)
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.config.email_sender
            msg['To'] = ", ".join(self.config.email_recipients)
            
            msg.attach(MIMEText(text_content, 'plain'))
            msg.attach(MIMEText(html_content, 'html'))
            
            with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port) as server:
                server.starttls()
                server.login(self.config.email_sender, self.config.email_password)
                server.send_message(msg)
            
            self.logger.info(f"Email sent to {len(self.config.email_recipients)} recipients")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send email: {e}")
            return False
    
    def _build_email_text(self, passing_tickers: List[TickerAnalysis]) -> str:
        """Build plain text email content"""
        
        lines = [
            "THEMATIC INVESTMENT ANALYSIS RESULTS",
            "=" * 50,
            f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "TOP THEMES:",
            "-" * 30
        ]
        
        for theme in self.themes:
            lines.append(f"#{theme.rank} {theme.name} (Score: {theme.composite_score:.2f})")
        
        lines.extend([
            "",
            "TICKERS PASSING THEME GATE:",
            "-" * 30
        ])
        
        if passing_tickers:
            for t in passing_tickers:
                lines.append(
                    f"{t.ticker}: {t.primary_theme} | "
                    f"Upside: {t.upside_score}/10 | "
                    f"Price: ${t.current_price:.2f if t.current_price else 'N/A'}"
                )
        else:
            lines.append("No tickers passed the theme gate.")
        
        lines.extend([
            "",
            f"Total analyzed: {len(self.ticker_analyses)}",
            f"Passing gate: {len(passing_tickers)}"
        ])
        
        return "\n".join(lines)
    
    def _build_email_html(self, passing_tickers: List[TickerAnalysis]) -> str:
        """Build HTML email content"""
        
        theme_rows = ""
        for theme in self.themes:
            theme_rows += f"""
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd;">#{theme.rank}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{theme.name}</td>
                <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{theme.composite_score:.2f}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{', '.join(theme.primary_etfs)}</td>
            </tr>
            """
        
        ticker_rows = ""
        for t in passing_tickers:
            color = "#28a745" if t.verdict == "STRONG FIT" else "#17a2b8"
            price_str = f"${t.current_price:.2f}" if t.current_price else "N/A"
            ticker_rows += f"""
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">{t.ticker}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{t.primary_theme}</td>
                <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{t.pure_play_score}%</td>
                <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{t.upside_score}/10</td>
                <td style="padding: 8px; border: 1px solid #ddd; color: {color}; font-weight: bold;">{t.verdict}</td>
                <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">{price_str}</td>
            </tr>
            """
        
        if not ticker_rows:
            ticker_rows = '<tr><td colspan="6" style="padding: 16px; text-align: center; color: #666;">No tickers passed the theme gate.</td></tr>'
        
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto;">
            <h1 style="color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px;">
                Thematic Investment Analysis
            </h1>
            <p style="color: #666;">Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
            
            <h2 style="color: #333;">Top Themes</h2>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                <thead>
                    <tr style="background-color: #007bff; color: white;">
                        <th style="padding: 10px; text-align: left;">Rank</th>
                        <th style="padding: 10px; text-align: left;">Theme</th>
                        <th style="padding: 10px; text-align: center;">Score</th>
                        <th style="padding: 10px; text-align: left;">ETFs</th>
                    </tr>
                </thead>
                <tbody>
                    {theme_rows}
                </tbody>
            </table>
            
            <h2 style="color: #333;">Tickers Passing Theme Gate</h2>
            <table style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="background-color: #28a745; color: white;">
                        <th style="padding: 10px; text-align: left;">Ticker</th>
                        <th style="padding: 10px; text-align: left;">Theme</th>
                        <th style="padding: 10px; text-align: center;">Pure Play</th>
                        <th style="padding: 10px; text-align: center;">Upside</th>
                        <th style="padding: 10px; text-align: center;">Verdict</th>
                        <th style="padding: 10px; text-align: right;">Price</th>
                    </tr>
                </thead>
                <tbody>
                    {ticker_rows}
                </tbody>
            </table>
            
            <p style="color: #666; margin-top: 20px; font-size: 12px;">
                Total analyzed: {len(self.ticker_analyses)} | Passing gate: {len(passing_tickers)}
            </p>
        </body>
        </html>
        """
    
    def run_full_analysis(self, tickers: List[str]) -> AnalysisResult:
        """Run complete two-step analysis"""
        
        start_time = time.time()
        
        self.logger.info("Starting full thematic analysis...")
        self.logger.info(f"Tickers to analyze: {len(tickers)}")
        
        # Step 1: Identify themes
        self.run_step_1()
        
        # CRITICAL: Cool down between steps to avoid rate limiting
        self.rate_limiter.wait_for_inter_step_cooldown("Step 2 - Ticker Analysis")
        
        # Step 2: Map tickers (handle batching if needed)
        if len(tickers) > self.config.max_tickers_per_batch:
            self.logger.warning(
                f"Ticker list exceeds batch size ({len(tickers)} > {self.config.max_tickers_per_batch}). "
                f"Processing in batches..."
            )
            all_analyses = []
            for i in range(0, len(tickers), self.config.max_tickers_per_batch):
                batch = tickers[i:i + self.config.max_tickers_per_batch]
                batch_num = i // self.config.max_tickers_per_batch + 1
                self.logger.info(f"Processing batch {batch_num}: {', '.join(batch)}")
                
                # Add delay between batches (except first)
                if i > 0:
                    self.rate_limiter.wait_for_inter_step_cooldown(f"Batch {batch_num}")
                
                analyses = self.run_step_2(batch)
                all_analyses.extend(analyses)
            self.ticker_analyses = all_analyses
        else:
            self.run_step_2(tickers)
        
        # Save outputs
        self.save_trade_log()
        analysis_file = self.save_full_analysis()
        
        # Send email notification
        self.send_email_notification()
        
        elapsed = time.time() - start_time
        
        # Final summary
        self.logger.info("")
        self.logger.info("=" * 60)
        self.logger.info("ANALYSIS COMPLETE")
        self.logger.info("=" * 60)
        self.logger.info(f"Time elapsed: {elapsed:.1f} seconds")
        self.logger.info(f"API calls made: {self.rate_limiter.request_count}")
        self.logger.info(f"Themes identified: {len(self.themes)}")
        self.logger.info(f"Tickers analyzed: {len(self.ticker_analyses)}")
        self.logger.info(f"Tickers passing gate: {len([t for t in self.ticker_analyses if t.passes_gate()])}")
        self.logger.info(f"Trade log: {self.config.trade_log_file}")
        self.logger.info(f"Full analysis: {analysis_file}")
        
        return AnalysisResult(
            timestamp=datetime.now().isoformat(),
            themes=self.themes,
            ticker_analyses=self.ticker_analyses,
            summary={
                "elapsed_seconds": elapsed,
                "api_calls": self.rate_limiter.request_count,
                "passing_gate": len([t for t in self.ticker_analyses if t.passes_gate()])
            }
        )


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def load_tickers(filepath: str) -> List[str]:
    """Load tickers from file"""
    
    path = Path(filepath)
    
    if not path.exists():
        raise FileNotFoundError(f"Ticker file not found: {filepath}")
    
    with open(path, 'r') as f:
        content = f.read()
    
    # Parse tickers - handle comma-separated, newline-separated, or space-separated
    tickers = []
    for line in content.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        # Split by comma or whitespace
        for ticker in line.replace(',', ' ').split():
            ticker = ticker.strip().upper()
            if ticker:
                tickers.append(ticker)
    
    return tickers


def main():
    """Main entry point"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description='Thematic Investment Analyzer')
    parser.add_argument('--tickers-file', default='LLM_tickers.txt', 
                        help='Path to tickers file (default: LLM_tickers.txt)')
    parser.add_argument('--batch-size', type=int, default=5,
                        help='Max tickers per API call (default: 5, reduce if hitting rate limits)')
    parser.add_argument('--step-delay', type=int, default=30,
                        help='Seconds to wait between steps (default: 30)')
    parser.add_argument('--conservative', action='store_true',
                        help='Use very conservative rate limiting (longer delays)')
    parser.add_argument('--skip-step1', action='store_true',
                        help='Skip Step 1 if themes.json exists from previous run')
    
    args = parser.parse_args()
    
    print("\n" + "=" * 70)
    print(" THEMATIC INVESTMENT ANALYZER ")
    print("=" * 70 + "\n")
    
    # Configuration
    config = Config()
    config.tickers_file = args.tickers_file
    config.max_tickers_per_batch = args.batch_size
    config.inter_step_delay = args.step_delay
    
    # Apply conservative mode if requested
    if args.conservative:
        print("CONSERVATIVE MODE: Using longer delays to avoid rate limits")
        config.inter_step_delay = 60.0
        config.base_delay = 10.0
        config.rate_limit_cooldown = 120.0
        config.max_tickers_per_batch = 3
    
    # Validate API key
    if not config.anthropic_api_key:
        print("ERROR: ANTHROPIC_API_KEY environment variable is not set.")
        print("Please set it before running:")
        print("  export ANTHROPIC_API_KEY='your-api-key'")
        sys.exit(1)
    
    # Load tickers
    try:
        tickers = load_tickers(config.tickers_file)
        print(f"Loaded {len(tickers)} tickers from {config.tickers_file}")
        print(f"Tickers: {', '.join(tickers)}")
        print(f"Batch size: {config.max_tickers_per_batch}")
        print(f"Step delay: {config.inter_step_delay}s")
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        print(f"\nPlease create {config.tickers_file} with tickers to analyze.")
        print("Example content:")
        print("  NVDA, CCJ, LMT, CRWD, NEM")
        print("  VRTX, PLTR, OKLO, ANET, RKLB")
        sys.exit(1)
    
    if not tickers:
        print("ERROR: No tickers found in file")
        sys.exit(1)
    
    # Check for previous themes if skip-step1 requested
    themes_cache_file = Path("themes_cache.json")
    cached_themes = None
    
    if args.skip_step1 and themes_cache_file.exists():
        try:
            with open(themes_cache_file, 'r') as f:
                cached_data = json.load(f)
            print(f"Loaded cached themes from {themes_cache_file}")
            cached_themes = cached_data
        except:
            print("Could not load cached themes, will run Step 1")
    
    # Run analysis
    try:
        analyzer = ThematicAnalyzer(config=config, verbose=True)
        
        if cached_themes:
            # Load themes from cache and skip to Step 2
            analyzer.themes = [
                Theme(**t) for t in cached_themes.get('themes', [])
            ]
            analyzer.logger.info(f"Using {len(analyzer.themes)} cached themes from previous run")
            analyzer.run_step_2(tickers)
            analyzer.save_trade_log()
            analyzer.save_full_analysis()
            analyzer.send_email_notification()
        else:
            result = analyzer.run_full_analysis(tickers)
            
            # Cache themes for potential re-runs
            with open(themes_cache_file, 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'themes': [t.to_dict() for t in analyzer.themes]
                }, f, indent=2)
            print(f"\nThemes cached to {themes_cache_file} for re-runs")
        
        print("\n" + "=" * 70)
        print(" ANALYSIS SUMMARY ")
        print("=" * 70)
        
        passing = [t for t in analyzer.ticker_analyses if t.passes_gate()]
        if passing:
            print(f"\n✓ {len(passing)} tickers passed the theme gate:\n")
            for t in passing:
                print(f"  {t.ticker:<8} | {t.primary_theme:<20} | Upside: {t.upside_score}/10 | {t.verdict}")
        else:
            print("\n⚠ No tickers passed the theme gate")
        
        print("\n" + "=" * 70)
        print(" FILES GENERATED ")
        print("=" * 70)
        print(f"  Trade Log:     {config.trade_log_file}")
        print(f"  Full Analysis: {config.analysis_output_dir}/")
        print(f"  Themes Cache:  {themes_cache_file}")
        print(f"  Logs:          logs/")
        
    except KeyboardInterrupt:
        print("\n\nAnalysis cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nERROR: {e}")
        traceback.print_exc()
        
        # Helpful suggestions
        print("\n" + "=" * 70)
        print(" TROUBLESHOOTING ")
        print("=" * 70)
        if "rate limit" in str(e).lower() or "429" in str(e):
            print("""
Rate limit issues detected. Try:

1. Use conservative mode:
   python thematic_analyzer.py --conservative

2. Reduce batch size:
   python thematic_analyzer.py --batch-size 3

3. Increase delay between steps:
   python thematic_analyzer.py --step-delay 60

4. If Step 1 succeeded, skip it on retry:
   python thematic_analyzer.py --skip-step1

5. Wait a few minutes and try again (rate limits reset)
""")
        sys.exit(1)


if __name__ == "__main__":
    main()
