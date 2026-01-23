#!/usr/bin/env python3
"""
SRC.COMMON - Shared Modules for BoS Momentum Scanner
=====================================================

Centralized utilities for configuration, logging, data models, data loading,
LLM integration, and prompt management.

Usage:
    from src.common import (
        # Configuration
        ANTHROPIC_API_KEY,
        MODEL_SONNET, MODEL_OPUS,
        TRAILING_STOP_PCT,
        TRADES_DIR,

        # Logging
        get_logger, log_step, log_success, log_warning, log_error,
        LoggedOperation,

        # Data Models
        Stock, Trade, Theme, SellSignal,
        GatekeeperResult, DDResult, TweetContent,
        TradeStatus, GateDecision, ThemeClassification,
        ScanStats, WeeklyContent,

        # Data Loading
        load_portfolio, load_signals, load_themes,
        load_tickers, fetch_live_prices,

        # LLM Client
        LLMClient, create_client, LLMResponse,

        # Prompt Templates
        render_prompt, get_system_prompt,
        GATEKEEPER_SYSTEM, TWEET_SYSTEM,
    )

Example:
    from src.common import (
        get_logger, log_step, log_success,
        LLMClient, render_prompt, get_system_prompt,
        load_portfolio, Stock
    )

    logger = get_logger(__name__)

    # Load data
    trades = load_portfolio()

    # Make LLM call
    client = LLMClient()
    prompt = render_prompt('gatekeeper_analysis', ticker='AAPL', theme='AI')
    response = client.complete(prompt, system=get_system_prompt('gatekeeper'))

    log_success(f"Analysis complete: {response.text[:100]}")
"""

# ═══════════════════════════════════════════════════════════════════════════════
# VERSION
# ═══════════════════════════════════════════════════════════════════════════════

__version__ = "1.0.0"
__author__ = "Sterling Signals"

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION (src.common.config)
# ═══════════════════════════════════════════════════════════════════════════════

from .config import (
    # Paths
    PROJECT_ROOT,
    TRADES_DIR,
    TICKERS_FILE,
    REPORTS_DIR,
    DOCS_DIR,

    # API Keys (from environment)
    ANTHROPIC_API_KEY,
    TWITTER_API_KEY,
    TWITTER_API_SECRET,
    TWITTER_ACCESS_TOKEN,
    TWITTER_ACCESS_SECRET,
    TWITTER_BEARER_TOKEN,

    # Trading Parameters
    TRAILING_STOP_PCT,
    STOP_WARNING_PCT,
    TIGHTEN_STOP_PCT,
    BETA_THRESHOLD,
    BANKER_TIER1,
    BANKER_TIER2,
    BANKER_TIER3,
    HMA_PERIOD,
    HMA_PIVOT_LOOKBACK,

    # LLM Models
    MODEL_SONNET,
    MODEL_OPUS,
    MODEL_THEMATIC,
    MODEL_GATEKEEPER,
    MODEL_TWEET,
    MODEL_NEWSLETTER,
    MODEL_MARKET,
    MODEL_DD_QUICK,
    MODEL_DD_FULL,

    # LLM API Settings
    MAX_RETRIES,
    RATE_LIMIT_COOLDOWN,
    INTER_STEP_DELAY,
    INTER_STOCK_DELAY,
    BACKOFF_FACTOR,
    BACKOFF_MAX_WAIT,
    MIN_REQUEST_INTERVAL,
    MAX_TOKENS,
    DEFAULT_MAX_TOKENS,
    COST_INPUT_PER_M,
    COST_OUTPUT_PER_M,
    COST_WEB_SEARCH,

    # Tweet Schedule
    SLOTS,
    SLOT_TIMES_ET,
    SLOT_TIMES_UTC,
    TWEETS_PER_DAY,
    TWEETS_PER_WEEK,

    # Content Types
    CONTENT_TYPES,

    # Theme Scoring
    THEME_SCORE_PRIME,
    THEME_SCORE_INVESTABLE,
    THEME_SCORE_SELECTIVE,
    THEME_WEIGHTS,

    # Data Download Settings
    YFINANCE_PERIOD,
    YFINANCE_INTERVAL,
    MIN_TRADING_DAYS,

    # Visualization Settings
    CARD_WIDTH,
    CARD_HEIGHT,
    CARD_BG_COLOR,
    CARD_TEXT_COLOR,
    CARD_ACCENT_GREEN,
    CARD_ACCENT_RED,

    # URLs
    SUBSTACK_URL,
    TWITTER_PROFILE_URL,
    TRADINGVIEW_LAYOUT_ID,

    # Validation Helpers
    validate_api_key,
    validate_twitter_credentials,
    validate_email_config,
    get_model_max_tokens,
    get_model_cost,
)

# ═══════════════════════════════════════════════════════════════════════════════
# LOGGING (src.common.logging_config)
# ═══════════════════════════════════════════════════════════════════════════════

from .logging_config import (
    # Logger Factory
    get_logger,
    configure_root_logger,

    # Convenience Functions
    log_step,
    log_success,
    log_warning,
    log_error,
    log_info,
    log_debug,
    log_progress,
    log_section,
    log_banner,
    log_summary,
    log_cost,

    # Context Manager
    LoggedOperation,

    # Formatters
    ConsoleFormatter,
    SimpleConsoleFormatter,
    FileFormatter,

    # Constants
    INDICATORS,
    DEFAULT_LOG_LEVEL,
    LOG_FORMAT,
    LOG_DATE_FORMAT,
)

# ═══════════════════════════════════════════════════════════════════════════════
# DATA MODELS (src.common.data_models)
# ═══════════════════════════════════════════════════════════════════════════════

from .data_models import (
    # Enums
    TradeStatus,
    GateDecision,
    ThemeClassification,
    ThemeFit,
    ThemeType,
    RedFlagLevel,

    # Base Classes
    BaseResult,
    BaseAnalysisResult,

    # Core Data Structures
    Stock,
    Trade,
    Theme,
    SellSignal,

    # Analysis Results
    GatekeeperResult,
    DDResult,

    # Content Generation
    TweetContent,
    WeeklyContent,
    GrokPrompt,

    # Statistics
    ScanStats,

    # Utility Functions
    safe_float,
    safe_int,
)

# ═══════════════════════════════════════════════════════════════════════════════
# DATA LOADER (src.common.data_loader)
# ═══════════════════════════════════════════════════════════════════════════════

from .data_loader import (
    # Portfolio Loading
    load_portfolio,
    load_open_positions,
    get_open_symbols,
    save_portfolio,

    # Signals Loading
    load_signals,
    load_scan_stats,
    save_signals,

    # Themes Loading
    load_themes,
    get_themes_by_classification,

    # Tickers Loading
    load_tickers,

    # Price Fetching
    fetch_live_prices,
    fetch_spy_return,
    fetch_spy_benchmark,

    # Content Queue
    load_content_queue,
    save_content_queue,

    # Chart Manifest
    load_chart_manifest,
)

# ═══════════════════════════════════════════════════════════════════════════════
# LLM CLIENT (src.common.llm_client)
# ═══════════════════════════════════════════════════════════════════════════════

from .llm_client import (
    # Client
    LLMClient,
    create_client,
    check_api_key,

    # Data Structures
    LLMResponse,
    CostTracker,

    # Rate Limiter
    RateLimiter,

    # Helpers
    estimate_cost,
    with_retry,
)

# ═══════════════════════════════════════════════════════════════════════════════
# PROMPT TEMPLATES (src.common.prompt_templates)
# ═══════════════════════════════════════════════════════════════════════════════

from .prompt_templates import (
    # System Prompts
    GATEKEEPER_SYSTEM,
    TWEET_SYSTEM,
    THEMATIC_ANALYZER_SYSTEM,
    MARKET_ANALYZER_SYSTEM,
    DD_QUICK_SYSTEM,
    DD_FULL_SYSTEM,
    NEWSLETTER_SYSTEM,

    # Template Functions
    render_prompt,
    get_system_prompt,
    get_template,
    list_templates,
    list_system_prompts,

    # Helper Functions
    format_list,
    format_dict,
    format_themes_context,
    format_tickers_list,

    # Template Registry
    TEMPLATES,
    SYSTEM_PROMPTS,
)

# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Version
    '__version__',
    '__author__',

    # Config - Paths
    'PROJECT_ROOT', 'TRADES_DIR', 'TICKERS_FILE', 'REPORTS_DIR', 'DOCS_DIR',

    # Config - API Keys
    'ANTHROPIC_API_KEY', 'TWITTER_API_KEY', 'TWITTER_API_SECRET',
    'TWITTER_ACCESS_TOKEN', 'TWITTER_ACCESS_SECRET', 'TWITTER_BEARER_TOKEN',

    # Config - Trading
    'TRAILING_STOP_PCT', 'STOP_WARNING_PCT', 'TIGHTEN_STOP_PCT',
    'BETA_THRESHOLD', 'BANKER_TIER1', 'BANKER_TIER2', 'BANKER_TIER3',
    'HMA_PERIOD', 'HMA_PIVOT_LOOKBACK',

    # Config - Models
    'MODEL_SONNET', 'MODEL_OPUS', 'MODEL_THEMATIC', 'MODEL_GATEKEEPER',
    'MODEL_TWEET', 'MODEL_NEWSLETTER', 'MODEL_MARKET', 'MODEL_DD_QUICK', 'MODEL_DD_FULL',

    # Config - API Settings
    'MAX_RETRIES', 'RATE_LIMIT_COOLDOWN', 'INTER_STEP_DELAY', 'INTER_STOCK_DELAY',
    'BACKOFF_FACTOR', 'BACKOFF_MAX_WAIT', 'MIN_REQUEST_INTERVAL',
    'MAX_TOKENS', 'DEFAULT_MAX_TOKENS', 'COST_INPUT_PER_M', 'COST_OUTPUT_PER_M', 'COST_WEB_SEARCH',

    # Config - Schedule
    'SLOTS', 'SLOT_TIMES_ET', 'SLOT_TIMES_UTC', 'TWEETS_PER_DAY', 'TWEETS_PER_WEEK',
    'CONTENT_TYPES',

    # Config - Theme Scoring
    'THEME_SCORE_PRIME', 'THEME_SCORE_INVESTABLE', 'THEME_SCORE_SELECTIVE', 'THEME_WEIGHTS',

    # Config - Validation
    'validate_api_key', 'validate_twitter_credentials', 'validate_email_config',
    'get_model_max_tokens', 'get_model_cost',

    # Logging
    'get_logger', 'configure_root_logger',
    'log_step', 'log_success', 'log_warning', 'log_error', 'log_info', 'log_debug',
    'log_progress', 'log_section', 'log_banner', 'log_summary', 'log_cost',
    'LoggedOperation', 'ConsoleFormatter', 'SimpleConsoleFormatter', 'FileFormatter',
    'INDICATORS', 'DEFAULT_LOG_LEVEL', 'LOG_FORMAT', 'LOG_DATE_FORMAT',

    # Data Models - Enums
    'TradeStatus', 'GateDecision', 'ThemeClassification', 'ThemeFit', 'ThemeType', 'RedFlagLevel',

    # Data Models - Classes
    'BaseResult', 'BaseAnalysisResult',
    'Stock', 'Trade', 'Theme', 'SellSignal',
    'GatekeeperResult', 'DDResult',
    'TweetContent', 'WeeklyContent', 'GrokPrompt',
    'ScanStats',
    'safe_float', 'safe_int',

    # Data Loader
    'load_portfolio', 'load_open_positions', 'get_open_symbols', 'save_portfolio',
    'load_signals', 'load_scan_stats', 'save_signals',
    'load_themes', 'get_themes_by_classification',
    'load_tickers',
    'fetch_live_prices', 'fetch_spy_return', 'fetch_spy_benchmark',
    'load_content_queue', 'save_content_queue',
    'load_chart_manifest',

    # LLM Client
    'LLMClient', 'create_client', 'check_api_key',
    'LLMResponse', 'CostTracker', 'RateLimiter',
    'estimate_cost', 'with_retry',

    # Prompt Templates
    'GATEKEEPER_SYSTEM', 'TWEET_SYSTEM', 'THEMATIC_ANALYZER_SYSTEM',
    'MARKET_ANALYZER_SYSTEM', 'DD_QUICK_SYSTEM', 'DD_FULL_SYSTEM', 'NEWSLETTER_SYSTEM',
    'render_prompt', 'get_system_prompt', 'get_template', 'list_templates', 'list_system_prompts',
    'format_list', 'format_dict', 'format_themes_context', 'format_tickers_list',
    'TEMPLATES', 'SYSTEM_PROMPTS',
]
