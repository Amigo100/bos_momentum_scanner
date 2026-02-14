# Sterling Signals Pipeline — Assessment Overhaul
## Investment Gate + Deep DD Integration Guide

---

## NEW ARCHITECTURE

```
                OLD PIPELINE                          NEW PIPELINE
            ┌─────────────────┐               ┌─────────────────────┐
  5-15      │  GATEKEEPER     │    5-15       │  INVESTMENT GATE    │
  stocks ──>│  ~$0.20/stock   │──> stocks ──> │  Sonnet, ~$0.20/ea  │
            │  3 web searches │               │  5 web searches     │
            │  PASS/FAIL      │               │  Regime-aware       │
            └────────┬────────┘               │  PASS/FAIL          │
                     │                        └────────┬────────────┘
            ┌────────▼────────┐                        │
  5-15      │  DD AUTOMATOR   │               ┌────────▼────────────┐
  stocks ──>│  ~$0.25/stock   │    1-3        │  DEEP DD            │
  (same!)   │  4 web searches │    stocks ──> │  Opus + Thinking    │
            │  Repeats work!  │    (passes    │  ~$1.50/ea          │
            │  BUY/NO GO      │     only)     │  Newsletter content │
            └─────────────────┘               │  Portfolio gate     │
                                              │  STRONG/SPEC/NO GO  │
                                              └─────────────────────┘
```

### Cost comparison (typical scan: 10 theme-pass stocks, 2 reach portfolio)

| | Old Pipeline | New Pipeline |
|---|---|---|
| Gatekeeper | 10 × $0.20 = $2.00 | — |
| DD Automator | 10 × $0.25 = $2.50 | — |
| Investment Gate | — | 10 × $0.20 = $2.00 |
| Deep DD (Opus) | — | 2 × $1.50 = $3.00 |
| **Total** | **$4.50** | **$5.00** |
| **Depth on buys** | **Shallow** (Sonnet) | **Deep** (Opus + thinking) |
| **Regime-aware** | ❌ | ✅ |
| **Duplicate work** | ~7 searches × 10 | ~5 searches × 10 + 4 × 2 |

Cost is similar but depth where it matters (on stocks you're actually buying) is dramatically higher. Opus + 10k thinking tokens vs Sonnet doing the same shallow pass twice.

---

## FILES

| File | Status | Purpose |
|------|--------|---------|
| `core/investment_gate.py` | **NEW** | Sonnet filter — replaces gatekeeper + quick DD |
| `core/deep_dd.py` | **NEW** | Opus deep analysis — newsletter content + final gate |
| `core/gatekeeper.py` | **RETIRE** | Keep for reference, stop importing |
| `core/dd_automator.py` | **RETIRE** | Keep for reference, stop importing |
| `due_diligence.py` | **KEEP** | Manual standalone deep-dive (unchanged) |

---

## SCANNER.PY CHANGES

### CHANGE 1: Stock dataclass — add new fields (after line ~164)

```python
    # ── v3 Theme Analyzer fields ──
    theme_classification: str = ""    # PRIME / INVESTABLE / SELECTIVE / AVOID
    valuation_regime: str = ""        # OPTIONALITY / FUNDAMENTAL / TRANSITION

    # ── Investment Gate fields ──
    gate_verdict: str = ""            # STRONG BUY / SPEC BUY / NO GO
    gate_conviction: int = 0          # 1-10
    gate_catalyst: str = ""           # Key catalyst from gate
    gate_bear_case: str = ""          # Bear case from gate
    gate_math: str = ""               # Math to 50% from gate

    # ── Deep DD fields (existing dd_ fields are reused) ──
    # dd_verdict, dd_conviction, dd_position_size already exist
    # dd_analysis, dd_key_catalyst, dd_fatal_flaw already exist
    dd_elevator_pitch: str = ""       # Newsletter: 2-3 sentence pitch
    dd_why_now: str = ""              # Newsletter: key catalyst with date
    dd_the_math: str = ""             # Newsletter: path to 50%+
    dd_bear_case: str = ""            # Newsletter: steelmanned bear
    dd_risk_to_monitor: str = ""      # Newsletter: single key risk
    dd_action: str = ""               # Newsletter: specific action
```

### CHANGE 2: Map v3 theme analyzer fields (lines ~658-661 and ~772-775)

Where theme results are mapped to Stock objects, add:
```python
    stock.theme_classification = a.classification
    stock.valuation_regime = a.valuation_regime
```

### CHANGE 3: Replace gatekeeper function (lines ~796-925)

Replace `run_gatekeeper()` with:

```python
def run_investment_gate_step(
    signals: List[Stock],
    top_n: int = None,
    themes_context: str = "",
    use_web_search: bool = False,
    save_reports: bool = False
) -> tuple:
    """Investment Gate — efficient filter on all theme-pass stocks.
    
    Returns: (confirmed, gate_pass, gate_fail)
    """
    if not signals:
        return [], [], []

    if top_n and len(signals) > top_n:
        signals = sorted(signals, key=lambda s: -s.banker)[:top_n]

    try:
        from core.investment_gate import (
            run_investment_gate_batch, apply_results_to_stocks, create_client
        )

        client = create_client()
        results = run_investment_gate_batch(
            client=client,
            stocks=signals,
            themes_context=themes_context,
            use_web_search=use_web_search,
            delay_between=8.0 if use_web_search else 3.0,
            save_reports=save_reports
        )
        
        gate_pass, gate_fail = apply_results_to_stocks(signals, results)
        
        # Store gate-specific fields for later use by Deep DD
        result_lookup = {r.ticker: r for r in results}
        for stock in gate_pass:
            r = result_lookup.get(stock.symbol)
            if r:
                stock.gate_verdict = r.verdict.value if hasattr(r.verdict, 'value') else str(r.verdict)
                stock.gate_conviction = r.conviction
                stock.gate_catalyst = r.catalyst_summary
                stock.gate_bear_case = r.bear_case
                stock.gate_math = r.math_to_50

        confirmed = [s for s in signals if s.final_decision in ("PASS", "FAIL")]
        return confirmed, gate_pass, gate_fail

    except ImportError as e:
        print(f"  ⚠ investment_gate.py not found: {e}")
        for s in signals:
            s.final_decision = "SKIPPED"
        return signals, [], []

    except RuntimeError as e:
        if "BILLING_ERROR" in str(e):
            print(f"\n  ❌ API BILLING ERROR")
        else:
            print(f"  ⚠ Investment Gate error: {e}")
        for s in signals:
            s.final_decision = "NOT_ASSESSED"
        return [], [], []
```

### CHANGE 4: Add Deep DD step after Investment Gate

Where the old DD block was (lines ~2826-2900), replace with:

```python
    # ══════════════════════════════════════════════════════════════════
    # STEP 8: DEEP DUE DILIGENCE (Opus) — Newsletter + Final Gate
    # ══════════════════════════════════════════════════════════════════
    
    dd_pass_stocks = []
    dd_fail_stocks = []
    
    if not args.no_dd and gate_pass:
        print(f"\n{'═' * 70}")
        print(f"  STEP 8: DEEP DUE DILIGENCE (Opus + Extended Thinking)")
        print(f"  Analyzing {len(gate_pass)} Investment Gate pass(es)")
        print(f"{'═' * 70}")
        
        try:
            from core.deep_dd import run_deep_dd_batch, apply_dd_to_stocks
            
            dd_results = run_deep_dd_batch(
                stocks=gate_pass,
                use_web_search=use_web_search,
                save_reports=getattr(args, 'save_dd', False)
            )
            
            dd_pass_stocks, dd_fail_stocks = apply_dd_to_stocks(gate_pass, dd_results)
            
            # Map DD newsletter fields to Stock for briefing generation
            dd_lookup = {r.ticker: r for r in dd_results}
            for stock in dd_pass_stocks:
                r = dd_lookup.get(stock.symbol)
                if r:
                    stock.dd_elevator_pitch = r.elevator_pitch
                    stock.dd_why_now = r.why_now
                    stock.dd_the_math = r.the_math
                    stock.dd_bear_case = r.bear_case
                    stock.dd_risk_to_monitor = r.risk_to_monitor
                    stock.dd_action = r.action_recommendation
            
        except ImportError as e:
            print(f"  ⚠ deep_dd.py not found: {e}")
            dd_pass_stocks = gate_pass  # Fall back to gate results
        except RuntimeError as e:
            print(f"  ⚠ Deep DD error: {e}")
            dd_pass_stocks = gate_pass
    
    elif args.no_dd and gate_pass:
        print(f"\n  ⚠️  Deep DD SKIPPED (--no-dd flag)")
        dd_pass_stocks = gate_pass  # Use gate results directly
    
    # ── Portfolio Updates ──
    if dd_pass_stocks:
        print(f"\n  ✅ Adding {len(dd_pass_stocks)} stock(s) to portfolio...")
        for stock in dd_pass_stocks:
            add_to_open_positions(stock)
            verdict = stock.dd_verdict or stock.final_decision
            conviction = stock.dd_conviction or stock.conviction
            print(f"     • {stock.symbol} — {verdict} ({conviction}/10)")
    
    if dd_fail_stocks:
        print(f"\n  ❌ {len(dd_fail_stocks)} stock(s) VETOED by Deep DD:")
        for stock in dd_fail_stocks:
            flaw = stock.dd_fatal_flaw or "See analysis"
            print(f"     • {stock.symbol} — {flaw[:60]}")
```

### CHANGE 5: Update newsletter briefing to include DD content (lines ~1788-1830)

In the briefing generation for PASS stocks, add the Deep DD newsletter fields:

```python
    if trades:
        lines.append("### 🟢 PASS - Ready for Entry (GREEN Signals)")
        lines.append("")
        for s in trades:
            lines.append(f"#### {s.symbol}")
            lines.append("")
            # ... existing table ...
            
            # Investment Gate summary
            if s.gate_catalyst:
                lines.append(f"| **Gate Catalyst** | {s.gate_catalyst} |")
            if s.valuation_regime:
                lines.append(f"| **Valuation Regime** | {s.valuation_regime} |")
            lines.append("")
            
            # Deep DD newsletter content (if available)
            if s.dd_elevator_pitch:
                lines.append("**The Pitch:**")
                lines.append(f"> {s.dd_elevator_pitch}")
                lines.append("")
            
            if s.dd_why_now:
                lines.append(f"**Why Now:** {s.dd_why_now}")
                lines.append("")
            
            if s.dd_the_math:
                lines.append(f"**The Math:** {s.dd_the_math}")
                lines.append("")
            
            if s.dd_bear_case:
                lines.append(f"**Bear Case:** {s.dd_bear_case}")
                lines.append("")
            
            if s.dd_risk_to_monitor:
                lines.append(f"**Risk to Monitor:** {s.dd_risk_to_monitor}")
                lines.append("")
            
            if s.dd_action:
                lines.append(f"**Action:** {s.dd_action}")
                lines.append("")
            
            # Fallback to existing fields if no DD content
            elif s.action:
                lines.append(f"**Recommended Action:** {s.action}")
                lines.append("")
```

### CHANGE 6: Update CLI arguments

```python
    parser.add_argument("--no-dd", action="store_true",
                        help="Skip Deep DD (uses Investment Gate results only)")
    parser.add_argument("--save-dd", action="store_true",
                        help="Save Deep DD reports to reports/ directory")
    parser.add_argument("--assess-top", type=int, metavar="N",
                        help="Only run Investment Gate on top N by Banker score")
    # Remove --full-dd (no longer needed)
```

### CHANGE 7: Remove old imports

Remove:
- `from core.gatekeeper import ...`
- `from core.dd_automator import ...`

---

## NEWSLETTER FLOW

The newsletter compilation prompt (Prompt 2 in scanner) references "DD outputs" for each PASS signal. With this architecture, the Deep DD produces **structured newsletter-ready content** instead of raw analysis:

| Newsletter Section | Populated By |
|---|---|
| **The Setup** | Scanner technical data (price, tier, theme, banker) |
| **The Pitch** | Deep DD `elevator_pitch` |
| **Why Now** | Deep DD `why_now` (catalyst with date) |
| **The Math** | Deep DD `the_math` (path to 50%+) |
| **Risk to Monitor** | Deep DD `risk_to_monitor` |
| **Bear Case** | Deep DD `bear_case` + `bear_rebuttal` |
| **Action** | Deep DD `action_recommendation` |

The briefing file now includes all this content directly, so the newsletter compilation prompt has richer source material than before.

---

## TESTING PLAN

```bash
# 1. Test Investment Gate standalone
python core/investment_gate.py NVDA PLTR --theme "AI Infrastructure" --regime FUNDAMENTAL
python core/investment_gate.py IONQ RGTI --theme "Quantum Computing" --regime OPTIONALITY

# 2. Test Deep DD standalone
python core/deep_dd.py NVDA --theme "AI Infrastructure" --regime FUNDAMENTAL --save
python core/deep_dd.py IONQ --theme "Quantum Computing" --regime OPTIONALITY --save

# 3. Test without web search (cheap)
python core/investment_gate.py CRWD --no-web
python core/deep_dd.py CRWD --no-web

# 4. Full pipeline test
python scanner.py --web-search --save-dd

# 5. Pipeline without DD (gate-only mode)
python scanner.py --web-search --no-dd
```

---

## IMPLEMENTATION ORDER

1. **Add `investment_gate.py`** and **`deep_dd.py`** to `core/`
2. **Update Stock dataclass** (Change 1) — add new fields
3. **Replace `run_gatekeeper()`** (Change 3) — swap function
4. **Add Deep DD step** (Change 4) — new step after gate
5. **Update briefing** (Change 5) — include DD newsletter content
6. **Update CLI** (Change 6) — clean up args
7. **Remove old imports** (Change 7)
8. **Test standalone** → test pipeline → test newsletter output
9. Once validated, stop importing gatekeeper.py and dd_automator.py

This is ideal for Claude Code — point it at this guide + the two new files + scanner.py and it can apply all changes surgically.
