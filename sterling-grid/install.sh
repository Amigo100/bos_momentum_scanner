#!/bin/sh
# Sterling Grid skill installer — the ONE edit point is sterling-grid/ (tracked):
#   skills/          the 16 canonical skill sources
#   shared/          the 5 canonical shared references
#   orchestration/   run-pipeline.md + weekend-run.md
#
# This script (1) propagates shared/ into every SOURCE skill's references/ so the
# tracked source stays complete, then (2) installs the skills into .claude/skills/
# (the gitignored runtime Claude Code loads). Edit in sterling-grid/, run this, done.
#
#   sh sterling-grid/install.sh
set -e
ROOT="$(CDPATH= cd "$(dirname "$0")/.." && pwd)"
SHARED="$ROOT/sterling-grid/shared"
SRC="$ROOT/sterling-grid/skills"
DST="$ROOT/.claude/skills"

# 1) shared refs -> each source skill's references/ (single source of truth)
for d in "$SRC"/sterling-grid-*; do
  [ -d "$d" ] || continue
  mkdir -p "$d/references"
  for f in shared-context-dna.md lineage-block.md diagnostic-reference.md \
           handoff-card-spec.md theme-intelligence.md; do
    cp "$SHARED/$f" "$d/references/$f"
  done
done

# 2) install: replace the runtime copies wholesale
mkdir -p "$DST"
for d in "$SRC"/sterling-grid-*; do
  n="$(basename "$d")"
  rm -rf "$DST/$n"
  cp -R "$d" "$DST/$n"
  echo "installed -> $n"
done
echo "done."
