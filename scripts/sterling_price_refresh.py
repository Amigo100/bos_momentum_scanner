#!/usr/bin/env python3
"""Sterling Grid — refresh portfolio.csv prices (the step-⑧ pre-newsletter refresh).

Rewrites ONLY the `Current` and `P&L%` columns (P&L% recomputed from `Entry`) of
sterling-run/portfolio.csv — the newsletter's SOLE price source. The two comment lines, the
header, row order, and every other column (including `Entry Date`, col 14 — the scanner's
exit-check anchor) are preserved byte-identical. A ticker whose fetch fails keeps its old
values (warned, never blanked) — prices are pulled, never fabricated.

`Days Held` is left untouched (informational; re-derivable from Entry Date).

Usage:
  python3 -m scripts.sterling_price_refresh [--run-root sterling-run] [--dry-run]
"""
import argparse, os, shutil, sys

NCOLS = 14
I_TICKER, I_ENTRY, I_CUR, I_PNL = 0, 1, 2, 3


def fetch_current_prices(tickers, warn_threshold=0.5):
    """Latest closes via a yfinance batch download (inlined from the retired
    portfolio.manager canonical implementation — identical semantics: 1d window,
    auto_adjust, NaN-safe, returns only successes, warns when incomplete)."""
    if not tickers:
        return {}
    try:
        import yfinance as yf
    except ImportError:
        print("ERROR: yfinance not installed (pip install yfinance pandas)")
        sys.exit(1)

    prices, failed = {}, []
    try:
        data = yf.download(tickers, period="1d", interval="1d",
                           progress=False, auto_adjust=True)
        if len(tickers) == 1:
            tk = tickers[0]
            if not data.empty and "Close" in data.columns:
                prices[tk] = round(float(data["Close"].iloc[-1]), 2)
            else:
                failed.append(tk)
        elif not data.empty and "Close" in data.columns:
            for tk in tickers:
                try:
                    px = data["Close"][tk].iloc[-1]
                    if px == px:  # NaN check
                        prices[tk] = round(float(px), 2)
                    else:
                        failed.append(tk)
                except (KeyError, IndexError):
                    failed.append(tk)
        else:
            failed = list(tickers)
    except Exception as e:
        print(f"  ERROR fetching prices: {e}")
        failed = list(tickers)

    if tickers and len(prices) / len(tickers) < warn_threshold:
        print(f"  WARN: price fetch incomplete — {len(prices)}/{len(tickers)} "
              f"(failed: {', '.join(failed[:5])}{' …' if len(failed) > 5 else ''})")
    return prices


def parse_lines(path):
    """Split the file into passthrough lines and data rows.

    Returns a list of ("raw", line) for comments/header/odd rows and ("row", fields) for
    13-field data rows. Plain comma split is deliberate: no field contains a comma by design
    (catalyst windows use `;`), and split/rejoin keeps the other columns byte-identical.
    """
    items = []
    with open(path) as f:
        for line in f:
            body = line.rstrip("\n")
            if body.startswith("#") or body.startswith("Ticker"):
                items.append(("raw", line))
                continue
            fields = body.split(",")
            if len(fields) != NCOLS or not fields[I_TICKER].strip():
                if body.strip():
                    print(f"  WARN: row passed through untouched (expected {NCOLS} fields): "
                          f"{body[:60]}…")
                items.append(("raw", line))
                continue
            items.append(("row", fields))
    return items


def refresh(items, prices):
    """Update Current + P&L% in place. Returns (updated, kept_old, skipped) ticker lists."""
    updated, kept, skipped = [], [], []
    for kind, payload in items:
        if kind != "row":
            continue
        fields = payload
        tk = fields[I_TICKER].strip()
        px = prices.get(tk)
        if px is None:
            kept.append(tk)
            continue
        try:
            entry = float(fields[I_ENTRY])
        except ValueError:
            skipped.append(tk)
            print(f"  WARN: {tk}: Entry `{fields[I_ENTRY]}` not numeric — row skipped")
            continue
        old = fields[I_CUR]
        fields[I_CUR] = f"{px:.2f}"
        fields[I_PNL] = f"{(px / entry - 1) * 100:+.1f}%" if entry else fields[I_PNL]
        updated.append(tk)
        print(f"  {tk:6} {old} -> {fields[I_CUR]}  ({fields[I_PNL]})")
    return updated, kept, skipped


def render(items):
    out = []
    for kind, payload in items:
        out.append(payload if kind == "raw" else ",".join(payload) + "\n")
    return "".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-root", default="sterling-run")
    ap.add_argument("--dry-run", action="store_true", help="fetch + report, write nothing")
    a = ap.parse_args()

    pf = os.path.join(a.run_root, "portfolio.csv")
    if not os.path.exists(pf):
        print(f"ERROR: {pf} not found"); sys.exit(1)

    items = parse_lines(pf)
    tickers = [p[I_TICKER].strip() for k, p in items if k == "row"]
    if not tickers:
        print("no held rows found — nothing to refresh"); sys.exit(0)

    print(f"fetching latest closes for {len(tickers)} held tickers…")
    prices = fetch_current_prices(tickers)
    if not prices:
        print("ERROR: zero prices fetched — portfolio.csv left untouched"); sys.exit(1)

    updated, kept, skipped = refresh(items, prices)
    print(f"\nrefreshed {len(updated)}/{len(tickers)}"
          + (f"; kept old (fetch failed): {kept}" if kept else "")
          + (f"; skipped (bad Entry): {skipped}" if skipped else ""))

    if a.dry_run:
        print("dry-run: no file written"); return

    shutil.copy(pf, pf + ".bak")
    tmp = pf + ".tmp"
    with open(tmp, "w") as f:
        f.write(render(items))
    os.replace(tmp, pf)
    print(f"written {pf} (previous version at {pf}.bak)")


if __name__ == "__main__":
    main()
