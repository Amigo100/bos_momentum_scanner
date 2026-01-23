# Migration Guide: Using /src/common/ Shared Modules

This document identifies which scripts should be updated to use the new centralized shared modules in `/src/common/`.

## Overview

The `/src/common/` package provides:
- **config.py** - All configuration values and environment variables
- **logging_config.py** - Standardized logging with consistent formatting
- **data_models.py** - Unified dataclasses (Stock, Trade, Theme, etc.)
- **data_loader.py** - Unified data loading functions
- **llm_client.py** - LLM API wrapper with rate limiting and cost tracking
- **prompt_templates.py** - All LLM prompts as templates

## Import Pattern

```python
# Old pattern (root-level imports)
from data_models import Stock, Trade
from config import ANTHROPIC_API_KEY
from logger import log_step, log_success

# New pattern (src.common imports)
from src.common import (
    Stock, Trade,
    ANTHROPIC_API_KEY,
    log_step, log_success
)
```

---

## Scripts to Update

### Priority 1: Core Pipeline Scripts

These scripts should be updated first as they form the core scanner pipeline.

| Script | Current Imports | Update To |
|--------|-----------------|-----------|
| **scanner.py** | Local `Stock` dataclass, hardcoded config | `from src.common import Stock, Trade, BETA_THRESHOLD, BANKER_TIER3, TRAILING_STOP_PCT, get_logger, log_step` |
| **gatekeeper.py** | Local `GateDecision` enum, `GatekeeperResult` | `from src.common import GateDecision, GatekeeperResult, GATEKEEPER_SYSTEM, render_prompt` |
| **thematic_analyzer.py** | Local `Theme`, `CostTracker`, `Config` | `from src.common import Theme, CostTracker, THEMATIC_ANALYZER_SYSTEM, MODEL_SONNET` |
| **portfolio_manager.py** | Local `Trade`, `TradeStatus` | `from src.common import Trade, TradeStatus, load_portfolio, save_portfolio` |
| **dd_automator.py** | Local `DDResult` | `from src.common import DDResult, DD_QUICK_SYSTEM, DD_FULL_SYSTEM, render_prompt` |

### Priority 2: Content Generation Scripts

| Script | Current Imports | Update To |
|--------|-----------------|-----------|
| **tweet_generator.py** | Local `Tweet`, hardcoded slots | `from src.common import TweetContent, WeeklyContent, SLOTS, SLOT_TIMES_ET, TWEET_SYSTEM` |
| **newsletter_compiler.py** | Local data structures | `from src.common import load_signals, load_portfolio, NEWSLETTER_SYSTEM, render_prompt` |
| **grok_prompts_generator.py** | Local `GrokPrompt` | `from src.common import GrokPrompt, load_signals, load_portfolio` |
| **substack_notes_generator.py** | Hardcoded prompts | `from src.common import render_prompt, get_system_prompt, load_portfolio` |
| **market_analyzer.py** | Local config, hardcoded prompt | `from src.common import MARKET_ANALYZER_SYSTEM, MODEL_SONNET, LLMClient` |

### Priority 3: Utility Scripts

| Script | Current Imports | Update To |
|--------|-----------------|-----------|
| **chart_capture.py** | Hardcoded paths | `from src.common import TRADES_DIR, TRADINGVIEW_LAYOUT_ID` |
| **twitter_poster.py** | Hardcoded config | `from src.common import TWITTER_API_KEY, TWITTER_ACCESS_TOKEN, load_content_queue` |
| **email_notifier.py** | Hardcoded SMTP config | `from src.common import SMTP_SERVER, SMTP_PORT, EMAIL_SENDER` |
| **output_paths.py** | Hardcoded paths | `from src.common import TRADES_DIR, PROJECT_ROOT` |

### Priority 4: Analysis/Debug Scripts

| Script | Current Imports | Update To |
|--------|-----------------|-----------|
| **verify_bos.py** | Local calculations | `from src.common import Stock, HMA_PERIOD, BETA_THRESHOLD` |
| **diagnose_bos.py** | Local data structures | `from src.common import load_tickers, Stock` |

---

## Module-by-Module Migration Details

### config.py → src.common.config

**What to replace:**
```python
# Old
MODEL = "claude-sonnet-4-20250514"
TRADES_DIR = Path(__file__).resolve().parent / "trades"
api_key = os.getenv("ANTHROPIC_API_KEY")

# New
from src.common import MODEL_SONNET, TRADES_DIR, ANTHROPIC_API_KEY
```

**Files using config values:**
- scanner.py (lines 37-50)
- gatekeeper.py (line 42)
- thematic_analyzer.py (lines 25-60)
- tweet_generator.py (lines 79-84)
- market_analyzer.py (lines 40-41)
- dd_automator.py (lines 30-40)

### logging → src.common.logging_config

**What to replace:**
```python
# Old
from logger import get_logger, log_step, log_success
print(f"  ✓ Success: {msg}")

# New
from src.common import get_logger, log_step, log_success
log_success(f"Success: {msg}")
```

**Files using logging:**
- scanner.py (throughout)
- gatekeeper.py (throughout)
- thematic_analyzer.py (throughout)
- portfolio_manager.py (throughout)
- tweet_generator.py (throughout)
- newsletter_compiler.py (throughout)

### data_models.py → src.common.data_models

**Dataclass replacements:**
| Old Location | Old Class | New Import |
|--------------|-----------|------------|
| scanner.py | `Stock` | `from src.common import Stock` |
| portfolio_manager.py | `Trade`, `TradeStatus` | `from src.common import Trade, TradeStatus` |
| gatekeeper.py | `GateDecision`, `GatekeeperResult` | `from src.common import GateDecision, GatekeeperResult` |
| thematic_analyzer.py | `Theme` | `from src.common import Theme` |
| dd_automator.py | `DDResult` | `from src.common import DDResult` |
| tweet_generator.py | `Tweet`, `WeeklyContent` | `from src.common import TweetContent, WeeklyContent` |
| grok_prompts_generator.py | `GrokPrompt` | `from src.common import GrokPrompt` |

### data_loader.py → src.common.data_loader

**Function replacements:**
```python
# Old (scattered implementations)
def load_portfolio():
    # Each script has its own implementation

# New (single source of truth)
from src.common import load_portfolio, load_signals, load_themes, fetch_live_prices
```

**Files with duplicate data loading:**
- tweet_generator.py
- grok_prompts_generator.py
- newsletter_compiler.py
- substack_notes_generator.py
- chart_capture.py

### llm_client.py → src.common.llm_client

**What to replace:**
```python
# Old
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
response = client.messages.create(model=MODEL, ...)

# New
from src.common import LLMClient, create_client
client = create_client()
response = client.complete(prompt, system=system_prompt, web_search=True)
```

**Files making LLM calls:**
- gatekeeper.py
- thematic_analyzer.py
- dd_automator.py
- tweet_generator.py
- newsletter_compiler.py
- market_analyzer.py

### prompt_templates.py → src.common.prompt_templates

**What to replace:**
```python
# Old
GATEKEEPER_SYSTEM_PROMPT = """You are a Senior Risk Manager..."""
user_prompt = f"Analyze {ticker}..."

# New
from src.common import GATEKEEPER_SYSTEM, render_prompt
prompt = render_prompt('gatekeeper_analysis', ticker=ticker, theme=theme)
```

**Files with hardcoded prompts:**
- gatekeeper.py (SYSTEM_PROMPT at line 45)
- thematic_analyzer.py (multiple prompts)
- dd_automator.py (DD_SYSTEM)
- tweet_generator.py (TWEET_SYSTEM_PROMPT)
- newsletter_compiler.py (prompts throughout)
- market_analyzer.py (MARKET_ANALYSIS_SYSTEM)

---

## Migration Steps for Each Script

### Example: Migrating scanner.py

1. **Add src.common imports at top:**
```python
from src.common import (
    # Config
    BETA_THRESHOLD, BANKER_TIER3, TRAILING_STOP_PCT,
    TRADES_DIR, TICKERS_FILE,

    # Logging
    get_logger, log_step, log_success, log_warning, log_banner, log_section,
    LoggedOperation,

    # Data Models
    Stock, Trade, SellSignal, ScanStats,

    # Data Loading
    load_portfolio, load_tickers, save_signals,
    fetch_live_prices,
)
```

2. **Remove local Stock dataclass definition (lines 25-60)**

3. **Replace hardcoded values:**
```python
# Before
if stock.beta >= 1.5 and stock.banker >= 55:

# After
if stock.beta >= BETA_THRESHOLD and stock.banker >= BANKER_TIER3:
```

4. **Replace print statements with logging:**
```python
# Before
print(f"  ✓ Loaded {len(tickers)} tickers")

# After
log_success(f"Loaded {len(tickers)} tickers")
```

5. **Test the script:**
```bash
python scanner.py --no-llm --top 10
```

---

## Backwards Compatibility

The root-level modules (`config.py`, `data_models.py`, `llm_client.py`, etc.) remain in place for backwards compatibility. Scripts can be migrated incrementally.

**Recommended approach:**
1. Start with new scripts using `src.common`
2. Migrate core pipeline scripts first
3. Update content generation scripts
4. Update utilities last

---

## Testing After Migration

After migrating a script:

```bash
# Syntax check
python -m py_compile script_name.py

# Basic functionality test
python script_name.py --help

# For scanner
python scanner.py --no-llm --top 10

# For tweet generator
python tweet_generator.py --mock

# For portfolio manager
python portfolio_manager.py --report
```

---

## Notes

- The `src.common` package uses relative imports internally
- All dataclasses include `to_dict()` methods for JSON serialization
- Logging functions print directly (don't use a logger instance)
- The LLMClient includes automatic rate limiting and cost tracking
