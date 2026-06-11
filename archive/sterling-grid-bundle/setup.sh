#!/bin/sh
# setup.sh — install the Sterling Grid skills + working folder into your repo.
# From inside the unzipped bundle, point it at your repo:
#   sh setup.sh /path/to/bos_momentum_scanner
# ...or cd into the repo and run with no argument:
#   cd ~/code/bos_momentum_scanner && sh ~/Downloads/sterling-grid-bundle/setup.sh
set -e
SCRIPT_DIR="$(CDPATH= cd "$(dirname "$0")" && pwd)"
SRC="$SCRIPT_DIR/sterling-grid-skills"
RUNSRC="$SCRIPT_DIR/sterling-run"
TARGET="$(CDPATH= cd "${1:-$(pwd)}" && pwd)"

[ -d "$SRC/skills" ] || { echo "error: $SRC/skills not found — run setup.sh from inside the unzipped sterling-grid-bundle folder."; exit 1; }
[ -d "$RUNSRC" ]     || { echo "error: $RUNSRC not found."; exit 1; }

echo "Source : $SCRIPT_DIR"
echo "Target : $TARGET"
echo ""

# 1) the 16 skills -> .claude/skills/  (invocable as /sterling-grid-*)
mkdir -p "$TARGET/.claude/skills"
for d in "$SRC"/skills/sterling-grid-*; do
  name="$(basename "$d")"
  if [ -e "$TARGET/.claude/skills/$name" ]; then echo "  skip (exists): .claude/skills/$name"
  else cp -R "$d" "$TARGET/.claude/skills/$name"; echo "  installed -> /$name"; fi
done

# 2) editable master: shared/ + orchestration/ + a re-pointed sync script -> sterling-grid/
mkdir -p "$TARGET/sterling-grid"
cp -R "$SRC/shared" "$TARGET/sterling-grid/shared"
cp -R "$SRC/orchestration" "$TARGET/sterling-grid/orchestration"
cat > "$TARGET/sterling-grid/sync-shared.sh" << 'SYNC'
#!/bin/sh
# Propagate the canonical shared refs into each installed skill. Run from repo root:
#   sh sterling-grid/sync-shared.sh
set -e
ROOT="$(CDPATH= cd "$(dirname "$0")/.." && pwd)"
SHARED="$ROOT/sterling-grid/shared"; SKILLS="$ROOT/.claude/skills"
for d in "$SKILLS"/sterling-grid-*; do [ -d "$d" ] || continue; mkdir -p "$d/references"
  for f in shared-context-dna.md lineage-block.md diagnostic-reference.md handoff-card-spec.md theme-intelligence.md; do cp "$SHARED/$f" "$d/references/$f"; done
  echo "synced -> $(basename "$d")"; done; echo done.
SYNC
chmod +x "$TARGET/sterling-grid/sync-shared.sh"
echo "  master -> sterling-grid/ (shared/ + orchestration/ + sync-shared.sh)"

# 3) the working state folder -> sterling-run/
if [ -e "$TARGET/sterling-run" ]; then echo "  skip (exists): sterling-run/"
else cp -R "$RUNSRC" "$TARGET/sterling-run"; echo "  working folder -> sterling-run/"; fi

# 3b) the deterministic helpers -> scripts/  (the validator, the weekly close, the price refresh —
#     the orchestration docs invoke them as `python3 -m scripts.<name>`)
mkdir -p "$TARGET/scripts"; touch "$TARGET/scripts/__init__.py" 2>/dev/null || true
for f in "$SCRIPT_DIR"/scripts/*.py; do
  name="$(basename "$f")"
  if [ -e "$TARGET/scripts/$name" ]; then echo "  skip (exists): scripts/$name"
  else cp "$f" "$TARGET/scripts/$name"; echo "  script -> scripts/$name"; fi
done

# 4) set xhigh as the project default effort, so EVERY session — and every workflow sub-agent it
#    spawns — runs deep. (Opus 4.8 defaults to 'high'; spawned sub-agents inherit the session level,
#    not a skill's frontmatter, so this is what makes the deep tiers actually run at xhigh.)
mkdir -p "$TARGET/.claude"
python3 - "$TARGET/.claude/settings.json" << 'PY' || echo "  (couldn't auto-set effort; in the app, type once: /effort xhigh)"
import json, os, sys
p = sys.argv[1]
s = json.load(open(p)) if os.path.exists(p) else {}
s["effortLevel"] = "xhigh"
json.dump(s, open(p, "w"), indent=2)
print("  effort  -> .claude/settings.json (effortLevel: xhigh; persists across sessions)")
PY

echo ""
echo "Installed. Next — in the Claude Code app (no terminal needed):"
echo "  - Open this folder as your workspace; accept the workspace-trust dialog (activates allowed-tools)."
echo "  - /skills   -> confirm the 16 sterling-grid-* skills are listed."
echo "  - Effort is already xhigh (the spinner shows 'with xhigh effort') — you never need /effort."
echo "  - Follow START-HERE.md for the run."
