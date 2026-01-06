# CLAUDE_CODE_WORKFLOWS.md

Copy-paste prompts for Claude Code sessions. These help you test, debug, and optimize the BoS Momentum Scanner.

---

## 🚀 Quick Start

### First Time Setup
```
Check this project is set up correctly:

1. Verify all required files exist
2. Check Python dependencies (yfinance, pandas, numpy, anthropic)
3. Check if ANTHROPIC_API_KEY is set
4. Run: python scanner.py --no-llm --top 20
5. Report any issues and how to fix them
```

### Run Weekly Scan (Technical Only - FREE)
```
Run the technical scan and analyze results:

python scanner.py --no-llm --top 100

For each signal found, explain:
- Why it triggered (beta, BoS, banker values)
- What tier it's in
- Any concerns

Then YOU analyze themes for the top candidates using web search.
This saves API costs by using Claude Code instead of the built-in API.
```

---

## 🧪 Testing Workflows

### Test Signal Calculation
```
Verify signal calculation for [TICKER]:

1. Run: python verify_bos.py [TICKER]
2. Show the HMA values, step lines, and signal status
3. Explain if the calculation looks correct
4. Compare to what TradingView would show (HMA 21, Pivot k=1, Weekly)
```

### Test Full Pipeline
```
Test the full pipeline end-to-end:

1. Run: python scanner.py --no-llm --top 20
   - Does it complete without errors?
   - How many signals found?

2. Run: python verify_bos.py NVDA TSLA AAPL
   - Do calculations look correct?

3. Check data quality:
   - Any missing data?
   - Any suspicious values?

Create a test report with findings.
```

### Validate Data Quality
```
Check data quality for the ticker universe:

1. Load complete_tickers.txt
2. For a sample of 10 tickers, download data with yfinance
3. Check for:
   - Missing days
   - Zero volumes
   - Suspicious price spikes
   - Split adjustment issues
4. Report any problematic tickers
```

---

## 🔍 Analysis Workflows

### Why Did/Didn't [TICKER] Trigger?
```
Analyze why [TICKER] did or didn't trigger a signal:

1. Run: python verify_bos.py [TICKER]
2. Check each gate:
   - Beta: Is it >= 1.5? Current value?
   - BoS: Did lower step change? What are the step values?
   - Banker: Is it >= 55? Current value?
3. If no signal, what would need to change?
4. Show the calculation trail
```

### Theme Analysis (FREE - Using Claude Code)
```
These tickers passed technical screening: [PASTE TICKERS]

Please analyze themes using web search:

1. What are the top 5 hot investment themes right now?
2. For each ticker, which theme fits best?
3. Score each as:
   - PRIME/INVESTABLE/SELECTIVE/AVOID (theme quality)
   - STRONG/GOOD/MODERATE/WEAK FIT (ticker fit)
4. Classify theme type: BOTTLENECK / CONTRARIAN / TREND
5. Recommend: TRADE / CONSIDER / SKIP for each

This replaces the built-in thematic_analyzer.py and saves API costs.
```

### Due Diligence (FREE - Using Claude Code)
```
Run due diligence on [TICKER] for potential entry:

Context:
- Budget: £5,000
- Hold period: 4-8 weeks
- Stop loss: 20% trailing
- Theme: [THEME if known]

Please search and analyze:
1. Recent news (past 2 weeks)
2. Upcoming earnings date
3. Insider activity (buying vs selling)
4. Short interest
5. Analyst ratings
6. Key risks

Bull case (strongest argument for buying):
Bear case (strongest argument against):

Verdict: PROCEED WITH CONVICTION / PROCEED WITH CAUTION / WAIT / PASS
Conviction: X/10
```

### Sector Performance Analysis
```
Analyze which sectors work best with this strategy:

1. Look at the ticker universe in complete_tickers.txt
2. Group by sector
3. For each sector, identify:
   - How many high-beta stocks?
   - Historical volatility patterns
   - Which sectors tend to have more BoS signals?
4. Recommend: Which sectors should we focus on?
```

---

## 🐛 Debugging Workflows

### Trace Signal Pipeline
```
Trace how [TICKER] flows through the pipeline:

1. Read scanner.py and identify each processing step
2. Add mental trace for [TICKER]:
   - Step 1: Data download → How many bars?
   - Step 2: Beta calculation → What value?
   - Step 3: BoS calculation → Up/Down?
   - Step 4: Banker calculation → What value?
   - Step 5: Technical gate → Pass/Fail?
3. Identify exactly where it passes or fails
```

### Check for Look-Ahead Bias
```
Audit the code for look-ahead bias:

1. In scanner.py calculate_bos():
   - Is pivot confirmation properly delayed by k bars?
   - Are we using any future data?

2. In calculate_banker():
   - Is the 20-day lookback correct?
   - Is VWAP calculation using only past data?

3. In calculate_beta():
   - Is the rolling window correct?

For each area, report:
- Potential issue: YES/NO
- If YES, explain the impact and suggest a fix
```

### Debug Empty Results
```
The scanner returned no signals. Debug:

1. Run: python diagnose_bos.py 50
   - What's the distribution of states?
   
2. Check yfinance is working:
   python -c "import yfinance as yf; print(yf.download('NVDA', period='5d'))"

3. Check ticker list:
   - Is complete_tickers.txt populated?
   - Are tickers valid?

4. Check date:
   - Is it a market holiday?
   - Did weekly candle just close?

Report findings and solutions.
```

### Debug Data Issues
```
I suspect data problems with [TICKER]. Investigate:

1. Download raw data:
   import yfinance as yf
   df = yf.download('[TICKER]', period='1y')
   
2. Check for:
   - Gaps (missing trading days)
   - Zero or negative prices
   - Volume anomalies
   - Recent splits (adjusted properly?)
   
3. If issues found:
   - What type of issue?
   - How does it affect signal calculation?
   - Should we exclude this ticker?
```

---

## ⚙️ Optimization Workflows

### Optimize LLM Prompts
```
Review and optimize the LLM prompts in this project:

1. Read thematic_analyzer.py - find the prompt templates
2. Read momentum_assessor.py - find the prompt templates
3. Read due_diligence_prompts.py - find the prompt templates

For each, suggest improvements for:
- Clarity (reduce ambiguity)
- Efficiency (shorter prompts = lower cost)
- Output structure (easier to parse)
- Consistency (standardized format)

Show before/after for the most impactful changes.
```

### Optimize API Costs
```
Analyze API usage in this project and suggest optimizations:

1. Map all Anthropic API calls:
   - Which files make calls?
   - What model is used?
   - Approximate tokens per call?

2. Identify cost reduction opportunities:
   - Can we batch more effectively?
   - Can we use a cheaper model for some tasks?
   - Can we cache results?
   - Can Claude Code replace any API calls?

3. Calculate estimated costs:
   - Current: $ per run
   - Optimized: $ per run
   - Annual savings

Show specific code changes to implement savings.
```

### Add Response Caching
```
Add caching to reduce redundant API calls:

1. Identify which calls could be cached:
   - Theme analysis (changes weekly)
   - Stock-to-theme mapping (changes weekly)
   - News/sentiment (changes daily)

2. Design caching strategy:
   - Where to store cache? (JSON files)
   - Cache invalidation rules?
   - Cache key structure?

3. Implement caching in thematic_analyzer.py:
   - Add cache check before API call
   - Save response to cache after call
   - Add --clear-cache flag

Show the code changes.
```

---

## 📋 Daily Operations

### Morning Pre-Market Check
```
Pre-market check for positions I'm considering:

Tickers: [LIST YOUR TICKERS]

For each:
1. Run verify_bos.py to confirm signal is still valid
2. Search for pre-market news
3. Check if earnings in next 2 weeks
4. Any overnight developments?

Create checklist:
| Ticker | Signal OK | News | Earnings | Proceed? |
```

### Weekly Scan Workflow
```
Run complete weekly scan:

1. python scanner.py --no-llm --top 100
   - List all technical candidates

2. For candidates, YOU do theme analysis:
   - Identify current hot themes
   - Map each ticker to best theme
   - Score fit quality

3. For top 5 theme-confirmed candidates:
   - Quick due diligence
   - Recent news
   - Key risks
   - Entry recommendation

This uses Claude Code for LLM work instead of API.
```

### Position Review
```
Review current positions for exit signals:

Positions: [LIST: TICKER entry_price]

For each:
1. Run verify_bos.py - any SELL signal?
2. Calculate trailing stop (20% from high since entry)
3. Search for recent news
4. Any concerning developments?

Create table:
| Ticker | Entry | Current | High | Stop | Distance | Action |
```

---

## 🛠️ Development Workflows

### Add New Indicator
```
I want to add a new indicator: [DESCRIBE IT]

1. Design the calculation:
   - Input: What data needed?
   - Formula: How to calculate?
   - Output: What values?

2. Implement in scanner.py:
   - Add calculation function
   - Add to Stock dataclass
   - Add to output

3. Test:
   - Calculate for known tickers
   - Verify values manually
   - Check edge cases

Show the code changes.
```

### Improve Output Format
```
Improve the scanner output for better readability:

1. Review current output in scanner.py
2. Identify improvements:
   - Better visual hierarchy
   - Clearer signal grouping
   - More actionable summary
   - Color coding (if terminal supports)

3. Implement changes

4. Show before/after example output
```

### Add Unit Tests
```
Create unit tests for indicator calculations:

1. Create tests/test_indicators.py

2. Test functions:
   - calculate_beta(): Known inputs → expected outputs
   - calculate_banker(): Edge cases (at VWAP, above, below)
   - calculate_hma(): Compare to known values
   - calculate_bos(): Verify signal alternation

3. Use pytest framework

4. Add test fixtures with sample data

5. Show how to run: pytest tests/
```

---

## 🆘 Troubleshooting Quick Reference

### "No signals found"
```
python diagnose_bos.py 100  # Check state distribution
python verify_bos.py NVDA   # Test specific ticker
# Check: Is it a holiday? Did market close?
```

### "API rate limit error"
```
# In thematic_analyzer.py, increase delays:
# base_delay: 5.0 → 10.0
# rate_limit_cooldown: 90.0 → 180.0
# Or use --no-llm and let Claude Code do analysis
```

### "Signal doesn't match TradingView"
```
python verify_bos.py [TICKER]
# Check TradingView settings:
# - HMA Length: 21
# - Pivot L=R: 1  
# - Timeframe: Weekly
# - Same week (Friday close)
```

### "Import error"
```
pip install yfinance pandas numpy anthropic
# Or with system packages:
pip install --break-system-packages yfinance pandas numpy anthropic
```

---

## 📊 Quick Command Reference

```bash
# Technical scan (FREE)
python scanner.py --no-llm
python scanner.py --no-llm --top 50

# With themes (~$0.13)
python scanner.py --no-momentum

# Full pipeline (~$0.25)
python scanner.py

# Full + DD
python run_full_pipeline.py
python run_full_pipeline.py --top-dd 3

# Debugging
python verify_bos.py NVDA TSLA
python diagnose_bos.py 100

# Validate
python -m py_compile scanner.py
```
