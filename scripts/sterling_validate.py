#!/usr/bin/env python3
"""Sterling Grid run validator — the deterministic checks behind handoff-card-spec.md.

Read-only over sterling-run/. Exit 1 on any FAIL. --json emits machine output
(the triage orchestrator's auto-gapfill consumes `phases.<phase>.missing`).

  python3 -m scripts.sterling_validate <YYYY-MM-DD> [--check lineage|counts|decisions|layout|all]
                                       [--json] [--run-root sterling-run]

Checks (spec sections in sterling-grid/shared/handoff-card-spec.md):
  lineage    cards carry lineage as the canonical ordered [{stage, line}] array (§2);
             stage sequence is a prefix of the canonical order; expected depth per tier;
             inherited elements byte-identical across boundaries (catches re-derivation).
  counts     per fan-out phase: _batch_manifest.json exists and the union of batch outputs
             covers the manifest set exactly — missing/extra/duplicates reported (§5).
  decisions  decisions.json records carry stage/reason_code/price_at_decision/forward with
             canonical enums and spellings (§0); legacy records (no `stage`) WARN until backfilled.
  layout     each tier's files live in its own runs/<date>/<tier>/ dir; no stray decision
             side-logs in log/ (§4).
"""
import argparse, json, re, sys
from pathlib import Path

BASE_STAGES = ["Macro", "Theme", "Mapping", "Triage", "Gate", "Evidence", "Geometry", "Verdict", "Decision"]
STAGE_IDS = {"tier0", "tier1", "tier1_5", "tier2", "tier2_5", "tier3", "tier4", "exit"}
DECISIONS = {"ADVANCE", "DROP", "BUY", "DO_NOT_BUY", "SELL"}
REASON_CODES = {
    "no-path", "ruin", "disqualifier", "verify-failed", "false-match", "weak-proxy",
    "inferior-expression", "theme-posture", "pre-inflection", "distant-catalyst",
    "move-exhausted", "thin-setup", "lottery-ticket", "outclassed", "wrong-instrument",
    "held-routed-out",
}
# expected lineage depth by (tier dir, file kind); Consensus adds +1 where it ran
EXPECT_LEN = {
    ("tier1", "advance"): 4, ("tier1_5", "advance"): 4, ("tier2", "card"): 5,
    ("tier3", "dossier"): 6, ("tier3", "geometry"): 7, ("tier3", "verdict"): 8,
    ("tier4", "card"): 9,
}


class Report:
    def __init__(self):
        self.lines, self.failed, self.warned = [], False, False
        self.phases = {}

    def ok(self, check, msg):   self.lines.append(("PASS", check, msg))
    def warn(self, check, msg): self.lines.append(("WARN", check, msg)); self.warned = True
    def fail(self, check, msg): self.lines.append(("FAIL", check, msg)); self.failed = True


def load_json(path):
    try:
        return json.loads(path.read_text())
    except Exception as e:
        return {"__parse_error__": str(e)}


def lineage_shape_errors(lin):
    """Return a list of shape problems for a lineage value (empty = canonical)."""
    if not isinstance(lin, list):
        return [f"lineage is {type(lin).__name__}, not the canonical ordered array (spec §2)"]
    errs = []
    stages = []
    for i, el in enumerate(lin):
        if not (isinstance(el, dict) and isinstance(el.get("stage"), str) and isinstance(el.get("line"), str)):
            errs.append(f"element {i} is not {{stage, line}}")
            continue
        stages.append(el["stage"])
    if errs:
        return errs
    seq = [s for s in stages if s != "Consensus"]
    if "Consensus" in stages and ("Gate" not in stages or stages.index("Consensus") != stages.index("Gate") + 1):
        errs.append("Consensus out of position (must follow Gate)")
    if seq != BASE_STAGES[: len(seq)]:
        errs.append(f"stage order {stages} is not a prefix of the canonical order (spec §0)")
    return errs


def iter_cards(node, source, batch_key=None):
    """Yield (card_dict, kind) for card-like dicts in a parsed JSON file."""
    if isinstance(node, dict):
        if "__parse_error__" in node:
            return
        if isinstance(node.get("ticker"), str):
            yield node, batch_key or "card"
        for key in ("advance", "rows", "cards", "queue", "drops"):
            v = node.get(key)
            if isinstance(v, list):
                for item in v:
                    if isinstance(item, dict) and isinstance(item.get("ticker"), str):
                        yield item, key
    elif isinstance(node, list):
        for item in node:
            if isinstance(item, dict) and isinstance(item.get("ticker"), str):
                yield item, batch_key or "card"


def tier3_kind(path):
    n = path.name.lower()
    for k in ("dossier", "geometry", "verdict"):
        if k in n:
            return k
    return None


def check_lineage(run_dir, rep):
    found_any = False
    by_stage = {}  # boundary identity index: {tier: {ticker: lineage}}
    for path in sorted(run_dir.rglob("*.json")):
        if path.name.startswith("_"):
            continue
        tier = next((p for p in path.relative_to(run_dir).parts if p in STAGE_IDS), None)
        if tier in (None, "tier0"):
            continue
        data = load_json(path)
        if isinstance(data, dict) and "__parse_error__" in data:
            rep.fail("lineage", f"{path}: unparseable JSON ({data['__parse_error__']})")
            continue
        for card, kind in iter_cards(data, path):
            if kind == "drops":
                continue
            found_any = True
            tick = card.get("ticker", "?")
            where = f"{path.relative_to(run_dir)}::{tick}"
            lin = card.get("lineage")
            if lin is None:
                legacy = [k for k in card if k.endswith("_lineage_line") or k == "lineage_complete"
                          or k == "gate_lineage_line"]
                rep.fail("lineage", f"{where}: no `lineage` array"
                         + (f" (legacy fields {legacy} are not a substitute — spec §2)" if legacy else ""))
                continue
            errs = lineage_shape_errors(lin)
            if errs:
                rep.fail("lineage", f"{where}: " + "; ".join(errs))
                continue
            k3 = tier3_kind(path) if tier == "tier3" else None
            expect = EXPECT_LEN.get((tier, k3 or ("advance" if kind == "advance" else "card")))
            stages = [e["stage"] for e in lin]
            base_len = len([s for s in stages if s != "Consensus"])
            if expect and base_len < expect:
                rep.fail("lineage", f"{where}: {base_len} base elements, expected ≥{expect} for {tier}"
                         + (f"/{k3}" if k3 else ""))
            if (tier, k3) == ("tier3", "verdict") and [s for s in stages if s != "Consensus"][:8] != BASE_STAGES[:8]:
                rep.fail("lineage", f"{where}: 3c card missing the eight-element block (spec §2)")
            key = (tier, k3) if k3 else (tier, None)
            prev = by_stage.setdefault(key, {}).get(tick)
            if prev is not None and prev != lin:
                rep.fail("lineage", f"{where}: conflicting lineage for {tick} across files in {tier}"
                         " — same ticker, different arrays (a merge or re-run left two versions)")
            by_stage[key][tick] = lin
    # boundary identity: inherited prefix must be byte-identical
    order = [("tier1", None), ("tier1_5", None), ("tier2", None), ("tier3", "dossier"),
             ("tier3", "geometry"), ("tier3", "verdict"), ("tier4", None)]
    present = [k for k in order if k in by_stage]
    for up, down in zip(present, present[1:]):
        for tick, lin_out in by_stage[down].items():
            lin_in = by_stage[up].get(tick)
            if not lin_in:
                continue
            for i, el in enumerate(lin_in):
                if i >= len(lin_out):
                    break
                if el["stage"] == "Triage" and up[0] == "tier1":
                    continue  # Tier 1.5 edits Triage in place
                if lin_out[i] != el:
                    rep.fail("lineage", f"{down[0]}::{tick}: inherited `{el['stage']}` line differs from "
                             f"{up[0]}'s — silent re-derivation (spec §2)")
                    break
    if found_any and not rep.failed:
        rep.ok("lineage", "all cards carry canonical, monotonic, identity-preserving lineage arrays")
    if not found_any:
        rep.warn("lineage", f"no cards found under {run_dir}")


def check_counts(run_dir, rep):
    for phase in ("tier1", "tier1_5"):
        pdir = run_dir / phase
        if not pdir.is_dir():
            continue
        info = rep.phases.setdefault(phase, {"manifest": False, "missing": [], "extra": [], "duplicates": []})
        manifest = pdir / "_batch_manifest.json"
        batch_files = sorted(p for p in pdir.glob("*.json")
                             if not p.name.startswith("_") and "result" not in p.name
                             and "queue" not in p.name and "input" not in p.name and "triage_" not in p.name)
        if not manifest.exists():
            rep.fail("counts", f"{phase}: no _batch_manifest.json — count conservation unprovable (spec §5)")
            continue
        info["manifest"] = True
        man = load_json(manifest)
        want = [t for b in man.get("batches", []) for t in b.get("input_tickers", [])]
        got = []
        for bf in batch_files:
            data = load_json(bf)
            if isinstance(data, dict) and "__parse_error__" in data:
                rep.fail("counts", f"{bf}: unparseable JSON")
                continue
            rows = list(iter_cards(data, bf))
            got += [c.get("ticker") for c, kind in rows]
            counts = data.get("counts") if isinstance(data, dict) else None
            if isinstance(counts, dict) and "input" in counts:
                declared = sum(counts.get(k, 0) for k in ("advance", "drop", "held")
                               if isinstance(counts.get(k, 0), int))
                if declared != counts["input"]:
                    rep.fail("counts", f"{bf.name}: counts.input={counts['input']} but "
                             f"advance+drop+held = {declared}")
        missing = sorted(set(want) - set(got))
        extra = sorted(set(got) - set(want))
        dups = sorted({t for t in got if got.count(t) > 1})
        info.update(missing=missing, extra=extra, duplicates=dups)
        for label, vals in (("missing", missing), ("extra", extra), ("duplicates", dups)):
            if vals:
                rep.fail("counts", f"{phase}: {label} vs manifest: {vals}")
        if not (missing or extra or dups):
            rep.ok("counts", f"{phase}: {len(want)} manifest tickers all accounted for")
        # merged-result coverage (spec §5): the merged result must cover the manifest set too.
        # Canonical name first; pre-V9.1 aliases accepted for old runs (spec §4).
        result_names = [f"{phase}_result_{run_dir.name}.json"]
        if phase == "tier1_5":
            result_names += [f"triage_final_{run_dir.name}.json", f"triage_result_{run_dir.name}.json"]
        result = next((pdir / n for n in result_names if (pdir / n).exists()), None)
        if result is not None:
            rdata = load_json(result)
            # collect every ticker-bearing dict in the result: top-level lists (tier2_queue,
            # drop_log, advance, drop, rows …) plus one nested level (tier1/tier15 batch echoes)
            rticks = {c.get("ticker") for c, kind in iter_cards(rdata, result)}
            def _collect(node, depth=0):
                if isinstance(node, dict):
                    if isinstance(node.get("ticker"), str):
                        rticks.add(node["ticker"])
                    if depth < 3:
                        for v in node.values():
                            _collect(v, depth + 1)
                elif isinstance(node, list) and depth < 3:
                    for item in node:
                        _collect(item, depth + 1)
            _collect(rdata)
            rticks.discard(None)
            short = sorted(set(want) - rticks)
            if short:
                rep.fail("counts", f"{phase}: merged result {result.name} omits {short} (spec §5 — "
                         "the merge must cover the manifest; re-merge, never trim)")
                info["missing"] = sorted(set(info["missing"]) | set(short))


def check_decisions(root, rep):
    path = root / "decisions.json"
    if not path.exists():
        rep.fail("decisions", f"{path} missing — it is the sole ledger")
        return
    data = load_json(path)
    recs = data if isinstance(data, list) else (data.get("decisions") if isinstance(data, dict) else None)
    if not isinstance(recs, list):
        rep.fail("decisions", f"{path}: expected a list of records, or a dict with a `decisions` list "
                 f"(got {type(data).__name__})")
        return
    seen, legacy, bad = set(), 0, 0
    for i, r in enumerate(recs):
        where = f"decisions[{i}] {r.get('ticker', '?')}/{r.get('date', '?')}"
        is_legacy = "stage" not in r
        backfilled = (not is_legacy) and bool(r.get("tier"))  # pre-V9.1 row carrying the mapped stage
        problems = []
        if is_legacy:
            legacy += 1
        else:
            if r["stage"] not in STAGE_IDS:
                problems.append(f"stage `{r['stage']}` not in {sorted(STAGE_IDS)}")
            # reason_code: required-and-enum on DROP/DO_NOT_BUY; null allowed on BUY/SELL, and
            # allowed-with-WARN on backfilled rows whose prose was unambiguous to no code.
            code = r.get("reason_code")
            needs_code = r.get("decision") in ("DROP", "DO_NOT_BUY")
            if needs_code and code is None and backfilled:
                rep.warn("decisions", f"{where}: reason_code null on backfilled pre-V9.1 row "
                         "(code underivable from prose — acceptable)")
            elif needs_code and code not in REASON_CODES:
                problems.append(f"reason_code `{code}` not in the closed enum (spec §0)")
            elif not needs_code and code is not None and code not in REASON_CODES:
                problems.append(f"reason_code `{code}` not in the closed enum (spec §0)")
            if "price_at_decision" not in r:
                problems.append("price_at_decision missing (number or null)")
            if "forward" not in r:
                problems.append("forward block missing (nullable members)")
        if r.get("decision") not in DECISIONS:
            if is_legacy:
                rep.warn("decisions", f"{where}: legacy spelling `{r.get('decision')}` — normalize at backfill")
            else:
                problems.append(f"decision `{r.get('decision')}` not canonical (spec §0)")
        if not r.get("reason"):
            problems.append("reason empty")
        if r.get("decision") == "BUY" and not is_legacy and not (r.get("type") and r.get("conviction")):
            problems.append("BUY without type+conviction")
        key = (r.get("ticker"), r.get("stage", r.get("tier")), r.get("week_id"))
        if key in seen:
            problems.append(f"duplicate (ticker, stage, week_id) {key}")
        seen.add(key)
        for p in problems:
            bad += 1
            rep.fail("decisions", f"{where}: {p}")
    if legacy:
        rep.warn("decisions", f"{legacy}/{len(recs)} legacy records lack `stage` — run the one-time "
                 "backfill (calibration card-schemas)")
    if not bad:
        rep.ok("decisions", f"{len(recs)} records structurally valid ({legacy} legacy pending backfill)")


def file_named_tier(name):
    """The most specific stage id a filename names (tier1_5 beats its tier1 substring), or None."""
    best = None
    for sid in STAGE_IDS - {"exit"}:
        token = sid.replace("_", "[_-]")
        if re.search(rf"(^|[^0-9a-z]){token}([^0-9a-z]|$)", name):
            if best is None or len(sid) > len(best):
                best = sid
    return best


def check_layout(root, run_dir, rep):
    misplaced = []
    for tier in ("tier1", "tier1_5", "tier2", "tier2_5", "tier3", "tier4"):
        d = run_dir / tier
        if not d.is_dir():
            continue
        for p in d.rglob("*"):
            name = p.name.lower()
            if "queue" in name or "input" in name:
                continue  # consumer-named handoff files are legal in the producing tier's dir (§4)
            named = file_named_tier(name)
            if named and named != tier:
                misplaced.append(f"{p.relative_to(run_dir)} looks like {named} output inside {tier}/")
    for m in sorted(set(misplaced)):
        rep.fail("layout", m + " (spec §4: each tier writes only its own dir)")
    strays = [p.name for p in (root / "log").glob("*decision*")
              if p.suffix in (".jsonl", ".json") and p.name not in ("decisions.json",)]
    if strays:
        rep.warn("layout", f"decision side-logs in log/: {strays} — decisions.json is the sole ledger; "
                 "consolidate via calibration Part A (run-pipeline hygiene)")
    if not misplaced:
        rep.ok("layout", "tier outputs are in their own directories")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("date", help="run date YYYY-MM-DD (the runs/<date>/ dir)")
    ap.add_argument("--check", default="all", choices=["lineage", "counts", "decisions", "layout", "all"])
    ap.add_argument("--json", action="store_true", help="machine output (auto-gapfill reads phases.*.missing)")
    ap.add_argument("--run-root", default="sterling-run")
    args = ap.parse_args()

    root = Path(args.run_root)
    run_dir = root / "runs" / args.date
    rep = Report()
    if not run_dir.is_dir() and args.check in ("lineage", "counts", "layout", "all"):
        rep.fail("setup", f"{run_dir} does not exist")
    else:
        if args.check in ("lineage", "all"):
            check_lineage(run_dir, rep)
        if args.check in ("counts", "all"):
            check_counts(run_dir, rep)
        if args.check in ("layout", "all"):
            check_layout(root, run_dir, rep)
    if args.check in ("decisions", "all"):
        check_decisions(root, rep)

    if args.json:
        print(json.dumps({"date": args.date, "ok": not rep.failed,
                          "phases": rep.phases,
                          "results": [{"level": l, "check": c, "msg": m} for l, c, m in rep.lines]}, indent=1))
    else:
        for level, check, msg in rep.lines:
            print(f"{level:4} [{check}] {msg}")
        n_fail = sum(1 for l, _, _ in rep.lines if l == "FAIL")
        print(f"\n{'FAIL' if rep.failed else 'PASS'} — {n_fail} failure(s), "
              f"{sum(1 for l, _, _ in rep.lines if l == 'WARN')} warning(s)")
    sys.exit(1 if rep.failed else 0)


if __name__ == "__main__":
    main()
