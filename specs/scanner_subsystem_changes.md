# Scanner Subsystem — Required Changes Specification
## Sterling Signals Architecture Optimisation

**Date:** 2026-02-25
**Scope:** scanner.py, merge_decisions.py, saturday_workflow.py, sterling_indicators.py, and related deletions
**Status:** Pre-testing optimisation — all changes must be validated before first live Friday scan

---

## TABLE OF CONTENTS

1. [Critical Bugs (Fix Before Any Testing)](#1-critical-bugs)
2. [scanner.py — Refactoring Specification](#2-scannerpy)
3. [merge_decisions.py — Bug Fixes & Hardening](#3-merge_decisionspy)
4. [saturday_workflow.py — Fixes & Improvements](#4-saturday_workflowpy)
5. [sterling_indicators.py — Status & Notes](#5-sterling_indicatorspy)
6. [File Deletions](#6-file-deletions)
7. [signals_technical.json Output Schema](#7-output-schema)
8. [decisions.json Input Validation](#8-decisions-validation)
9. [Implementation Order](#9-implementation-order)
10. [Testing Checklist](#10-testing-checklist)
11. [Deferred Items (Pending Downstream Audit)](#11-deferred-items)

---

## 1. CRITICAL BUGS

These are runtime failures or silent data corruption. Fix before any testing.

### BUG-1: saturday_workflow.py loads wrong technical data source [CRITICAL]

**File:** `saturday_workflow.py` line 102
**Current:**
```python
tech = load_json(SIGNALS_FILE, required=False)
```
**Problem:** `SIGNALS_FILE` points to `scanner/output/signals.json`, which is the *merged* output that merge_decisions.py produces. On the first run, this file either doesn't exist or contains stale data from a previous week. The scanner writes technical data to `signals_technical.json`, not `signals.json`.

**Impact:** The merge operates on empty or stale technical data. All technical fields (`uc`, `rsi14`, `macd_cross_up`, `beta`, etc.) in the merged output will be zeroed/missing. Downstream consumers (tweet_generator, content_production_guide) get signals with no technical context.

**Fix:** Import and use `SIGNALS_TECH_FILE`:
```python
# At top — add SIGNALS_TECH_FILE to the import
try:
    from config.output_paths import (
        SCANNER_OUTPUT, SIGNALS_FILE, SIGNALS_TECH_FILE,
        get_scanner_current_dir, get_scanner_archive_dir,
        get_substack_current_dir, get_substack_archive_dir,
        get_week_identifier,
    )
    CURRENT_DIR = get_scanner_current_dir()
    SUBSTACK_CURRENT = get_substack_current_dir()
except ImportError:
    SCANNER_OUTPUT = Path("scanner/output")
    CURRENT_DIR = SCANNER_OUTPUT / "current"
    SIGNALS_FILE = SCANNER_OUTPUT / "signals.json"
    SIGNALS_TECH_FILE = SCANNER_OUTPUT / "signals_technical.json"
    # ... rest of fallbacks
```

```python
# In step_merge(), line 102 — change to:
tech = load_json(SIGNALS_TECH_FILE, required=False)
if not tech:
    # Fallback: try current/ directory
    tech_alt = CURRENT_DIR / "signals_technical.json"
    tech = load_json(tech_alt, required=False)
if not tech:
    print("  ⚠ No signals_technical.json found — decisions-only mode")
    tech = {"buy_signals": [], "sell_signals": [], "stats": {}}
```

---

### BUG-2: merge_decisions.py fabricates technical data with dangerous defaults [CRITICAL]

**File:** `merge_decisions.py` lines 205, 208
**Current:**
```python
"hma_pivot_low": tech_data.get("hma_pivot_low", True),
"buy_signal": tech_data.get("buy_signal", True),
```
**Problem:** If a ticker in `decisions.json` doesn't appear in `signals_technical.json` (e.g., manually added in chat, or a ticker symbol mismatch), the default values claim the stock has a confirmed HMA pivot low and a valid buy signal. This silently fabricates technical confirmation that never happened.

**Impact:** Downstream systems treat the stock as technically confirmed. Tweet generator may reference "system-confirmed pivot" for a stock that was never scanned.

**Fix:** Change ALL boolean defaults to `False`, all numeric defaults to `0`, and emit a warning:
```python
# Before the signal-building loop, add:
unmatched_tickers = []

for pos in decisions.get("new_positions", []):
    symbol = pos.get("symbol", "")
    tech_data = tech_lookup.get(symbol, {})
    
    if not tech_data:
        unmatched_tickers.append(symbol)

    signal = {
        # Technical data — all defaults FALSE/ZERO (not fabricated)
        "hma_pivot_low": tech_data.get("hma_pivot_low", False),
        "hma_pivot_high": tech_data.get("hma_pivot_high", False),
        "hma_slope_rising": tech_data.get("hma_slope_rising", False),
        "buy_signal": tech_data.get("buy_signal", False),
        "exd_signal": tech_data.get("exd_signal", False),
        "uc": tech_data.get("uc", 0),
        "uc_rising": tech_data.get("uc_rising", False),
        "rsi14": tech_data.get("rsi14", 0),
        "macd_cross_up": tech_data.get("macd_cross_up", False),
        "beta": tech_data.get("beta", 0),
        "return_20d": tech_data.get("return_20d", 0),
        "banker": tech_data.get("uc", tech_data.get("banker", 0)),
        "uc_rising_above": tech_data.get("uc_rising_above", False),
        # ... rest unchanged
    }

# After the loop, warn about unmatched:
if unmatched_tickers:
    print(f"  ⚠ {len(unmatched_tickers)} ticker(s) in decisions.json not found in "
          f"signals_technical.json: {', '.join(unmatched_tickers)}")
    print(f"    Technical fields will be empty for these tickers")
```

---

### BUG-3: scanner.py references undefined variable `signals_file` [RUNTIME ERROR]

**File:** `scanner.py` line 2282
**Current:**
```python
print(f"     • {rel_path(signals_file)} (transitional — signals.json)")
```
**Problem:** The variable `signals_file` is never defined in `save_results()`. This was left behind when the transitional `signals.json` write was removed during refactoring. This line will raise a `NameError` at runtime, crashing the scanner after all work is complete but before the email notification fires.

**Fix:** Remove the line entirely. The scanner no longer writes `signals.json` — that's merge_decisions.py's job. The print statement on line 2281 already shows the primary output.

```python
# Remove line 2282 entirely. The remaining output lines become:
print(f"\n  📁 Results saved:")
print(f"     • {rel_path(signals_tech_file)} (PRIMARY — signals_technical.json)")
print(f"     • {rel_path(signals_current)} (current week)")
print(f"     • {rel_path(signals_archive)} (archived)")
print(f"     • {rel_path(analysis_log)}")
print(f"     • {rel_path(report_current)} (current week)")
```

---

### BUG-4: merge_decisions.py builds tech_lookup from only `buy_signals` array [FRAGILE]

**File:** `merge_decisions.py` lines 113-115
**Current:**
```python
tech_lookup: Dict[str, dict] = {}
for sig in tech.get("buy_signals", []):
    tech_lookup[sig.get("symbol", "")] = sig
```
**Problem:** If the scanner ever changes to populate only `pass_signals`/`consider_signals` without the legacy `buy_signals` union, the lookup returns empty for every ticker.

**Fix:** Build from all three arrays:
```python
tech_lookup: Dict[str, dict] = {}
for key in ("buy_signals", "pass_signals", "consider_signals"):
    for sig in tech.get(key, []):
        sym = sig.get("symbol", "")
        if sym and sym not in tech_lookup:  # first match wins
            tech_lookup[sym] = sig
```

---

### BUG-5: saturday_workflow Step 5 copies newsletter to itself (no-op) [LOGIC ERROR]

**File:** `saturday_workflow.py` lines 229-248
**Current:**
```python
newsletter_src = SUBSTACK_CURRENT / "newsletter.html"
# ...
targets = [
    SUBSTACK_CURRENT / "newsletter.html",  # Same as source!
]
# ...
for target in targets:
    shutil.copy2(newsletter_src, target)  # Copies file to itself
```
**Problem:** The source and the only target are the same path. The step does nothing. In the new workflow, the user produces `newsletter.html` from the Claude.ai chat (Prompt 4) and needs to save it somewhere that the workflow can pick up and distribute.

**Fix:** The newsletter should be saved from chat to `scanner/output/decisions/newsletter.html` (alongside `decisions.json`), then the workflow copies it to the Substack output directory:
```python
def step_newsletter(decisions_path: Path, dry_run: bool = False):
    """Step 5: Place newsletter.html in output directories."""
    print("─" * 60)
    print("  STEP 5: Newsletter Distribution")
    print("─" * 60)

    # Newsletter source: same directory as decisions.json
    newsletter_src = decisions_path.parent / "newsletter.html"
    if not newsletter_src.exists():
        # Fallback: check scanner output root
        newsletter_src = SCANNER_OUTPUT / "newsletter.html"
    if not newsletter_src.exists():
        print(f"  ⚠ No newsletter.html found")
        print(f"    Save Prompt 4 output as newsletter.html alongside decisions.json")
        print()
        return

    targets = [
        SUBSTACK_CURRENT / "newsletter.html",
    ]

    if dry_run:
        print(f"  [DRY RUN] Would copy {newsletter_src} to {len(targets)} location(s)")
        print()
        return

    for target in targets:
        if target.resolve() == newsletter_src.resolve():
            continue  # Skip self-copy
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(newsletter_src, target)
        print(f"  ✓ Copied to {target}")

    print()
```

---

## 2. SCANNER.PY — REFACTORING SPECIFICATION

**Current:** 2,518 lines
**Target:** ~900-1,000 lines
**Reduction:** ~1,500 lines of dead code, unused fields, and archived functions

### 2.1 Stock Dataclass — Strip to Technical-Only Fields

**Current location:** Lines 176-310 (~135 lines, ~60 fields)
**Target:** ~40 lines, ~20 fields

**Fields to KEEP:**
```python
@dataclass
class Stock:
    symbol: str
    price: float = 0.0
    beta: float = 0.0  # Informational, not an entry gate

    # Sterling Grid V6 indicators
    hma_value: float = 0.0
    hma_pivot_low: bool = False
    hma_pivot_high: bool = False
    hma_slope_rising: bool = False
    rsi14: float = 0.0
    macd_cross_up: bool = False
    macd_line: float = 0.0
    macd_signal_line: float = 0.0
    macd_histogram: float = 0.0
    uc: float = 0.0
    uc_prev: float = 0.0
    uc_rising: bool = False
    uc_falling: bool = False
    price_under_cap: bool = False
    buy_signal: bool = False
    exd_signal: bool = False
    quality_tier: int = 0
    week_date: str = ""

    # Computed fields
    return_20d: float = 0.0
    momentum_4w: float = 0.0
    tier: str = ""

    def meets_technical_criteria(self) -> bool:
        return self.buy_signal

    def get_tier(self) -> str:
        if not self.meets_technical_criteria():
            return ""
        if self.quality_tier == 1:
            return "T1"
        elif self.quality_tier == 2:
            return "T2"
        elif self.quality_tier == 3:
            return "T3"
        # Fallback classification
        if self.uc_rising and self.macd_cross_up:
            self.quality_tier = 1
            return "T1"
        elif self.macd_cross_up:
            self.quality_tier = 2
            return "T2"
        elif self.uc_rising:
            self.quality_tier = 3
            return "T3"
        return "T3"
```

**Fields to REMOVE:**

| Field | Reason |
|-------|--------|
| `hma_slope_falling` | Only used in display, can derive from exit_data at output time |
| `rsi_above_50` | V6 doesn't gate on RSI — remove the bool, keep `rsi14` value |
| `uc_rising_above` | V4 legacy — daily scanner being removed |
| `banker`, `banker_prev`, `banker_rising` | Legacy indicator — daily scanner being removed |
| `bos_bullish`, `bos_bearish`, `bos_debug` | Legacy indicator — daily scanner being removed |
| `theme`, `theme_score`, `pure_play_score` | Populated by chat, not scanner |
| `theme_verdict`, `theme_classification` | Populated by chat, not scanner |
| `valuation_regime` | Populated by chat, not scanner |
| `final_decision`, `conviction` | Populated by chat, not scanner |
| `gate_verdict`, `gate_conviction` | Populated by chat, not scanner |
| `gate_catalyst`, `gate_bear_case`, `gate_math` | Populated by chat, not scanner |
| `sector_status`, `upside_potential` | Populated by chat, not scanner |
| `bullish_factors`, `risk_factors`, `reasoning` | Populated by chat, not scanner |
| `catalyst_summary`, `red_flag_level`, `action` | Populated by chat, not scanner |
| `position_size_pct`, `position_dollars`, `position_tier`, `sizing_gear` | Populated by chat, not scanner |
| `dd_verdict`, `dd_conviction`, `dd_position_size` | Populated by chat, not scanner |
| `dd_analysis`, `dd_key_catalyst`, `dd_fatal_flaw` | Populated by chat, not scanner |
| `dd_elevator_pitch`, `dd_why_now`, `dd_the_math` | Populated by chat, not scanner |
| `dd_bear_case`, `dd_risk_to_monitor`, `dd_action` | Populated by chat, not scanner |

**Also remove these methods:**
- `passes_theme_gate()` — chat decides theme fit
- `is_confirmed()` — chat decides confirmation

---

### 2.2 ScanStats — Strip Legacy Fields

**Current location:** Lines 312-343
**Fields to REMOVE:**

| Field | Reason |
|-------|--------|
| `beta_gte_1_5` | Beta is no longer a gate |
| `bos_bullish`, `bos_bearish` | Legacy indicators being removed |
| `banker_rising` | Legacy indicator being removed |
| `uc_rising_above` | V4 legacy |
| `momentum_filtered`, `passes_momentum` | Always 0 in new architecture |
| `theme_confirmed` | Populated by chat, not scanner |
| `final_trade`, `final_consider`, `final_skip` | Populated by chat, not scanner |

---

### 2.3 Remove Dead Functions

**Functions to DELETE entirely:**

| Function | Lines (approx) | Reason |
|----------|----------------|--------|
| `generate_newsletter_briefing()` | 1419-1431 | Stub — returns single line |
| `_generate_newsletter_briefing_ARCHIVED()` | 1433-1913 | ~480 lines of archived dead code |
| `save_newsletter_briefing()` | 1916-1930 | Stub — no-op |
| `print_newsletter_prompts()` | 1933-1939 | Stub — no-op |

**Total dead code removed:** ~500 lines

---

### 2.4 Simplify generate_report()

**Current:** Lines 1190-1412 (~220 lines). Produces elaborate text report with sections for BUY NOW / BUY ON PULLBACK / PENDING DD / CONSIDER, signal details tables, entry criteria references, and exit strategy reminders.

**Problem:** In the new workflow, the human reviews `signals_technical.json` in the Claude.ai chat, not a text report. The report is saved to `report.txt` and emailed. The elaborate sections about STRONG_BUY, SPEC_BUY, PENDING_DD gate verdicts are meaningless because the scanner no longer populates those fields — `final_decision` is always "TECHNICAL_ONLY".

**Recommended approach:** Replace with a ~50-line summary report:

```python
def generate_report(technical_signals: List[Stock], sell_signals: List[SellSignal], 
                   stats: ScanStats) -> str:
    """Generate scan summary report for email notification and archival."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date_display = datetime.now().strftime("%A, %B %d, %Y")
    
    lines = []
    lines.append("=" * 72)
    lines.append(f"  STERLING GRID V6 — WEEKLY SCAN REPORT")
    lines.append(f"  {date_display}")
    lines.append("=" * 72)
    
    # Scan funnel
    lines.append("")
    lines.append(f"  Tickers scanned:     {stats.tickers_loaded:>6}")
    lines.append(f"  Data downloaded:     {stats.data_downloaded:>6}")
    lines.append(f"  Price < ${PRICE_CAP:.0f}:        {stats.price_under_cap:>6}")
    lines.append(f"  HMA pivot low:       {stats.hma_pivot_low:>6}")
    lines.append(f"  Buy signal (V6):     {stats.buy_signal:>6}")
    lines.append(f"    T1 (UC + MACD):    {stats.tier_t1:>6}")
    lines.append(f"    T2 (MACD only):    {stats.tier_t2:>6}")
    lines.append(f"    T3 (UC only):      {stats.tier_t3:>6}")
    lines.append(f"  ExD exit signals:    {stats.exd_exit:>6}")
    
    # Entry candidates
    if technical_signals:
        lines.append("")
        lines.append("─" * 72)
        lines.append("  ENTRY CANDIDATES (pending Claude.ai analysis)")
        lines.append("─" * 72)
        lines.append(f"  {'TIER':<5} {'SYMBOL':<7} {'PRICE':>8} {'UC':>6} {'RSI':>5} {'MACD':>5} {'20D':>7}")
        lines.append("  " + "-" * 50)
        for s in sorted(technical_signals, key=lambda x: -x.uc):
            macd = "✓" if s.macd_cross_up else "✗"
            lines.append(f"  {s.tier:<5} {s.symbol:<7} ${s.price:>7.2f} {s.uc:>5.1f} {s.rsi14:>5.0f} {macd:>5} {s.return_20d:>+6.1f}%")
    else:
        lines.append("")
        lines.append("  No technical entry signals this week.")
    
    # Exit signals
    if sell_signals:
        lines.append("")
        lines.append("─" * 72)
        lines.append("  EXIT SIGNALS")
        lines.append("─" * 72)
        for s in sell_signals:
            pnl = ((s.price / s.entry_price) - 1) * 100 if s.entry_price > 0 else 0
            lines.append(f"  🔴 {s.symbol} @ ${s.price:.2f} | {s.reason} | P&L: {pnl:+.1f}%")
    
    # Next steps
    lines.append("")
    lines.append("─" * 72)
    lines.append("  NEXT: Review signals_technical.json in Claude.ai chat")
    lines.append("  (Thematic analysis → Investment Gate → Deep DD)")
    lines.append("=" * 72)
    
    return "\n".join(lines)
```

---

### 2.5 Simplify save_results()

**Current:** Lines 1942-2292 (~350 lines). Builds full `_signal_dict()` with all LLM fields, constructs `signals_data` with LLM fields populated, then zeroes every LLM field out.

**Replace with:**
```python
def save_results(technical_signals: List[Stock], sell_signals: List[SellSignal], 
                stats: ScanStats, archive: bool = False):
    """Save technical scan results to signals_technical.json and analysis log."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    current_dir, week_dir = ensure_output_structure()

    # Build signal dicts — technical fields only
    def _tech_signal(s: Stock) -> dict:
        return {
            "symbol": s.symbol,
            "price": s.price,
            "tier": s.tier,
            "quality_tier": s.quality_tier,
            "beta": s.beta,
            "uc": s.uc,
            "uc_rising": s.uc_rising,
            "rsi14": s.rsi14,
            "macd_cross_up": s.macd_cross_up,
            "hma_pivot_low": s.hma_pivot_low,
            "hma_pivot_high": s.hma_pivot_high,
            "hma_slope_rising": s.hma_slope_rising,
            "buy_signal": s.buy_signal,
            "exd_signal": s.exd_signal,
            "return_20d": s.return_20d,
            "momentum_4w": s.momentum_4w,
            "week_date": s.week_date,
            # Legacy key for downstream compat
            "banker": s.uc,
        }

    signals_data = {
        "timestamp": timestamp,
        "timeframe": "WEEKLY",
        "entry_criteria": f"Sterling Grid V6: HMA pivot + (UC rising OR MACD cross-up) + Price<${PRICE_CAP:.0f}",
        "exit_criteria": "ExD compound exit + tiered profit lock",
        "stats": {
            "tickers_loaded": stats.tickers_loaded,
            "data_downloaded": stats.data_downloaded,
            "price_under_cap": stats.price_under_cap,
            "hma_pivot_low": stats.hma_pivot_low,
            "macd_cross_up": stats.macd_cross_up,
            "uc_rising": stats.uc_rising,
            "buy_signal": stats.buy_signal,
            "tier_t1": stats.tier_t1,
            "tier_t2": stats.tier_t2,
            "tier_t3": stats.tier_t3,
            "exd_exit": stats.exd_exit,
            "technical_signals": stats.technical_signals,
        },
        "buy_signals": [_tech_signal(s) for s in technical_signals],
        "sell_signals": [
            {
                "symbol": s.symbol,
                "price": s.price,
                "reason": s.reason,
                "entry_price": s.entry_price,
                "highest_close": s.highest_close,
                "pnl_pct": round(((s.price / s.entry_price) - 1) * 100, 2) if s.entry_price > 0 else 0.0,
            }
            for s in sell_signals
        ],
        # Historical tracking for content systems
        "historical_winners": [],
        "big_wins": [],
        "home_runs": [],
    }

    # Populate historical wins from signal_tracker
    try:
        from twitter.signal_tracker import load_historical_signals, find_big_wins
        from config import MARKETING_THRESHOLDS
        historical = load_historical_signals()
        signals_data["historical_winners"] = [
            {"ticker": h.ticker, "entry_price": h.entry_price,
             "current_price": h.current_price, "pnl_pct": h.pnl_pct,
             "signal_date": h.entry_date, "theme": h.theme}
            for h in historical
        ]
        all_big_wins = find_big_wins()
        big_win_threshold = MARKETING_THRESHOLDS.get('big_win_threshold', 25.0)
        home_run_threshold = MARKETING_THRESHOLDS.get('home_run_threshold', 50.0)
        signals_data["big_wins"] = [
            {"ticker": w.ticker, "entry_price": w.entry_price,
             "current_price": w.current_price, "pnl_pct": w.pnl_pct,
             "signal_date": w.entry_date, "theme": w.theme}
            for w in all_big_wins if w.pnl_pct >= big_win_threshold
        ]
        signals_data["home_runs"] = [
            {"ticker": w.ticker, "entry_price": w.entry_price,
             "current_price": w.current_price, "pnl_pct": w.pnl_pct,
             "signal_date": w.entry_date, "theme": w.theme}
            for w in all_big_wins if w.pnl_pct >= home_run_threshold
        ]
    except (ImportError, Exception) as e:
        print(f"  ⚠ Historical wins not populated: {e}")

    # Write outputs
    signals_json = json.dumps(signals_data, indent=2)
    
    with open(SIGNALS_TECH_FILE, 'w') as f:
        f.write(signals_json)
    
    signals_current = current_dir / "signals_technical.json"
    with open(signals_current, 'w') as f:
        f.write(signals_json)
    
    signals_archive = week_dir / "signals_technical.json"
    with open(signals_archive, 'w') as f:
        f.write(signals_json)

    # Analysis log (CSV) — simplified to technical fields
    # ... (keep existing CSV logic but remove LLM fields from fieldnames)

    # Generate and save report
    report = generate_report(technical_signals, sell_signals, stats)
    report_current = current_dir / "report.txt"
    with open(report_current, 'w') as f:
        f.write(report)

    print(f"\n  📁 Results saved:")
    print(f"     • {rel_path(SIGNALS_TECH_FILE)} (signals_technical.json)")
    print(f"     • {rel_path(signals_current)} (current/)")
    print(f"     • {rel_path(report_current)} (report)")

    return report
```

---

### 2.6 Simplify run_scan() Return Value

**Current:** Returns 6-tuple:
```python
return confirmed, confirmed, sell_signals, stats, momentum_rejected, themes_data
# where confirmed == all_assessed, momentum_rejected == [], themes_data == []
```

**Change to:** Return 3-tuple:
```python
return technical_signals, sell_signals, stats
```

**Update main() accordingly:**
```python
# Current (line 2417):
confirmed, all_assessed, sell_signals, stats, momentum_rejected, themes_data = run_scan(...)

# Change to:
technical_signals, sell_signals, stats = run_scan(top_n=args.top, verbose=args.verbose)
```

---

### 2.7 Simplify print_final_report()

**Current:** Lines 995-1174 (~180 lines). Prints elaborate BUY NOW / BUY ON PULLBACK / PENDING DD sections referencing gate verdicts that are never populated.

**Replace with ~50 lines:** Print technical signals table, sell signals, and action summary. Remove all references to `gate_verdict`, `final_decision`, `conviction`, `reasoning`, `theme`, etc. since these are all empty in the technical-only output.

---

### 2.8 Clean Up main()

**Remove legacy CLI flags (lines 2367-2378):**
```python
# These are suppressed but still parsed — remove entirely
parser.add_argument("--no-llm", ...)        # DELETE
parser.add_argument("--no-momentum", ...)    # DELETE
parser.add_argument("--assess-top", ...)     # DELETE
parser.add_argument("--web-search", ...)     # DELETE
parser.add_argument("--no-dd", ...)          # DELETE
parser.add_argument("--save-dd", ...)        # DELETE
parser.add_argument("--no-prompts", ...)     # DELETE
parser.add_argument("--no-dd-prompts", ...)  # DELETE
parser.add_argument("--no-grok-prompts", ...) # DELETE
parser.add_argument("--full-dd", ...)        # DELETE
parser.add_argument("--dd-top", ...)         # DELETE
parser.add_argument("--dd", ...)             # DELETE
```

---

### 2.9 Clean Up Imports

**Remove (line 104):**
```python
PORTFOLIO_MANAGER_AVAILABLE = True  # Hard dependency as of audit remediation
```
The import at lines 96-103 will raise ImportError if unavailable — no need for a flag.

**Remove legacy threshold aliases (lines 152-154):**
```python
BETA_MIN = BETA_THRESHOLD        # Only used by removed beta stat counter
BETA_SIGNAL = BETA_THRESHOLD     # Never used
TRAILING_STOP_PCT = float(...)   # "Used by daily scanner only" — daily scanner being removed
```

---

### 2.10 Estimated Line Count After Refactoring

| Section | Current | Target | Notes |
|---------|---------|--------|-------|
| Imports & config | ~160 | ~120 | Remove legacy aliases, simplify |
| Stock + ScanStats + PipelineCostTracker | ~210 | ~80 | Strip to technical fields |
| load_tickers() | ~25 | ~25 | Keep as-is |
| calculate_beta() | ~15 | ~15 | Keep as-is |
| download_and_process() | ~130 | ~120 | Remove legacy field population |
| SellSignal + check_sell_signals() | ~80 | ~80 | Keep as-is — works correctly |
| run_scan() | ~310 | ~250 | Remove verbose display sections for empty fields |
| print_final_report() | ~180 | ~50 | Simplified technical-only output |
| _print_wrapped() | ~12 | 0 | No longer needed (no text to wrap) |
| generate_report() | ~220 | ~50 | Simplified summary |
| newsletter functions (4 stubs + archived) | ~520 | 0 | All deleted |
| save_results() | ~350 | ~100 | Direct technical output, no build-then-zero |
| send_notification() | ~60 | ~50 | Minor cleanup |
| main() | ~160 | ~80 | Remove legacy flags, simplify flow |
| **TOTAL** | **~2,518** | **~900** | **~64% reduction** |

---

## 3. MERGE_DECISIONS.PY — BUG FIXES & HARDENING

Beyond the critical bugs (BUG-2, BUG-4) addressed in Section 1:

### 3.1 Remove `has_newsletter` Check From build_content_schedule()

**Line 354:**
```python
"has_newsletter": (CURRENT_DIR / "newsletter.html").exists(),
```
**Problem:** At merge time, the newsletter hasn't been placed in `CURRENT_DIR` yet — it's saved alongside `decisions.json` by the user and distributed in Step 5 of the workflow. This will always return `False`.

**Fix:** Either remove the field, or check the correct location:
```python
# Check same directory as decisions.json
newsletter_path = DECISIONS_DEFAULT.parent / "newsletter.html"
"has_newsletter": newsletter_path.exists(),
```

### 3.2 Add `market_context_summary` to Merged Output

The `market_context_summary` from decisions.json is useful for the content production guide and tweet generator. It's captured in `build_content_schedule()` but not in the main `merge_signals()` output.

**Add to merge_signals():**
```python
merged = {
    # ... existing fields
    "market_context_summary": decisions.get("market_context_summary", ""),
    "market_regime": decisions.get("market_regime", ""),
    # ...
}
```

### 3.3 Validate Theme Sub-Scores Are Numeric

Prompt 7 asks Claude to estimate theme sub-scores (catalyst, momentum, crowding, runway) as 0-10 floats. If Claude outputs strings or nulls, downstream consumers break silently.

**Add to validate_decisions():**
```python
for i, theme in enumerate(decisions.get("themes_this_week", [])):
    prefix = f"themes_this_week[{i}]"
    for score_field in ["composite_score", "catalyst_score", "momentum_score", 
                        "crowding_score", "runway_score"]:
        val = theme.get(score_field)
        if val is not None and not isinstance(val, (int, float)):
            warnings.append(f"{prefix}: {score_field} is {type(val).__name__}, expected number")
```

### 3.4 Handle `position_size_pct` Correctly

**Line 238:** `"position_size_pct": pos.get("position_size_pct", 0)`

If decisions.json has `"position_size_pct": 0.20` (correct), this works. But the Prompt 7 schema also has `"position_size": "FULL"`. The merge should derive `position_size_pct` from the tier if not explicitly provided:

```python
# After building signal dict, before appending:
if signal["position_size_pct"] == 0 and signal["tier"]:
    tier_pcts = {"T1": 0.20, "T2": 0.10, "T3": 0.05}
    signal["position_size_pct"] = tier_pcts.get(signal["tier"], 0.10)
```

---

## 4. SATURDAY_WORKFLOW.PY — FIXES & IMPROVEMENTS

Beyond BUG-1 and BUG-5 in Section 1:

### 4.1 Add `--decisions-dir` Flag

Currently the workflow expects `decisions.json` in `scanner/output/`. The user saves it from chat and may have it elsewhere. Allow specifying a directory where both `decisions.json` and `newsletter.html` live:

```python
parser.add_argument("--decisions-dir", type=Path, default=None,
    help="Directory containing decisions.json and newsletter.html")
```

Then in main():
```python
if args.decisions_dir:
    decisions_path = args.decisions_dir / "decisions.json"
else:
    decisions_path = args.decisions
```

### 4.2 Add Pre-Flight Validation

Before running any steps, validate that inputs exist and are reasonable:

```python
def preflight_check(decisions_path: Path) -> bool:
    """Validate inputs before running workflow."""
    ok = True
    
    # Check decisions.json exists
    if not decisions_path.exists():
        print(f"  ✗ decisions.json not found: {decisions_path}")
        print(f"    Run Claude.ai analysis and save Prompt 7 output here")
        ok = False
    
    # Check signals_technical.json exists (optional but important)
    if not SIGNALS_TECH_FILE.exists():
        alt = CURRENT_DIR / "signals_technical.json"
        if not alt.exists():
            print(f"  ⚠ signals_technical.json not found — merge will use decisions-only mode")
    
    # Check decisions.json is valid JSON
    if decisions_path.exists():
        try:
            with open(decisions_path) as f:
                data = json.load(f)
            if not data.get("scan_date"):
                print(f"  ⚠ decisions.json missing scan_date")
        except json.JSONDecodeError as e:
            print(f"  ✗ decisions.json is not valid JSON: {e}")
            ok = False
    
    return ok
```

### 4.3 Print Clearer Next Steps Based on What Was Produced

The current summary always prints the same 5 next steps. Conditionally show only relevant ones:

```python
def step_summary(decisions: dict, dry_run: bool = False):
    # ... existing summary code ...
    
    print("  NEXT STEPS:")
    print("  ─────────────────────────────────────────")
    step = 1
    
    newsletter_exists = (SUBSTACK_CURRENT / "newsletter.html").exists()
    if newsletter_exists:
        print(f"  {step}. Publish newsletter to Substack")
        step += 1
    else:
        print(f"  {step}. Generate newsletter in Claude.ai (Prompt 4) and re-run workflow")
        step += 1
    
    guide_exists = (SUBSTACK_CURRENT / "content_production_guide.md").exists()
    if guide_exists:
        print(f"  {step}. Attach content_production_guide.md to Claude.ai for daily posts")
        step += 1
    
    print(f"  {step}. Post 3 Substack notes for today")
    print("  ─────────────────────────────────────────")
```

---

## 5. STERLING_INDICATORS.PY — STATUS & NOTES

**Status: No changes required.** This file is clean, well-documented, and backtest-verified.

**One verification to confirm:** The constants defined locally (QUALITY_TIERS, SIZING_GEARS, LOCK_TIERS, MAX_CONCURRENT_POSITIONS) should be the canonical source. Verify that `config/settings.py` imports from `sterling_indicators` or defines identical values. If both define independently, consolidate to one source.

```python
# config/settings.py should either:
# Option A (preferred): Import from sterling_indicators
from scanner.sterling_indicators import QUALITY_TIERS, SIZING_GEARS, LOCK_TIERS, MAX_CONCURRENT_POSITIONS

# Option B: Be verified to match exactly
# (fragile — changes need two edits)
```

---

## 6. FILE DELETIONS

### 6.1 Files to Delete

| File | Lines | Reason |
|------|-------|--------|
| `scanner/daily_scanner.py` | ~791 | User confirmed removal — uses legacy indicators, separate portfolio |
| `scanner/legacy_indicators.py` | ~177 | User confirmed removal — only used by daily_scanner |
| `scanner/due_diligence.py` | ~494 | User confirmed removal — standalone CLI tool, never in pipeline |

### 6.2 Related Cleanup

After deleting these files:

- **Remove** `daily_scan.yml` GitHub Actions workflow (or comment out triggers and add deprecation notice)
- **Remove** `daily_scanner` imports from `config/__init__.py` if any
- **Remove** `DAILY_PORTFOLIO_BACKUP_DIR` from `config/output_paths.py` if no longer needed
- **Check** `tests/test_daily_scanner.py` — delete or archive (11 tests that will break)
- **Check** `run_friday.sh` and `run_local_friday.sh` for any daily_scanner references

---

## 7. SIGNALS_TECHNICAL.JSON OUTPUT SCHEMA

The scanner should produce this exact schema. This is the contract between the Friday scanner and the Saturday merge step.

```json
{
  "timestamp": "2026-02-21 16:30:00",
  "timeframe": "WEEKLY",
  "entry_criteria": "Sterling Grid V6: HMA pivot + (UC rising OR MACD cross-up) + Price<$25",
  "exit_criteria": "ExD compound exit + tiered profit lock",
  
  "stats": {
    "tickers_loaded": 1800,
    "data_downloaded": 1650,
    "price_under_cap": 820,
    "hma_pivot_low": 45,
    "macd_cross_up": 32,
    "uc_rising": 89,
    "buy_signal": 14,
    "tier_t1": 2,
    "tier_t2": 5,
    "tier_t3": 7,
    "exd_exit": 3,
    "technical_signals": 14
  },
  
  "buy_signals": [
    {
      "symbol": "TICKER",
      "price": 12.50,
      "tier": "T1",
      "quality_tier": 1,
      "beta": 1.82,
      "uc": 15.3,
      "uc_rising": true,
      "rsi14": 58.2,
      "macd_cross_up": true,
      "hma_pivot_low": true,
      "hma_pivot_high": false,
      "hma_slope_rising": true,
      "buy_signal": true,
      "exd_signal": false,
      "return_20d": 8.5,
      "momentum_4w": 12.3,
      "week_date": "2026-02-20",
      "banker": 15.3
    }
  ],
  
  "sell_signals": [
    {
      "symbol": "HELD",
      "price": 18.50,
      "reason": "ExD exit (HMA pivot high + UC falling)",
      "entry_price": 10.00,
      "highest_close": 22.00,
      "pnl_pct": 85.0
    }
  ],
  
  "historical_winners": [
    {
      "ticker": "PREV",
      "entry_price": 5.00,
      "current_price": 12.50,
      "pnl_pct": 150.0,
      "signal_date": "2025-11-15",
      "theme": "AI Infrastructure"
    }
  ],
  "big_wins": [],
  "home_runs": []
}
```

**Notes:**
- `banker` is a legacy alias for `uc` value — kept for tweet_generator backward compat
- `buy_signals` is the single flat array of all technical signals (no pass/consider split at this stage)
- `sell_signals` come from portfolio position checks, not from decisions.json (those are merged later)
- `historical_winners`, `big_wins`, `home_runs` come from signal_tracker and portfolio data

---

## 8. DECISIONS.JSON INPUT VALIDATION

The `validate_decisions()` function should check for real issues that will cause downstream failures. Current validation is good but missing a few checks:

### 8.1 Required Fields (Current — Keep)

```python
["scan_date", "market_regime", "new_positions", "themes_this_week"]
```

### 8.2 Add These Checks

```python
# Validate scan_date is a real date
try:
    datetime.strptime(decisions.get("scan_date", ""), "%Y-%m-%d")
except ValueError:
    warnings.append(f"scan_date '{decisions.get('scan_date')}' is not YYYY-MM-DD format")

# Validate market_regime is one of expected values
valid_regimes = {"risk_on", "risk_off", "selective"}
regime = decisions.get("market_regime", "")
if regime not in valid_regimes:
    warnings.append(f"market_regime '{regime}' not in {valid_regimes}")

# Validate new positions have tier
for i, pos in enumerate(decisions.get("new_positions", [])):
    prefix = f"new_positions[{i}] ({pos.get('symbol', '?')})"
    if pos.get("tier", "") not in ("T1", "T2", "T3"):
        warnings.append(f"{prefix}: tier '{pos.get('tier')}' not in T1/T2/T3")
    if pos.get("price", 0) <= 0:
        warnings.append(f"{prefix}: price is {pos.get('price', 0)}")

# Validate themes have names
for i, theme in enumerate(decisions.get("themes_this_week", [])):
    if not theme.get("name"):
        warnings.append(f"themes_this_week[{i}]: missing name")

# Validate exits have required fields
for i, ex in enumerate(decisions.get("exits", [])):
    prefix = f"exits[{i}] ({ex.get('symbol', '?')})"
    if not ex.get("symbol"):
        warnings.append(f"{prefix}: missing symbol")
    if ex.get("exit_price", 0) <= 0:
        warnings.append(f"{prefix}: exit_price is {ex.get('exit_price', 0)}")
```

---

## 9. IMPLEMENTATION ORDER

Execute in this order. Each step is independently testable. Commit after each.

### Phase 1: Critical Bug Fixes (30 minutes)

1. **BUG-1:** Fix saturday_workflow.py to load `SIGNALS_TECH_FILE`
2. **BUG-2:** Fix merge_decisions.py default values (True → False)
3. **BUG-3:** Remove undefined `signals_file` reference from scanner.py
4. **BUG-4:** Fix tech_lookup to read from all signal arrays
5. **BUG-5:** Fix newsletter step source/target logic

**Test:** `python -m scanner.saturday_workflow --dry-run` with sample data should not crash. Verify merge output has correct defaults.

**Commit:** `Fix 5 critical bugs in scanner workflow (pre-testing hardening)`

### Phase 2: Delete Dead Files (5 minutes)

1. Delete `scanner/daily_scanner.py`
2. Delete `scanner/legacy_indicators.py`
3. Delete `scanner/due_diligence.py`
4. Archive or delete `tests/test_daily_scanner.py`

**Test:** `python -m scanner.scanner --help` still works. `python -c "from scanner.sterling_indicators import generate_entry_signal"` still works.

**Commit:** `Remove daily scanner, legacy indicators, and standalone DD tool`

### Phase 3: Strip Scanner Dead Code (1-2 hours)

1. Remove archived newsletter functions (~500 lines)
2. Strip Stock dataclass to technical-only fields
3. Strip ScanStats legacy fields
4. Simplify run_scan() return value to 3-tuple
5. Simplify generate_report() to ~50 lines
6. Simplify save_results() — direct technical output
7. Simplify print_final_report() — technical-only display
8. Remove legacy CLI flags from main()
9. Clean up imports and legacy aliases

**Test:** Run `python -m scanner.scanner --verbose` (may need mock data or small ticker file). Verify `signals_technical.json` output matches schema in Section 7. Run existing test suite (`pytest tests/test_sterling_indicators.py`).

**Commit:** `Refactor scanner.py: strip to technical-only (2518→~900 lines)`

### Phase 4: Harden Merge & Workflow (30 minutes)

1. Apply merge_decisions.py improvements (Sections 3.1-3.4)
2. Apply saturday_workflow.py improvements (Sections 4.1-4.3)
3. Add validation improvements (Section 8)

**Test:** Create a realistic `decisions.json` by hand (matching Prompt 7 schema), run `python -m scanner.saturday_workflow --dry-run`. Verify merged output has all expected fields.

**Commit:** `Harden merge_decisions and saturday_workflow for production use`

### Phase 5: Verify Config Constants (15 minutes)

1. Confirm `config/settings.py` and `sterling_indicators.py` define identical constants (or import from one source)
2. Remove any orphaned config references to daily scanner or legacy indicators

**Commit:** `Consolidate config constants, remove orphaned references`

---

## 10. TESTING CHECKLIST

### Scanner Tests
- [ ] `python -m scanner.scanner --verbose` completes without errors
- [ ] `signals_technical.json` output matches Section 7 schema
- [ ] All `buy_signals[]` entries have `buy_signal: true` and valid tier
- [ ] `sell_signals[]` correctly identifies exits on held positions
- [ ] `historical_winners` / `big_wins` / `home_runs` populated from signal_tracker
- [ ] Email notification fires with simplified report
- [ ] Analysis log CSV has correct (simplified) fieldnames
- [ ] `report.txt` is readable and contains scan summary
- [ ] `--top 50` flag works (limits to top 50 by UC)
- [ ] `--no-email` flag suppresses email

### Merge Tests
- [ ] `python -m scanner.merge_decisions --dry-run` with sample decisions.json
- [ ] Merged `signals.json` has correct schema for downstream consumers
- [ ] Tickers in decisions.json but NOT in signals_technical.json get warning + False defaults
- [ ] Tickers in signals_technical.json but NOT in decisions.json appear in assessed_signals
- [ ] Sell signals from both scanner and decisions.json are merged without duplicates
- [ ] Theme data maps correctly with all sub-scores
- [ ] Portfolio update adds trades with correct parameters

### Workflow Tests
- [ ] `python -m scanner.saturday_workflow --dry-run` completes all 7 steps
- [ ] Step 1 loads from `signals_technical.json` (not `signals.json`)
- [ ] Step 5 finds and distributes newsletter from correct location
- [ ] Step 6 archives all files to weekly folder
- [ ] `--skip-market` and `--skip-guide` flags work
- [ ] Summary shows correct counts and relevant next steps

### Integration Test (Pre-Live)
- [ ] Run scanner against small ticker file (50 tickers)
- [ ] Create decisions.json matching Prompt 7 schema with 1-2 test positions
- [ ] Run full saturday_workflow
- [ ] Verify `signals.json` is consumable by content_production_guide.py
- [ ] Verify `signals.json` is consumable by tweet_generator.py (import + load)
- [ ] Verify portfolio.csv is updated correctly

---

## 11. DEFERRED ITEMS (Pending Downstream Audit)

These changes may be needed but depend on what the tweet system, content production guide, and newsletter compiler actually read from `signals.json`. We'll refine after reviewing those subsystems.

### 11.1 Legacy Field Pruning in Merged signals.json

The merge currently outputs ~50 fields per signal for downstream compat. Some may be unused:
- `uc_rising_above` — V4 legacy, may not be read by anything
- `banker` — alias for UC, may be read by tweet_generator
- `pure_play_score` — alias for theme_score, may be read by content systems
- `sector_status` — always empty string, may be read by something

**Action:** After auditing downstream consumers, remove any fields that nothing reads.

### 11.2 Newsletter Workflow — Prompt 4 vs Automated

The current architecture has the newsletter produced in the chat session (Prompt 4). An alternative is to have the automated newsletter_compiler.py generate it from signals.json after merge, which would ensure consistency with the content production guide's weekly schedule. This decision depends on how the Substack content system is structured.

### 11.3 `content_schedule.json` — Is It Actually Consumed?

`build_content_schedule()` produces a minimal metadata file. If nothing reads it, it can be removed from the merge step. Verify during content system audit.

### 11.4 Prompt 7 Schema Alignment

The Prompt 7 JSON schema in `sterling_prompt_library.md` should be validated against what merge_decisions.py actually reads. Any fields in the schema that merge_decisions.py ignores are wasted chat tokens. Any fields merge_decisions.py expects but Prompt 7 doesn't produce will be silently missing.

**Known mismatches to verify:**
- `opportunity_type` — in Prompt 7 schema, not sure if merge reads it
- `variant_perception`, `key_assumption`, `kill_switch`, `downside_floor` — in Prompt 7 schema, merge reads some for bullish/risk_factors construction
- `stop_price` — in Prompt 7 schema, merge doesn't seem to use it

### 11.5 Analysis Log CSV — Simplify or Remove

The analysis log appends every assessed stock to a growing CSV. In the new workflow, only technical signals are in the scanner output. The LLM analysis fields (`theme`, `conviction`, `reasoning`) are always empty. The CSV structure should either be simplified to technical-only fields, or the log should be removed if nobody analyses it.

---

## SUMMARY

| Category | Count | Impact |
|----------|-------|--------|
| Critical bugs to fix | 5 | Prevents runtime errors and silent data corruption |
| Lines to remove from scanner.py | ~1,600 | 64% reduction — dead code, archived functions, unused fields |
| Files to delete | 3 | ~1,462 lines of unused code (daily scanner, legacy indicators, DD CLI) |
| Merge improvements | 4 | Better validation, correct defaults, missing fields |
| Workflow improvements | 3 | Correct data source, working newsletter step, pre-flight checks |
| Deferred items | 5 | Pending downstream consumer audit |

**Net result:** A scanner subsystem that does exactly one thing well — detect technical entry/exit signals on Friday — and a merge/workflow layer that reliably bridges the Saturday chat session to downstream automation. No dead code, no fabricated data, no runtime errors waiting to fire.
