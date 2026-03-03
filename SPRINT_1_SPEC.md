# Sprint 1 Implementation Spec — Zero-Risk Foundations (Phase 0)

## Context for Claude Code

You are working on the Sterling Signals repository — an automated stock screening and content generation system. This sprint creates NEW files and makes one small deletion. Nothing existing is modified except for one line removal in scanner.py.

**Important**: Read the actual files referenced below before implementing. This spec was written from a code review — verify all paths, key names, and structures against what actually exists in the repo.

---

## Task 1: Create Tweet Category Example YAML Files

### What This Does

The tweet generator (`twitter/live_tweet_generator.py`) currently has a hardcoded dict called `LIVE_CATEGORY_EXAMPLES` (look for it — it's approximately lines 140-210). These examples are the #1 lever on tweet quality, but editing them requires touching a 2,500-line production script.

Move these examples to individual YAML files so they can be iterated on without code changes.

### Steps

1. Read `twitter/live_tweet_generator.py` and find the `LIVE_CATEGORY_EXAMPLES` dict. Note the exact category names used as keys and the exact example tweets stored as values.

2. Create `config/tweet_prompts/` directory.

3. For each category in `LIVE_CATEGORY_EXAMPLES`, create a YAML file: `config/tweet_prompts/{category_name_lowercase}.yaml`

The expected categories (verify against the actual code — these may differ slightly):
- SIGNAL_ALERT
- RECEIPT
- MARKET_COMMENTARY
- TECHNICAL_ANALYSIS
- THEME_CATALYST
- THEME_LIST
- TRENDING_TAKE
- EDUCATIONAL
- ENGAGEMENT
- SUBSTACK_TEASER
- SELL_SIGNAL

4. Each YAML file should have this structure:

```yaml
# config/tweet_prompts/signal_alert.yaml
category: SIGNAL_ALERT
description: "Announcing new scanner signals and GREEN signal alerts"

# Examples from the original LIVE_CATEGORY_EXAMPLES dict
# These are the existing examples, preserved exactly
examples:
  - "example tweet 1 from the original dict"
  - "example tweet 2 from the original dict"

# Per-persona examples (NEW — start empty, to be filled in later)
# These give each account a distinct voice for this category
persona_examples:
  variant_1: []  # Alex — The Analyst
  variant_2: []  # Rozalia — The Strategist  
  variant_3: []  # James — The Scout

# Anti-examples: tweets that violate our rules (NEW — to be filled in later)
bad_examples: []

# Banned terms that must NEVER appear in tweets of this category
# These come from content_prompt_handbook_v5.md
banned_terms:
  - "HMA"
  - "Hull Moving Average"
  - "MACD"
  - "RSI"
  - "UC"
  - "Undercurrent"
  - "Banker"
  - "BoS"
  - "ExD"
  - "VWAP"
  - "KDJ"
  - "Gatekeeper"
  - "Investment Gate"
  - "Deep DD"
  - "5-gate"
  - "Tier 1"
  - "Tier 2"
  - "Tier 3"
  - "conviction score"
  - "conviction rating"
  - "STRONG BUY"
  - "SPEC BUY"
  - "NO GO"
  - "TEAL signal"
  - "VIOLET signal"
  - "AMBER signal"
  - "stay tuned"
  - "more to come"
  - "some interesting setups"
  - "keep an eye on"
  - "picks and shovels"
```

5. The `examples` list for each file should contain the EXACT examples from the original `LIVE_CATEGORY_EXAMPLES` dict for that category. Copy them verbatim — do not rewrite them.

6. The `banned_terms` list should be identical across all 11 files (it's the master banned list). This is intentionally duplicated per file so each file is self-contained.

### DO NOT modify live_tweet_generator.py in this sprint

We are only creating the config files now. Sprint 4 will modify the generator to load from YAML instead of the hardcoded dict. This separation is intentional — we want to verify the YAML content is correct before switching the code to use it.

### Verification

```bash
# Count YAML files created
ls config/tweet_prompts/*.yaml | wc -l
# Should match the number of categories in LIVE_CATEGORY_EXAMPLES

# Verify each file is valid YAML
python3 -c "
import yaml, glob
for f in sorted(glob.glob('config/tweet_prompts/*.yaml')):
    with open(f) as fh:
        data = yaml.safe_load(fh)
    cats = data.get('category', 'MISSING')
    examples = len(data.get('examples', []))
    print(f'{f}: category={cats}, examples={examples}')
"

# Verify examples match original
python3 -c "
import yaml, glob

# Load all YAML examples
yaml_examples = {}
for f in sorted(glob.glob('config/tweet_prompts/*.yaml')):
    with open(f) as fh:
        data = yaml.safe_load(fh)
    yaml_examples[data['category']] = data.get('examples', [])

# Compare count against original (you'll need to import/reference the original dict)
print(f'YAML categories: {len(yaml_examples)}')
for cat, exs in yaml_examples.items():
    print(f'  {cat}: {len(exs)} examples')
"
```

---

## Task 2: Create Persona Voice Guides

### What This Does

The tweet generator's `build_system_prompt()` method currently has one-line persona descriptions like:
```
variant_1 (Alex — The Analyst): Tone = confident, traits = [data-driven, decisive]. Angle = data-driven.
```

This tells Sonnet to sound different but doesn't show HOW. Voice guides with rhythm examples give the LLM specific constraints for genuinely distinct output across the three accounts.

### Steps

1. Read `twitter/live_tweet_generator.py` and find the `build_system_prompt()` method. Note the exact persona names, variant keys (variant_1, variant_2, variant_3), and current descriptions.

2. Create `config/persona_voice_guides.yaml`:

```yaml
# config/persona_voice_guides.yaml
# Extended voice guides for each Twitter persona
# These supplement (don't replace) the existing persona config in live_tweet_generator.py

personas:
  variant_1:
    name: "Alex"
    role: "The Analyst"
    voice_guide: >
      Alex writes like a quant who also trades. Short declarative sentences.
      Leads with data — prices, percentages, timeframes, rejection rates.
      Never uses questions as hooks — makes statements.
      Dry confidence. Never uses exclamation marks.
      Uses numbers as anchors: "$8.50 to $13.25" not "significant gains."
      Sentence rhythm: short-short-medium. Never more than 2 sentences before a data point.
    rhythm_examples:
      - "1,817 stocks. 14 passed technical screening. 2 cleared all gates. That rejection rate is the edge."
      - "$RCAT entered at $8.50. Now $13.25. +55.9% in 6 weeks. Structural momentum, not luck."
      - "Friday scan complete. Zero GREEN signals this week. Selectivity protects capital — the right setup will come."
    never:
      - "What do you think about..."
      - "Could this be the next..."
      - "Exciting developments!"
      - Any sentence ending in "!"

  variant_2:
    name: "Rozalia"
    role: "The Strategist"
    voice_guide: >
      Rozalia connects individual stocks to bigger themes and capital flows.
      Writes in flowing sentences that build from specific to structural.
      Uses "we" naturally — positions herself as part of a community.
      Warm authority — confident but inviting, never cold or dismissive.
      Frequently links what the scanner found to why it matters for the broader thesis.
      Balances data with narrative — every number gets context.
    rhythm_examples:
      - "Our scanner screened 1,817 stocks down to 2 this week. That 99.9% rejection rate is why a GREEN signal means something — when we find momentum, it's backed by structural confirmation."
      - "The drone thesis keeps compounding. $RCAT is now our strongest position at +55.9%, and the defence spending wave behind it shows no signs of slowing."
      - "We passed on every signal this week. No theme clustering, no institutional confirmation. Patience is the hardest part of this system — and the most profitable."
    never:
      - Starting tweets with "$TICKER is..."
      - Pure data without narrative context
      - "Stay tuned" or "more to come"

  variant_3:
    name: "James"
    role: "The Scout"
    voice_guide: >
      James is the most conversational and accessible voice.
      Writes like a sharp friend sharing what he's watching — informal but informed.
      Uses casual transitions: "Meanwhile," "Here's the thing," "Worth noting."
      Occasionally addresses the reader directly: "If you're watching defence stocks..."
      Shorter tweets than the other personas. Punchy, not exhaustive.
      Comfortable with uncertainty — "on my radar" rather than definitive calls.
    rhythm_examples:
      - "$RCAT on my radar at $13.25. +55.9% from entry. Drone thesis intact, momentum confirmed. NFA"
      - "Friday scan done. 1,817 screened, 2 survived. When the system says GREEN, pay attention."
      - "No signals this week. That's not a bug — it's the whole point. Cash is a position too."
    never:
      - Long multi-sentence analytical paragraphs
      - "Our proprietary system indicates..."
      - Formal or institutional tone
```

3. Verify the variant keys (variant_1, variant_2, variant_3) match what `live_tweet_generator.py` actually uses for persona routing. Check the account mapping — it might use different keys like account names or numeric IDs.

### DO NOT modify live_tweet_generator.py in this sprint

Same as Task 1 — we're creating the config. Sprint 4 integrates it.

### Verification

```bash
python3 -c "
import yaml
with open('config/persona_voice_guides.yaml') as f:
    data = yaml.safe_load(f)
personas = data.get('personas', {})
for key, persona in personas.items():
    examples = len(persona.get('rhythm_examples', []))
    nevers = len(persona.get('never', []))
    print(f'{key} ({persona[\"name\"]}): {examples} examples, {nevers} anti-patterns')
"
```

---

## Task 3: Create State Directory with JSON Scaffolds

### What This Does

Several upcoming features need persistent state files. Creating the directory and empty scaffolds now means future sprints can start writing to them immediately.

### Steps

1. Create `state/` directory at the repo root.

2. Create `state/.gitkeep` (empty file to ensure the directory is tracked).

3. Create `state/README.md`:

```markdown
# State Directory

Persistent state files for Sterling Signals automation. These files are read and written by various pipeline scripts.

## Files

| File | Written By | Read By | Frequency |
|------|-----------|---------|-----------|
| `engagement.json` | engagement-fetch.yml | live_tweet_generator.py, daily_context_builder.py | Daily 9 PM ET |
| `content_tracker.json` | daily_content_pipeline.py | Dashboard Content Calendar | Daily |
| `cost_summary.json` | live_tweet_generator.py | Dashboard System Health | Per tweet slot |
| `system_log.json` | health-check.yml | Dashboard System Health | Daily 10 PM ET |
| `notes.json` | notes_poster.py | Dashboard Activity Feed | 3x daily |

## Important

- All JSON files use UTF-8 encoding
- Scripts should handle missing files gracefully (create with defaults on first run)
- Git-committed (not gitignored) so dashboard can read via GitHub API
```

4. Create each scaffold file with sensible empty defaults:

**state/engagement.json:**
```json
{
  "last_updated": null,
  "fetch_source": "twitter_api",
  "accounts": {
    "variant_1": {
      "handle": "",
      "last_7d_avg_likes": 0,
      "last_7d_avg_retweets": 0,
      "last_7d_avg_replies": 0,
      "by_category": {}
    },
    "variant_2": {
      "handle": "",
      "last_7d_avg_likes": 0,
      "last_7d_avg_retweets": 0,
      "last_7d_avg_replies": 0,
      "by_category": {}
    },
    "variant_3": {
      "handle": "",
      "last_7d_avg_likes": 0,
      "last_7d_avg_retweets": 0,
      "last_7d_avg_replies": 0,
      "by_category": {}
    }
  }
}
```

**state/content_tracker.json:**
```json
{
  "current_week": null,
  "posts": [],
  "notes": [],
  "streak": {
    "posts_on_schedule": 0,
    "notes_streak": 0,
    "last_post_date": null,
    "last_note_date": null
  }
}
```

**state/cost_summary.json:**
```json
{
  "last_updated": null,
  "today": {
    "date": null,
    "total_cost_usd": 0.0,
    "slots_generated": 0,
    "slots_repaired": 0,
    "repair_cost_usd": 0.0,
    "by_account": {}
  },
  "last_7_days": {
    "total_cost_usd": 0.0,
    "avg_daily_cost_usd": 0.0,
    "total_slots": 0
  }
}
```

**state/system_log.json:**
```json
{
  "last_updated": null,
  "last_health_check": null,
  "components": {
    "scanner": {"status": "unknown", "last_run": null, "last_error": null},
    "tweet_generator": {"status": "unknown", "last_run": null, "last_error": null},
    "daily_content": {"status": "unknown", "last_run": null, "last_error": null},
    "notes_publisher": {"status": "unknown", "last_run": null, "last_error": null},
    "git_sync": {"status": "unknown", "last_run": null, "last_error": null}
  },
  "recent_errors": []
}
```

**state/notes.json:**
```json
{
  "last_updated": null,
  "today": {
    "date": null,
    "notes_published": 0,
    "notes_target": 3,
    "slots": []
  },
  "recent": []
}
```

### Verification

```bash
# Check all files exist and are valid JSON
python3 -c "
import json, glob
for f in sorted(glob.glob('state/*.json')):
    with open(f) as fh:
        data = json.load(fh)
    print(f'{f}: valid JSON, {len(data)} top-level keys')
"
```

---

## Task 4: Remove Price Gate from Scanner

### What This Does

The scanner currently filters stocks with price > $25 (or similar threshold — verify the exact value). This was designed for penny/micro-cap focus but prevents catching larger small-cap multibagger opportunities (e.g., a $50 stock doubling to $100).

### Steps

1. Open `scanner/scanner.py` and search for the price filter. Look for patterns like:
   - `price < 25` or `price <= 25`
   - `max_price` or `price_cap` or `price_threshold`
   - A filter in the screening logic that excludes stocks above a dollar threshold
   - It might be in a config dict, a constant, or inline in a filter function

2. **Before removing**: Check if this price gate is referenced ANYWHERE else in the codebase:
```bash
grep -rn "25" scanner/scanner.py | grep -i "price\|cap\|max\|filter"
grep -rn "price_cap\|max_price\|price_filter\|price_gate" scanner/ twitter/ portfolio/
```

3. If the price gate is a simple comparison (like `if price > 25: continue`), remove or comment it out.

4. If it's a config value, change it to a very high number (e.g., 999999) rather than removing the config key — this preserves the option to re-enable later.

5. **Important**: Also check `complete_tickers.txt` or wherever the ticker universe is defined. If the ticker list itself was pre-filtered to only include sub-$25 stocks, the price gate removal in scanner.py won't help. The ticker universe may need updating separately (but that's a larger change — just flag it if you find this).

### Verification

```bash
# Search for any remaining price filtering
grep -in "price.*25\|25.*price\|price_cap\|max_price" scanner/scanner.py

# Run scanner in test mode to verify it still works
python3 -m scanner.scanner --top 20 --test 2>&1 | head -20
# (use whatever test/dry-run flags exist — check the argparse setup)
```

### Risk Assessment

LOW — this is a filter removal. If it breaks something unexpected, the scanner will simply return more results (not fewer), and the downstream pipeline handles any number of signals.

---

## Task 5: Verify Signal History File

### What This Does

This isn't a build task — it's a verification that confirms the state of signal_history.csv so Sprint 2 (analysis package builder) can rely on it.

### Steps

1. Find signal_history.csv (or signal_history_rows.csv) in the repo:
```bash
find . -name "*signal_history*" -type f
```

2. Check its format and content:
```bash
head -5 <path_to_file>
wc -l <path_to_file>
```

3. Verify the format matches what Prompt 8 expects:
```
date,ticker,price,tier,theme,composite_score,system_fit,advanced,session_verdict
```

4. Note the exact path and filename — Sprint 2 needs this.

5. Check if there's an append mechanism in the Saturday workflow:
```bash
grep -rn "signal_history" .github/workflows/ scripts/ scanner/
```

### Report back

Tell me:
- Exact file path
- Number of rows
- Column format (does it match the spec above?)
- Whether any workflow currently appends to it, or if it's manually maintained

---

## Sprint 1 Completion Checklist

After all tasks, verify the full state:

```bash
echo "=== YAML Category Files ==="
ls -la config/tweet_prompts/*.yaml | wc -l

echo "=== Voice Guides ==="
ls -la config/persona_voice_guides.yaml

echo "=== State Directory ==="
ls -la state/

echo "=== Price Gate ==="
grep -c "price.*25\|25.*price" scanner/scanner.py
# Should be 0 or only in comments

echo "=== Signal History ==="
find . -name "*signal_history*" -type f
```

Commit message suggestion:
```
Phase 0: Config foundations for tweet quality and state tracking

- config/tweet_prompts/: 11 YAML files with category examples (extracted from live_tweet_generator.py)
- config/persona_voice_guides.yaml: Extended voice guides for 3 Twitter personas
- state/: Directory with JSON scaffolds for engagement, content tracking, costs, system health, notes
- scanner.py: Removed $25 price gate to expand scanner universe
- No existing code modified (YAML/voice integration deferred to Sprint 4)
```

---

## Notes for Claude Code

- **PyYAML**: Should already be installed. If not: `pip install pyyaml`
- **Read before writing**: Every task says "read the actual file first" — do this. The exact variable names, key names, and structures in the spec above are from a code review, not from the live repo. Trust the repo over this spec if they differ.
- **Ask if unclear**: If anything in this spec contradicts what you see in the repo, flag it rather than guessing. The spec author reviewed the code but may have misremembered details.
