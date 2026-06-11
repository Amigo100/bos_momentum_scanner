# 05 - Content Generation

> Sterling Signals / BoS Momentum Scanner
> Audit date: 2026-02-06
> Branch: `refactor/cleanup-reorg`

---

## 1. Overview

The content generation subsystem transforms raw scanner outputs (signals, themes, portfolio data) into publication-ready content across multiple channels: X/Twitter tweets, Substack newsletters, Substack notes, and Grok prompts.

**Scope:** 13 Python files totalling 12,032 lines in the `content/` package, plus 3 persona YAML files and 1 examples JSON file in `content/personas/` and `content/examples/`.

| File | Lines | Role |
|------|------:|------|
| `content/reaction_generator.py` | 2,451 | Primary tweet generator (3 accounts, persona-driven) |
| `content/tweet_generator.py` | 2,205 | Legacy tweet generator (template-first fallback) |
| `content/content_planner.py` | 1,440 | Persona-based content planning and cross-account validation |
| `content/grok_prompts_generator.py` | 1,612 | 21 weekly Grok prompts for manual X posting |
| `content/newsletter_compiler.py` | 970 | Newsletter compilation (markdown to HTML) |
| `content/chart_capture.py` | 648 | TradingView chart screenshots via Playwright |
| `content/funnel_graphic.py` | 671 | Scan funnel visualisation via PIL |
| `content/substack_content_generator.py` | 528 | Mon/Thu/Sat/Sun Substack post generation |
| `content/substack_notes_generator.py` | 502 | Tuesday/Thursday Substack Notes |
| `content/market_analyzer.py` | 265 | Market context via Claude + web search |
| `content/winner_showcase_generator.py` | 271 | Winner showcase with entry price rules |
| `content/editorial_board.py` | 266 | Editorial planning (cross-account coordination) |
| `content/morning_briefing.py` | 203 | Morning briefing formatter |

**Content output volumes per week:**
- 105 tweets (3 accounts x 35 tweets)
- 1 HTML newsletter
- 2 Substack Notes (Tuesday + Thursday)
- 4 Substack posts (Mon/Thu/Sat/Sun)
- 21 Grok prompts
- Charts for all PASS signals and open positions

---

## 2. Tweet Generation Architecture

### 2.1 reaction_generator.py (Primary) -- 2,451 lines

The primary tweet generator uses a "reaction-based" approach: personas react to scanner data rather than filling templates.

**File:** `/Users/mattydeighton/Downloads/bos_momentum_scanner/content/reaction_generator.py`

#### Configuration (lines 54-95)

```python
MODEL = "claude-sonnet-4-20250514"    # line 58
MAX_TOKENS = 4096                      # line 59
PERSONAS_DIR = Path(__file__).parent / "personas"   # line 61
EXAMPLES_FILE = Path(__file__).parent / "examples" / "tweet_examples.json"  # line 62
NEWSLETTER_URL = "https://sterlingsignals.substack.com"  # line 64
```

Account mapping (lines 67-83):

| Account Key | Persona File | Queue File | Examples Key |
|-------------|-------------|------------|--------------|
| `main` | `alex.yaml` | `content_queue.json` | `alex` |
| `account2` | `rozalia.yaml` | `content_queue_account2.json` | `rozalia` |
| `account3` | `james.yaml` | `content_queue_account3.json` | `james` |

Day order (line 86): `['Saturday', 'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']` -- starts Saturday for newsletter drop.

Slot times (lines 89-95):

| Slot | Time (ET) | Context |
|------|-----------|---------|
| 1 | 08:00 | Morning, starting the day |
| 2 | 10:00 | Mid-morning, market open 30 mins |
| 3 | 12:30 | Midday, lunch break |
| 4 | 15:30 | Power hour (3:30pm) |
| 5 | 18:00 | After hours, reflecting |

#### Dataclasses

**Persona** (lines 102-112):

```python
@dataclass
class Persona:
    name: str
    identity: dict
    background: str
    personality: dict
    voice: dict
    content_approach: dict
    example_tweets: dict
    day_tendencies: dict
```

**MarketContext** (lines 115-157):

```python
@dataclass
class MarketContext:
    scan_date: str
    green_signals: List[dict]
    consider_signals: List[dict]
    signal_count: int
    open_positions: List[dict]
    winners: List[dict]          # 25%+ positions
    losers: List[dict]           # Negative positions
    closed_trades: List[dict]
    hot_themes: List[str]
    total_positions: int
    green_count: int
    portfolio_vs_spy: float
    is_quiet_week: bool
    has_big_winner: bool
    has_new_signals: bool
    chart_manifest: Dict[str, str]
    theme_tickers: Dict[str, List[Dict]]
    content_phase: str           # "EARLY" / "BUILDING" / "ESTABLISHED"
    scan_stats: Dict[str, int]
```

**DayContext** (lines 160-174):

```python
@dataclass
class DayContext:
    day_name: str
    day_number: int       # 0=Saturday
    is_weekend: bool
    is_friday: bool
    is_scan_day: bool
    time_reference: str   # "Friday's close", "today", etc.
    mood: str
    energy: str
    temporal: dict
```

**GeneratedTweet** (lines 178-194):

```python
@dataclass
class GeneratedTweet:
    id: str
    day: str
    slot: int
    time: str
    text: str
    category: str
    account: str
    persona_name: str
    generation_method: str = 'reaction'
    mentioned_tickers: List[str] = field(default_factory=list)
    has_url: bool = False
    char_count: int = 0
    image_path: Optional[str] = None
```

**ContentTracker** (lines 198-334): Tracks ticker mentions, phrase usage, and fact mentions across the week to prevent repetition.

Key limits:
- `TICKER_LIMIT_PER_ACCOUNT = 2` (line 213) -- each ticker mentioned max 2x per account per week
- `FACT_LIMITS` (lines 214-219):
  - `scan_count`: 2 (e.g., "1,800 stocks")
  - `portfolio_status`: 3 (e.g., "3 green, 1 red")
  - `spy_comparison`: 3 (e.g., "+12.5% vs SPY")
  - `winner_pnl`: 2 (specific winner P&L)

Methods:
- `record_tweet(text, account_id, persona_name)` (line 227) -- records trackable items from a generated tweet
- `check_tweet(text, account_id, persona_name) -> List[str]` (line 255) -- returns violations
- `get_avoidance_guidance(account_id, persona_name) -> str` (line 291) -- generates avoidance rules for the next Claude call, includes content-shift guidance based on how many days have been generated

Per-persona phrase weekly limits (lines 337-356):

| Persona | Phrase | Max |
|---------|--------|-----|
| alex | "the system" | 3 |
| alex | "the scanner" | 3 |
| alex | "look," | 3 |
| rozalia | "here's the thing" | 2 |
| rozalia | "i wish someone told me" | 2 |
| rozalia | "honest question" | 2 |
| rozalia | "the lesson" | 3 |
| james | "eyes on" | 2 |
| james | "let the winners run" | 1 |
| james | "that's how you" | 2 |
| james | "here we go" | 2 |

#### V2 Flow -- Reaction-Based LLM Generation

The generation prompt is assembled by `build_generation_prompt()` (lines 1072-1135) from these components:

1. **Persona section** -- `build_persona_section(persona)` (line 903): name, background, personality traits, vocabulary (uses/never_uses), emoji guidance, content approach
2. **Structured data blocks** -- `build_structured_data_blocks(ctx)` (line 504): categorised scanner data including buy signals, watchlist, winners, hot themes with tickers, portfolio snapshot, scan funnel stats
3. **Day section** -- `build_day_section(day_ctx, persona)` (line 944): temporal rules, weekend/Friday restrictions, mood and energy
4. **Anti-repetition rules** -- from `ContentTracker.get_avoidance_guidance()`: tickers/phrases/facts at limit
5. **FinTwit examples** -- hardcoded example tweets showing ideal style
6. **Phase guidance** -- `_get_phase_guidance(content_phase)`: EARLY/BUILDING/ESTABLISHED content strategy
7. **Few-shot examples** -- `build_examples_section(persona_key, examples, ctx)` (line 996): context-aware examples from `tweet_examples.json`
8. **Slot guidance** -- `build_slot_guidance()` (line 1038): 5-tweet format, rules, variety requirements

Output format: JSON array of 5 tweet objects `[{"slot": N, "text": "...", "has_url": bool}]`.

Generation function: `generate_day_tweets()` (lines 1142-1196):

```python
def generate_day_tweets(
    client: anthropic.Anthropic,
    persona: Persona,
    persona_key: str,
    market_ctx: MarketContext,
    day_ctx: DayContext,
    examples: dict,
    account_id: str,
    tracker: Optional[ContentTracker] = None
) -> List[GeneratedTweet]:
```

- Makes single Claude API call per account per day (7 calls per account, 21 total)
- Parses JSON response via `parse_json_response()` (line 1199)
- Falls back to `generate_fallback_tweets()` (line 1260) on failure -- 5 generic tweets

#### Content Loading

- `load_chart_manifest()` (line 417): Scans `twitter/output/charts/` and `twitter/output/charts/` for PNG files, maps ticker to most recent file path
- `build_theme_ticker_map(scanner_data)` (line 436): Builds `theme_name -> [{ticker, price, status, theme_score}]` from signals.json. Status values: `SIGNAL`, `WATCHLIST`, `IN_THEME`
- `create_market_context(scanner_data, portfolio_data)` (line 759): Master context builder. Fetches live prices via `fetch_current_prices()` from `core.portfolio_manager`, recalculates P&L, detects content phase, loads scan stats
- `detect_content_phase(positions, winners) -> str` (line 404): Returns `"EARLY"` (no positions), `"BUILDING"` (green positions), or `"ESTABLISHED"` (25%+ winners)

#### FinTwit Validation (lines 604-698)

Banned phrases (lines 607-614): 18 phrases including "theme keeps delivering", "trust the process", "still bleeding", "stay tuned"

Loser patterns (lines 616-620): 9 regex patterns detecting emphasis on losing positions

`validate_fintwit_style(tweet, assignment)` (line 641): Category-specific validation:
- `scanner_result`: must have tickers and prices
- `theme_analysis`: must have 2+ tickers, should have prices/percentages
- `performance`: must have specific winners with percentage gains
- `watchlist`: must have tickers, should have prices
- `newsletter_cta`: must include substack URL
- `funnel_graphic`: must include scan numbers
- `process`: should reference specific ticker example
- `educational`: should use specific ticker as example

`build_fallback_tweet(category, ctx, slot) -> str` (line 700): Deterministic data-rich fallback for each category.

#### Main Generation Flow (lines 1420-1549)

`generate_weekly_content(scanner_data, portfolio_data, output_dir, accounts_to_generate) -> Dict[str, List[dict]]`:

1. Initialise Anthropic client, load examples, build MarketContext
2. For each account in `['main', 'account2', 'account3']`:
   a. Load persona from YAML
   b. Create ContentTracker for anti-repetition
   c. For each day in `DAYS` (Sat-Fri):
      - Create DayContext
      - Call `generate_day_tweets()` (single Claude call = 5 tweets)
      - Record all tweets in tracker for next day's avoidance
      - Validate with `validate_day_tweets()`
3. Run `deduplicate_weekly_content()` across all accounts (line 1528)
4. Post-fix temporal references (line 1531): replace "yesterday" on wrong days
5. Save content queues to JSON files

#### Output Saving

Saves per account:
- `twitter/output/content_queue.json` (main)
- `twitter/output/content_queue_account2.json`
- `twitter/output/content_queue_account3.json`

Tweet dict format:

```json
{
    "id": "saturday_1_main",
    "day": "Saturday",
    "slot": 1,
    "time": "08:00",
    "text": "Tweet content...",
    "category": "scanner_result",
    "account": "main",
    "persona": "Alexander Sterling",
    "scheduled_date": "2026-02-07",
    "status": "pending",
    "generation_method": "reaction",
    "char_count": 245
}
```

---

### 2.2 tweet_generator.py (Legacy Fallback) -- 2,205 lines

**File:** `/Users/mattydeighton/Downloads/bos_momentum_scanner/content/tweet_generator.py`

Legacy template-first tweet generator. Still functional and used as fallback if `reaction_generator.py` is unavailable.

#### Imports (lines 1-100)

Notable conditional imports:
- `anthropic` (required, exits on missing)
- `config.output_paths` (optional, `OUTPUT_PATHS_AVAILABLE` flag)
- `distribution.signal_tracker` (optional, `SIGNAL_TRACKER_AVAILABLE` flag) -- provides `should_post_beat_spy()`, `has_enough_wins()`, `filter_public_positions()`, `get_uncelebrated_wins()`, `calculate_portfolio_vs_spy()`, `check_cold_streak()`
- `config` settings (optional) -- `MARKETING_THRESHOLDS`, `SIGNAL_COLORS`, `CONVICTION_LANGUAGE`, `can_show_entry_price`, etc.

#### Template System (AUTHENTIC_TEMPLATES, lines 235-593)

16-category template library with `{{PLACEHOLDER}}` markers. Categories:
- `scanner_result`, `theme_analysis`, `performance`, `watchlist`
- `educational`, `engagement`, `newsletter_cta`, `funnel_graphic`
- `process`, `power_hour`, `power_hour_recap`, `market_outlook`
- `beat_spy`, `winner_reaction`, `week_ahead`, `after_hours`

Each category has 3-6 template variants to prevent repetition.

#### Data Structures

**Tweet** dataclass (line 658):

```python
@dataclass
class Tweet:
    id: str
    day: str
    slot: int
    category: str
    text: str
    ticker: str
    theme: str
    image_path: str
    scheduled_date: str
    status: str
    posted_at: str
    tweet_id: str
    template_id: str
    generation_method: str
```

**WeeklyContent** dataclass (line 680):

```python
@dataclass
class WeeklyContent:
    pass_signals: List[dict]
    consider_signals: List[dict]
    caution_signals: List[dict]
    sell_signals: List[dict]
    open_positions: List[dict]
    closed_trades: List[dict]
    themes: dict           # 4 tiers: prime, investable, selective, avoid
    scan_date: str
    chart_manifest: dict
```

**TemplateTracker** class (line 600): Tracks used template IDs per category, prevents reuse within a week.

#### Generation Modes

1. **Template-only** (default): Select template from `AUTHENTIC_TEMPLATES`, populate placeholders with data
2. **Hybrid**: Template + Claude enhancement pass
3. **Claude-only**: LLM generates from scratch with template examples as guidance
4. **Mock**: No API calls, for testing

#### Multi-Account Variation

- `generate_account_variations(base_queue_path)`: Uses Claude to rephrase main account tweets for account2/account3
- `_rephrase_tweet_batch(client, tweets_batch, account_key)`: Batch rephrasing via single Claude call
- `_rotate_slots(queue, account_key)`: Rotate slot assignments to avoid same-time posting
- `_fallback_copy()`: If rephrasing fails, copy base queue unchanged

**Key difference from reaction_generator:** Account variations are generated post-hoc by rephrasing the main account's tweets, rather than generating independently per persona.

---

### 2.3 content_planner.py -- 1,440 lines

**File:** `/Users/mattydeighton/Downloads/bos_momentum_scanner/content/content_planner.py`

More sophisticated content planning system with data-driven category selection and cross-account coordination. Not yet fully integrated as the primary generator.

#### Persona Definitions (lines 56-172)

**PersonaVoice** dataclass (lines 57-62):

```python
@dataclass
class PersonaVoice:
    tone: str                    # 'authoritative', 'conversational', 'direct'
    formality: str               # 'professional', 'approachable', 'casual'
    traits: List[str]            # ['data-driven', 'precise', 'confident']
    avoid: List[str]             # Things this persona wouldn't say
```

**Persona** dataclass (lines 65-76):

```python
@dataclass
class Persona:
    name: str                    # 'The System', 'The Mentor', 'The Trader'
    account_id: str              # 'main', 'account2', 'account3'
    archetype: str               # 'Analyst', 'Teacher', 'Practitioner'
    voice: PersonaVoice
    focus_areas: Dict[str, List[str]]  # primary, secondary, tertiary
    content_mix: Dict[str, float]      # category -> percentage
    signature_phrases: List[str]
    post_timing: str             # 'market_aligned', 'educational_hours', etc.
```

Three hardcoded personas (lines 79-172):

| Key | Name | Archetype | Tone | Content Mix |
|-----|------|-----------|------|-------------|
| `main` | The System | Analyst | authoritative / professional | signals 45%, educational 25%, engagement 15%, themes 15% |
| `account2` | The Mentor | Teacher | conversational / approachable | educational 40%, signals 25%, engagement 20%, themes 15% |
| `account3` | The Trader | Practitioner | direct / casual | signals 35%, market_color 25%, engagement 25%, educational 15% |

#### Day-Aware Content Rules (lines 175-255)

**DayRules** dataclass (lines 179-188):

```python
@dataclass
class DayRules:
    day: str
    context: str
    allowed_phrases: List[str]
    blocked_phrases: List[str]
    time_reference: str
    primary_focus: List[str]
    avoid_categories: List[str]
```

`DAY_CONTENT_RULES` dict (lines 191-255) defines rules for each day of the week. Saturday and Sunday block "Today", "Power hour", "Into the close". Friday allows all live-market references.

#### Content Availability System (lines 258-299)

**ContentCategory** enum (lines 262-288): 18 categories:
- Signal-based (requires data): `WINNER_SHOWCASE`, `SELF_QUOTE`, `BEAT_SPY`, `SIGNAL_SPOTLIGHT`, `WATCHLIST_UPDATE`, `THEME_MOMENTUM`, `EARLY_MOVERS`, `CLOSED_TRADE`, `MILESTONE_ALERT`
- Always available: `FUNNEL_STATS`, `EDUCATIONAL`, `ENGAGEMENT`, `PROCESS_EXPLAINER`, `NEWSLETTER_PROMO`
- Building phase specific: `PATIENCE_CONTENT`, `WHY_PROCESS_MATTERS`
- Time-specific: `POWER_HOUR`, `MARKET_COLOR`

**ContentRequirement** dataclass (lines 291-299):

```python
@dataclass
class ContentRequirement:
    category: ContentCategory
    check_function: Callable[[dict], bool]
    priority: int                # 1=highest, 5=lowest
    valid_personas: List[str]    # Which personas can use this
    min_data_points: int = 1
    description: str = ""
```

#### Key Classes

**ContentPlanner**: Analyses scanner data and determines content allocation.
- `_assess_availability()`: Checks which content categories have sufficient data
- `_create_weekly_slots()`: Assigns categories to the day x slot grid
- `_select_primary_category()`: Priority-based selection considering data availability
- `_build_fallback_chain()`: Fallback categories if primary lacks data
- `_ensure_differentiation()`: Cross-account deduplication
- `create_brief() -> ContentBrief`: Generate brief for one account
- `create_all_briefs() -> Dict[str, ContentBrief]`: Generate for all 3 accounts

**PersonaGenerator**: Claude-based generation with persona context.
- `generate()`: Full week generation
- `_generate_day_batch()`: Batches a day's tweets into a single LLM call
- `_build_generation_prompt()`: Constructs system + user prompt with persona voice
- `_parse_response()`: Extracts tweets from LLM output
- `_generate_fallback_tweets()`: Template fallback on failure

**CrossAccountValidator**: Ensures differentiation across accounts.
- `_check_cross_account_duplicates()`: Text similarity check via `SequenceMatcher`
- `_check_topic_overlap()`: Same ticker/theme in the same slot
- `_check_day_appropriateness()`: Weekend rules enforcement
- `_text_similarity()`: `SequenceMatcher` ratio calculation

---

### 2.4 Generation Flow Comparison

| Aspect | reaction_generator (Primary) | tweet_generator (Legacy) | content_planner |
|--------|------------------------------|--------------------------|-----------------|
| **Approach** | Persona reacts to data | Template-first + LLM enhancement | Data-first planning + persona generation |
| **Persona source** | YAML files | Hardcoded | Hardcoded dataclasses |
| **Multi-account** | Independent per-persona generation | Post-hoc rephrasing of main | Independent planning + generation |
| **LLM calls per week** | 21 (7 days x 3 accounts) | 1-3 (main + optional rephrase) | ~21 (day batches per account) |
| **Anti-repetition** | ContentTracker with limits | TemplateTracker (template reuse) | CrossAccountValidator |
| **Fallback** | Deterministic data fallbacks | Template population | Template fallback |
| **Validation** | FinTwit style + banned phrases + persona | Template completeness | Cross-account dedup + day rules |
| **Status** | Production | Fallback | Available, not primary |

---

## 3. Persona System

### 3.1 YAML Configuration

Persona YAML files are stored at `content/personas/`. Loaded by `load_persona(persona_file) -> Persona` (reaction_generator.py, line 731).

Structure:

```yaml
identity:
  name: "Alexander Sterling"
  handle: "@SterlingSignals"
background: "Multi-paragraph character backstory..."
personality:
  core_traits: ["data-driven", "confident", ...]
voice:
  vocabulary:
    uses: ["the system", "5-gate", ...]
    never_uses: ["let's go!", "WAGMI", ...]
  emoji_style:
    frequency: "sparse"
    allowed: ["chart_increasing", "green_circle", ...]
    never: ["rocket", "moon", ...]
content_approach:
  what_he_shares: [...]
  what_he_doesnt_share: [...]
example_tweets:
  scanner_results: [...]
  winner_reactions: [...]
day_of_week_tendencies:
  saturday:
    mood: "reflective"
    energy: "low-key"
    typical_content: "newsletter drop, weekend recap"
```

### 3.2 Three Personas

**Alexander Sterling** (`personas/alex.yaml`):
- Handle: `@SterlingSignals`
- Archetype: "The System Builder"
- Voice: Data-driven, confident but not arrogant, system-focused
- Emoji style: Sparse -- green circle (TEAL), chart, target, gem
- Vocabulary uses: "the system", "5-gate", "capital preservation protocol"
- Never uses: "let's go!", "WAGMI", "to the moon"
- Content focus: Scanner results, system performance, theme analysis

**Rozalia** (`personas/rozalia.yaml`):
- Handle: Account 2
- Archetype: "The Mentor"
- Voice: Educational, encouraging, shares past mistakes openly
- Emoji style: Moderate -- chart, lightbulb, graduation cap, sparkle
- Vocabulary uses: "I learned this the hard way", "here's what I'd tell my younger self"
- Never uses: "the system says", Alex's signature phrases
- Content focus: Teaching moments, trading psychology, process explanation

**James** (`personas/james.yaml`):
- Handle: Account 3
- Archetype: "The Trader"
- Voice: High energy, real-time observations, sports commentary style
- Emoji style: Frequent -- fire, lightning, muscle, trophy
- Vocabulary uses: "Let's go!", "momentum is building", "this is why we trade"
- Never uses: Alex's dry analytical language, Rozalia's teaching phrases
- Special focus: Power Hour (15:30-16:00 ET) content

### 3.3 Few-Shot Examples

**File:** `content/examples/tweet_examples.json`

Organized by persona key (`alex`, `rozalia`, `james`) and content category. Categories include:
- `scanner_results` -- signal announcement tweets
- `winner_reactions` -- celebrating winning positions
- `no_signal_weeks` -- handling quiet scanner weeks
- `vulnerability_honesty` -- authentic sharing of losses/mistakes
- `educational` -- teaching moments
- `theme_analysis` -- sector analysis tweets

The `build_examples_section()` function (reaction_generator.py, line 996) selects context-appropriate examples: quiet-week examples when `is_quiet_week`, winner examples when `has_big_winner`, etc. Falls back to random sampling if no context match. Maximum 5 examples per prompt.

### 3.4 Cross-Account Differentiation

Three layers of differentiation:

1. **Prompt-level** (reaction_generator.py): Each persona gets distinct voice traits, vocabulary constraints, and `never_uses` phrases that belong to other accounts.

2. **ContentTracker** (reaction_generator.py, lines 198-334): Per-account tracking of ticker mentions and phrase usage with configurable limits. The `get_avoidance_guidance()` method generates explicit "DO NOT mention" instructions for Claude.

3. **CrossAccountValidator** (content_planner.py): Post-generation validation checking text similarity (SequenceMatcher), topic overlap in same time slots, and day-appropriateness rules.

4. **Editorial Board** (editorial_board.py): Pre-generation coordination. The editorial board prompt (line 14) explicitly prevents same-slot ticker collisions: "If Alex mentions $AMPX in slot 2, Rozalia and James must NOT mention $AMPX in slot 2." Ticker budget: configurable max per day across all 3 accounts.

---

## 4. Tweet Categories and Schedule

### 4.1 Weekly Schedule Grid

The reaction_generator uses slot context rather than a fixed category grid -- each day's 5 tweets are generated holistically by Claude based on the day's mood and data. However, the editorial_board.py and content_planner.py define explicit category assignments.

Editorial board slot guidance (editorial_board.py, lines 21-27):

| Slot | Time (ET) | Weekday Character | Weekend Character |
|------|-----------|-------------------|-------------------|
| 1 | 08:00 | Morning prep / reflective | Morning prep / reflective |
| 2 | 10:00 | Market open energy | Casual |
| 3 | 12:30 | Midday check-in, engagement | Midday check-in, engagement |
| 4 | 15:30 | Power hour | General reflection |
| 5 | 18:00 | End of day, newsletter CTAs | Looking ahead |

Content_planner.py `DayRules` primary focus by day:

| Day | Primary Focus Categories | Avoid Categories |
|-----|-------------------------|------------------|
| Saturday | signal_recap, newsletter_promo, top_performers, funnel_stats | power_hour, real_time |
| Sunday | watchlist, theme_outlook, engagement, educational | power_hour, real_time, market_color |
| Monday | theme_momentum, educational, market_color, signals | (none) |
| Tuesday | educational, early_movers, engagement, theme_analysis | newsletter_promo |
| Wednesday | watchlist, educational, engagement, process | newsletter_promo, top_performers |
| Thursday | anticipation, educational, engagement, theme_preview | top_performers, newsletter_promo |
| Friday | power_hour, scan_anticipation, real_time, market_color | newsletter_promo |

### 4.2 Category Definitions (18 from content_planner.py)

**Signal-based (requires data):**

| Category | Description | Data Requirement |
|----------|-------------|------------------|
| `WINNER_SHOWCASE` | Celebrate 25%+ winners with entry -> current price | At least 1 position with P&L >= 25% |
| `SELF_QUOTE` | Quote-tweet earlier prediction that came true | Historical signal data from signal_tracker |
| `BEAT_SPY` | Portfolio alpha over S&P 500 | Positive portfolio_vs_spy value |
| `SIGNAL_SPOTLIGHT` | New PASS signal deep dive | At least 1 pass_signal |
| `WATCHLIST_UPDATE` | CONSIDER signal monitoring | At least 1 consider_signal |
| `THEME_MOMENTUM` | Hot theme analysis with tickers | At least 1 PRIME/INVESTABLE theme |
| `EARLY_MOVERS` | Stocks moving pre-market or early session | Live price data |
| `CLOSED_TRADE` | Recently closed position with P&L | At least 1 closed trade |
| `MILESTONE_ALERT` | Position hitting 25%, 50%, or 100% milestone | Position crossing threshold |

**Always available:**

| Category | Description |
|----------|-------------|
| `FUNNEL_STATS` | Scan funnel numbers (1800 -> 48 -> 6) |
| `EDUCATIONAL` | Teaching moments using specific examples |
| `ENGAGEMENT` | Questions, observations, community building |
| `PROCESS_EXPLAINER` | Trading discipline with proof |
| `NEWSLETTER_PROMO` | Drive Substack signups (exactly 2 per account per day) |

**Phase-specific and time-specific:**

| Category | Description |
|----------|-------------|
| `PATIENCE_CONTENT` | Building phase -- waiting for winners |
| `WHY_PROCESS_MATTERS` | Building phase -- system trust content |
| `POWER_HOUR` | 15:30-16:00 ET market reaction (weekdays only) |
| `MARKET_COLOR` | Real-time market commentary (weekdays only) |

### 4.3 Slot Times

All times in Eastern Time (ET):

| Slot | Time | Typical Content |
|------|------|-----------------|
| 1 | 08:00 | Pre-market, morning prep, reflective |
| 2 | 10:00 | Market open reaction (weekday), casual (weekend) |
| 3 | 12:30 | Midday check-in, engagement questions |
| 4 | 15:30 | Power hour on weekdays (CRITICAL), reflection on weekends |
| 5 | 18:00 | After hours wrap-up, newsletter CTAs, week ahead |

---

## 5. Safeguard System

### 5.1 The Validation Checks

The reaction_generator implements validation at multiple levels:

**Tweet-level validation** -- `validate_tweet()` (line 1293):
1. **Character limit**: `char_count > 280` flagged
2. **Forbidden persona phrases**: Checks `voice.vocabulary.never_uses` list
3. **Hallucinated tickers**: Tickers not in scanner data or benchmark set (`SPY`, `QQQ`, `VIX`)
4. **Robotic language**: Detects "systematic analysis", "algorithmic", "data drives decisions", "execute", "protocol"

**Day-level validation** -- `validate_day_tweets()` (line 1325):
5. **Duplicate content**: Checks first 50 chars of each tweet for duplicates
6. **URL distribution**: Flags if fewer than 2 or more than 4 tweets have URLs

**FinTwit style validation** -- `validate_fintwit_style()` (line 641):
7. **Category-specific data requirements**: scanner_result needs tickers+prices, performance needs specific winners+percentages, etc.
8. **Banned phrases**: 18 hardcoded phrases (line 607) including "theme keeps delivering", "quality over quantity", "stay tuned"
9. **Loser focus detection**: 9 regex patterns (line 616) detecting emphasis on losing positions

**ContentTracker validation** -- `check_tweet()` (line 255):
10. **Ticker over-mention**: Each ticker max 2x per account per week
11. **Phrase limits**: Per-persona phrase caps (e.g., "the system" max 3x for Alex)
12. **Fact repetition**: Scan count max 2x, portfolio status max 3x, SPY comparison max 3x

**Week-level validation** -- `deduplicate_weekly_content()` (line 1357):
13. **Cross-day ticker repetition**: Flags tickers mentioned more than 3x per account across the week
14. **Portfolio stats repetition**: Flags portfolio stats repeated on the same day

**Post-generation fixes** (lines 1531-1543):
15. **Temporal reference correction**: Replaces "yesterday" on wrong days with appropriate temporal references (e.g., "Friday's scan" on Tuesday)

### 5.2 Marketing Vocabulary Integration

The `config/marketing_vocabulary.py` module provides `validate_content()` and `BANNED_TERMS` list. These are imported by:
- `newsletter_compiler.py` (line 44)
- `substack_notes_generator.py` (line 40)
- `grok_prompts_generator.py` (line 57)

Banned terms from CLAUDE.md:
- "20% trailing stop" -> use "Capital Preservation Protocol"
- "HMA pivots" -> use "Structural Pivot Confirmation"
- "Banker indicator" / "Banker >= 55" -> use "Institutional Accumulation Divergence"
- "Beta >= 1.5" -> use "Volatility Expansion Criteria"
- "Weekly BoS" -> use "Structural Trend Confirmation"
- "Tier 1/2/3" -> use "Conviction Rating"
- "Gatekeeper" -> use "The 5th Gate: Forensic Audit"
- "Theme scoring" -> use "Sector Flow Analysis"
- Also banned: UK ISA, ISA account, GMT, BST, UK Time, RSI, MACD, KDJ

### 5.3 Entry Price Display Rules

Entry prices may only be shown publicly when:
- **Closed winners:** Always show entry prices for profitable closed trades
- **Open positions:** Only show entry prices for positions above 25% gain

Enforced by `can_show_entry_price()` from `config/settings.py`, used by:
- `winner_showcase_generator.py` (line 77)
- `substack_content_generator.py` (line 39)
- `tweet_generator.py` (line 100)

### 5.4 Loss Suppression

Multiple layers prevent public display of losing positions:

1. **MarketContext** separates `winners` (25%+) from `losers` (negative) at data loading time (reaction_generator.py, line 768-769)
2. **build_structured_data_blocks()** (line 537): Only the WINNERS section is labeled "show receipts". Losers are tracked internally but not promoted.
3. **Newsletter compiler system prompt** (line 82-84): "NEVER mention losing positions or underwater trades", "Only showcase wins above 15% threshold"
4. **Loser pattern detection** (reaction_generator.py, line 616): Regex patterns detect emphasis on losses
5. **Content phase guidance**: During EARLY phase (no winners), content focuses on process and new signals rather than P&L

**Honesty exception:** Per CLAUDE.md marketing rules, losses are never hidden in the newsletter's full P&L table -- they are always shown. The suppression applies only to individual tweet spotlights and promotional content. The framing is "stop hit = system working as designed."

---

## 6. Newsletter Pipeline

### 6.1 newsletter_compiler.py -- 970 lines

**File:** `/Users/mattydeighton/Downloads/bos_momentum_scanner/content/newsletter_compiler.py`

#### Imports and Configuration (lines 1-61)

```python
TRADES_DIR = Path(__file__).resolve().parent.parent / "trades"  # line 56
CHARTS_DIR = TRADES_DIR / "charts"                               # line 57
SUBSTACK_URL = "https://sterlingsignals.substack.com"            # line 60
NEWSLETTER_NAME = "Sterling Signals"                              # line 61
```

Conditional imports:
- `anthropic` (optional, `None` if missing)
- `config.output_paths` (optional, `OUTPUT_PATHS_AVAILABLE`)
- `config.marketing_vocabulary` (optional, `MARKETING_VOCABULARY_AVAILABLE`)
- `core.portfolio_manager.get_spy_ytd_return` (optional)

#### System Prompt (COMPILATION_SYSTEM, line 68)

Role: Editor of Sterling Signals, compiling a polished publication-ready newsletter.

Key instructions:
- Professional but accessible tone
- Data-driven with specific numbers
- Confident without arrogance
- US investor perspective
- Use "GREEN signal" branding (not "PASS signal")
- NEVER mention losing positions or underwater trades
- Only showcase wins above 15% threshold
- Handle zero-signals weeks: "Sometimes the best trade is no trade"
- Subject line formula: `Week ${WEEK_NUM}: ${NEW_SIGNALS} GREEN Signals | ${HOOK_PHRASE}`

#### Data Loading Functions

| Function | Line | Purpose |
|----------|------|---------|
| `load_market_analysis()` | ~243 | Loads `scanner/output/current/market_analysis.md` or `scanner/output/current/market_analysis.md` |
| `load_scanner_briefing()` | ~267 | Loads `scanner/output/current/newsletter_briefing.md` or `scanner/output/current/newsletter_briefing.md` |
| `load_dd_results()` | ~285 | Extracts DD sections from `scanner/output/signals.json`, returns `(str, int)` count |
| `load_portfolio_status()` | ~334 | WIN HIGHLIGHTS only from portfolio (no losses per marketing rules) |
| `calculate_portfolio_ytd_return()` | ~401 | Calculates from portfolio.csv via yfinance |
| `generate_benchmark_comparison()` | ~445 | Portfolio vs SPY markdown comparison |

### 6.2 Simple vs Full Mode

**Simple mode** (default, `compile_newsletter()`):
1. Load scanner briefing markdown
2. Convert directly to HTML via `markdown_to_html()`
3. Save to `substack/output/current/newsletter.html`

**Full mode** (`compile_newsletter(full_mode=True)`):
1. Load market analysis (or generate via `market_analyzer.py`)
2. Load scanner briefing
3. Load DD results from signals.json
4. Load portfolio status (wins only)
5. Generate benchmark comparison
6. Call `compile_newsletter_llm()` -- single Claude API call to compile all inputs into a cohesive newsletter
7. Convert compiled markdown to HTML
8. Save to `substack/output/current/newsletter.html` and weekly archive

`compile_newsletter_llm()` (line 198): Sends market_context, scanner_briefing, dd_results, portfolio_status, and benchmark_comparison as structured user message to Claude with `COMPILATION_SYSTEM` prompt.

### 6.3 HTML Template and Styling

`markdown_to_html(md_content, chart_manifest) -> str` (line 514):

- Full CSS styling for Substack compatibility
- Dark theme with blue accents
- Responsive design
- Chart image placeholders replaced: `[CHART: TICKER]` markers are substituted with `<img>` tags pointing to chart files from the manifest
- Handles markdown headers, lists, tables, code blocks, bold/italic

### 6.4 Chart Embedding

Charts from `twitter/output/charts/chart_manifest.json` are embedded during HTML conversion. The manifest maps ticker symbols to file paths:

```json
{
    "NVDA": "twitter/output/charts/NVDA_20260206.png",
    "RCAT": "twitter/output/charts/RCAT_20260206.png"
}
```

The `[CHART: TICKER]` placeholder in the newsletter briefing is replaced with an `<img>` tag. For Substack publishing, images must be manually uploaded since Substack does not support external image references in email HTML.

---

## 7. Substack Content

### 7.1 substack_notes_generator.py (Tuesday/Thursday) -- 502 lines

**File:** `/Users/mattydeighton/Downloads/bos_momentum_scanner/content/substack_notes_generator.py`

Generates two mid-week Substack Notes for engagement between newsletter issues.

#### Configuration (lines 31-75)

```python
BASE_DIR = Path(__file__).resolve().parent.parent   # line 35
TRADES_DIR = BASE_DIR / "trades"                     # line 36
```

Output directories: `substack/output/current/substack_notes/` and `scanner/output/archive/YYYY-WXX/substack_notes/`

#### Tuesday Note -- "Portfolio Pulse" (line ~198)

`generate_tuesday_note()`:
- Portfolio performance summary (total positions, green/red count)
- Open positions with live P&L (fetched via yfinance)
- Theme momentum analysis (which themes are performing)
- Stop distance warnings (positions within 10% of stop)
- Win/loss ratio for closed trades

#### Thursday Note -- "Trade Spotlight" (line ~259)

`generate_thursday_note()`:
- Spotlight on a specific PASS signal (if available)
- Theme deep dive for the spotlighted stock
- Technical setup description (using approved marketing language)
- Risk factors and catalyst timeline
- Watchlist update for CONSIDER signals

Both notes use `validate_content()` from `config.marketing_vocabulary` to enforce banned terms compliance.

**Output files:**
- `substack/output/current/substack_notes/tuesday_note.md`
- `substack/output/current/substack_notes/thursday_note.md`
- Archived to `scanner/output/archive/YYYY-WXX/substack_notes/`

### 7.2 substack_content_generator.py (Mon/Thu/Sat/Sun) -- 528 lines

**File:** `/Users/mattydeighton/Downloads/bos_momentum_scanner/content/substack_content_generator.py`

Generates four weekly Substack posts on a content calendar.

#### Imports (lines 1-44)

```python
from config import (
    BASE_DIR, TRADES_DIR, SIGNAL_COLORS, CONVICTION_LANGUAGE,
    SUBSTACK_CONTENT, BRANDING, get_signal_emoji, get_conviction_text,
    can_show_entry_price,
)
from config.marketing_vocabulary import validate_content, APPROVED_VOCABULARY
```

#### Content Calendar

| Day | Post Type | Description |
|-----|-----------|-------------|
| Monday | "Week Ahead" | Market context + top performers preview |
| Thursday | "Theme Spotlight" | Hot theme deep dive with all related tickers |
| Saturday | "Weekly Signals" | Full GREEN/RED/CONSIDER recap |
| Sunday | "Deep Dive" | Single stock analysis |

#### Key Functions

- `load_signals() -> Dict` (line 47): Loads `scanner/output/signals.json`
- `load_portfolio() -> List[Dict]` (line 55): Delegates to `core.portfolio_manager.load_portfolio(status_filter="OPEN")`
- `load_themes() -> List[Dict]` (line 64): Extracts themes from signals
- `format_winner_line(position, show_entry) -> str` (line 70): Formats `$TICKER: $XX.XX -> $XX.XX (+XX.X%)` respecting `can_show_entry_price()` rules

**Output:** `substack/output/current/substack_posts/{day}_post.md`

---

## 8. Grok Prompts

### 8.1 grok_prompts_generator.py -- 1,612 lines

**File:** `/Users/mattydeighton/Downloads/bos_momentum_scanner/content/grok_prompts_generator.py`

Generates 21 prompts (3/day x 7 days) designed for manual copy-paste into X's Grok AI to produce ready-to-post tweets.

#### Configuration (lines 39-61)

```python
BASE_DIR = Path(__file__).resolve().parent.parent         # line 43
TRADES_DIR = BASE_DIR / "trades"                           # line 44
OUTPUT_DIR = TRADES_DIR / "grok_prompts"                   # line 45
SUBSTACK_URL = "https://sterlingsignals.substack.com"      # line 49
ACCOUNT_HANDLE = "@SterlingSignals"                         # line 50
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]  # line 53
```

#### Dataclasses

**PortfolioData** (line 69):

```python
@dataclass
class PortfolioData:
    prime_themes: List[Dict]
    investable_themes: List[Dict]
    selective_themes: List[Dict]
    avoid_themes: List[Dict]
    pass_signals: List[Dict]
    caution_signals: List[Dict]
    fail_signals: List[Dict]
    technical_only: List[Dict]
    open_positions: List[Dict]
    sell_signals: List[Dict]
    scan_stats: Dict
    scan_date: str
```

**GrokPrompt** (line 93):

```python
@dataclass
class GrokPrompt:
    day: str
    slot: int           # 1, 2, or 3
    category: str       # theme_hot, buy_signal, etc.
    title: str
    prompt: str
    visual_suggestion: str
```

### 8.2 21-Prompt Weekly Schedule

`generate_weekly_prompts()` (line ~1066):

| Day | Slot 1 (08:00) | Slot 2 (12:00) | Slot 3 (18:00) |
|-----|----------------|----------------|----------------|
| Monday | Week Ahead Preview | Hot Theme Deep Dive | Position Update |
| Tuesday | Buy Signal | Cold Theme / Lesson | Watchlist Stock |
| Wednesday | Market Pulse | Theme Comparison | Sell Signal / Position |
| Thursday | Buy Signal 2 | Hot Theme 2 / Lesson | Watchlist 2 |
| Friday | Scanner Stats Teaser | Cold Theme 2 | Position Update |
| Saturday | Newsletter Drop | Signal Deep Dive | Why Passed |
| Sunday | Engagement | Trading Lesson | Week Ahead Preview |

#### Prompt Creation Functions

14 specialized prompt builders:

| Function | Line | Input Data |
|----------|------|------------|
| `create_hot_theme_prompt()` | 508 | PRIME/INVESTABLE themes |
| `create_cold_theme_prompt()` | 546 | SELECTIVE/AVOID themes |
| `create_buy_signal_prompt()` | 582 | PASS signals |
| `create_watchlist_prompt()` | 622 | CAUTION signals |
| `create_position_update_prompt()` | 664 | Open positions |
| `create_sell_signal_prompt()` | 721 | Sell signals |
| `create_scanner_stats_prompt()` | 760 | Scan funnel stats |
| `create_why_passed_prompt()` | 797 | FAIL signals with reasoning |
| `create_theme_comparison_prompt()` | 838 | Two themes for comparison |
| `create_trading_lesson_prompt()` | 872 | Static educational templates |
| `create_market_pulse_prompt()` | 916 | Live search instruction |
| `create_newsletter_drop_prompt()` | 946 | Newsletter URL + highlights |
| `create_week_ahead_prompt()` | 989 | Themes + watchlist |
| `create_engagement_prompt()` | 1020 | Static engagement templates |

### 8.3 Live Price Feature

The `create_position_update_prompt()` includes instructions for Grok to look up current prices:

```
POSITION CONTEXT (may be outdated - look up current price):
Ticker: $RCAT
Entry: $8.50 on 2025-12-29
Theme: Drone Technology | Tier: TIER1
Days Held: ~23
Snapshot P&L: +55.9% (verify with current price)

---

IMPORTANT: The P&L above may be stale. Before drafting:
1. Look up the CURRENT price of $RCAT
2. Calculate the LIVE P&L: ((current_price / 8.50) - 1) * 100
```

This compensates for the fact that prompts are generated once on Friday but used throughout the following week when prices may have changed significantly.

#### Output Files

| File | Description |
|------|-------------|
| `twitter/output/grok_prompts/grok_prompts_{YYYYMMDD}.md` | Dated archive of all 21 prompts |
| `twitter/output/grok_prompts/latest_grok_prompts.md` | Symlink/copy of latest prompts |
| `twitter/output/grok_prompts/monday_prompts.md` | Monday's 3 prompts |
| `twitter/output/grok_prompts/tuesday_prompts.md` | Tuesday's 3 prompts |
| `twitter/output/grok_prompts/wednesday_prompts.md` | Wednesday's 3 prompts |
| `twitter/output/grok_prompts/thursday_prompts.md` | Thursday's 3 prompts |
| `twitter/output/grok_prompts/friday_prompts.md` | Friday's 3 prompts |
| `twitter/output/grok_prompts/saturday_prompts.md` | Saturday's 3 prompts |
| `twitter/output/grok_prompts/sunday_prompts.md` | Sunday's 3 prompts |

---

## 9. Visual Content

### 9.1 chart_capture.py (TradingView) -- 648 lines

**File:** `/Users/mattydeighton/Downloads/bos_momentum_scanner/content/chart_capture.py`

Captures TradingView charts with custom BoS/Banker indicators using Playwright browser automation.

#### Configuration (lines 50-80)

```python
BASE_DIR = Path(__file__).resolve().parent.parent                   # line 54
CHARTS_DIR = BASE_DIR / "trades" / "charts"                         # line 55
TRADINGVIEW_LAYOUT_ID = os.environ.get("TRADINGVIEW_LAYOUT_ID", "rxC5j0SK")  # line 59
PLAYWRIGHT_USER_DATA_DIR = os.environ.get(
    "PLAYWRIGHT_USER_DATA_DIR",
    str(BASE_DIR / ".playwright_profile")
)                                                                    # lines 63-66
CHART_SIZE_X = (1400, 900)           # X/Twitter card size          # line 70
CHART_SIZE_SUBSTACK = (1000, 700)    # Substack embed size          # line 71
```

`HIDE_UI_ELEMENTS_JS` (line 76): JavaScript injected into TradingView to declutter UI -- hides right-side panels, watchlist, news widgets while preserving indicator visuals and pane labels.

#### Key Functions

| Function | Line | Purpose |
|----------|------|---------|
| `capture_chart(page, ticker, output_dir, date_str, sizes)` | 122 | Capture single ticker chart at specified sizes |
| `capture_charts(tickers, headless, output_dir, ...)` | 213 | Batch capture for multiple tickers |
| `extract_chrome_cookies(domain)` | 320 | Extract TradingView cookies from Chrome's SQLite database |
| `save_cookies(cookies, path)` | 394 | Save cookies to `.tradingview_cookies.json` |
| `load_cookies(path)` | 402 | Load saved cookies |
| `check_indicators_loaded(page)` | 417 | Verify custom indicators are visible on chart |
| `load_tickers_from_json(filepath)` | 479 | Extract tickers from `signals.json` |
| `load_tickers_from_portfolio(filepath)` | 516 | Extract tickers from `portfolio.csv` |
| `save_chart_manifest(results, output_dir)` | 536 | Write `chart_manifest.json` |

#### Workflow

1. Launch Playwright with persistent user data directory
2. Load saved TradingView cookies (or extract from Chrome)
3. Navigate to `https://www.tradingview.com/chart/{LAYOUT_ID}/?symbol={TICKER}`
4. Wait for chart and indicators to load
5. Inject `HIDE_UI_ELEMENTS_JS` to declutter
6. Take screenshot at `CHART_SIZE_X` and `CHART_SIZE_SUBSTACK`
7. Save to `twitter/output/charts/{TICKER}_{date}.png` and `{TICKER}_{date}_substack.png`
8. Update `chart_manifest.json`

**Authentication note:** First run must be non-headless to log into TradingView. Subsequent runs use saved session. CI cannot capture charts (no GUI for login).

### 9.2 funnel_graphic.py (PIL) -- 671 lines

**File:** `/Users/mattydeighton/Downloads/bos_momentum_scanner/content/funnel_graphic.py`

Generates a visual funnel graphic showing the 5-gate stock filtering process.

#### Configuration (lines 47-80)

```python
TRADES_DIR = Path(__file__).resolve().parent.parent / "trades"   # line 52
CHARTS_DIR = TRADES_DIR / "charts"                                # line 53
DEFAULT_OUTPUT = CHARTS_DIR / "funnel_graphic.png"                # line 54
MANIFEST_FILE = CHARTS_DIR / "chart_manifest.json"                # line 55
IMAGE_WIDTH = 1200                                                 # line 58
IMAGE_HEIGHT = 675                                                 # line 59
```

Image dimensions: 1200x675 pixels (Twitter/X card ratio 1.91:1).

#### Color Themes (lines 62-80)

Two themes available:
- **dark** (default): `#0d1117` background, `#ffffff` primary text, `#58a6ff` accent, `#7ee787` highlight
- **light**: `#ffffff` background, `#24292f` primary text, `#0969da` accent, `#1a7f37` highlight

#### Funnel Stages

The funnel visualises the 5-gate filtering:

| Gate | Label | Example Value |
|------|-------|---------------|
| 1. Universe | Stocks scanned | 1,817 |
| 2. Volatility Expansion | Beta >= 1.5 filter | 485 |
| 3. Institutional Accumulation | Banker >= 55 | 312 |
| 4. Theme Alignment | Sector flow confirmation | 17 |
| 5. Forensic Audit | Final PASS signals | 6 |

Uses PIL/Pillow for rendering. Falls back gracefully if PIL is not installed (`PIL_AVAILABLE` flag, line 37).

**Output:** `twitter/output/charts/funnel_graphic.png`, automatically added to `chart_manifest.json`.

---

## 10. Supporting Modules

### 10.1 market_analyzer.py -- 265 lines

**File:** `/Users/mattydeighton/Downloads/bos_momentum_scanner/content/market_analyzer.py`

Generates current market analysis using Claude with web search enabled.

#### Configuration

```python
MODEL = "claude-sonnet-4-20250514"   # line 41
MAX_TOKENS = 3000                     # line 42
```

#### Dataclass

**MarketAnalysisResult** (lines 49-57):

```python
@dataclass
class MarketAnalysisResult:
    analysis: str = ""
    cost: float = 0.0
    error: str = ""
    def success(self) -> bool:
        return bool(self.analysis) and not self.error
```

#### Prompts

**MARKET_ANALYSIS_SYSTEM** (line 64): "Senior market analyst writing the weekly market context section." Style: professional, specific numbers, connect macro to momentum stocks, no hedging language.

**MARKET_ANALYSIS_PROMPT** (line 79): Instructs Claude to generate market context covering S&P 500, sectors, VIX, Treasury yields. Uses web search tool for current data.

#### Key Function

`analyze_market(save=False) -> str` (line ~80): Makes single Claude API call with web search enabled. Returns markdown analysis. If `save=True`, writes to `scanner/output/current/market_analysis.md` and `scanner/output/current/market_analysis.md` (legacy).

### 10.2 editorial_board.py -- 266 lines

**File:** `/Users/mattydeighton/Downloads/bos_momentum_scanner/content/editorial_board.py`

Pre-generation coordination module. Plans content allocation across all 3 accounts before any tweets are generated.

**EDITORIAL_BOARD_PROMPT** (line 14): Comprehensive prompt for Claude to plan 15 slots (5 per account) for a single day. Includes:
- Account personality descriptions (Alex = dry/data-driven, Rozalia = warm/educational, James = high-energy/real-time)
- Time slot definitions (08:00 through 18:00 ET)
- Content category definitions (8 categories with data requirements)
- FinTwit rules (every scanner_result must include tickers, every performance must reference specific winners)
- Coordination rules: no same-slot ticker collisions, ticker budget per day, top winner quota, category variety, newsletter CTA distribution, persona fit matching

Output format: JSON with assignments for Alex, Rozalia, James each having 5 slots with `{category, topic, tickers, include_url, attach_chart}`.

Key functions:
- `create_editorial_plan(scanner_data, portfolio_data, day_name)`: Generates the plan via Claude
- `validate_editorial_plan(plan)`: Validates the plan against coordination rules

### 10.3 morning_briefing.py -- 203 lines

**File:** `/Users/mattydeighton/Downloads/bos_momentum_scanner/content/morning_briefing.py`

Transforms raw scanner JSON and portfolio data into a structured narrative briefing consumed by the editorial board and writer room.

**Main function** -- `generate_morning_briefing(scanner_data, portfolio_data, day_name, week_tracker=None) -> str` (line 13):

Sections produced:
1. Scanner results (stocks scanned, passed all gates, on watchlist)
2. New signals (formatted with ticker, price, theme)
3. Watchlist (CONSIDER signals)
4. Theme analysis (hot themes, cold themes)
5. Portfolio state (total positions, green/red count, vs SPY)
6. Big winners (25%+ positions with entry -> current)
7. Recent closes (last 5 closed trades with P&L)
8. Week coverage notes (if `week_tracker` provided, shows already-featured tickers)

Helper functions:
- `_format_signals(signals) -> str`: Format signal list
- `_format_theme_names(themes) -> str`: Extract and format theme names
- `_format_positions(positions) -> str`: Format position list with P&L

### 10.4 winner_showcase_generator.py -- 271 lines

**File:** `/Users/mattydeighton/Downloads/bos_momentum_scanner/content/winner_showcase_generator.py`

Generates winner showcase content with strict entry price display rules.

#### Key Functions

`get_winners_for_showcase(threshold=25.0, include_entry_price=True, max_positions=5) -> List[Dict]` (line 46):
- Loads portfolio via `core.portfolio_manager.load_portfolio(compute_pnl=True)`
- Filters to OPEN positions with P&L >= threshold
- Checks `can_show_entry_price(pos)` for each position
- Returns sorted by P&L descending, capped at `max_positions`

Winner dict format:

```python
{
    'ticker': 'RCAT',
    'pnl_pct': 55.9,
    'entry_price': 8.50,      # Only if can_show_entry_price() returns True
    'current_price': 13.25,   # Only if can_show_entry_price() returns True
    'days_held': 23,
    'theme': 'Drone Technology',
    'tier': 'TIER1',
}
```

Additional functions:
- `generate_showcase_tweet(position) -> str`: Single winner tweet
- `generate_showcase_thread(positions) -> list`: Multi-tweet thread of winners

---

## 11. Output Files Summary

| Generator | Output File(s) | Format | Destination |
|-----------|---------------|--------|-------------|
| reaction_generator.py | `content_queue.json` | JSON | `twitter/output/` |
| reaction_generator.py | `content_queue_account2.json` | JSON | `twitter/output/` |
| reaction_generator.py | `content_queue_account3.json` | JSON | `twitter/output/` |
| reaction_generator.py | Tweets archive | JSON | `twitter/output/`, `scanner/output/archive/YYYY-WXX/tweets/` |
| tweet_generator.py | `tweets_{date}.json` | JSON | `twitter/output/` |
| tweet_generator.py | `content_queue.json` | JSON | `twitter/output/` |
| newsletter_compiler.py | `newsletter.html` | HTML | `scanner/output/current/` |
| newsletter_compiler.py | `newsletter.html` (archive) | HTML | `scanner/output/archive/YYYY-WXX/` |
| newsletter_compiler.py | `latest_newsletter.html` | HTML | `substack/output/current/` |
| substack_notes_generator.py | `tuesday_note.md` | Markdown | `substack/output/current/substack_notes/` |
| substack_notes_generator.py | `thursday_note.md` | Markdown | `substack/output/current/substack_notes/` |
| substack_notes_generator.py | Notes (archive) | Markdown | `scanner/output/archive/YYYY-WXX/substack_notes/` |
| substack_content_generator.py | `{day}_post.md` | Markdown | `substack/output/current/substack_posts/` |
| grok_prompts_generator.py | `grok_prompts_{YYYYMMDD}.md` | Markdown | `twitter/output/grok_prompts/` |
| grok_prompts_generator.py | `latest_grok_prompts.md` | Markdown | `twitter/output/grok_prompts/` |
| grok_prompts_generator.py | `{day}_prompts.md` (x7) | Markdown | `twitter/output/grok_prompts/` |
| market_analyzer.py | `market_analysis.md` | Markdown | `scanner/output/current/` |
| chart_capture.py | `{TICKER}_{date}.png` | PNG | `twitter/output/charts/` |
| chart_capture.py | `{TICKER}_{date}_substack.png` | PNG | `twitter/output/charts/` |
| chart_capture.py | `chart_manifest.json` | JSON | `twitter/output/charts/` |
| funnel_graphic.py | `funnel_graphic.png` | PNG | `twitter/output/charts/` |
| morning_briefing.py | (in-memory only) | str | Consumed by editorial_board.py |
| editorial_board.py | (in-memory only) | dict | Consumed by reaction_generator.py |
| winner_showcase_generator.py | (stdout or in-memory) | str/JSON | Consumed by tweet generators |

---

## 12. API Usage

| Module | API | Model | Web Search | Approximate Cost |
|--------|-----|-------|------------|-----------------|
| `reaction_generator.py` | Anthropic Claude | `claude-sonnet-4-20250514` | No | ~$1.50-3.00/week (21 calls x 3 accounts) |
| `tweet_generator.py` | Anthropic Claude | `claude-sonnet-4-20250514` | No | ~$0.50-1.00/week (hybrid mode) |
| `content_planner.py` | Anthropic Claude | Configured via `MODEL_SONNET` | No | ~$1.50-3.00/week (21 calls) |
| `editorial_board.py` | Anthropic Claude | `claude-sonnet-4-20250514` | No | ~$0.10-0.20/day (1 call/day) |
| `newsletter_compiler.py` | Anthropic Claude | `claude-sonnet-4-20250514` | No | ~$0.15-0.25 (1 call in full mode) |
| `market_analyzer.py` | Anthropic Claude | `claude-sonnet-4-20250514` | Yes | ~$0.25-0.50 (1 call + web searches) |
| `substack_notes_generator.py` | yfinance | N/A | N/A | Free (price lookups) |
| `substack_content_generator.py` | None | N/A | N/A | Free (template-based) |
| `grok_prompts_generator.py` | None | N/A | N/A | Free (template-based) |
| `chart_capture.py` | TradingView (browser) | N/A | N/A | Free (uses existing account) |
| `funnel_graphic.py` | None (PIL) | N/A | N/A | Free (local rendering) |
| `morning_briefing.py` | None | N/A | N/A | Free (data formatting) |
| `winner_showcase_generator.py` | None | N/A | N/A | Free (data formatting) |

**Total weekly content generation cost:** ~$2.50-7.00 depending on generation mode and number of accounts.

**Note:** The reaction_generator.py also calls `fetch_current_prices()` from `core.portfolio_manager` which uses yfinance (free) for live price refreshes during MarketContext building.
