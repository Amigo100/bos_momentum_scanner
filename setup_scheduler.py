#!/usr/bin/env python3
"""
SCHEDULER SETUP - Automated Weekly Scans
=========================================

This script sets up automated WEEKLY scans after the weekly candle closes.

WEEKLY TIMEFRAME LOGIC:
- Weekly candles close Friday at US market close (4:00 PM ET)
- HMA Pivot signals can only change once per week
- Running daily would give identical results and waste API budget
- Best time to scan: Sunday evening (data settled, ready for Monday open)

Default schedule: Sunday at 9:30 PM local time
- Gives you signals Sunday night
- Ready to act Monday at market open

IMPORTANT NOTES:
----------------
1. Your laptop MUST be ON at the scheduled time for the scan to run
2. If your laptop is asleep/off, the scan will be SKIPPED (not queued)
3. macOS will run missed tasks when you wake up IF you use launchd (not cron)

Usage:
    python setup_scheduler.py install    # Install weekly schedule (Sunday 9:30 PM)
    python setup_scheduler.py uninstall  # Remove schedule
    python setup_scheduler.py status     # Check if installed
    python setup_scheduler.py test       # Run a test scan now
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime
import getpass
import plistlib

# Configuration
SCANNER_DIR = Path(__file__).resolve().parent
SCANNER_SCRIPT = SCANNER_DIR / "scanner.py"
PLIST_NAME = "com.bos.momentum.scanner"
PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / f"{PLIST_NAME}.plist"

# Default schedule: Sunday at 9:30 PM (21:30) - ready for Monday open
DEFAULT_WEEKDAY = 0  # 0 = Sunday, 1 = Monday, etc.
DEFAULT_HOUR = 21
DEFAULT_MINUTE = 30

WEEKDAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]


def get_python_path():
    """Get the path to the Python interpreter."""
    return sys.executable


def get_api_key():
    """Get the Anthropic API key from environment or prompt."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("\n⚠ ANTHROPIC_API_KEY not found in environment")
        print("The scheduler needs this to run the LLM sector filter.")
        api_key = input("Enter your Anthropic API key (or press Enter to skip LLM): ").strip()
    return api_key


def create_wrapper_script():
    """Create a wrapper script that sets up the environment."""
    wrapper_path = SCANNER_DIR / "run_scanner.sh"
    api_key = get_api_key()
    python_path = get_python_path()
    
    # Get shell profile to source
    shell = os.environ.get("SHELL", "/bin/zsh")
    if "zsh" in shell:
        profile = "~/.zshrc"
    else:
        profile = "~/.bash_profile"
    
    script_content = f"""#!/bin/bash
# BoS Momentum Scanner - Wrapper Script
# This script is called by launchd to run the scanner

# Source shell profile to get PATH and other settings
source {profile} 2>/dev/null || true

# Set API key
export ANTHROPIC_API_KEY="{api_key}"

# Change to scanner directory
cd "{SCANNER_DIR}"

# Create log directory if needed
mkdir -p logs

# Run scanner and log output
LOG_FILE="logs/scan_$(date +%Y-%m-%d_%H%M).log"
echo "=== Scanner started at $(date) ===" >> "$LOG_FILE"

"{python_path}" "{SCANNER_SCRIPT}" >> "$LOG_FILE" 2>&1

echo "=== Scanner finished at $(date) ===" >> "$LOG_FILE"
"""
    
    with open(wrapper_path, 'w') as f:
        f.write(script_content)
    
    wrapper_path.chmod(0o755)
    print(f"  ✓ Created wrapper script: {wrapper_path}")
    return wrapper_path


def create_launchd_plist(weekday: int = DEFAULT_WEEKDAY, hour: int = DEFAULT_HOUR, minute: int = DEFAULT_MINUTE):
    """Create a launchd plist for weekly scheduled execution."""
    wrapper_path = create_wrapper_script()
    
    plist_content = {
        "Label": PLIST_NAME,
        "ProgramArguments": ["/bin/bash", str(wrapper_path)],
        "StartCalendarInterval": {
            "Weekday": weekday,  # 0 = Sunday, 1 = Monday, etc.
            "Hour": hour,
            "Minute": minute,
        },
        "WorkingDirectory": str(SCANNER_DIR),
        "StandardOutPath": str(SCANNER_DIR / "logs" / "launchd_stdout.log"),
        "StandardErrorPath": str(SCANNER_DIR / "logs" / "launchd_stderr.log"),
        "RunAtLoad": False,  # Don't run immediately on load
    }
    
    # Ensure LaunchAgents directory exists
    PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    with open(PLIST_PATH, 'wb') as f:
        plistlib.dump(plist_content, f)
    
    print(f"  ✓ Created launchd plist: {PLIST_PATH}")
    return PLIST_PATH


def install(weekday: int = DEFAULT_WEEKDAY, hour: int = DEFAULT_HOUR, minute: int = DEFAULT_MINUTE):
    """Install the weekly scheduled task."""
    print("\n" + "=" * 60)
    print("INSTALLING WEEKLY SCHEDULED SCANNER")
    print("=" * 60)
    
    # Check if already installed
    if PLIST_PATH.exists():
        print(f"\n⚠ Schedule already exists at {PLIST_PATH}")
        response = input("Replace it? (y/n): ").strip().lower()
        if response != 'y':
            print("Cancelled.")
            return
        uninstall(quiet=True)
    
    # Create plist
    day_name = WEEKDAY_NAMES[weekday]
    print(f"\nScheduling weekly scan for {day_name} at {hour:02d}:{minute:02d} (local time)")
    create_launchd_plist(weekday, hour, minute)
    
    # Load the plist
    try:
        subprocess.run(["launchctl", "load", str(PLIST_PATH)], check=True)
        print(f"  ✓ Loaded into launchd")
    except subprocess.CalledProcessError as e:
        print(f"  ✗ Failed to load: {e}")
        return
    
    print(f"""
╔══════════════════════════════════════════════════════════════════╗
║                    INSTALLATION COMPLETE                         ║
╚══════════════════════════════════════════════════════════════════╝

  Schedule: Every {day_name} at {hour:02d}:{minute:02d} (local time)
  
  WHY WEEKLY?
  ────────────────────────────────────────────────────────────────
  • This is a WEEKLY timeframe scanner
  • Signals only change when weekly candle closes (Friday)
  • Running daily would give identical results & waste API budget
  • Sunday night = ready for Monday market open
  
  ESTIMATED COST: ~$0.85/week = ~$3.40/month = ~$44/year
  
  IMPORTANT:
  ────────────────────────────────────────────────────────────────
  • Laptop MUST be ON and AWAKE at {hour:02d}:{minute:02d} on {day_name}s
  • If laptop is asleep/off, the scan will be SKIPPED
  • Logs saved to: {SCANNER_DIR}/logs/
  
  TO TEST NOW:
    python setup_scheduler.py test
  
  TO CHECK STATUS:
    python setup_scheduler.py status
  
  TO UNINSTALL:
    python setup_scheduler.py uninstall

""")


def uninstall(quiet=False):
    """Remove the scheduled task."""
    if not quiet:
        print("\n" + "=" * 60)
        print("UNINSTALLING SCHEDULED SCANNER")
        print("=" * 60)
    
    if not PLIST_PATH.exists():
        if not quiet:
            print("  No schedule found to uninstall.")
        return
    
    # Unload from launchd
    try:
        subprocess.run(["launchctl", "unload", str(PLIST_PATH)], 
                      check=True, capture_output=True)
        if not quiet:
            print("  ✓ Unloaded from launchd")
    except:
        pass
    
    # Remove plist file
    PLIST_PATH.unlink(missing_ok=True)
    if not quiet:
        print(f"  ✓ Removed {PLIST_PATH}")
    
    # Remove wrapper script
    wrapper = SCANNER_DIR / "run_scanner.sh"
    wrapper.unlink(missing_ok=True)
    if not quiet:
        print(f"  ✓ Removed wrapper script")
        print("\n  Schedule removed successfully.")


def status():
    """Check scheduler status."""
    print("\n" + "=" * 60)
    print("SCHEDULER STATUS")
    print("=" * 60)
    
    if not PLIST_PATH.exists():
        print("\n  ✗ Not installed")
        print("  Run: python setup_scheduler.py install")
        return
    
    # Check if loaded
    result = subprocess.run(
        ["launchctl", "list", PLIST_NAME],
        capture_output=True, text=True
    )
    
    if result.returncode == 0:
        print(f"\n  ✓ Installed and active")
    else:
        print(f"\n  ⚠ Installed but not loaded")
        print("  Try: launchctl load ~/Library/LaunchAgents/com.bos.momentum.scanner.plist")
    
    # Read schedule from plist
    try:
        with open(PLIST_PATH, 'rb') as f:
            plist = plistlib.load(f)
        
        schedule = plist.get("StartCalendarInterval", {})
        weekday = schedule.get("Weekday")
        hour = schedule.get("Hour", "??")
        minute = schedule.get("Minute", "??")
        
        if weekday is not None:
            day_name = WEEKDAY_NAMES[weekday]
            print(f"  Schedule: Every {day_name} at {hour:02d}:{minute:02d} (local time)")
        else:
            print(f"  Schedule: Daily at {hour:02d}:{minute:02d} (local time)")
            print(f"  ⚠ Consider reinstalling for weekly schedule (saves API costs)")
    except:
        pass
    
    print(f"  Plist: {PLIST_PATH}")
    print(f"  Logs:  {SCANNER_DIR}/logs/")
    
    # Check recent logs
    log_dir = SCANNER_DIR / "logs"
    if log_dir.exists():
        logs = sorted(log_dir.glob("scan_*.log"), reverse=True)[:3]
        if logs:
            print(f"\n  Recent scans:")
            for log in logs:
                mtime = datetime.fromtimestamp(log.stat().st_mtime)
                print(f"    {mtime.strftime('%Y-%m-%d %H:%M')} - {log.name}")


def test():
    """Run a test scan now."""
    print("\n" + "=" * 60)
    print("RUNNING TEST SCAN")
    print("=" * 60)
    print("\nThis will run the scanner now to verify everything works.\n")
    
    # Run scanner
    result = subprocess.run(
        [get_python_path(), str(SCANNER_SCRIPT)],
        cwd=str(SCANNER_DIR)
    )
    
    return result.returncode


def print_usage():
    """Print usage information."""
    print("""
Scheduler Setup - Automated Weekly Scans
=========================================

Usage:
  python setup_scheduler.py install              # Sunday 21:30 (default)
  python setup_scheduler.py install DAY          # Specific day at 21:30
  python setup_scheduler.py install DAY HH:MM    # Specific day and time
  python setup_scheduler.py uninstall            # Remove schedule
  python setup_scheduler.py status               # Check if installed
  python setup_scheduler.py test                 # Run scanner now

Days: sun, mon, tue, wed, thu, fri, sat (or full names)

Examples:
  python setup_scheduler.py install              # Sunday 21:30 (default)
  python setup_scheduler.py install sun 20:00    # Sunday 8:00 PM
  python setup_scheduler.py install monday 08:30 # Monday 8:30 AM

WHY WEEKLY?
  • This scanner uses WEEKLY timeframe signals
  • HMA Pivot signals only change when weekly candle closes (Friday)
  • Running daily gives identical results and wastes API budget
  • Cost: ~$0.85/week = ~$44/year

IMPORTANT:
  • Your laptop MUST be ON at the scheduled time
  • If laptop is asleep/off, the scan will be SKIPPED
  • Best day: Sunday (ready for Monday market open)
""")


def parse_weekday(day_str: str) -> int:
    """Parse weekday string to integer (0=Sunday, 6=Saturday)."""
    day_str = day_str.lower().strip()
    
    # Short names
    short_map = {"sun": 0, "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6}
    if day_str in short_map:
        return short_map[day_str]
    
    # Full names
    for i, name in enumerate(WEEKDAY_NAMES):
        if name.lower().startswith(day_str):
            return i
    
    raise ValueError(f"Unknown day: {day_str}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(0)
    
    command = sys.argv[1].lower()
    
    if command == "install":
        weekday = DEFAULT_WEEKDAY
        hour = DEFAULT_HOUR
        minute = DEFAULT_MINUTE
        
        # Parse optional arguments
        if len(sys.argv) >= 3:
            arg2 = sys.argv[2]
            
            # Check if it's a day or a time
            if ":" in arg2:
                # It's a time (HH:MM)
                try:
                    parts = arg2.split(":")
                    hour = int(parts[0])
                    minute = int(parts[1]) if len(parts) > 1 else 0
                except:
                    print(f"Invalid time format. Use HH:MM (e.g., 21:30)")
                    sys.exit(1)
            else:
                # It's a day
                try:
                    weekday = parse_weekday(arg2)
                except ValueError as e:
                    print(f"Invalid day: {arg2}")
                    print("Use: sun, mon, tue, wed, thu, fri, sat")
                    sys.exit(1)
                
                # Check for time in arg3
                if len(sys.argv) >= 4:
                    try:
                        parts = sys.argv[3].split(":")
                        hour = int(parts[0])
                        minute = int(parts[1]) if len(parts) > 1 else 0
                    except:
                        print(f"Invalid time format. Use HH:MM (e.g., 21:30)")
                        sys.exit(1)
        
        install(weekday, hour, minute)
    
    elif command == "uninstall":
        uninstall()
    
    elif command == "status":
        status()
    
    elif command == "test":
        test()
    
    else:
        print_usage()
