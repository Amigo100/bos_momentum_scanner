#!/usr/bin/env python3
"""Sterling Grid — export the Friday scan into the weekend pipeline's signal list.

Converts scanner/output/signals_technical.json (buy_signals) into
sterling-run/signals/this-week.csv — the Tier-1 input contract
(header: ticker,sector,last_price,signal_type,signal_strength) — plus a dated
snapshot in sterling-run/signals/archive/. This replaces the manual weekly
extraction step.

Mapping (deterministic canon — the pre-2026-06-11 csv's strength labels were
hand-assigned and are NOT reproduced):
  ticker          <- symbol
  sector          <- enrichment.sector (else "Unknown")
  last_price      <- price (2dp)
  signal_type     <- "HMA-pivot"; "ExD" when exd_signal fired without a pivot low
  signal_strength <- "strong" if (buy_signal_v6 or macd_cross_up or uc_rising) else "weak"

Held-name dedup: tickers already in sterling-run/portfolio.csv are skipped
(held names enter the pipeline via re-underwrite, not triage); --include-held
overrides.

Usage:
  python3 -m scripts.sterling_signals_export [--signals PATH] [--run-root sterling-run]
                                             [--date YYYY-MM-DD] [--dry-run] [--include-held]
"""
import argparse, csv, json, os, sys

HEADER = ["ticker", "sector", "last_price", "signal_type", "signal_strength"]


def held_tickers(run_root):
    pf = os.path.join(run_root, "portfolio.csv")
    held = set()
    if os.path.exists(pf):
        for line in open(pf):
            if line.startswith("#") or line.startswith("Ticker") or not line.strip():
                continue
            held.add(line.split(",")[0].strip())
    return held


def build_rows(signals, skip):
    rows, skipped = [], []
    for s in signals:
        tk = (s.get("symbol") or "").strip()
        if not tk:
            continue
        if tk in skip:
            skipped.append(tk)
            continue
        sector = (s.get("enrichment") or {}).get("sector") or "Unknown"
        sig_type = "ExD" if (s.get("exd_signal") and not s.get("hma_pivot_low")) else "HMA-pivot"
        strength = "strong" if (s.get("buy_signal_v6") or s.get("macd_cross_up")
                                or s.get("uc_rising")) else "weak"
        rows.append([tk, sector, f"{float(s.get('price') or 0):.2f}", sig_type, strength])
    return rows, skipped


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--signals", default="scanner/output/signals_technical.json")
    ap.add_argument("--run-root", default="sterling-run")
    ap.add_argument("--date", default=None, help="snapshot date (default: signal week_date / scan timestamp date)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--include-held", action="store_true",
                    help="do not skip tickers already held in sterling-run/portfolio.csv")
    a = ap.parse_args()

    try:
        data = json.load(open(a.signals))
    except Exception as e:
        print(f"ERROR: cannot read {a.signals}: {e}")
        sys.exit(1)
    signals = data.get("buy_signals") or []

    date = a.date
    if not date:
        date = (signals[0].get("week_date") if signals else None) \
               or (data.get("timestamp", "")[:10] or None)
    if not date:
        print("ERROR: no date derivable — pass --date")
        sys.exit(1)

    skip = set() if a.include_held else held_tickers(a.run_root)
    rows, skipped = build_rows(signals, skip)

    if not rows:
        print(f"WARNING: 0 exportable buy signals in {a.signals} "
              f"({len(signals)} raw, {len(skipped)} held-skipped) — writing header-only csv")

    strong = sum(1 for r in rows if r[4] == "strong")
    print(f"{len(rows)} signals -> this-week.csv ({strong} strong / {len(rows)-strong} weak)"
          + (f"; skipped held: {sorted(skipped)}" if skipped else ""))

    if a.dry_run:
        for r in rows[:10]:
            print("  " + ",".join(r))
        if len(rows) > 10:
            print(f"  … +{len(rows)-10} more")
        print("dry-run: nothing written")
        return

    out_dir = os.path.join(a.run_root, "signals")
    arch_dir = os.path.join(out_dir, "archive")
    os.makedirs(arch_dir, exist_ok=True)
    out = os.path.join(out_dir, "this-week.csv")
    snap = os.path.join(arch_dir, f"this-week-{date}.csv")
    for path in (out, snap):
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(HEADER)
            w.writerows(rows)
    print(f"written {out} + snapshot {snap}")


if __name__ == "__main__":
    main()
