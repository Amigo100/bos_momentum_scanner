#!/usr/bin/env python3
"""
LOGGING CONFIG - Standardized Logging Setup
============================================

Provides consistent logging across all modules with:
- Console output with color-coded indicators
- Optional file output
- Structured log format

Usage:
    from src.common.logging_config import get_logger, log_step, log_success

    logger = get_logger(__name__)
    logger.info("Processing started")

    # Or use convenience functions
    log_step("Step 1: Loading data")
    log_success("Loaded 100 items")
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import TRADES_DIR


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

DEFAULT_LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_FILE_DIR = TRADES_DIR / "logs"

# Console indicators (from STYLE_GUIDE.md)
INDICATORS = {
    'success': '✓',
    'warning': '⚠',
    'error': '✗',
    'info': 'ℹ',
    'step': '→',
    'debug': '·',
}


# ═══════════════════════════════════════════════════════════════════════════════
# CUSTOM FORMATTERS
# ═══════════════════════════════════════════════════════════════════════════════

class ConsoleFormatter(logging.Formatter):
    """Custom formatter with colored level indicators."""

    COLORS = {
        'DEBUG': '\033[90m',      # Gray
        'INFO': '\033[0m',        # Default
        'WARNING': '\033[93m',    # Yellow
        'ERROR': '\033[91m',      # Red
        'CRITICAL': '\033[91;1m', # Bold Red
    }
    RESET = '\033[0m'

    def __init__(self, use_color: bool = True):
        super().__init__(LOG_FORMAT, LOG_DATE_FORMAT)
        self.use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        if self.use_color:
            color = self.COLORS.get(record.levelname, self.RESET)
            record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


class SimpleConsoleFormatter(logging.Formatter):
    """Simple formatter with indicators, no timestamps (for user-facing output)."""

    def format(self, record: logging.LogRecord) -> str:
        indicator = ''
        if record.levelno >= logging.ERROR:
            indicator = f"  {INDICATORS['error']} "
        elif record.levelno >= logging.WARNING:
            indicator = f"  {INDICATORS['warning']} "
        elif record.levelno >= logging.INFO:
            if hasattr(record, 'indicator'):
                indicator = f"  {record.indicator} "
            else:
                indicator = "  "
        else:
            indicator = f"  {INDICATORS['debug']} "

        return f"{indicator}{record.getMessage()}"


class FileFormatter(logging.Formatter):
    """Formatter for file output with full timestamps."""

    def __init__(self):
        super().__init__(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt=LOG_DATE_FORMAT
        )


# ═══════════════════════════════════════════════════════════════════════════════
# LOGGER FACTORY
# ═══════════════════════════════════════════════════════════════════════════════

_loggers: dict = {}


def get_logger(
    name: str,
    level: int = None,
    log_file: Optional[Path] = None,
    simple_format: bool = True,
    enable_file_logging: bool = False
) -> logging.Logger:
    """
    Get or create a logger with standard configuration.

    Args:
        name: Logger name (typically __name__)
        level: Log level (default: INFO)
        log_file: Specific file path for logging
        simple_format: Use simple format without timestamps (default: True)
        enable_file_logging: Enable automatic file logging (default: False)

    Returns:
        Configured Logger instance

    Example:
        logger = get_logger(__name__)
        logger.info("Starting process")
        logger.warning("Potential issue")
        logger.error("Failed operation")
    """
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)
    logger.setLevel(level or DEFAULT_LOG_LEVEL)

    # Prevent duplicate handlers
    if not logger.handlers:
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level or DEFAULT_LOG_LEVEL)

        if simple_format:
            console_handler.setFormatter(SimpleConsoleFormatter())
        else:
            console_handler.setFormatter(ConsoleFormatter())

        logger.addHandler(console_handler)

        # File handler (optional)
        if enable_file_logging or log_file:
            file_path = log_file or _get_default_log_file(name)
            file_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(file_path)
            file_handler.setLevel(level or DEFAULT_LOG_LEVEL)
            file_handler.setFormatter(FileFormatter())
            logger.addHandler(file_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    _loggers[name] = logger
    return logger


def _get_default_log_file(name: str) -> Path:
    """Generate default log file path for a module."""
    LOG_FILE_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    safe_name = name.replace(".", "_")
    return LOG_FILE_DIR / f"{safe_name}_{date_str}.log"


def configure_root_logger(
    level: int = logging.INFO,
    log_file: Optional[Path] = None
) -> None:
    """
    Configure the root logger for the entire application.

    Call this once at application startup for consistent logging.

    Args:
        level: Log level for root logger
        log_file: Optional file for all log output
    """
    root = logging.getLogger()
    root.setLevel(level)

    # Clear existing handlers
    root.handlers.clear()

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(ConsoleFormatter())
    root.addHandler(console)

    # File handler
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(FileFormatter())
        root.addHandler(file_handler)


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS (Match STYLE_GUIDE.md patterns)
# ═══════════════════════════════════════════════════════════════════════════════

_default_logger: Optional[logging.Logger] = None


def _get_default_logger() -> logging.Logger:
    """Get or create the default module logger."""
    global _default_logger
    if _default_logger is None:
        _default_logger = get_logger('bos_scanner')
    return _default_logger


def log_step(message: str, step_num: Optional[int] = None) -> None:
    """
    Log a step in a multi-step process.

    Args:
        message: Step description
        step_num: Optional step number

    Example:
        log_step("Loading data", 1)
        log_step("Processing")
    """
    if step_num:
        print(f"\n  Step {step_num}: {message}...")
    else:
        print(f"\n  {INDICATORS['step']} {message}...")


def log_success(message: str) -> None:
    """Log a success message."""
    print(f"  {INDICATORS['success']} {message}")


def log_warning(message: str) -> None:
    """Log a warning message."""
    print(f"  {INDICATORS['warning']} Warning: {message}")


def log_error(message: str) -> None:
    """Log an error message."""
    print(f"  {INDICATORS['error']} Error: {message}")


def log_info(message: str) -> None:
    """Log an info message."""
    print(f"  {INDICATORS['info']} {message}")


def log_debug(message: str, verbose: bool = False) -> None:
    """
    Log a debug message (only if verbose=True).

    Args:
        message: Debug message
        verbose: Whether to actually print
    """
    if verbose:
        print(f"  DEBUG: {message}")


def log_progress(current: int, total: int, prefix: str = "") -> None:
    """
    Log progress through a loop.

    Args:
        current: Current item number (1-indexed)
        total: Total items
        prefix: Optional prefix
    """
    percent = (current / total) * 100 if total > 0 else 0
    prefix_str = f"{prefix}: " if prefix else ""
    print(f"\r  {prefix_str}[{current}/{total}] {percent:.0f}%", end="", flush=True)
    if current == total:
        print()  # Newline at end


def log_section(title: str, char: str = "─", width: int = 70) -> None:
    """
    Log a section divider.

    Args:
        title: Section title
        char: Divider character
        width: Total width
    """
    print(f"\n{char * width}")
    print(f"  {title}")
    print(f"{char * width}")


def log_banner(title: str, subtitle: Optional[str] = None, width: int = 78) -> None:
    """
    Log a banner header.

    Args:
        title: Main title
        subtitle: Optional subtitle
        width: Banner width
    """
    border = "=" * width
    print(f"\n{border}")
    print(f"{title:^{width}}")
    if subtitle:
        print(f"{subtitle:^{width}}")
    print(border)


def log_summary(items: dict, title: str = "Summary") -> None:
    """
    Log a summary dictionary.

    Args:
        items: Key-value pairs to display
        title: Section title
    """
    print(f"\n  {title}:")
    for key, value in items.items():
        print(f"    {key}: {value}")


def log_cost(cost: float, label: str = "Total Cost") -> None:
    """Log API cost."""
    print(f"  {label}: ${cost:.4f}")


# ═══════════════════════════════════════════════════════════════════════════════
# CONTEXT MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class LoggedOperation:
    """
    Context manager for logging operation start/end.

    Example:
        with LoggedOperation("Loading data"):
            load_data()

        # Output:
        # → Loading data...
        # ✓ Loading data complete (2.3s)
    """

    def __init__(self, name: str, show_time: bool = True):
        self.name = name
        self.show_time = show_time
        self.start_time: float = 0

    def __enter__(self) -> 'LoggedOperation':
        import time
        self.start_time = time.time()
        print(f"  {INDICATORS['step']} {self.name}...", end="", flush=True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        import time
        elapsed = time.time() - self.start_time

        if exc_type is not None:
            print(f" {INDICATORS['error']} FAILED")
            return False

        if self.show_time:
            print(f" {INDICATORS['success']} ({elapsed:.1f}s)")
        else:
            print(f" {INDICATORS['success']}")

        return False


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import time

    print("Logger Test")
    print("=" * 50)

    # Test banner
    log_banner("BoS MOMENTUM SCANNER", "Weekly Timeframe")

    # Test section
    log_section("STEP 1: Loading Data")

    # Test convenience functions
    log_step("Loading tickers", 1)
    log_success("Loaded 1,817 tickers")
    log_warning("Some tickers may be delisted")
    log_info("Processing in batches of 100")

    # Test progress
    print("\n  Progress test:")
    for i in range(1, 6):
        log_progress(i, 5, "Processing")
        time.sleep(0.1)

    # Test summary
    log_summary({
        "Tickers Loaded": 1817,
        "Data Downloaded": 1814,
        "Signals Found": 48,
        "Final PASS": 6
    }, "Scan Statistics")

    # Test cost
    log_cost(2.50, "Total API Cost")

    # Test error
    log_error("This is an error test")

    # Test context manager
    print("\n  Context manager test:")
    with LoggedOperation("Simulated operation"):
        time.sleep(0.5)

    # Test file logging
    logger = get_logger("test_module", enable_file_logging=True)
    logger.info("Test log message to file")
    print(f"\n  Log file: {_get_default_log_file('test_module')}")

    print("\n✓ All logging functions working correctly")
