#!/usr/bin/env python3
"""
FULL PIPELINE WITH DUE DILIGENCE
================================

Runs the complete BoS Momentum Scanner pipeline including:
1. Technical scan (BoS + Beta + Banker)
2. Thematic analysis (LLM identifies themes, maps stocks)
3. Momentum assessment (LLM evaluates news/catalysts)
4. Due diligence (LLM deep-dive on TRADE candidates)

Usage:
    python run_full_pipeline.py                    # Full pipeline
    python run_full_pipeline.py --top-dd 3         # DD on top 3 only
    python run_full_pipeline.py --skip-dd          # Skip DD step
    python run_full_pipeline.py --no-llm           # Technical only
    python run_full_pipeline.py --budget "$5000"   # Set DD budget context
"""

import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import subprocess

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).resolve().parent.parent
TRADES_DIR = BASE_DIR / "trades"


def run_scanner(no_llm: bool = False, no_momentum: bool = False, top_n: Optional[int] = None) -> Dict:
    """Run the main scanner and capture results."""
    
    cmd = [sys.executable, "-m", "core.scanner"]
    
    if no_llm:
        cmd.append("--no-llm")
    elif no_momentum:
        cmd.append("--no-momentum")
    
    if top_n:
        cmd.extend(["--top", str(top_n)])
    
    cmd.append("--no-email")  # Don't send email in pipeline mode
    
    print("\n" + "═" * 70)
    print("  STEP 1: RUNNING SCANNER")
    print("═" * 70)
    
    result = subprocess.run(cmd, capture_output=False, cwd=str(BASE_DIR))
    
    # Load results from signals.json
    signals_file = TRADES_DIR / "signals.json"
    if signals_file.exists():
        with open(signals_file) as f:
            return json.load(f)
    
    return {}


def run_due_diligence(ticker: str, budget: str = "$5,000", theme: str = "", save: bool = True) -> Dict:
    """Run due diligence on a single ticker."""
    
    try:
        from core.due_diligence import run_due_diligence_for_pipeline
        
        result = run_due_diligence_for_pipeline(
            ticker=ticker,
            budget=budget,
            theme=theme,
            save_report=save
        )
        
        return result
        
    except ImportError as e:
        print(f"    ⚠ Import error: {e}")
        # Fall back to subprocess if import fails
        cmd = [sys.executable, "-m", "core.due_diligence", ticker]
        cmd.extend(["--budget", budget])
        if theme:
            cmd.extend(["--theme", theme])
        if save:
            cmd.append("--save")
        
        subprocess.run(cmd, cwd=str(BASE_DIR))
        return {"ticker": ticker, "status": "completed", "verdict": "UNKNOWN"}


def extract_trade_candidates(scanner_results: Dict) -> List[Dict]:
    """Extract TRADE candidates from scanner results."""
    
    candidates = []
    
    # Check for signals in various formats
    signals = scanner_results.get("signals", [])
    if not signals:
        signals = scanner_results.get("entry_candidates", [])
    if not signals:
        signals = scanner_results.get("technical_signals", [])
    
    for signal in signals:
        # Check if it passed momentum assessment
        decision = signal.get("momentum_decision", "").upper()
        theme_verdict = signal.get("theme_verdict", "").upper()
        
        # Include if TRADE or if no momentum assessment was run
        if decision == "TRADE" or (decision == "" and "STRONG" in theme_verdict):
            candidates.append({
                "ticker": signal.get("symbol", signal.get("ticker", "")),
                "theme": signal.get("theme", signal.get("theme_name", "")),
                "tier": signal.get("tier", ""),
                "beta": signal.get("beta", 0),
                "banker": signal.get("banker", 0),
                "price": signal.get("price", 0),
                "momentum_decision": decision,
                "theme_verdict": theme_verdict
            })
    
    return candidates


def print_summary(candidates: List[Dict], dd_results: List[Dict]):
    """Print final summary."""
    
    print("\n" + "═" * 70)
    print("  FINAL SUMMARY")
    print("═" * 70)
    
    if not candidates:
        print("\n  No TRADE candidates found.")
        return
    
    print(f"\n  TRADE Candidates: {len(candidates)}")
    print("  " + "─" * 66)
    
    for c in candidates:
        print(f"    {c['ticker']:<6} | {c['tier']:<6} | β={c['beta']:.2f} | ${c['price']:.2f}")
        print(f"           Theme: {c['theme'][:50]}")
    
    if dd_results:
        print("\n  Due Diligence Results:")
        print("  " + "─" * 66)
        
        for dd in dd_results:
            ticker = dd.get("ticker", "???")
            verdict = dd.get("verdict", "UNKNOWN")
            conviction = dd.get("conviction", "?")
            
            emoji = {
                "PROCEED WITH CONVICTION": "🟢",
                "PROCEED WITH CAUTION": "🟡",
                "WAIT FOR BETTER ENTRY": "🟠",
                "PASS ON THIS ONE": "🔴",
                "INVEST": "🟢",
                "DO NOT INVEST": "🔴",
                "WAIT": "🟡"
            }.get(verdict.upper(), "⚪")
            
            print(f"    {emoji} {ticker:<6} | {verdict} | Conviction: {conviction}/10")
    
    print("\n" + "═" * 70)


def main() -> int:
    parser = argparse.ArgumentParser(description="Full BoS Pipeline with Due Diligence")
    parser.add_argument("--no-llm", action="store_true", help="Skip ALL LLM steps")
    parser.add_argument("--no-momentum", action="store_true", help="Skip momentum assessor")
    parser.add_argument("--skip-dd", action="store_true", help="Skip due diligence step")
    parser.add_argument("--top-dd", type=int, default=5, help="Run DD on top N candidates only")
    parser.add_argument("--top", type=int, help="Scan top N stocks by beta")
    parser.add_argument("--budget", default="$5,000", help="Budget for DD context")
    parser.add_argument("--save-reports", action="store_true", help="Save DD reports to files")
    args = parser.parse_args()
    
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + "FULL PIPELINE: SCANNER → THEMES → MOMENTUM → DUE DILIGENCE".center(68) + "║")
    print("║" + datetime.now().strftime("%Y-%m-%d %H:%M:%S").center(68) + "║")
    print("╚" + "═" * 68 + "╝")
    
    # Step 1: Run scanner
    scanner_results = run_scanner(
        no_llm=args.no_llm,
        no_momentum=args.no_momentum,
        top_n=args.top
    )
    
    if args.no_llm:
        print("\n  Pipeline complete (technical only, no LLM steps).")
        return 0
    
    # Step 2: Extract TRADE candidates
    candidates = extract_trade_candidates(scanner_results)
    
    if not candidates:
        print("\n  No TRADE candidates to analyze further.")
        return 0
    
    print(f"\n  Found {len(candidates)} TRADE candidate(s)")
    
    # Step 3: Run Due Diligence (if not skipped)
    dd_results = []
    
    if not args.skip_dd:
        print("\n" + "═" * 70)
        print("  STEP 2: DUE DILIGENCE (Deep Analysis)")
        print("═" * 70)
        
        # Limit to top N
        dd_candidates = candidates[:args.top_dd]
        
        for i, candidate in enumerate(dd_candidates, 1):
            ticker = candidate["ticker"]
            theme = candidate.get("theme", "")
            
            print(f"\n  [{i}/{len(dd_candidates)}] Analyzing {ticker}...")
            print("  " + "─" * 60)
            
            try:
                result = run_due_diligence(
                    ticker=ticker,
                    budget=args.budget,
                    theme=theme,
                    save=args.save_reports
                )
                dd_results.append(result)
            except Exception as e:
                print(f"    ⚠ Error: {e}")
                dd_results.append({
                    "ticker": ticker,
                    "verdict": "ERROR",
                    "error": str(e)
                })
    
    # Step 4: Print summary
    print_summary(candidates, dd_results)
    
    # Save combined results
    output = {
        "timestamp": datetime.now().isoformat(),
        "candidates": candidates,
        "due_diligence": dd_results
    }
    
    output_file = TRADES_DIR / "pipeline_results.json"
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2, default=str)
    
    print(f"\n  Results saved to: {output_file}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
