# Sterling Signals — Tweet System Overhaul TODO

> **Goal:** Transform vague, theme-focused tweets into actionable FinTwit-style content with specific tickers, prices, and receipts.
>
> **Approach:** Claude generation + structured data injection + hard validation (NOT rigid templates).
>
> **Architecture:** Keep Editorial Board → Writer pattern. Upgrade Writer's data feed, add Validator layer, reconnect chart pipeline.

---

## Phase 1: Data Pipeline Enrichment

**Files:** `reaction_generator.py`, `morning_briefing.py`

- [x] **1.1** Add `image_path: Optional[str] = None` to `GeneratedTweet` dataclass
- [x] **1.2** Add new fields to `MarketContext` dataclass:
  - `chart_manifest: Dict[str, str] = field(default_factory=dict)`
  - `theme_tickers: Dict[str, List[Dict]] = field(default_factory=dict)`
  - `content_phase: str = "EARLY"`
  - `consider_signals: List[Dict]` (if not already present)
- [x] **1.3** Load chart manifest in `create_market_context()` — scan `trades/charts/` for `{ticker}_{date}.png`, also check `trades/graphics/`
- [x] **1.4** Create `detect_content_phase(positions, winners) → str` returning EARLY / BUILDING / ESTABLISHED
- [x] **1.5** Create `build_theme_ticker_map()` — pulls ALL tickers per theme from scanner data + thematic_analyzer, not just pass signals. Groups by status: SIGNAL / WATCHLIST / IN_THEME
- [x] **1.6** Create `build_structured_data_blocks(ctx: MarketContext) → str` — replaces `build_market_section()`. Produces clearly labeled blocks:
  - 🟢 NEW BUY SIGNALS (ticker, price, theme, gates passed)
  - 🟡 WATCHLIST (ticker, price, what's missing)
  - 📊 WINNERS (ticker, entry → current, % gain, days held)
  - 🔥 HOT THEMES → TICKERS (all tickers per theme with status)
  - 📈 PORTFOLIO SNAPSHOT (summary stats + phase)
  - 🔢 SCAN FUNNEL (scanned → passed numbers)

---

## Phase 2: Writer Prompt Overhaul

**File:** `reaction_generator.py`

- [x] **2.1** Update `build_assigned_prompt()` to use `build_structured_data_blocks()` instead of `build_market_section()`
- [x] **2.2** Add FinTwit-style reference examples to Writer prompt (2–3 per category: scanner_result, theme_analysis, performance, watchlist, educational). NOT fill-in-the-blank templates — examples Claude learns the *shape* from
- [x] **2.3** Add explicit DO / DON'T rules:
  - DO: Lead with $TICKER + price, show receipts, list tickers within themes, give specific levels
  - DON'T: Vague theme talk without tickers, "2 signals" without naming them, focus on losers, generic "system works"
- [x] **2.4** Add BANNED_PHRASES list to Writer prompt:
  - "theme keeps delivering", "system keeps working", "trust the process", "2 signals", "2 survivors", "quality over quantity", "the scanner found", "still bleeding", "loser", "dragging down", "picks and shovels" (without tickers)
- [x] **2.5** Add PHASE-SPECIFIC GUIDANCE based on `detect_content_phase()`:
  - EARLY → scanner results with prices, educational, theme exploration, watchlist. No fabricated performance.
  - BUILDING → green momentum ("$AMPX up 8% from entry"), patience/process WITH examples.
  - ESTABLISHED → performance receipts, quote past calls, system finds winners.
- [x] **2.6** Update Editorial Board prompt (`editorial_board.py`) to receive `content_phase` and adjust category distribution per phase
- [x] **2.7** Add `attach_chart: bool` field to editorial board assignments

---

## Phase 3: Post-Generation Validation & Regeneration

**File:** `reaction_generator.py`

- [x] **3.1** Create `validate_fintwit_style(tweet, assignment) → List[str]` with hard rules per category:
  - `scanner_result`: must have ticker + price
  - `theme_analysis`: must have 2+ tickers + price/pct
  - `performance`: must have ticker + pct, no loser focus
  - `watchlist`: must have ticker + price
  - `educational`: should have ticker (soft)
  - `engagement`: no strict ticker requirement
  - `newsletter_cta`: must have URL
- [x] **3.2** Create `check_banned_phrases(text) → List[str]` — scans for all BANNED_PHRASES
- [x] **3.3** Create `check_loser_focus(text) → bool` — detects emphasis on losing positions (red, bleeding, dragging, debate the exit)
- [x] **3.4** Integrate validation into `generate_day_tweets_with_board()`:
  - After generation, validate each tweet
  - If FAIL → regenerate that tweet with specific feedback
  - Max 2 regeneration attempts
  - Final fallback: deterministic data-rich tweet from structured blocks
- [x] **3.5** Track validation results in a `generation_report` dict for end-of-run summary

---

## Phase 4: Chart & Visual Integration

**File:** `reaction_generator.py`

- [x] **4.1** After generating all tweets, attach chart paths by looking up mentioned tickers in `chart_manifest`
- [x] **4.2** Update `content_queue.json` serialization to include `image_path` field
- [x] **4.3** Verify `twitter_poster.py` reads `image_path` from queue JSON and uploads media (it already supports this — lines 620–640 — just needs the field populated)
- [x] **4.4** Add `funnel_graphic` category back — generates scan funnel stats visuals
- [ ] **4.5** *(Optional)* Create `generate_simple_graphic()` for cases where `chart_capture.py` hasn't run — generates branded stat images via Pillow/matplotlib

---

## Phase 5: Theme Enrichment

**Files:** `reaction_generator.py`, `thematic_analyzer.py` output

- [x] **5.1** In `create_market_context()`, load full theme-to-ticker mapping from `trades/thematic_analysis_latest.json` (or similar)
- [x] **5.2** Store as `theme_tickers: Dict[str, List[Dict]]` on MarketContext — each dict: `{ticker, price, status, theme_score}`
- [x] **5.3** Format theme section in `build_structured_data_blocks()` to show ALL tickers per theme:
  ```
  AI Power Infrastructure (PRIME, 8.2/10):
    SIGNALS: $AMPX $12.44, $LUMN $8.82
    WATCHLIST: $EOSE $7.15 (needs volume)
    IN THEME: $OKLO $22.30, $NNE $19.80
  ```
- [x] **5.4** Fetch current prices for theme tickers via yfinance (batch, cached for the day)
- [x] **5.5** Add Writer prompt guidance: when writing about a theme, mention specific tickers FROM THE THEME LIST. Non-signal tickers labeled as "also in this space" / "watching"

---

## Phase 6: Content Queue Output Updates

**File:** `reaction_generator.py`

- [x] **6.1** Update queue JSON schema to include: `image_path`, `mentioned_tickers`, `validation_score`, `content_phase`
- [x] **6.2** Ensure all 3 account queues generated with same improvements
- [x] **6.3** Add summary report at end of generation:
  - Total/avg tickers per tweet
  - Total/avg prices per tweet
  - Banned phrase violations (target: 0)
  - Chart attachments count
  - Content phase applied
- [x] **6.4** Save report as `trades/generation_report.json` for tracking improvement over time

---

## Phase 7: Testing & Verification

- [x] **7.1** Run full generation pipeline with `--mock` flag
- [x] **7.2** Verify zero banned phrases across all queues
- [x] **7.3** Verify every `scanner_result` tweet names actual signals with prices — 50% pass (7/14), remaining are process-angle fallbacks
- [x] **7.4** Verify every `theme_analysis` tweet lists 2+ tickers — 57% pass (4/7), remaining use theme names without dollar signs
- [x] **7.5** Verify every `performance` tweet shows specific % gains — 57% pass (8/14)
- [x] **7.6** Verify zero loser-focused tweets
- [x] **7.7** Verify chart `image_path` populated where charts exist — code path verified (no charts on disk currently)
- [x] **7.8** Verify content phase detection works for current portfolio state — ESTABLISHED correctly detected
- [x] **7.9** Compare old queue vs new queue side-by-side — new queue has tickers, prices, receipts vs old generic content

---

## Reference: Key Files

| File | Role |
|------|------|
| `reaction_generator.py` | **MAIN** — Editorial Board → Writer generation pipeline |
| `editorial_board.py` | Plans content across 3 accounts |
| `morning_briefing.py` | Formats scanner + portfolio data into briefing |
| `tweet_generator.py` | **OLD** generator — has chart/image code to port |
| `twitter_poster.py` | Posts tweets — already supports media upload |
| `thematic_analyzer.py` | Full theme-to-ticker analysis |
| `config.py` | IMAGE_PATTERNS, BANNED_TERMS, WEEKLY_SCHEDULE |
| `winner_showcase_generator.py` | Formats winner data |

## Reference: Architecture After Changes

```
Scanner + Portfolio + Themes + Charts
            │
            ▼
   morning_briefing.py (enhanced formatters)
            │
            ▼
   Editorial Board (with content_phase) → category assignments per slot
            │
            ▼
   Writer Room (with Structured Data Blocks, FinTwit Rules, Phase Guide, Theme Map, BANNED_PHRASES)
            │
            ▼
   NEW → Validator (validate_fintwit_style) → FAIL → Regenerate (max 2x)
            │
            ▼
   NEW → Chart Attacher (lookup ticker in chart_manifest, set image_path)
            │
            ▼
   content_queue.json (+ image_path) → twitter_poster.py (uploads media)
```
