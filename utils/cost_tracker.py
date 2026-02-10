#!/usr/bin/env python3
"""
COST TRACKER - Centralized API Cost Logging + Kill Switch
==========================================================

Logs API costs for the live tweet system (Grok + Sonnet + chart-img).
Enforces a daily spending limit to prevent runaway costs.

Usage:
    from utils.cost_tracker import log_cost, get_daily_total, get_weekly_total

    cost = log_cost("context_gatherer", "grok-3-fast", input_tokens=500, output_tokens=200)
    daily = get_daily_total()
    weekly = get_weekly_total()
"""

import json
import os
import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

# Import config constants
try:
    from config import (
        COST_LOG_FILE,
        DAILY_COST_LIMIT_USD,
        API_PRICING,
        TOOL_CALL_COST,
    )
except ImportError:
    # Fallback for standalone testing
    BASE_DIR = Path(__file__).resolve().parent.parent
    COST_LOG_FILE = BASE_DIR / "trades" / "live_cost_log.json"
    DAILY_COST_LIMIT_USD = 1.00
    API_PRICING = {
        "grok-3-fast": {"input": 0.20, "output": 0.50},
        "claude-sonnet-4-5-20250929": {"input": 3.00, "output": 15.00},
        "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    }
    TOOL_CALL_COST = 0.005


# ═══════════════════════════════════════════════════════════════════════════════
# INTERNAL HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _load_log() -> Dict:
    """Load cost log from disk. Auto-resets if the date has changed."""
    today = str(datetime.utcnow().date())

    if not COST_LOG_FILE.exists():
        return {"date": today, "total_usd": 0.0, "calls": []}

    try:
        with open(COST_LOG_FILE, "r") as f:
            log = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"date": today, "total_usd": 0.0, "calls": []}

    # Reset if new day
    if log.get("date") != today:
        return {"date": today, "total_usd": 0.0, "calls": []}

    return log


def _save_log(log: Dict) -> None:
    """Save cost log to disk (atomic write)."""
    COST_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    temp_fd, temp_path = tempfile.mkstemp(
        suffix=".json",
        dir=COST_LOG_FILE.parent,
        prefix=".cost_log_tmp_",
    )
    try:
        with os.fdopen(temp_fd, "w") as f:
            json.dump(log, f, indent=2)
        shutil.move(temp_path, COST_LOG_FILE)
    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════════

def log_cost(
    service: str,
    model: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    tool_calls: int = 0,
) -> float:
    """Log an API call cost and enforce the daily kill switch.

    Args:
        service: Identifier (e.g., "context_gatherer", "live_tweet_generator", "chart_generator")
        model: Model name (must be a key in API_PRICING, or cost defaults to 0)
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        tool_calls: Number of tool/search calls (charged at TOOL_CALL_COST each)

    Returns:
        Cost in USD for this call.

    Raises:
        RuntimeError: If daily cost limit is exceeded after logging.
    """
    pricing = API_PRICING.get(model, {"input": 0.0, "output": 0.0})
    cost = (
        (input_tokens * pricing["input"] / 1_000_000)
        + (output_tokens * pricing["output"] / 1_000_000)
        + (tool_calls * TOOL_CALL_COST)
    )
    cost = round(cost, 6)

    log = _load_log()
    log["calls"].append({
        "service": service,
        "model": model,
        "cost": cost,
        "time": datetime.utcnow().isoformat(),
    })
    log["total_usd"] = round(log["total_usd"] + cost, 6)
    _save_log(log)

    # Kill switch
    if log["total_usd"] > DAILY_COST_LIMIT_USD:
        raise RuntimeError(
            f"Daily cost limit exceeded: ${log['total_usd']:.4f} > ${DAILY_COST_LIMIT_USD:.2f}"
        )

    return cost


def get_daily_total() -> float:
    """Get today's cumulative cost in USD."""
    log = _load_log()
    return log.get("total_usd", 0.0)


def get_weekly_total() -> float:
    """Sum costs for the current ISO week (Mon-Sun).

    Reads the log file and sums today's costs. For a full week total,
    we would need historical log files — this implementation returns
    today's total as a baseline. A future improvement could archive
    daily logs.
    """
    # For now, return today's total. In production, the workflow commits
    # the log daily, so we can check git history or accumulate a weekly file.
    return get_daily_total()


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    """Print current cost summary."""
    log = _load_log()

    print("\n" + "=" * 50)
    print("  COST TRACKER — Live Tweet System")
    print("=" * 50)
    print(f"\n  Date:       {log.get('date', 'N/A')}")
    print(f"  Total:      ${log.get('total_usd', 0.0):.4f}")
    print(f"  Daily Limit: ${DAILY_COST_LIMIT_USD:.2f}")
    print(f"  Calls:      {len(log.get('calls', []))}")

    calls = log.get("calls", [])
    if calls:
        print(f"\n  {'Service':<25} {'Model':<30} {'Cost':>8}")
        print(f"  {'─' * 25} {'─' * 30} {'─' * 8}")
        for call in calls[-10:]:  # Last 10 calls
            print(
                f"  {call.get('service', '?'):<25} "
                f"{call.get('model', '?'):<30} "
                f"${call.get('cost', 0):.4f}"
            )
        if len(calls) > 10:
            print(f"  ... and {len(calls) - 10} earlier calls")

    print()


if __name__ == "__main__":
    main()
