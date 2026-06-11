#!/bin/sh
# Propagate the canonical shared refs into each installed skill. Run from repo root:
#   sh sterling-grid/sync-shared.sh
set -e
ROOT="$(CDPATH= cd "$(dirname "$0")/.." && pwd)"
SHARED="$ROOT/sterling-grid/shared"; SKILLS="$ROOT/.claude/skills"
for d in "$SKILLS"/sterling-grid-*; do [ -d "$d" ] || continue; mkdir -p "$d/references"
  for f in shared-context-dna.md lineage-block.md diagnostic-reference.md handoff-card-spec.md theme-intelligence.md; do cp "$SHARED/$f" "$d/references/$f"; done
  echo "synced -> $(basename "$d")"; done; echo done.
