# Sterling Signals Codebase Cleanup Action Plan

**Based on:** CODEBASE_AUDIT_REPORT.md (2026-01-27)  
**Purpose:** Execute cleanup, remove superfluous files, improve organization

---

## Priority Summary

| Priority | Category | Items | Effort |
|----------|----------|-------|--------|
| 🔴 **P0** | Security | .env in git | 15 min |
| 🟠 **P1** | Delete | Duplicates & old versions | 10 min |
| 🟡 **P2** | Archive | Orphaned utility files | 20 min |
| 🟢 **P3** | Organize | Documentation structure | 30 min |
| 🔵 **P4** | Review | Decide on edge cases | 30 min |

---

## 🔴 Priority 0: CRITICAL SECURITY FIX

### Issue
`.env` file containing API keys is tracked by git. Secrets may be in git history.

### Actions

```bash
# Step 1: Remove .env from git tracking (keeps local file)
git rm --cached .env

# Step 2: Verify it's in .gitignore (should already be there)
grep "^\.env$" .gitignore || echo ".env" >> .gitignore

# Step 3: Commit the fix
git add .gitignore
git commit -m "security: remove .env from git tracking"

# Step 4: Push to remote
git push origin main
```

### Post-Fix: Rotate ALL API Keys

Since secrets may be in git history, rotate these credentials:

- [ ] **Anthropic API Key** - Generate new key at console.anthropic.com
- [ ] **Twitter/X API Keys** - Regenerate at developer.twitter.com
  - API Key
  - API Secret
  - Access Token
  - Access Token Secret
- [ ] **Email credentials** (if any SMTP passwords in .env)

Update `.env` with new keys after rotation.

---

## 🟠 Priority 1: Delete Definite Duplicates

### Files to DELETE (No Dependencies)

| File | Location | Reason |
|------|----------|--------|
| `newsletter_briefing_old.md` | `scanner/output/archive/2026-W04/` | Old version backup |
| `report_old.txt` | `scanner/output/archive/2026-W04/` | Old version backup |
| `generate_example_graphics.py` | Root | Never called, demo only |

### Commands

```bash
# Delete old version files
rm -f scanner/output/archive/2026-W04/newsletter_briefing_old.md
rm -f scanner/output/archive/2026-W04/report_old.txt

# Delete unused demo script
rm -f generate_example_graphics.py

# Commit
git add -A
git commit -m "cleanup: remove duplicate and unused files"
```

---

## 🟡 Priority 2: Archive Orphaned Utility Files

### Identified Orphaned Files (Not Imported Anywhere)

| File | Lines | Original Purpose | Recommendation |
|------|-------|------------------|----------------|
| `data_models.py` | 610 | Dataclass definitions | ARCHIVE - may be useful reference |
| `prompt_templates.py` | 687 | LLM prompt templates | ARCHIVE - prompts now inline |
| `llm_client.py` | 574 | Anthropic API wrapper | ARCHIVE - using direct calls |
| `logger.py` | 434 | Logging utilities | ARCHIVE - using standard logging |
| `data_loader.py` | 857 | Data loading utilities | ARCHIVE - functions moved elsewhere |
| `newsletter_prompts.py` | 228 | Newsletter prompts | ARCHIVE - merged into compiler |
| `due_diligence_prompts.py` | 421 | DD prompts | ARCHIVE - merged into dd_automator |
| `funnel_graphic.py` | 666 | Filter funnel charts | REVIEW - may be manually used |
| `winner_showcase_generator.py` | 233 | Winner content | REVIEW - part of new system? |

### Commands

```bash
# Create archive directory
mkdir -p archive/legacy_code

# Move orphaned utility files
mv data_models.py archive/legacy_code/
mv prompt_templates.py archive/legacy_code/
mv llm_client.py archive/legacy_code/
mv logger.py archive/legacy_code/
mv data_loader.py archive/legacy_code/
mv newsletter_prompts.py archive/legacy_code/
mv due_diligence_prompts.py archive/legacy_code/

# Add README to archive
cat > archive/legacy_code/README.md << 'EOF'
# Legacy Code Archive

These files were identified as orphaned (not imported by any active code) 
during the codebase audit on 2026-01-27.

They are preserved here for reference but are NOT part of the active system.

## Files

| File | Original Purpose |
|------|------------------|
| data_models.py | Dataclass definitions (superseded by inline definitions) |
| prompt_templates.py | LLM prompt templates (now inline in respective files) |
| llm_client.py | Anthropic API wrapper (now using direct calls) |
| logger.py | Logging utilities (using standard logging) |
| data_loader.py | Data loading utilities (functions moved to other files) |
| newsletter_prompts.py | Newsletter prompts (merged into newsletter_compiler.py) |
| due_diligence_prompts.py | DD prompts (merged into dd_automator.py) |

## Restoration

If any of these files are needed, they can be restored:
```bash
mv archive/legacy_code/filename.py ./
```
EOF

# Commit
git add -A
git commit -m "cleanup: archive orphaned utility files"
```

### Files to REVIEW Before Archiving

These may be actively used manually or part of new system:

| File | Question | How to Verify |
|------|----------|---------------|
| `funnel_graphic.py` | Is this run manually for marketing? | Check if funnel_*.png are used |
| `winner_showcase_generator.py` | Part of new system improvements? | Check TODO list |

**Decision needed:**
- If `funnel_graphic.py` is used manually → KEEP
- If `winner_showcase_generator.py` is part of new system → KEEP (it's in our improvement plan)

---

## 🟢 Priority 3: Organize Documentation

### Current State

Documentation is spread across:
- Root directory (5 files)
- `docs/` (5 files)
- `docs/audit/` (8 files)
- `docs/archive/` (13 files)

### Proposed Structure

```
docs/
├── README.md                           # Documentation index
├── SYSTEM_ARCHITECTURE.md              # Main system doc (from root)
├── SETUP.md                            # Setup instructions (from root)
├── STYLE_GUIDE.md                      # Python coding standards
├── MARKETING_GUIDE.md                  # Marketing rules (NEW)
├── audit/                              # Audit reports (KEEP AS-IS)
│   ├── AUDIT_REPORT.md
│   ├── 01-scanner-logic.md
│   ├── 02-signal-detection.md
│   └── ... (7 files)
├── planning/                           # Planning docs
│   ├── OPTIMISATION_PLAN.md
│   ├── MIGRATION_GUIDE.md
│   └── PORTFOLIO_DASHBOARD_SPEC.md
└── archive/                            # Historical docs (KEEP AS-IS)
    └── ... (13 files)

Root:
├── README.md                           # Keep - project entry point
├── CLAUDE.md                           # Keep - AI context
└── MASTER_TODO_v2.md                   # Keep - active task list
```

### Commands

```bash
# Create planning subdirectory
mkdir -p docs/planning

# Move planning docs
mv docs/OPTIMISATION_PLAN.md docs/planning/
mv docs/MIGRATION_GUIDE.md docs/planning/
mv docs/PORTFOLIO_DASHBOARD_SPEC.md docs/planning/

# Move system docs to docs/ (optional - or keep in root for visibility)
# cp SYSTEM_OVERVIEW.md docs/SYSTEM_ARCHITECTURE.md
# cp SETUP.md docs/

# Create documentation index
cat > docs/README.md << 'EOF'
# Sterling Signals Documentation

## Quick Links

| Document | Description |
|----------|-------------|
| [../CLAUDE.md](../CLAUDE.md) | AI assistant context |
| [../README.md](../README.md) | Project overview |
| [STYLE_GUIDE.md](STYLE_GUIDE.md) | Python coding standards |

## System Documentation

- [../SYSTEM_OVERVIEW.md](../SYSTEM_OVERVIEW.md) - Architecture & marketing
- [../SETUP.md](../SETUP.md) - Setup instructions

## Audit Reports

See [audit/](audit/) directory for comprehensive system audits.

## Planning

See [planning/](planning/) directory for roadmaps and specs.

## Archive

See [archive/](archive/) directory for historical documents.
EOF

# Commit
git add -A
git commit -m "docs: reorganize documentation structure"
```

---

## 🔵 Priority 4: Review & Decide

### Files Requiring Human Decision

| File | Question | Options |
|------|----------|---------|
| `funnel_graphic.py` | Used for marketing images? | KEEP if yes, ARCHIVE if no |
| `winner_showcase_generator.py` | Part of new improvements? | KEEP - in our TODO list |
| `self_quote_tracker.py` | Part of new improvements? | KEEP - in our TODO list |
| `substack_content_generator.py` | Part of new improvements? | KEEP - actively used |
| `due_diligence.py` | Used manually for DD? | KEEP if yes, ARCHIVE if no |

### Documentation Requiring Update

| File | Issue | Action |
|------|-------|--------|
| `CLAUDE.md` | May reference non-existent files | Review after cleanup |
| `docs/STERLING_SIGNALS_MASTER_PROMPTS.md` | UK ISA references (now US focused?) | Update or archive |

### Edge Cases

| Item | Notes |
|------|-------|
| Legacy symlinks in `trades/` | KEEP for backwards compatibility |
| `portfolio_google_sheets.csv` | Useful export format - KEEP |
| `__pycache__/` directories | Should be gitignored, not committed |

---

## Complete Cleanup Script

Run this after making decisions on review items:

```bash
#!/bin/bash
# Sterling Signals Codebase Cleanup Script
# Run from repository root

set -e  # Exit on error

echo "=== Sterling Signals Codebase Cleanup ==="
echo ""

# P0: Security Fix
echo "[P0] Fixing .env security issue..."
git rm --cached .env 2>/dev/null || echo ".env not tracked (already fixed)"
grep -q "^\.env$" .gitignore || echo ".env" >> .gitignore

# P1: Delete Duplicates
echo "[P1] Removing duplicate/old files..."
rm -f scanner/output/archive/2026-W04/newsletter_briefing_old.md
rm -f scanner/output/archive/2026-W04/report_old.txt
rm -f generate_example_graphics.py

# P2: Archive Orphaned Files
echo "[P2] Archiving orphaned utility files..."
mkdir -p archive/legacy_code

# Only move files that exist and aren't in our new system
for file in data_models.py prompt_templates.py llm_client.py logger.py data_loader.py newsletter_prompts.py due_diligence_prompts.py; do
    if [ -f "$file" ]; then
        mv "$file" archive/legacy_code/
        echo "  Archived: $file"
    fi
done

# Create archive README
cat > archive/legacy_code/README.md << 'ARCHIVEREADME'
# Legacy Code Archive

Archived during codebase cleanup on $(date +%Y-%m-%d).
These files are not imported by any active code.
ARCHIVEREADME

# P3: Organize Docs
echo "[P3] Organizing documentation..."
mkdir -p docs/planning
[ -f docs/OPTIMISATION_PLAN.md ] && mv docs/OPTIMISATION_PLAN.md docs/planning/
[ -f docs/MIGRATION_GUIDE.md ] && mv docs/MIGRATION_GUIDE.md docs/planning/
[ -f docs/PORTFOLIO_DASHBOARD_SPEC.md ] && mv docs/PORTFOLIO_DASHBOARD_SPEC.md docs/planning/

# Clean up __pycache__
echo "[P3] Cleaning Python cache..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Ensure __pycache__ is gitignored
grep -q "^__pycache__/$" .gitignore || echo "__pycache__/" >> .gitignore
grep -q "^\*.pyc$" .gitignore || echo "*.pyc" >> .gitignore

# Commit all changes
echo ""
echo "[COMMIT] Staging changes..."
git add -A

echo ""
echo "=== Cleanup Complete ==="
echo ""
echo "Review staged changes with: git status"
echo "Commit with: git commit -m 'cleanup: comprehensive codebase cleanup'"
echo ""
echo "⚠️  IMPORTANT: After pushing, rotate all API keys in .env!"
```

---

## Post-Cleanup Verification

After running cleanup:

```bash
# Verify file counts
echo "Python files: $(find . -name '*.py' -not -path './.git/*' -not -path './archive/*' | wc -l)"
# Expected: ~25 (down from 34)

# Verify no .env in git
git ls-files .env
# Expected: empty output

# Verify archive created
ls archive/legacy_code/
# Expected: 7 Python files + README.md

# Verify workflows still parse
python -c "import yaml; yaml.safe_load(open('.github/workflows/friday_scan.yml'))"
python -c "import yaml; yaml.safe_load(open('.github/workflows/daily_post.yml'))"
# Expected: no errors

# Test imports of core files
python -c "import scanner; print('scanner OK')"
python -c "import tweet_generator; print('tweet_generator OK')"
python -c "import config; print('config OK')"
# Expected: no import errors
```

---

## Final Codebase Structure (After Cleanup)

```
sterling-signals/
├── .github/
│   └── workflows/
│       ├── friday_scan.yml          # Weekly scan
│       └── daily_post.yml           # Daily posting
│
├── archive/
│   └── legacy_code/                 # Orphaned files (7)
│       ├── README.md
│       ├── data_models.py
│       ├── prompt_templates.py
│       ├── llm_client.py
│       ├── logger.py
│       ├── data_loader.py
│       ├── newsletter_prompts.py
│       └── due_diligence_prompts.py
│
├── docs/
│   ├── README.md                    # Documentation index
│   ├── STYLE_GUIDE.md
│   ├── audit/                       # 8 audit files
│   ├── planning/                    # 3 planning files
│   └── archive/                     # 13 historical files
│
├── tests/
│   ├── test_safeguards.py
│   └── test_edge_cases.py
│
├── trades/                          # Runtime data
│   ├── current/
│   ├── weeks/
│   ├── charts/
│   ├── portfolio_backups/
│   ├── substack_posts/
│   ├── grok_prompts/
│   ├── portfolio.csv
│   ├── signals.json
│   └── content_queue.json
│
├── # Core Pipeline (5 files)
├── scanner.py
├── thematic_analyzer.py
├── gatekeeper.py
├── portfolio_manager.py
├── dd_automator.py
│
├── # Content Generation (7 files)
├── tweet_generator.py
├── twitter_poster.py
├── newsletter_compiler.py
├── substack_notes_generator.py
├── substack_content_generator.py
├── grok_prompts_generator.py
├── market_analyzer.py
│
├── # Configuration (5 files)
├── config.py
├── output_paths.py
├── marketing_vocabulary.py
├── signal_tracker.py
├── self_quote_tracker.py
│
├── # Utilities (6 files)
├── chart_capture.py
├── funnel_graphic.py               # KEEP if used
├── winner_showcase_generator.py    # Part of new system
├── email_notifier.py
├── backup_cleanup.py
├── due_diligence.py                # CLI tool
│
├── # Setup/Orchestration (4 files)
├── setup_scheduler.py
├── tradingview_login.py
├── run_full_pipeline.py
├── run_friday.sh
├── run_local_friday.sh
│
├── # Root Config
├── .env                            # NOT in git
├── .env.example
├── .gitignore
├── requirements.txt
├── complete_tickers.txt
│
├── # Root Docs
├── README.md
├── CLAUDE.md
├── MASTER_TODO_v2.md
├── SYSTEM_OVERVIEW.md
└── SETUP.md
```

**File Count After Cleanup:**
- Python files: ~27 (active) + 7 (archived) = 34 total (unchanged)
- But **active codebase** is cleaner with orphans archived

---

## Summary of Actions

| Action | Files Affected | Risk |
|--------|----------------|------|
| Remove .env from git | 1 | LOW (file stays local) |
| Delete old versions | 2 | NONE |
| Delete unused demo | 1 | NONE |
| Archive orphaned files | 7 | LOW (can restore) |
| Reorganize docs | 3-5 | NONE |
| Add gitignore entries | 2 | NONE |

**Total files removed from active codebase:** 10  
**Files permanently deleted:** 3  
**Files archived (recoverable):** 7

---

## Next Steps After Cleanup

1. ✅ Run cleanup script
2. ✅ Verify all imports work
3. ✅ Rotate API keys
4. ✅ Push changes
5. ➡️ Proceed with system improvements (implementation prompt)
