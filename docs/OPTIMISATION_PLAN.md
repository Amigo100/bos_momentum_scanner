# CODEBASE OPTIMISATION PLAN

**Generated:** 2026-01-23
**Scope:** All Python modules in BoS Momentum Scanner
**Methodology:** Static analysis of code patterns, duplication, quality indicators

---

## EXECUTIVE SUMMARY

| Metric | Current State | Potential Improvement |
|--------|---------------|----------------------|
| Total Python Files | 23 modules | Consolidate to ~18 |
| Estimated Code Duplication | 30-40% | Reduce to <10% |
| Test Coverage | ~0% | Target 60%+ on core logic |
| Type Hint Coverage | ~60% | Target 95% |

**Key Findings:**
- Core pipeline (scanner → thematic → gatekeeper) is well-architected
- Significant duplication in data loading, LLM calls, and prompt templates
- Two modules (`output_paths.py`, `marketing_vocabulary.py`) are exemplary
- Missing centralized utilities for common patterns

---

## FILE ASSESSMENT TABLE

Sorted by **optimisation priority** (highest first):

| Priority | File | Purpose | Criticality | Type Hints | Error Handling | LOC | Key Issues |
|----------|------|---------|-------------|------------|----------------|-----|------------|
| **P1** | `scanner.py` | Main pipeline orchestrator | Core | Partial | Good | ~1500 | CSV/JSON loading duplicated; rate limiting scattered |
| **P1** | `thematic_analyzer.py` | Theme discovery + scoring (Step 5) | Core | Partial | Good | ~400 | Rate limiting custom impl; cost tracking duplicated |
| **P1** | `gatekeeper.py` | Final quality gate (Step 6) | Core | Yes | Good | ~350 | Result dataclass similar to others; model config scattered |
| **P2** | `tweet_generator.py` | Generate 35 weekly tweets | Supporting | Yes | Good | ~1540 | 20+ prompt templates redundant; scheduling logic duplicated |
| **P2** | `grok_prompts_generator.py` | Generate 21 Grok prompts | Supporting | Yes | Good | ~1600 | 15+ factory functions identical pattern; data loading duplicated |
| **P2** | `newsletter_compiler.py` | Compile HTML newsletter | Supporting | Partial | Basic | ~885 | Regex markdown→HTML fragile; SPY calculation duplicated |
| **P2** | `dd_automator.py` | Automated due diligence | Supporting | Yes | Good | ~300 | DDResult similar to GatekeeperResult |
| **P2** | `substack_notes_generator.py` | Tue/Thu Substack notes | Supporting | Partial | Good | ~500 | Data loading duplicated from grok_prompts |
| **P3** | `portfolio_manager.py` | Trade tracking + exports | Core | Yes | Good | ~912 | Price fetching duplicated; hardcoded stop percentages |
| **P3** | `market_analyzer.py` | Market context generation | Supporting | Partial | Basic | ~250 | LLM wrapper needed |
| **P3** | `twitter_poster.py` | Post tweets to X | Glue | Partial | Good | ~200 | Error recovery could be stronger |
| **P3** | `chart_capture.py` | TradingView screenshots | Supporting | Partial | Basic | ~300 | Playwright session management |
| **P4** | `card_generator.py` | Visual trade cards | Supporting | Yes | Good | ~400 | PIL patterns could be shared with funnel_graphic |
| **P4** | `funnel_graphic.py` | Funnel visualization | Supporting | Yes | Good | ~350 | Duplicate PIL drawing utilities |
| **P4** | `email_notifier.py` | SMTP notifications | Glue | Partial | Good | ~150 | Config management |
| **P4** | `due_diligence.py` | DD prompt utilities | One-off | Partial | Basic | ~200 | Could merge with dd_automator |
| **P4** | `due_diligence_prompts.py` | DD prompt templates | One-off | No | None | ~150 | Static templates |
| **P4** | `newsletter_prompts.py` | Newsletter prompt templates | One-off | No | None | ~350 | Static templates |
| **MAINTAIN** | `output_paths.py` | Directory structure management | Infra | Yes | Good | ~310 | Exemplary design - extend don't rewrite |
| **MAINTAIN** | `marketing_vocabulary.py` | Brand language enforcement | Infra | Yes | Good | ~280 | Exemplary - increase usage across codebase |

---

## IDENTIFIED PATTERNS FOR REFACTORING

### 1. Data Loading Duplication (CRITICAL)

**Problem:** 5 different CSV/JSON parsing implementations across files

| File | Function | What It Does |
|------|----------|--------------|
| `portfolio_manager.py` | `load_trades()` | Parse portfolio.csv |
| `grok_prompts_generator.py` | `load_open_positions_csv()` | Parse portfolio.csv (duplicate) |
| `tweet_generator.py` | `load_briefing_data()` | Parse newsletter_briefing.md |
| `grok_prompts_generator.py` | `parse_briefing_markdown()` | Parse newsletter_briefing.md (duplicate) |
| `newsletter_compiler.py` | `load_*()` functions | Multiple loaders |

**Solution:** Create `data_loader.py`

```python
# Proposed data_loader.py API
def load_portfolio() -> List[Trade]
def load_signals() -> Dict
def load_briefing() -> BriefingData
def load_themes() -> List[Theme]
def fetch_live_prices(tickers: List[str]) -> Dict[str, float]
```

**Impact:** ~25% code reduction in affected files

---

### 2. LLM API Call Patterns (HIGH)

**Problem:** Rate limiting, cost tracking, and error handling implemented independently in 6+ files

| File | Implementation |
|------|----------------|
| `scanner.py` | Custom retry with delays |
| `thematic_analyzer.py` | Exponential backoff |
| `gatekeeper.py` | Similar backoff |
| `dd_automator.py` | Similar backoff |
| `tweet_generator.py` | Basic retry |
| `newsletter_compiler.py` | Basic retry |

**Solution:** Create `llm_client.py`

```python
# Proposed llm_client.py API
class LLMClient:
    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        self.cost_tracker = CostTracker()

    @rate_limited(calls_per_minute=50)
    @retry(max_attempts=5, backoff_factor=2)
    def complete(self, prompt: str, web_search: bool = False) -> str

    def get_total_cost(self) -> float
```

**Impact:** Centralized cost control, consistent rate limiting

---

### 3. Prompt Template Sprawl (MEDIUM)

**Problem:** 30+ prompt templates hardcoded across files with 80% structural similarity

**Locations:**
- `tweet_generator.py`: `TWEET_SYSTEM_PROMPT` + category contexts
- `grok_prompts_generator.py`: 15+ `create_*_prompt()` functions
- `thematic_analyzer.py`: `THEMATIC_SYSTEM_PROMPT`
- `gatekeeper.py`: `GATEKEEPER_SYSTEM_PROMPT`

**Solution:** Create `prompt_templates.py`

```python
# Proposed structure
TEMPLATES = {
    "tweet_system": Template("You are a financial content writer..."),
    "tweet_buy_signal": Template("Generate {count} tweets about ${ticker}..."),
    "gatekeeper_system": Template("You are a senior analyst..."),
    # ...etc
}

def render_prompt(template_name: str, **kwargs) -> str
```

**Impact:** Version control for prompts, easier A/B testing

---

### 4. Result Dataclass Proliferation (LOW)

**Problem:** 6+ similar result dataclasses with overlapping fields

| Class | File | Common Fields |
|-------|------|---------------|
| `GatekeeperResult` | gatekeeper.py | ticker, decision, conviction, reasoning |
| `DDResult` | dd_automator.py | ticker, decision, conviction, reasoning |
| `GrokPrompt` | grok_prompts_generator.py | category, text, ticker |
| `Tweet` | tweet_generator.py | category, text, ticker |
| `WeeklyContent` | tweet_generator.py | signals, themes, positions |
| `PortfolioData` | grok_prompts_generator.py | signals, themes, positions |

**Solution:** Create `data_models.py` with inheritance

```python
@dataclass
class BaseAnalysisResult:
    ticker: str
    decision: str
    conviction: int
    reasoning: str
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class GatekeeperResult(BaseAnalysisResult):
    red_flag_level: str
    catalyst_summary: str
    # ...specific fields
```

---

## INCONSISTENCIES ACROSS FILES

### Date/Time Handling

| Pattern | Files Using It |
|---------|----------------|
| `datetime.now().strftime("%Y-%m-%d")` | 8 files |
| ISO week: `datetime.now().isocalendar()` | 3 files (different implementations) |
| Day offset from Monday | `tweet_generator.py` (old) |
| Day offset from Saturday | `tweet_generator.py` (new), `grok_prompts_generator.py` |

**Fix:** Create `scheduler.py` with unified date utilities

---

### Marketing Vocabulary Validation

| File | Validation Status |
|------|-------------------|
| `tweet_generator.py` | ✅ Validates all tweets |
| `grok_prompts_generator.py` | ✅ Validates prompts |
| `newsletter_compiler.py` | ✅ Validates output |
| `substack_notes_generator.py` | ✅ Validates notes |
| `dd_automator.py` | ❌ No validation |
| `market_analyzer.py` | ❌ No validation |

**Fix:** Add validation to remaining content generators

---

### Error Handling Approaches

| Approach | Files |
|----------|-------|
| `try/except` with logging | `scanner.py`, `portfolio_manager.py` |
| `try/except` with fallback | `tweet_generator.py` |
| `try/except` silent continue | `grok_prompts_generator.py` |
| Minimal handling | `newsletter_compiler.py` |

**Fix:** Establish standard error handling pattern

---

## QUICK WINS (High Impact, Low Effort)

### 1. Centralize Configuration Constants
**Effort:** 1 hour | **Impact:** Single source of truth

Create `config.py`:
```python
# config.py
TRAILING_STOP_PCT = 0.20
STOP_WARNING_PCT = 0.05
SLOTS = {1: "pre_market", 2: "morning", 3: "midday", 4: "power_hour", 5: "after_hours"}
SLOT_TIMES_ET = {1: "08:00", 2: "10:00", 3: "12:30", 4: "15:30", 5: "18:00"}
MODEL_SONNET = "claude-sonnet-4-20250514"
MODEL_OPUS = "claude-opus-4-5-20251101"
```

**Files to update:** scanner.py, portfolio_manager.py, tweet_generator.py, grok_prompts_generator.py

---

### 2. Add Marketing Validation Decorator
**Effort:** 30 min | **Impact:** Zero brand violations

```python
# In marketing_vocabulary.py
def validate_output(func):
    """Decorator to validate function output for banned terms."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        if isinstance(result, str):
            is_valid, violations = validate_content(result)
            if not is_valid:
                logger.warning(f"Output contains banned terms: {violations}")
        return result
    return wrapper
```

---

### 3. Complete Type Hints in Core Files
**Effort:** 2 hours | **Impact:** IDE support, catch bugs early

Priority files:
1. `thematic_analyzer.py` - Add return types to all functions
2. `gatekeeper.py` - Add parameter types
3. `market_analyzer.py` - Full type coverage

---

### 4. Standardize Logging
**Effort:** 1 hour | **Impact:** Debuggability

Current: Mix of `print()` statements and no logging

Fix: Add `logger.py` utility
```python
import logging

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger
```

---

## IMPLEMENTATION ROADMAP

### Phase 1: Infrastructure (Week 1)
| Task | Files Affected | Effort | Impact |
|------|----------------|--------|--------|
| Create `config.py` | All | 1h | Centralized settings |
| Create `data_loader.py` | 5 files | 4h | 25% code reduction |
| Create `scheduler.py` | 4 files | 2h | Unified date logic |
| Add logging utility | All | 1h | Debuggability |

### Phase 2: API Layer (Week 2)
| Task | Files Affected | Effort | Impact |
|------|----------------|--------|--------|
| Create `llm_client.py` | 6 files | 6h | Centralized costs |
| Refactor LLM calls | scanner, analyzers | 4h | Consistent rate limiting |
| Add cost dashboard | New file | 2h | Budget visibility |

### Phase 3: Content Generation (Week 3)
| Task | Files Affected | Effort | Impact |
|------|----------------|--------|--------|
| Create `prompt_templates.py` | 4 files | 4h | Maintainable prompts |
| Refactor prompt factories | grok_prompts, tweets | 6h | 50% less code |
| Create `data_models.py` | 6 files | 3h | Unified structures |

### Phase 4: Testing (Week 4)
| Task | Coverage Target | Effort | Impact |
|------|-----------------|--------|--------|
| Unit tests: `data_loader.py` | 90% | 4h | Parsing reliability |
| Unit tests: `scheduler.py` | 95% | 2h | Date edge cases |
| Integration: core pipeline | 70% | 8h | Regression prevention |

---

## METRICS TO TRACK

After implementing optimizations:

| Metric | Before | Target |
|--------|--------|--------|
| Lines of Code | ~12,000 | ~9,000 (-25%) |
| Duplicated Functions | ~35 | <10 |
| Type Hint Coverage | 60% | 95% |
| Test Coverage | 0% | 60% |
| Files with Marketing Validation | 4/10 | 10/10 |
| Centralized Config Values | 0% | 100% |

---

## APPENDIX: FILE DEPENDENCY GRAPH

```
scanner.py
├── thematic_analyzer.py
├── gatekeeper.py
├── portfolio_manager.py
├── output_paths.py
└── email_notifier.py

tweet_generator.py
├── marketing_vocabulary.py
├── output_paths.py
└── (data from scanner outputs)

grok_prompts_generator.py
├── marketing_vocabulary.py
├── output_paths.py
└── (data from scanner outputs)

newsletter_compiler.py
├── marketing_vocabulary.py
├── output_paths.py
└── (data from scanner outputs)

dd_automator.py
├── due_diligence_prompts.py
└── (API client)

twitter_poster.py
├── (content_queue.json)
└── (X API)
```

---

**Document Maintainer:** Claude Code
**Next Review:** After Phase 1 implementation
