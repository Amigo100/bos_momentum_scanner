#!/usr/bin/env bash
# Propagate the canonical shared references into every skill's references/ dir.
# Edit the DNA or the diagnostic toolkit ONCE in shared/, then run this so every
# tier skill picks up the change. Keeps each skill self-contained (portable as its
# own .skill bundle) while preserving a single source of truth.
set -euo pipefail
cd "$(dirname "$0")"

SHARED=(shared/shared-context-dna.md shared/diagnostic-reference.md shared/lineage-block.md
        shared/handoff-card-spec.md shared/theme-intelligence.md)

for skill_refs in skills/*/references; do
  for f in "${SHARED[@]}"; do
    cp "$f" "$skill_refs/"
    echo "synced $(basename "$f") -> $skill_refs/"
  done
done
echo "done."
