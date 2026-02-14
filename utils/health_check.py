#!/usr/bin/env python3
"""
HEALTH CHECK - Live Tweet System Diagnostics
==============================================

Probes all external APIs and system components used by the live tweet system.
Reports pass/fail status for each service.

Usage:
    python -m utils.health_check            # Run all checks
    python -m utils.health_check --quiet    # Only show failures

Exit Codes:
    0 — All critical checks passed
    1 — One or more critical checks failed
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict

# Import config
try:
    from config import (
        TRADES_DIR,
        TWITTER_ACCOUNTS,
        COST_LOG_FILE,
        DAILY_COST_LIMIT_USD,
        MONTHLY_COST_LIMIT_USD,
        XAI_BASE_URL,
        MODEL_CONTEXT,
        MODEL_LIVE_TWEET,
        CHARTIMG_API_URL,
        CHART_IMG_WIDTH,
        CHART_IMG_HEIGHT,
    )
except ImportError:
    BASE_DIR = Path(__file__).resolve().parent.parent
    TRADES_DIR = BASE_DIR / "trades"
    TWITTER_ACCOUNTS = {"main": {"env_prefix": "X1"}}
    COST_LOG_FILE = TRADES_DIR / "live_cost_log.json"
    DAILY_COST_LIMIT_USD = 1.00
    MONTHLY_COST_LIMIT_USD = 30.00
    XAI_BASE_URL = "https://api.x.ai/v1"
    MODEL_CONTEXT = "grok-4-fast-non-reasoning"
    MODEL_LIVE_TWEET = "claude-sonnet-4-5-20250929"
    CHARTIMG_API_URL = "https://api.chart-img.com/v1/tradingview/advanced-chart"
    CHART_IMG_WIDTH = 1200
    CHART_IMG_HEIGHT = 675


# ═══════════════════════════════════════════════════════════════════════════════
# INDIVIDUAL CHECKS
# ═══════════════════════════════════════════════════════════════════════════════

def check_xai_api() -> Dict:
    """Test xAI Grok API connectivity with a minimal prompt."""
    api_key = os.environ.get("XAI_API_KEY")
    if not api_key:
        return {"status": "fail", "detail": "XAI_API_KEY not set"}

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=XAI_BASE_URL)
        response = client.chat.completions.create(
            model=MODEL_CONTEXT,
            messages=[{"role": "user", "content": "Say OK"}],
            max_tokens=5,
        )
        text = response.choices[0].message.content.strip() if response.choices else ""
        return {"status": "pass", "detail": f"{MODEL_CONTEXT} responding ({text})"}
    except ImportError:
        return {"status": "fail", "detail": "openai package not installed"}
    except Exception as e:
        return {"status": "fail", "detail": str(e)[:100]}


def check_anthropic_api() -> Dict:
    """Test Anthropic Claude API connectivity with a minimal prompt."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {"status": "fail", "detail": "ANTHROPIC_API_KEY not set"}

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=MODEL_LIVE_TWEET,
            max_tokens=5,
            messages=[{"role": "user", "content": "Say OK"}],
        )
        text = response.content[0].text.strip() if response.content else ""
        return {"status": "pass", "detail": f"{MODEL_LIVE_TWEET} responding ({text})"}
    except ImportError:
        return {"status": "fail", "detail": "anthropic package not installed"}
    except Exception as e:
        return {"status": "fail", "detail": str(e)[:100]}


def check_x_api(account_key: str) -> Dict:
    """Test X/Twitter API credentials for a given account."""
    try:
        from config import TWITTER_ACCOUNTS
        account = TWITTER_ACCOUNTS.get(account_key, TWITTER_ACCOUNTS.get("main", {}))
        prefix = account.get("env_prefix", "X1")
    except (ImportError, KeyError):
        prefix = "X1" if account_key == "main" else f"X{account_key[-1]}"

    api_key = os.environ.get(f"{prefix}_API_KEY")
    api_secret = os.environ.get(f"{prefix}_API_SECRET")
    access_token = os.environ.get(f"{prefix}_ACCESS_TOKEN")
    access_secret = os.environ.get(f"{prefix}_ACCESS_SECRET")

    missing = []
    if not api_key:
        missing.append(f"{prefix}_API_KEY")
    if not api_secret:
        missing.append(f"{prefix}_API_SECRET")
    if not access_token:
        missing.append(f"{prefix}_ACCESS_TOKEN")
    if not access_secret:
        missing.append(f"{prefix}_ACCESS_SECRET")

    if missing:
        return {"status": "fail", "detail": f"Missing: {', '.join(missing)}"}

    try:
        import tweepy
        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_secret,
        )
        me = client.get_me()
        username = me.data.username if me.data else "?"
        return {"status": "pass", "detail": f"@{username}"}
    except ImportError:
        return {"status": "fail", "detail": "tweepy package not installed"}
    except Exception as e:
        return {"status": "fail", "detail": str(e)[:100]}


def check_chartimg_api() -> Dict:
    """Test chart-img.com API connectivity."""
    api_key = os.environ.get("CHARTIMG_API_KEY")
    if not api_key:
        return {"status": "warn", "detail": "CHARTIMG_API_KEY not set (charts disabled)"}

    try:
        import requests
        response = requests.get(
            CHARTIMG_API_URL,
            params={
                "key": api_key,
                "symbol": "NASDAQ:AAPL",
                "interval": "1D",
                "width": 320,
                "height": 220,
            },
            timeout=30,
        )
        if response.status_code == 200 and "image" in response.headers.get("Content-Type", ""):
            return {"status": "pass", "detail": "chart-img.com responding"}
        else:
            return {"status": "fail", "detail": f"HTTP {response.status_code}"}
    except ImportError:
        return {"status": "warn", "detail": "requests package not installed"}
    except Exception as e:
        return {"status": "fail", "detail": str(e)[:100]}


def check_tv_session() -> Dict:
    """Test TradingView session validity via chart-img.com."""
    layout_id = os.environ.get("TRADINGVIEW_LAYOUT_ID")
    session = os.environ.get("TRADINGVIEW_SESSION")

    if not layout_id or not session:
        return {"status": "warn", "detail": "No TradingView session configured (using default layout)"}

    api_key = os.environ.get("CHARTIMG_API_KEY")
    if not api_key:
        return {"status": "warn", "detail": "CHARTIMG_API_KEY not set (cannot test TV session)"}

    try:
        import requests
        response = requests.get(
            f"{CHARTIMG_API_URL}/storage",
            params={
                "key": api_key,
                "layout": layout_id,
                "symbol": "NASDAQ:AAPL",
                "interval": "1D",
                "width": 200,
                "height": 150,
                "session": session,
            },
            timeout=15,
        )
        if response.status_code == 200 and "image" in response.headers.get("Content-Type", ""):
            return {"status": "pass", "detail": "TradingView session valid"}
        else:
            return {"status": "fail", "detail": f"HTTP {response.status_code} — session may be expired"}
    except Exception as e:
        return {"status": "fail", "detail": str(e)[:100]}


def check_portfolio_freshness() -> Dict:
    """Check if portfolio.csv was modified within the last 10 days."""
    portfolio_path = TRADES_DIR / "portfolio.csv"

    if not portfolio_path.exists():
        return {"status": "fail", "detail": "portfolio.csv not found"}

    try:
        mtime = datetime.fromtimestamp(portfolio_path.stat().st_mtime)
        age_days = (datetime.now() - mtime).days

        if age_days <= 3:
            return {"status": "pass", "detail": f"Modified {age_days} day(s) ago"}
        elif age_days <= 10:
            return {"status": "warn", "detail": f"Modified {age_days} days ago — may be stale"}
        else:
            return {"status": "fail", "detail": f"Modified {age_days} days ago — likely stale"}
    except Exception as e:
        return {"status": "fail", "detail": str(e)[:100]}


def get_weekly_cost() -> Dict:
    """Report cost tracking status."""
    try:
        from utils.cost_tracker import get_daily_total
        daily = get_daily_total()
        return {
            "status": "pass",
            "detail": f"${daily:.4f} today / ${DAILY_COST_LIMIT_USD:.2f} limit",
        }
    except ImportError:
        return {"status": "warn", "detail": "cost_tracker not available"}
    except Exception as e:
        return {"status": "warn", "detail": str(e)[:100]}


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def run_health_checks() -> Dict[str, Dict]:
    """Run all health checks and return unified results.

    Returns:
        Dict mapping check name to {"status": "pass"|"warn"|"fail", "detail": str}
    """
    results = {}

    # Critical checks (affect exit code)
    results["xai_api"] = check_xai_api()
    results["anthropic_api"] = check_anthropic_api()
    results["x_api_main"] = check_x_api("main")

    # Secondary checks (warnings only)
    results["x_api_account2"] = check_x_api("account2")
    results["x_api_account3"] = check_x_api("account3")
    results["chartimg_api"] = check_chartimg_api()
    results["tv_session"] = check_tv_session()
    results["portfolio"] = check_portfolio_freshness()
    results["cost_tracking"] = get_weekly_cost()

    return results


CRITICAL_CHECKS = {"xai_api", "anthropic_api", "x_api_main"}


def main() -> int:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Sterling Signals Health Check")
    parser.add_argument("--quiet", "-q", action="store_true", help="Only show failures")
    args = parser.parse_args()

    print("\n" + "=" * 55)
    print("  STERLING SIGNALS — HEALTH CHECK")
    print("=" * 55 + "\n")

    results = run_health_checks()

    # Display results
    status_icons = {"pass": "PASS", "warn": "WARN", "fail": "FAIL"}
    status_colors = {"pass": "✅", "warn": "⚠️ ", "fail": "❌"}

    critical_failures = 0

    for name, result in results.items():
        status = result.get("status", "fail")
        detail = result.get("detail", "")
        icon = status_colors.get(status, "?")
        label = status_icons.get(status, "?")

        if args.quiet and status == "pass":
            continue

        is_critical = name in CRITICAL_CHECKS
        marker = " [CRITICAL]" if is_critical and status == "fail" else ""
        print(f"  {icon} {name:<22} {label:<5} {detail}{marker}")

        if is_critical and status == "fail":
            critical_failures += 1

    print()

    if critical_failures > 0:
        print(f"  ❌ {critical_failures} critical check(s) FAILED")
        print("     Fix these before running the live tweet system.\n")
        return 1
    else:
        total_pass = sum(1 for r in results.values() if r["status"] == "pass")
        total_warn = sum(1 for r in results.values() if r["status"] == "warn")
        print(f"  ✅ All critical checks passed ({total_pass} pass, {total_warn} warn)")
        print()
        return 0


if __name__ == "__main__":
    sys.exit(main())
