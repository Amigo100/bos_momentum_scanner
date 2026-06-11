#!/usr/bin/env python3
"""
Sterling Weekly Briefing — V4
=============================
Generates a briefing pack for a list of buy candidates: fetches data, applies
the V4 rubric to the current technical setup, renders annotated charts, and
writes a self-contained markdown briefing ready to drop into a Claude.ai chat
for final conviction discussion.

USAGE
-----
    python weekly_briefing.py --tickers KARO OSS ACA
    python weekly_briefing.py --ticker-file candidates.txt
    python weekly_briefing.py --tickers AAA BBB --output ./briefings/custom/

OUTPUT (in ./briefings/YYYY-MM-DD/ by default)
----------------------------------------------
    briefing.md             unified analysis document (drop in Claude.ai)
    charts/<TICKER>.png     per-ticker annotated chart
    snapshots/<TICKER>.json structured feature snapshot per ticker

DEPENDENCIES
------------
    Same folder must contain sterling_backtest_yf.py with the V4 implementation
    (classify_archetype, grade_signal router, _grade_reversal, grade_continuation).
"""

from __future__ import annotations
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Import the V4 stack from the sibling module
import sterling_backtest_yf as sb


# ═══════════════════════════════════════════════════════════════════════
# V4 framework primer + LLM prompt (embedded in briefing.md)
# ═══════════════════════════════════════════════════════════════════════

V4_FRAMEWORK_PRIMER = """\
The Sterling V4 rubric scores a weekly buy candidate after the mechanical V7
trigger (HMA pivot + UC/MACD gates + ATR squeeze split) has already fired.
The rubric classifies each signal into one of three archetypes based on
distance from 52-week high, then applies a dedicated sub-rubric:

  Reversal     (pct_from_52w_high < -20)  → V3 'Reversal Quality' rubric
  Mixed        (pct in [-20, -10])        → default grade C
                                            (exception: T4×Mixed → B)
  Continuation (pct > -10)                → V4 Continuation sub-rubric

Each sub-rubric scores five dimensions 0-2 for a 0-10 subtotal, mapped to
A/B/C/D/F. Risk flags can cap the grade. Backtest performance on 198 signals
(2021-2026, time-based holdout):

  A: 70% WR / +31% mean  → trade at full size
  B: 59% WR / +17% mean  → trade at full size
  C: 40% WR /  -1% mean  → half size or skip
  D: 38% WR /  +0% mean  → skip
  F: 24% WR /  -3% mean  → reject

Out-of-sample (2024-03 onwards): A held at 68% WR, F dropped to 18% WR.
Rubric is calibrated, not overfit.

REVERSAL sub-rubric dimensions (V3):
  1. Drawdown depth      — reward bombed-out, penalize near-highs
  2. Momentum turn       — reward MACD hist rising with line still <0
  3. UC re-engagement    — reward UC rising from low, penalize saturation
  4. Inst. divergence    — reward banker_uc_divergent (Banker bled out, UC up)
  5. RSI recovery        — reward RSI rising from 40-60, penalize >70

CONTINUATION sub-rubric dimensions (V4):
  1. Extension discipline — reward pct_vs_sma50 < 19%, penalize > 55%
  2. Cycle stage         — reward ret_26w < 25%, penalize > 80%
  3. UC discipline       — reward UC rising not saturated, penalize saturated
  4. Banker reset        — reward Banker <= 17, penalize > 17 (binary)
  5. Late-entry guard    — reward neither macd_above_signal nor cross_up

KNOWN STRUCTURAL CELLS (from backtest):
  T2×anything: 0/6 historical WR — auto-skip
  T4×Continuation (pct > -10 AND ret_26w > 50): 28% WR — auto-cap at D
  T3×Reversal: 75% WR (n=24) — EMPHASIZE
  T4×Mixed: 73% WR (n=11) — EMPHASIZE (B by exception)

KEY MENTAL MODEL:
The mechanical V7 trigger is fundamentally a reversion-trade detector in
this universe. The Reversal archetype is where the alpha primarily lives.
The Continuation archetype produces a smaller second alpha source via the
"momentum-continuation-but-disciplined" pattern (extension < 55%, ret_26w
< 80%, MACD hasn't fully extended). Most bad signals look like reversals
or continuations but fail one or two of the discipline dimensions — that's
what the rubric is built to catch.

INDICATOR SEMANTICS (key — easy to misread):
  UC        = clip(1.5*(RSI(close,10)-50), 0, 20)  → FAST inst. flow
  Hot Money = clip(0.7*(RSI(close,40)-30), 0, 20)  → MID inst. flow
  Banker    = clip(1.5*(RSI(close,50)-50), 0, 20)  → SLOW inst. flow
                                                     (literally a slow UC)
  Retailer  = constant 20 (baseline reference — IGNORE, not a flow)

  banker_uc_divergent = Banker < 5 AND not rising AND UC > previous UC
                      = the smart-money-quietly-returning fingerprint
"""

LLM_TASK_PROMPT = """\
For each ticker in this briefing:

  1. Read the V4 framework primer above and the per-ticker data block.
  2. Examine the attached chart (charts/<TICKER>.png).
  3. Confirm or revise the mechanical V4 grade based on the chart context.
     The mechanical grade is correct ~70% of the time on A and ~76% on F;
     your job is to catch the ~30% of A grades that look wrong on chart
     and the cases where the rubric missed something (gap risk, support
     breakdown, sector dislocation, etc).
  4. Issue a final conviction verdict in this exact format:

     TICKER: <verdict> (<conviction>/10)
       Archetype: <Reversal/Mixed/Continuation>
       V4 grade: <A-F>  →  Final: <A-F>  (revised because: <reason or "rubric concurs">)
       Strengths: <1-2 bullets>
       Concerns:  <1-2 bullets>
       Invalidation: <specific price level or condition that voids the thesis>

     <verdict> ∈ {BUY, WATCH, PASS}
       BUY    = full or half size depending on grade (A/B = full, C = half)
       WATCH  = setup is forming but premature; set alert at <level>
       PASS   = skip this cycle

  5. After per-ticker verdicts, write a 2-3 sentence portfolio-level
     comment: which name has the best risk/reward, which has the highest
     conviction but worst risk/reward (often different), and whether
     anything in the batch suggests a sector/theme worth zooming into.

Do NOT:
  - Restate the V4 framework
  - Repeat the per-ticker data blocks verbatim
  - Grade signals not in this briefing
"""


# ═══════════════════════════════════════════════════════════════════════
# CORE — fetch, evaluate, chart, write
# ═══════════════════════════════════════════════════════════════════════

def fetch_and_compute(ticker: str, years: int = 5) -> pd.DataFrame:
    """Fetch from yfinance, compute V7+MCDX+RSIDiv stack, enrich for V4."""
    daily = sb.fetch_daily_ohlcv(ticker, years)
    if daily.empty:
        return pd.DataFrame()
    weekly = sb.compute_all_indicators(daily)
    weekly = sb.enrich(weekly)
    return weekly


def evaluate_current_state(d: pd.DataFrame, ticker: str) -> dict:
    """Apply V4 grading to the most recent bar; return structured summary."""
    if d.empty or len(d) < 60:
        return {'ticker': ticker, 'error': f'Insufficient data ({len(d)} weekly bars; need >=60)'}

    latest = d.iloc[-1]
    grade = sb.grade_signal(latest)

    # Find most recent T1-T6 signal in last 13 weeks (the trade-relevant window)
    recent = d.tail(13)
    recent_signals = recent[recent['tier'] > 0]
    most_recent_signal = recent_signals.iloc[-1] if len(recent_signals) > 0 else None

    def _num(v, dp=2):
        return None if pd.isna(v) else round(float(v), dp)

    summary = {
        'ticker': ticker,
        'as_of': latest.name.strftime('%Y-%m-%d'),
        'close': _num(latest['close']),
        # V4 grade on current bar
        'archetype':  getattr(grade, 'archetype', 'Unknown'),
        'grade':      grade.grade,
        'subtotal':   grade.subtotal,
        'scores': {
            'dim1_drawdown_or_extension':   getattr(grade, 'trend', None),
            'dim2_momentum':                getattr(grade, 'macd', None),
            'dim3_uc':                      getattr(grade, 'uc', None),
            'dim4_mcdx_or_banker':          getattr(grade, 'mcdx', None),
            'dim5_rsi_or_late_entry':       getattr(grade, 'rsi', None),
        },
        'risk_flags': list(grade.flags) if grade.flags else [],
        # Most recent V7 signal
        'recent_signal': None if most_recent_signal is None else {
            'date':  most_recent_signal.name.strftime('%Y-%m-%d'),
            'tier':  int(most_recent_signal['tier']),
            'weeks_ago': int((latest.name - most_recent_signal.name).days / 7),
            'close_at_signal': _num(most_recent_signal['close']),
            'price_change_since': _num(
                (latest['close'] / most_recent_signal['close'] - 1) * 100, 1),
        },
        # Trend context
        'trend': {
            'pct_from_52w_high':   _num(latest['pct_from_52wh'], 1),
            'pct_vs_ema21':        _num(latest['pct_vs_ema21'], 1),
            'pct_vs_sma50':        _num(latest['pct_vs_sma50'], 1),
            'ret_4w':              _num(latest['ret_4w'], 1),
            'ret_13w':             _num(latest['ret_13w'], 1),
            'ret_26w':             _num(latest['ret_26w'], 1),
        },
        # Institutional state
        'institutional': {
            'uc':                  _num(latest['uc']),
            'uc_rising':           bool(latest['uc_rising']),
            'uc_saturated':        bool(latest['uc_saturated']),
            'mcdx_banker':         _num(latest['mcdx_banker']),
            'mcdx_banker_rising':  bool(latest['mcdx_banker_rising']),
            'mcdx_hot_money':      _num(latest['mcdx_hot_money']),
            'banker_uc_divergent': bool(latest.get('banker_uc_divergent', False)),
            'banker_uc_aligned':   bool(latest.get('banker_uc_aligned', False)),
        },
        # Momentum state
        'momentum': {
            'macd_line':           _num(latest['macd_line'], 3),
            'macd_signal':         _num(latest['macd_signal'], 3),
            'macd_hist':           _num(latest['macd_hist'], 3),
            'macd_hist_rising':    bool(latest['macd_hist_rising']),
            'macd_above_zero':     bool(latest['macd_above_zero']),
            'macd_above_signal':   bool(latest['macd_above_signal']),
            'macd_cross_up_now':   bool(latest['macd_cross_up']),
        },
        # RSI state
        'rsi': {
            'rsi14':               _num(latest['rsi14'], 1),
            'rsi_rising':          bool(latest['rsi_rising']),
            'rsi_bullish_divergence': bool(latest.get('rsi_bull_div', False)),
            'rsi_bearish_divergence': bool(latest.get('rsi_bear_div', False)),
        },
        # Volatility
        'volatility': {
            'atr':                 _num(latest['atr'], 3),
            'atr_rank':            _num(latest['atr_rank'], 1),
            'atr_squeeze':         bool(latest['atr_squeeze']),
        },
    }
    return summary


def build_briefing_chart(d: pd.DataFrame, ticker: str, summary: dict, output_path: Path) -> Path:
    """Render a 4-panel chart zoomed to the last 60 weeks with V4 grade in title."""
    d_recent = d.tail(60).copy()  # zoom for clarity

    fig, axes = plt.subplots(4, 1, figsize=(13, 11), sharex=True,
                             gridspec_kw={'height_ratios': [3, 1.2, 1.2, 1.2]})
    fig.subplots_adjust(hspace=0.18, top=0.92, bottom=0.06, left=0.08, right=0.96)

    bg, fg, muted = '#0b1220', '#E8ECF4', '#8A93A6'
    g, a, r, b, p = '#5DCAA5', '#EF9F27', '#E24B4A', '#378ADD', '#7F77DD'
    grade_colors = {'A': g, 'B': '#9DD17E', 'C': a, 'D': '#D88454', 'F': r}

    for ax in axes:
        ax.set_facecolor(bg)
        ax.tick_params(colors=fg, labelsize=9)
        for s in ax.spines.values():
            s.set_color(muted)
        ax.grid(True, alpha=0.08, color=fg)
    fig.patch.set_facecolor(bg)

    # ── Title with V4 grade badge ───────────────────────────────
    gc = grade_colors.get(summary.get('grade', 'C'), muted)
    title = (f"{ticker}   "
             f"V4 grade: {summary.get('grade','?')} ({summary.get('archetype','?')})   "
             f"{summary.get('subtotal','?')}/10   "
             f"close ${summary.get('close','?')}   "
             f"as of {summary.get('as_of','?')}")
    fig.suptitle(title, color=gc, fontsize=14, fontweight='bold', y=0.97)

    # ── Panel 1: price + HMA + EMA + signals ────────────────────
    ax = axes[0]
    ax.plot(d_recent.index, d_recent['close'], color=fg, linewidth=1.5, label='Close')
    ax.plot(d_recent.index, d_recent['hma'],   color=a, linewidth=1.7, label='HMA(21)')
    if 'ema_21' in d_recent.columns:
        ax.plot(d_recent.index, d_recent['ema_21'], color=b, linewidth=1.1, alpha=0.7, label='EMA(21)')

    # Recent T1-T6 signals
    sigs = d_recent[d_recent['tier'] > 0]
    if len(sigs):
        ax.scatter(sigs.index, sigs['close'] * 0.92, marker='^', s=180,
                   color=g, edgecolor=fg, linewidths=1, zorder=5, label='T1-T6 fire')
        for dt, row in sigs.iterrows():
            ax.annotate(f"T{int(row['tier'])}",
                        xy=(dt, row['close'] * 0.92),
                        xytext=(dt, row['close'] * 0.85),
                        color=g, fontsize=9, ha='center', fontweight='bold',
                        arrowprops=dict(arrowstyle='-', color=g, lw=0.8))

    # ExD exits
    exits = d_recent[d_recent['exd']]
    if len(exits):
        ax.scatter(exits.index, exits['close'] * 1.08, marker='X', s=130,
                   color=r, edgecolor=fg, linewidths=1, zorder=5, label='ExD exit')

    # Mark current bar prominently
    latest = d_recent.iloc[-1]
    ax.axvline(latest.name, color=gc, alpha=0.3, linewidth=1.5)
    ax.scatter([latest.name], [latest['close']], marker='o', s=120,
               color=gc, edgecolor=fg, linewidths=2, zorder=6, label='Current bar')

    # 52w high reference
    high_52w = d_recent['close'].max()
    ax.axhline(high_52w, color=muted, linewidth=0.5, alpha=0.4, linestyle='--')
    ax.text(d_recent.index[0], high_52w * 1.005, f' 52w high: ${high_52w:.2f}',
            color=muted, fontsize=8)

    ax.set_ylabel('Price ($)', color=fg, fontsize=10)
    ax.legend(loc='upper left', facecolor=bg, edgecolor=muted, labelcolor=fg,
              fontsize=8, ncol=5, framealpha=0.85)

    # ── Panel 2: MACD ───────────────────────────────────────────
    ax = axes[1]
    hist = d_recent['macd_hist']
    pos = hist > 0
    ax.bar(d_recent.index[pos],  hist[pos],  color=g, alpha=0.55, width=5)
    ax.bar(d_recent.index[~pos], hist[~pos], color=r, alpha=0.55, width=5)
    ax.plot(d_recent.index, d_recent['macd_line'],   color=b, linewidth=1.3, label='MACD')
    ax.plot(d_recent.index, d_recent['macd_signal'], color=a, linewidth=1.0, label='Signal')
    ax.axhline(0, color=muted, linewidth=0.6)
    ax.axvline(latest.name, color=gc, alpha=0.3, linewidth=1.5)
    ax.set_ylabel('MACD', color=fg, fontsize=10)
    ax.legend(loc='upper left', facecolor=bg, edgecolor=muted, labelcolor=fg, fontsize=8, framealpha=0.85)

    # ── Panel 3: UC + RSI ───────────────────────────────────────
    ax = axes[2]
    ax.fill_between(d_recent.index, 0, d_recent['uc'].fillna(0),
                    color=p, alpha=0.35, label='UC (fast)')
    ax.axhline(20, color=muted, linewidth=0.6, linestyle='--', alpha=0.5)
    ax.set_ylim(0, 21)
    ax2 = ax.twinx()
    ax2.plot(d_recent.index, d_recent['rsi14'], color=a, linewidth=1.1, label='RSI(14)')
    for lvl in (30, 50, 70):
        ax2.axhline(lvl, color=muted, linewidth=0.5, alpha=0.4,
                    linestyle='--' if lvl == 50 else '-')
    ax2.set_ylim(0, 100)
    ax.axvline(latest.name, color=gc, alpha=0.3, linewidth=1.5)
    ax.set_ylabel('UC', color=p, fontsize=10)
    ax2.set_ylabel('RSI', color=a, fontsize=10)
    ax.tick_params(axis='y', colors=p)
    ax2.tick_params(axis='y', colors=a)
    for s in ax2.spines.values():
        s.set_color(muted)

    # ── Panel 4: MCDX ───────────────────────────────────────────
    ax = axes[3]
    ax.fill_between(d_recent.index, 0, d_recent['mcdx_banker'].fillna(0),
                    color=r, alpha=0.45, label='Banker (slow inst.)')
    ax.plot(d_recent.index, d_recent['mcdx_hot_money'], color=a, linewidth=1.2, label='Hot Money')
    ax.axhline(15, color=muted, linewidth=0.5, alpha=0.5, linestyle='--')
    ax.axhline(5,  color=muted, linewidth=0.5, alpha=0.3, linestyle=':')
    ax.set_ylim(0, 21)
    ax.axvline(latest.name, color=gc, alpha=0.3, linewidth=1.5)
    ax.set_ylabel('MCDX', color=fg, fontsize=10)
    ax.set_xlabel('Week ending', color=fg, fontsize=10)
    ax.legend(loc='upper left', facecolor=bg, edgecolor=muted, labelcolor=fg, fontsize=8, framealpha=0.85)
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))

    plt.savefig(output_path, dpi=130, facecolor=bg, bbox_inches='tight')
    plt.close()
    return output_path


# ═══════════════════════════════════════════════════════════════════════
# Per-ticker briefing section formatter
# ═══════════════════════════════════════════════════════════════════════

def format_ticker_section(s: dict) -> str:
    """Format one ticker's section in the briefing.md."""
    if 'error' in s:
        return f"### {s['ticker']}\n\n*Error: {s['error']}*\n"

    grade_emoji = {'A': '🟢', 'B': '🟢', 'C': '🟡', 'D': '🟠', 'F': '🔴'}.get(s['grade'], '⚪')

    lines = [
        f"### {s['ticker']}   {grade_emoji} **Grade {s['grade']}**   "
        f"({s['archetype']}, {s['subtotal']}/10, as of {s['as_of']})",
        "",
        f"**Chart:** `charts/{s['ticker']}.png`",
        "",
        f"**Close:** ${s['close']}    **52w high:** "
        f"{s['trend']['pct_from_52w_high']}% away    "
        f"**vs EMA21:** {s['trend']['pct_vs_ema21']}%    "
        f"**vs SMA50:** {s['trend']['pct_vs_sma50']}%",
        "",
        f"**Trailing returns:** 4w {s['trend']['ret_4w']:+}%, "
        f"13w {s['trend']['ret_13w']:+}%, "
        f"26w {s['trend']['ret_26w']:+}%",
        "",
    ]

    if s['recent_signal']:
        rs = s['recent_signal']
        lines += [
            f"**Most recent T-signal:** T{rs['tier']} on {rs['date']} "
            f"({rs['weeks_ago']}w ago) @ ${rs['close_at_signal']} → "
            f"now {rs['price_change_since']:+}% since",
            "",
        ]
    else:
        lines += ["**Most recent T-signal:** none in last 13 weeks", ""]

    # V4 score breakdown
    sc = s['scores']
    lines += [
        "**V4 sub-scores:**",
        "",
        "| Dimension | Score |",
        "|-----------|------:|",
        f"| 1. Drawdown / Extension | {sc['dim1_drawdown_or_extension']} / 2 |",
        f"| 2. Momentum turn | {sc['dim2_momentum']} / 2 |",
        f"| 3. UC | {sc['dim3_uc']} / 2 |",
        f"| 4. MCDX / Banker | {sc['dim4_mcdx_or_banker']} / 2 |",
        f"| 5. RSI / Late-entry guard | {sc['dim5_rsi_or_late_entry']} / 2 |",
        "",
    ]

    # Risk flags
    if s['risk_flags']:
        lines += [f"**Risk flags fired:** {', '.join(s['risk_flags'])}", ""]
    else:
        lines += ["**Risk flags fired:** none", ""]

    # Institutional state
    inst = s['institutional']
    inst_notes = []
    if inst['banker_uc_divergent']:
        inst_notes.append("🎯 **banker_uc_divergent**: Banker bled out and UC re-engaging — reversal fingerprint")
    if inst['uc_saturated']:
        inst_notes.append("⚠️  UC saturated at 20 — momentum likely topped")
    if inst['mcdx_banker'] > 15 and inst['mcdx_banker_rising']:
        inst_notes.append("📈 Banker strong and rising — established institutional flow")
    if inst['mcdx_banker'] < 1:
        inst_notes.append("❄️  Banker absent — no slow institutional bid")

    lines += [
        f"**Institutional:** UC {inst['uc']} "
        f"({'↑' if inst['uc_rising'] else '↓'}{' SAT' if inst['uc_saturated'] else ''}), "
        f"Banker {inst['mcdx_banker']} "
        f"({'↑' if inst['mcdx_banker_rising'] else '↓'}), "
        f"Hot Money {inst['mcdx_hot_money']}",
    ]
    for note in inst_notes:
        lines.append(f"  - {note}")
    lines.append("")

    # Momentum state
    mom = s['momentum']
    lines += [
        f"**Momentum:** MACD line {mom['macd_line']:+}, "
        f"hist {mom['macd_hist']:+} ({'↑' if mom['macd_hist_rising'] else '↓'}), "
        f"{'above' if mom['macd_above_zero'] else 'below'} zero, "
        f"{'above' if mom['macd_above_signal'] else 'below'} signal"
        + (", **cross-up this bar**" if mom['macd_cross_up_now'] else ""),
        "",
    ]

    # RSI + vol
    rsi = s['rsi']; vol = s['volatility']
    rsi_extras = []
    if rsi['rsi_bullish_divergence']:
        rsi_extras.append("**bullish divergence** (last 5w)")
    if rsi['rsi_bearish_divergence']:
        rsi_extras.append("⚠️ **bearish divergence** (last 5w)")
    lines += [
        f"**RSI/Vol:** RSI {rsi['rsi14']} ({'↑' if rsi['rsi_rising'] else '↓'}), "
        f"ATR rank {vol['atr_rank']}% "
        + ('(SQUEEZE)' if vol['atr_squeeze'] else '')
        + (' ' + ' '.join(rsi_extras) if rsi_extras else ''),
        "",
        "---",
        "",
    ]

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════
# Briefing writer
# ═══════════════════════════════════════════════════════════════════════

def write_briefing_md(summaries: list, output_dir: Path):
    date_str = datetime.now().strftime('%Y-%m-%d')

    # Quick summary table at the top
    table_lines = [
        "| Ticker | Grade | Archetype | Sub | Close | 52wH | 26w ret | Flags |",
        "|--------|-------|-----------|----:|------:|-----:|--------:|-------|",
    ]
    for s in summaries:
        if 'error' in s:
            table_lines.append(f"| {s['ticker']} | — | — | — | — | — | — | *{s['error']}* |")
            continue
        flags = ','.join(s['risk_flags']) if s['risk_flags'] else '—'
        table_lines.append(
            f"| {s['ticker']} | **{s['grade']}** | {s['archetype']} | "
            f"{s['subtotal']}/10 | ${s['close']} | "
            f"{s['trend']['pct_from_52w_high']}% | "
            f"{s['trend']['ret_26w']:+}% | {flags} |"
        )

    lines = [
        f"# Sterling Weekly Briefing — {date_str}",
        "",
        f"Candidates: **{len(summaries)}** "
        f"({sum(1 for s in summaries if s.get('grade') in ('A','B'))} grade A/B, "
        f"{sum(1 for s in summaries if s.get('grade') in ('D','F'))} grade D/F)",
        "",
        "## Snapshot",
        "",
        *table_lines,
        "",
        "## V4 Framework Primer",
        "",
        "```",
        V4_FRAMEWORK_PRIMER,
        "```",
        "",
        "## Per-Ticker Data",
        "",
    ]

    for s in summaries:
        lines.append(format_ticker_section(s))

    lines += [
        "---",
        "",
        "## Your task",
        "",
        LLM_TASK_PROMPT,
    ]

    (output_dir / 'briefing.md').write_text("\n".join(lines))


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

def main():
    ap = argparse.ArgumentParser(description="Sterling Weekly Briefing — V4")
    ap.add_argument('--tickers',     nargs='+', help="Tickers to brief")
    ap.add_argument('--ticker-file', type=Path, help="File with one ticker per line")
    ap.add_argument('--years',       type=int, default=5,
                    help="Years of yfinance history (default: 5)")
    ap.add_argument('--output',      type=Path, default=None,
                    help="Output dir (default: ./briefings/YYYY-MM-DD/)")
    args = ap.parse_args()

    # Resolve tickers
    tickers = []
    if args.tickers:
        tickers.extend([t.upper() for t in args.tickers])
    if args.ticker_file and args.ticker_file.exists():
        for line in args.ticker_file.read_text().splitlines():
            line = line.split('#')[0].strip()
            if line:
                tickers.append(line.upper())
    tickers = sorted(set(tickers))

    if not tickers:
        print("No tickers specified. Use --tickers or --ticker-file.", file=sys.stderr)
        sys.exit(1)

    # Resolve output dir
    if args.output is None:
        args.output = Path(f'./briefings/{datetime.now().strftime("%Y-%m-%d")}/')
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'charts').mkdir(exist_ok=True)
    (args.output / 'snapshots').mkdir(exist_ok=True)

    print(f"Building briefing for {len(tickers)} ticker(s) → {args.output}/")
    print()

    summaries = []
    for ticker in tickers:
        try:
            d = fetch_and_compute(ticker, args.years)
            if d.empty:
                print(f"  {ticker:6s} → no data (delisted? typo?)")
                summaries.append({'ticker': ticker, 'error': 'No yfinance data'})
                continue

            summary = evaluate_current_state(d, ticker)
            summaries.append(summary)

            # Save snapshot JSON
            (args.output / 'snapshots' / f'{ticker}.json').write_text(
                json.dumps(summary, indent=2, default=str)
            )

            # Build chart (only if we got a real summary, not an error)
            if 'error' not in summary:
                build_briefing_chart(d, ticker, summary,
                                     args.output / 'charts' / f'{ticker}.png')
                print(f"  {ticker:6s} → {summary['grade']} ({summary['archetype']}, "
                      f"{summary['subtotal']}/10)"
                      + (f"  flags: {','.join(summary['risk_flags'])}"
                         if summary['risk_flags'] else ''))
            else:
                print(f"  {ticker:6s} → {summary['error']}")

        except Exception as e:
            print(f"  {ticker:6s} → ERROR: {e}", file=sys.stderr)
            summaries.append({'ticker': ticker, 'error': str(e)})

    write_briefing_md(summaries, args.output)

    print()
    print(f"Done. Briefing pack ready in {args.output.resolve()}")
    print(f"  • briefing.md   ← drop into Claude.ai chat")
    print(f"  • charts/       ← drag images into the same chat")
    print(f"  • snapshots/    ← per-ticker JSON if you want raw data")


if __name__ == '__main__':
    main()
