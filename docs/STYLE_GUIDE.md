# PYTHON STYLE GUIDE

**Exemplar files:** `output_paths.py`, `marketing_vocabulary.py`, `portfolio_manager.py`

---

## 1. File Structure

```python
#!/usr/bin/env python3
"""
MODULE NAME - Brief Description in Title Case
==============================================

What this module does in 2-3 sentences.

Usage:
    from module_name import main_function
    result = main_function(args)
"""

# Imports (see section 6)
# Constants (ALL_CAPS)
# Data structures (dataclasses/enums)
# Main class or functions
# CLI (if applicable)
# if __name__ == "__main__": block
```

Use `═══` section dividers for major sections, `───` for subsections within classes.

---

## 2. Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Files | `snake_case.py` | `portfolio_manager.py` |
| Classes | `PascalCase` | `PortfolioManager` |
| Functions | `snake_case` | `get_open_positions()` |
| Constants | `SCREAMING_SNAKE` | `TRAILING_STOP_PCT` |
| Private methods | `_leading_underscore` | `_load()`, `_save()` |
| Type aliases | `PascalCase` | `TradeList = List[Trade]` |

**Booleans:** Prefix with `is_`, `has_`, `can_`, `should_`

---

## 3. Type Hints

**Required on:**
- All public function signatures (parameters + return)
- Class attributes in dataclasses
- Module-level constants with non-obvious types

**Format:**
```python
def process_data(items: List[str], threshold: float = 0.5) -> Tuple[bool, List[str]]:
    """Process items and return (success, results)."""
```

**Use `Optional[]` explicitly** for nullable parameters:
```python
def fetch_price(ticker: str, fallback: Optional[float] = None) -> float:
```

---

## 4. Error Handling

**Pattern 1: Graceful degradation (preferred for non-critical)**
```python
try:
    result = risky_operation()
except SpecificException as e:
    print(f"  ⚠ Warning: {e}")
    result = fallback_value
```

**Pattern 2: Fail-fast (for critical operations)**
```python
if not required_file.exists():
    print(f"  ✗ Error: Required file not found: {required_file}")
    sys.exit(1)
```

**Pattern 3: Optional imports**
```python
try:
    import optional_package
    FEATURE_AVAILABLE = True
except ImportError:
    FEATURE_AVAILABLE = False
```

**Never:** Bare `except:` or `except Exception:` without logging.

---

## 5. Documentation

**Module docstring:** Always include purpose + usage example.

**Function docstring format:**
```python
def calculate_metrics(price: float, threshold: float = 0.0) -> Dict:
    """
    Calculate performance metrics for a given price.

    Args:
        price: Current market price
        threshold: Minimum threshold for alerts (default: 0.0)

    Returns:
        Dict with keys: 'pnl_pct', 'stop_level', 'alert'
    """
```

**When to skip docstrings:**
- Private methods (`_helper()`) with obvious purpose
- Simple getters/setters
- Methods under 3 lines with clear names

---

## 6. Import Organisation

```python
# Standard library
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# Third-party (alphabetical)
import pandas as pd
import yfinance as yf

# Local modules (alphabetical)
from marketing_vocabulary import validate_content
from output_paths import get_current_dir
```

Blank line between each group. Use `from x import y` for specific items, `import x` for namespaced access.

---

## 7. Configuration

**In-file constants** (for single-module config):
```python
TRAILING_STOP_PCT = 20.0
MODEL_NAME = "claude-sonnet-4-20250514"
```

**Environment variables** (for secrets):
```python
API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not API_KEY:
    print("Error: ANTHROPIC_API_KEY not set")
    sys.exit(1)
```

**Path configuration:**
```python
BASE_DIR = Path(__file__).resolve().parent
TRADES_DIR = BASE_DIR / "trades"
```

**Never:** Hardcode absolute paths, API keys, or passwords in source files.

---

## 8. Logging & Output

**User-facing output** (use print with indicators):
```python
print(f"  ✓ Success: Loaded {count} items")
print(f"  ⚠ Warning: File not found, using defaults")
print(f"  ✗ Error: Invalid configuration")
print(f"  ℹ Info: Processing {filename}...")
```

**Progress indicators** (for multi-step operations):
```python
print(f"\n  Step 1: Loading data...")
print(f"  Step 2: Processing...")
print(f"  ✓ Complete: {total} items processed")
```

**Debug output** (guard with verbose flag):
```python
if args.verbose:
    print(f"  DEBUG: {variable_name} = {value}")
```

---

## Quick Reference

| Do | Don't |
|----|-------|
| `Path(__file__).parent` | `os.path.dirname(__file__)` |
| `f"Value: {x}"` | `"Value: " + str(x)` |
| `if items:` | `if len(items) > 0:` |
| `x or default` | `x if x else default` |
| `@dataclass` | Manual `__init__` for data containers |
| `from typing import List` | `list` (for Python < 3.9 compat) |

---

**Enforcement:** Run `python -m py_compile filename.py` before committing.
