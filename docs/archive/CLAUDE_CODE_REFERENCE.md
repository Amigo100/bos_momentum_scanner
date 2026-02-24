# Claude Code Quick Reference - Sterling Signals

## Mode Selection Guide

| Situation | Mode | Why |
|-----------|------|-----|
| "How should I structure this?" | Plan | Think through architecture |
| "Create this file for me" | Act | Execute and generate code |
| "Is this correct?" | Ask | Quick clarification |
| "Build X, then Y, then Z" | Act | Complex multi-step task |
| "What are the trade-offs?" | Plan | Decision analysis |
| "Debug this error" | Ask or Act | Depending on complexity |

---

## Recommended Session Sequence

### Session 1: DD Automation (Highest Impact)

```
[Plan] "Review my scanner.py and gatekeeper.py - plan how to add automated 
       due diligence that runs after gatekeeper for PASS signals"

[Act]  "Create dd_automator.py that:
       - Takes PASS signals from gatekeeper
       - Uses Claude API with web search to generate Deal Memos
       - Saves to scanner/output/due_diligence/{TICKER}_DD.md
       - Has a --skip-dd flag for cost-conscious runs"

[Act]  "Integrate dd_automator.py into scanner.py main() function"

[Ask]  "How do I test this without burning API credits?"
```

### Session 2: Market Analysis

```
[Act]  "Create market_analyzer.py that:
       - Uses Claude API with web search
       - Generates market analysis (VIX, sector performance, macro)
       - Saves to scanner/output/current/market_analysis_{date}.md
       - Can run standalone or as part of pipeline"
```

### Session 3: Tweet Generation

```
[Plan] "Review grok_prompts_generator.py - plan how to modify it to output 
       final tweet text instead of prompts for Grok"

[Act]  "Modify grok_prompts_generator.py to:
       - Generate final tweet text (not prompts)
       - Include chart file paths for media attachment
       - Output content_queue.json for GitHub Actions"
```

### Session 4: Chart Capture

```
[Plan] "Should I use CHART-IMG API or Playwright for chart capture? 
       My goal is to include my custom BoS/Banker indicators."

[Act]  "Create chart_capture.py using Playwright that:
       - Uses my TradingView Chrome profile for session
       - Loads my saved chart layout with indicators
       - Captures charts at 1200x630 for X cards
       - Saves to twitter/output/charts/{TICKER}_{date}.png"
```

### Session 5: X Posting

```
[Act]  "Create twitter_poster.py that:
       - Reads content_queue.json
       - Posts next pending tweet for current time slot
       - Uploads chart image as media
       - Marks as posted and commits updated queue
       - Uses Tweepy with OAuth 1.0a"

[Act]  "Create .github/workflows/daily_post.yml that runs twitter_poster.py 
       at 08:00, 12:30, and 18:00 UK time"
```

### Session 6: Friday Pipeline

```
[Act]  "Create run_friday.sh that orchestrates the full Friday pipeline:
       1. scanner.py --web-search
       2. chart_capture.py
       3. content_queue_generator.py
       4. git add, commit, push to GitHub"

[Act]  "Create .github/workflows/friday_scan.yml that runs at 21:30 UTC 
       (4:30 PM EST) on Fridays"
```

---

## Common Claude Code Patterns

### Creating a New Python Module

```
[Act] Create {module_name}.py that:
      - Purpose: {what it does}
      - Input: {what it takes}
      - Output: {what it produces}
      - Integration: {how it connects to existing code}
```

### Modifying Existing Code

```
[Act] Modify {existing_file}.py to:
      - Add {new feature}
      - Import {new_module}
      - Call {new_function} after {existing_step}
      - Add command-line flag --{new_flag}
```

### Creating GitHub Actions Workflow

```
[Act] Create .github/workflows/{name}.yml that:
      - Triggers: {cron schedule or event}
      - Steps: {what it runs}
      - Secrets: {which GitHub Secrets it needs}
      - Commits: {whether it commits back changes}
```

### Testing Without API Costs

```
[Act] Add a --dry-run flag to {script}.py that:
      - Prints what it would do
      - Uses mock data instead of API calls
      - Doesn't modify any files
```

---

## Key Files Reference

| File | Purpose | Creates |
|------|---------|---------|
| `scanner.py` | Main pipeline | `latest_newsletter_briefing.md` |
| `thematic_analyzer.py` | Theme classification | `themes_cache.json` |
| `gatekeeper.py` | Quality gate | PASS/CAUTION/FAIL decisions |
| `grok_prompts_generator.py` | X content | `grok_prompts/*.md` |
| `dd_automator.py` (new) | Due diligence | `due_diligence/{TICKER}_DD.md` |
| `market_analyzer.py` (new) | Market analysis | `market_analysis_{date}.md` |
| `chart_capture.py` (new) | Screenshots | `charts/{TICKER}_{date}.png` |
| `content_queue_generator.py` (new) | Posting queue | `content_queue.json` |
| `twitter_poster.py` (new) | X posting | Updates `content_queue.json` |
| `newsletter_compiler.py` (new) | Newsletter | `newsletter_{date}.md/.html` |

---

## Debugging Tips

### "Module not found" errors

```
[Act] Check if {module} is imported correctly and installed.
      Add to requirements.txt if missing.
```

### API rate limit errors

```
[Ask] How do I add exponential backoff to {function}?
```

### GitHub Actions failures

```
[Act] Add error handling and logging to {workflow}.yml
      Send email notification on failure
```

### Path/file not found

```
[Ask] What's the correct relative path from {script} to {file}?
      My directory structure is: {describe structure}
```

---

## Useful Prompts

### Quick Wins

```
"Add logging to {script}.py so I can debug issues"
"Create a test mode for {script}.py that uses mock data"
"Add --verbose flag to show detailed output"
```

### Integration

```
"How should {new_module}.py integrate with the existing scanner pipeline?"
"What's the data format I should pass between {module_a} and {module_b}?"
```

### Optimization

```
"The scanner is slow - how can I parallelize the API calls?"
"How do I cache theme analysis to avoid redundant API calls?"
```

---

## Session Endings

Always end sessions with:

```
[Ask] "What are the next steps I should take?"
[Act] "Commit the changes with message: '{descriptive message}'"
[Ask] "Are there any tests I should run before pushing?"
```

---

*Keep this reference handy while working in Claude Code*
