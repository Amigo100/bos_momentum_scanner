#!/usr/bin/env python3
"""
REMINDER SETUP - Timed Substack Posting Reminders
==================================================

Sets up macOS launchd plists that send reminder emails at posting times.
Each reminder emails the specific HTML file you need to paste into Substack.

Creates 3 plists in ~/Library/LaunchAgents/:
  com.sterling.reminder.morning.plist  → 07:45 AEDT (15 min before 08:00 post)
  com.sterling.reminder.midday.plist   → 11:45 AEDT (15 min before 12:00 post)
  com.sterling.reminder.evening.plist  → 19:45 AEDT (15 min before 20:00 post)

Each runs: python3 -m scripts.send_slot_reminder --slot {slot}

Times are 15 minutes BEFORE the posting time so you have time to paste.

Usage:
    python3 -m scripts.setup_reminders install      # Install all 3 reminders
    python3 -m scripts.setup_reminders uninstall     # Remove all 3 reminders
    python3 -m scripts.setup_reminders status        # Check status
    python3 -m scripts.setup_reminders test morning  # Test a specific slot
    python3 -m scripts.setup_reminders test          # Test all slots

IMPORTANT:
    Your Mac must be ON and AWAKE at the scheduled times for reminders to fire.
    If your Mac is asleep, the reminder will be SKIPPED (not queued).
"""

import os
import plistlib
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

PROJECT_DIR = Path(__file__).resolve().parent.parent
PYTHON_PATH = sys.executable

PLIST_BASE = "com.sterling.reminder"
PLIST_DIR = Path.home() / "Library" / "LaunchAgents"
LOG_DIR = Path.home() / "Library" / "Logs"

# Reminder schedule: 15 minutes before each posting slot
# Times are in LOCAL time (AEDT — Australia/Sydney)
SLOTS = {
    "morning": {
        "hour": 7,
        "minute": 45,
        "post_time": "08:00 AEDT",
        "description": "Morning note reminder",
    },
    "midday": {
        "hour": 11,
        "minute": 45,
        "post_time": "12:00 AEDT",
        "description": "Midday note/post reminder",
    },
    "evening": {
        "hour": 19,
        "minute": 45,
        "post_time": "20:00 AEDT",
        "description": "Evening note reminder",
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# WRAPPER SCRIPT
# ═══════════════════════════════════════════════════════════════════════════════


def _create_wrapper_script(slot: str) -> Path:
    """Create a shell wrapper that sets up the environment and runs the reminder."""
    wrapper_path = PROJECT_DIR / f"run_reminder_{slot}.sh"

    # Detect shell profile
    shell = os.environ.get("SHELL", "/bin/zsh")
    profile = "~/.zshrc" if "zsh" in shell else "~/.bash_profile"

    env_file = PROJECT_DIR / ".env"

    script_content = f"""#!/bin/bash
# Sterling Signals — {slot.title()} Reminder Wrapper
# Called by launchd to send the {slot} posting reminder

# Source shell profile for PATH and environment variables
source {profile} 2>/dev/null || true

# Load .env file if present
if [ -f "{env_file}" ]; then
    set -a
    source "{env_file}"
    set +a
fi

# Change to project directory
cd "{PROJECT_DIR}"

# Run the reminder
"{PYTHON_PATH}" -m scripts.send_slot_reminder --slot {slot} >> "{LOG_DIR}/sterling_reminder_{slot}.log" 2>&1
"""

    with open(wrapper_path, "w") as f:
        f.write(script_content)

    # Owner-only permissions
    wrapper_path.chmod(0o700)
    return wrapper_path


# ═══════════════════════════════════════════════════════════════════════════════
# PLIST MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════


def _plist_path(slot: str) -> Path:
    """Get the plist file path for a slot."""
    return PLIST_DIR / f"{PLIST_BASE}.{slot}.plist"


def _create_plist(slot: str) -> Path:
    """Create a launchd plist for a specific slot."""
    config = SLOTS[slot]
    wrapper = _create_wrapper_script(slot)
    plist_file = _plist_path(slot)

    plist_content = {
        "Label": f"{PLIST_BASE}.{slot}",
        "ProgramArguments": ["/bin/bash", str(wrapper)],
        "StartCalendarInterval": {
            "Hour": config["hour"],
            "Minute": config["minute"],
        },
        "WorkingDirectory": str(PROJECT_DIR),
        "StandardOutPath": str(LOG_DIR / f"sterling_reminder_{slot}.log"),
        "StandardErrorPath": str(LOG_DIR / f"sterling_reminder_{slot}.log"),
        "RunAtLoad": False,
    }

    PLIST_DIR.mkdir(parents=True, exist_ok=True)

    with open(plist_file, "wb") as f:
        plistlib.dump(plist_content, f)

    return plist_file


def _load_plist(slot: str) -> bool:
    """Load a plist into launchd. Returns True on success."""
    plist_file = _plist_path(slot)
    try:
        subprocess.run(
            ["launchctl", "load", str(plist_file)],
            check=True,
            capture_output=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def _unload_plist(slot: str) -> bool:
    """Unload a plist from launchd. Returns True on success."""
    plist_file = _plist_path(slot)
    if not plist_file.exists():
        return False
    try:
        subprocess.run(
            ["launchctl", "unload", str(plist_file)],
            check=True,
            capture_output=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def _is_loaded(slot: str) -> bool:
    """Check if a plist is currently loaded in launchd."""
    label = f"{PLIST_BASE}.{slot}"
    result = subprocess.run(
        ["launchctl", "list", label],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


# ═══════════════════════════════════════════════════════════════════════════════
# COMMANDS
# ═══════════════════════════════════════════════════════════════════════════════


def install():
    """Install all 3 reminder plists."""
    print("\n" + "=" * 60)
    print("  INSTALLING POSTING REMINDERS")
    print("=" * 60 + "\n")

    for slot, config in SLOTS.items():
        print(f"  [{slot.upper()}]")

        # Unload existing if present
        if _plist_path(slot).exists():
            _unload_plist(slot)

        # Create plist
        plist = _create_plist(slot)
        print(f"    ✓ Created plist: {plist.name}")

        # Create wrapper
        wrapper = PROJECT_DIR / f"run_reminder_{slot}.sh"
        print(f"    ✓ Created wrapper: {wrapper.name}")

        # Load
        if _load_plist(slot):
            print(f"    ✓ Loaded into launchd")
        else:
            print(f"    ✗ Failed to load — try: launchctl load {plist}")

        print(f"    → Fires at {config['hour']:02d}:{config['minute']:02d} local time")
        print(f"    → Reminds you to post at {config['post_time']}")
        print()

    print(f"""
╔════════════════════════════════════════════════════════════╗
║                  REMINDERS INSTALLED                       ║
╚════════════════════════════════════════════════════════════╝

  Schedule (15 min before each posting slot):
    📋 07:45 → Morning note    (post at 08:00 AEDT)
    📋 11:45 → Midday note     (post at 12:00 AEDT)
    📋 19:45 → Evening note    (post at 20:00 AEDT)

  Each reminder emails:
    • Subject line with slot + content type
    • The HTML file attached for copy/paste
    • Instructions for posting

  IMPORTANT:
    • Mac must be ON and AWAKE at scheduled times
    • If asleep, the reminder will be SKIPPED
    • Content must be generated first (run Cowork)

  COMMANDS:
    python3 -m scripts.setup_reminders status      # Check status
    python3 -m scripts.setup_reminders test morning # Test one slot
    python3 -m scripts.setup_reminders uninstall    # Remove all

  LOGS:
    ~/Library/Logs/sterling_reminder_morning.log
    ~/Library/Logs/sterling_reminder_midday.log
    ~/Library/Logs/sterling_reminder_evening.log
""")


def uninstall():
    """Remove all 3 reminder plists and wrapper scripts."""
    print("\n" + "=" * 60)
    print("  UNINSTALLING POSTING REMINDERS")
    print("=" * 60 + "\n")

    for slot in SLOTS:
        # Unload
        if _unload_plist(slot):
            print(f"  ✓ Unloaded {slot}")
        else:
            print(f"  ℹ {slot} was not loaded")

        # Remove plist
        plist = _plist_path(slot)
        if plist.exists():
            plist.unlink()
            print(f"  ✓ Removed {plist.name}")

        # Remove wrapper
        wrapper = PROJECT_DIR / f"run_reminder_{slot}.sh"
        if wrapper.exists():
            wrapper.unlink()
            print(f"  ✓ Removed {wrapper.name}")

    print("\n  All reminders removed.\n")


def status():
    """Check status of all 3 reminder plists."""
    print("\n" + "=" * 60)
    print("  REMINDER STATUS")
    print("=" * 60 + "\n")

    any_installed = False
    for slot, config in SLOTS.items():
        plist = _plist_path(slot)
        installed = plist.exists()
        loaded = _is_loaded(slot) if installed else False

        if installed:
            any_installed = True
            if loaded:
                icon = "✓"
                state = "Active"
            else:
                icon = "⚠"
                state = "Installed but NOT loaded"
        else:
            icon = "✗"
            state = "Not installed"

        print(f"  {icon} {slot.upper():10s} {config['hour']:02d}:{config['minute']:02d} → post at {config['post_time']:10s} [{state}]")

        # Check recent log
        log = LOG_DIR / f"sterling_reminder_{slot}.log"
        if log.exists():
            mtime = datetime.fromtimestamp(log.stat().st_mtime)
            print(f"    Last log: {mtime.strftime('%Y-%m-%d %H:%M')}")

    if not any_installed:
        print("\n  No reminders installed.")
        print("  Run: python3 -m scripts.setup_reminders install")

    print()


def test(slot=None):
    """Test reminder(s) by running them immediately."""
    slots_to_test = [slot] if slot else list(SLOTS.keys())

    print("\n" + "=" * 60)
    print("  TESTING REMINDER(S)")
    print("=" * 60 + "\n")

    for s in slots_to_test:
        if s not in SLOTS:
            print(f"  Unknown slot: {s}")
            print(f"  Valid slots: morning, midday, evening")
            continue

        print(f"  Testing {s}...")
        result = subprocess.run(
            [PYTHON_PATH, "-m", "scripts.send_slot_reminder", "--slot", s],
            cwd=str(PROJECT_DIR),
        )

        if result.returncode == 0:
            print(f"  ✓ {s} test passed\n")
        else:
            print(f"  ✗ {s} test failed (exit code {result.returncode})\n")


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════


def print_usage():
    print("""
Reminder Setup — Timed Substack Posting Reminders
==================================================

Usage:
  python3 -m scripts.setup_reminders install           # Install all 3 reminders
  python3 -m scripts.setup_reminders uninstall          # Remove all 3 reminders
  python3 -m scripts.setup_reminders status             # Check status
  python3 -m scripts.setup_reminders test               # Test all slots
  python3 -m scripts.setup_reminders test morning       # Test specific slot

Schedule (fires 15 min before posting time):
  07:45 local → Morning note    (post at 08:00 AEDT)
  11:45 local → Midday note     (post at 12:00 AEDT)
  19:45 local → Evening note    (post at 20:00 AEDT)

Each reminder:
  • Reads today's daily_manifest.json
  • Finds the file for the matching slot
  • Emails it with the HTML attached
  • Subject line tells you exactly what to post

Prerequisites:
  • Cowork must have run today (generates manifest + files)
  • Email must be configured (SMTP settings in .env)
  • Mac must be awake at scheduled times
""")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(0)

    command = sys.argv[1].lower()

    if command == "install":
        install()
    elif command == "uninstall":
        uninstall()
    elif command == "status":
        status()
    elif command == "test":
        slot_arg = sys.argv[2].lower() if len(sys.argv) >= 3 else None
        test(slot_arg)
    else:
        print_usage()
