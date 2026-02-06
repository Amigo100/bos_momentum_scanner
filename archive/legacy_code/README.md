# Legacy Code Archive

**Archived:** 2026-01-27
**Reason:** These files were identified as orphaned during the codebase audit (not imported by any active code).

---

## Archived Files

| File | Lines | Original Purpose |
|------|-------|------------------|
| `data_models.py` | 610 | Dataclass definitions (superseded by inline definitions in scanner.py) |
| `prompt_templates.py` | 687 | LLM prompt templates (now inline in respective files) |
| `llm_client.py` | 574 | Anthropic API wrapper (now using direct API calls) |
| `logger.py` | 434 | Logging utilities (using standard logging module) |
| `data_loader.py` | 857 | Data loading utilities (functions moved to other files) |
| `newsletter_prompts.py` | 228 | Newsletter prompts (merged into newsletter_compiler.py) |
| `due_diligence_prompts.py` | 421 | DD prompts (merged into dd_automator.py) |

### Archived 2026-02-06 (Content System v2 Migration)

| File | Lines | Original Purpose |
|------|-------|------------------|
| `reaction_generator.py` | ~1700 | 3-persona tweet generation system (replaced by `content/tweet_generator.py` v2) |
| `tweet_generator.py` | ~1800 | Legacy tweet generator v1 (replaced by `content/tweet_generator.py` v2) |
| `editorial_board.py` | ~450 | Editorial planning for persona system (no longer needed) |
| `personas/alex.yaml` | ~150 | "Alex" persona voice configuration |
| `personas/james.yaml` | ~140 | "James" persona voice configuration |
| `personas/rozalia.yaml` | ~170 | "Rozalia" persona voice configuration |

---

## Why Archived (Not Deleted)

These files may contain useful code patterns, dataclass definitions, or prompt templates that could be referenced in the future. They are preserved here but excluded from the active codebase to reduce clutter.

**Verification Method:**
- No `import` statements reference these files in any active `.py` file
- No workflow (`.yml`) calls these files
- No shell script references these files

---

## Restoration

To restore any file to the active codebase:

```bash
mv archive/legacy_code/filename.py ./
```

To restore all files:

```bash
mv archive/legacy_code/*.py ./
```

---

## Related Audit

See `CODEBASE_AUDIT_REPORT.md` for the full audit that identified these files as orphaned.
