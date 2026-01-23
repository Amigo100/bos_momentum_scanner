#!/usr/bin/env python3
"""
LLM CLIENT - Unified API Wrapper with Rate Limiting and Cost Tracking
======================================================================

Centralized Anthropic API client with:
- Automatic rate limiting with exponential backoff
- Cost tracking across all API calls
- Consistent error handling and retries
- Web search tool integration

Usage:
    from llm_client import LLMClient

    client = LLMClient()
    response = client.complete(
        prompt="Analyze this stock...",
        system="You are a financial analyst...",
        web_search=True
    )

    print(f"Response: {response.text}")
    print(f"Cost: ${client.get_total_cost():.4f}")
"""

import os
import time
import functools
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Any, Callable
import logging

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    print("  ⚠ anthropic package not installed")

# Import config if available
try:
    from config import (
        MODEL_SONNET, MODEL_OPUS,
        MAX_RETRIES, RATE_LIMIT_COOLDOWN,
        BACKOFF_FACTOR, BACKOFF_MAX_WAIT,
        COST_INPUT_PER_M, COST_OUTPUT_PER_M, COST_WEB_SEARCH
    )
except ImportError:
    MODEL_SONNET = "claude-sonnet-4-20250514"
    MODEL_OPUS = "claude-opus-4-5-20251101"
    MAX_RETRIES = 5
    RATE_LIMIT_COOLDOWN = 60.0
    BACKOFF_FACTOR = 2.0
    BACKOFF_MAX_WAIT = 300.0
    COST_INPUT_PER_M = {MODEL_SONNET: 3.00, MODEL_OPUS: 15.00}
    COST_OUTPUT_PER_M = {MODEL_SONNET: 15.00, MODEL_OPUS: 75.00}
    COST_WEB_SEARCH = 0.01


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class LLMResponse:
    """Unified response from LLM API call."""
    text: str = ""
    thinking: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0
    model: str = ""
    web_searches: int = 0
    stop_reason: str = ""
    raw_response: Any = None


@dataclass
class CostTracker:
    """Tracks API costs across all calls."""
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_web_searches: int = 0
    total_cost: float = 0.0
    calls_by_model: Dict[str, int] = field(default_factory=dict)
    cost_by_model: Dict[str, float] = field(default_factory=dict)
    call_count: int = 0

    def add_call(self, model: str, input_tokens: int, output_tokens: int,
                 web_searches: int = 0) -> float:
        """
        Record a call and return the cost.

        Args:
            model: Model used for the call
            input_tokens: Input token count
            output_tokens: Output token count
            web_searches: Number of web searches performed

        Returns:
            Cost of this call in USD
        """
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_web_searches += web_searches
        self.call_count += 1

        # Track by model
        self.calls_by_model[model] = self.calls_by_model.get(model, 0) + 1

        # Calculate cost
        input_cost = (input_tokens / 1_000_000) * COST_INPUT_PER_M.get(model, 3.0)
        output_cost = (output_tokens / 1_000_000) * COST_OUTPUT_PER_M.get(model, 15.0)
        search_cost = web_searches * COST_WEB_SEARCH

        call_cost = input_cost + output_cost + search_cost
        self.total_cost += call_cost
        self.cost_by_model[model] = self.cost_by_model.get(model, 0) + call_cost

        return call_cost

    def get_summary(self) -> Dict:
        """Get cost summary."""
        return {
            "total_cost": f"${self.total_cost:.4f}",
            "call_count": self.call_count,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_web_searches": self.total_web_searches,
            "by_model": {
                model: {
                    "calls": self.calls_by_model.get(model, 0),
                    "cost": f"${self.cost_by_model.get(model, 0):.4f}"
                }
                for model in set(list(self.calls_by_model.keys()) + list(self.cost_by_model.keys()))
            }
        }


# ═══════════════════════════════════════════════════════════════════════════════
# RATE LIMITER
# ═══════════════════════════════════════════════════════════════════════════════

class RateLimiter:
    """Handles API rate limiting with exponential backoff."""

    def __init__(
        self,
        min_interval: float = 1.0,
        base_delay: float = 5.0,
        max_delay: float = 300.0,
        cooldown: float = 60.0,
        logger: logging.Logger = None
    ):
        self.min_interval = min_interval
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.cooldown = cooldown
        self.logger = logger or logging.getLogger(__name__)

        self.request_count = 0
        self.last_request_time = 0.0
        self.consecutive_rate_limits = 0
        self.total_rate_limits = 0

    def wait_if_needed(self) -> None:
        """Wait if making requests too quickly."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            sleep_time = self.min_interval - elapsed
            self.logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)

    def handle_rate_limit(self, attempt: int) -> float:
        """
        Calculate delay after rate limit hit.

        Args:
            attempt: Current retry attempt number

        Returns:
            Delay time in seconds
        """
        self.consecutive_rate_limits += 1
        self.total_rate_limits += 1

        # Exponential backoff with jitter
        delay = min(
            self.base_delay * (BACKOFF_FACTOR ** attempt) + (time.time() % 1),
            self.max_delay
        )

        # Add extra cooldown if multiple rate limits
        if self.consecutive_rate_limits >= 3:
            delay += self.cooldown
            self.logger.warning(
                f"Multiple rate limits ({self.consecutive_rate_limits}). "
                f"Adding {self.cooldown}s cooldown"
            )

        return delay

    def record_success(self) -> None:
        """Record successful request."""
        self.last_request_time = time.time()
        self.request_count += 1
        self.consecutive_rate_limits = 0

    def get_stats(self) -> Dict:
        """Get rate limiter statistics."""
        return {
            "total_requests": self.request_count,
            "consecutive_rate_limits": self.consecutive_rate_limits,
            "total_rate_limits": self.total_rate_limits
        }


# ═══════════════════════════════════════════════════════════════════════════════
# DECORATORS
# ═══════════════════════════════════════════════════════════════════════════════

def with_retry(max_attempts: int = None, backoff_factor: float = None):
    """
    Decorator for retrying API calls with exponential backoff.

    Args:
        max_attempts: Maximum retry attempts (default from config)
        backoff_factor: Backoff multiplier (default from config)
    """
    _max_attempts = max_attempts or MAX_RETRIES
    _backoff_factor = backoff_factor or BACKOFF_FACTOR

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(_max_attempts):
                try:
                    return func(*args, **kwargs)
                except anthropic.RateLimitError as e:
                    last_exception = e
                    delay = min(
                        5 * (_backoff_factor ** attempt),
                        BACKOFF_MAX_WAIT
                    )
                    logging.warning(f"Rate limited (attempt {attempt + 1}). Waiting {delay:.1f}s...")
                    time.sleep(delay)
                except anthropic.APIStatusError as e:
                    if e.status_code >= 500:
                        last_exception = e
                        delay = min(2 * (_backoff_factor ** attempt), 60)
                        logging.warning(f"Server error {e.status_code}. Retrying in {delay:.1f}s...")
                        time.sleep(delay)
                    else:
                        raise
                except Exception as e:
                    logging.error(f"Unexpected error: {e}")
                    raise

            raise last_exception or Exception("Max retries exceeded")

        return wrapper
    return decorator


# ═══════════════════════════════════════════════════════════════════════════════
# LLM CLIENT
# ═══════════════════════════════════════════════════════════════════════════════

class LLMClient:
    """
    Unified Anthropic API client with rate limiting and cost tracking.

    Example:
        client = LLMClient()
        response = client.complete(
            prompt="What is the capital of France?",
            model="claude-sonnet-4-20250514"
        )
        print(response.text)
        print(f"Cost: ${client.get_total_cost():.4f}")
    """

    def __init__(
        self,
        model: str = None,
        api_key: str = None,
        rate_limit_interval: float = 1.0,
        logger: logging.Logger = None
    ):
        """
        Initialize LLM client.

        Args:
            model: Default model to use (defaults to MODEL_SONNET)
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            rate_limit_interval: Minimum seconds between requests
            logger: Logger instance
        """
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("anthropic package required: pip install anthropic")

        self.default_model = model or MODEL_SONNET
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")

        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.cost_tracker = CostTracker()
        self.rate_limiter = RateLimiter(
            min_interval=rate_limit_interval,
            logger=logger or logging.getLogger(__name__)
        )
        self.logger = logger or logging.getLogger(__name__)

    @with_retry()
    def complete(
        self,
        prompt: str,
        system: str = None,
        model: str = None,
        max_tokens: int = 4096,
        web_search: bool = False,
        thinking: bool = False,
        thinking_budget: int = 10000,
        temperature: float = None,
        stop_sequences: List[str] = None
    ) -> LLMResponse:
        """
        Make a completion request to the Anthropic API.

        Args:
            prompt: User prompt text
            system: System prompt (optional)
            model: Model to use (default: self.default_model)
            max_tokens: Maximum tokens in response
            web_search: Enable web search tool
            thinking: Enable extended thinking (Opus only)
            thinking_budget: Token budget for thinking
            temperature: Sampling temperature
            stop_sequences: Custom stop sequences

        Returns:
            LLMResponse with text, tokens, and cost
        """
        self.rate_limiter.wait_if_needed()

        model = model or self.default_model

        # Build API parameters
        params = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}]
        }

        if system:
            params["system"] = system

        if temperature is not None:
            params["temperature"] = temperature

        if stop_sequences:
            params["stop_sequences"] = stop_sequences

        # Add web search tool
        if web_search:
            params["tools"] = [{"type": "web_search_20250305", "name": "web_search"}]

        # Add extended thinking (Opus only)
        if thinking and "opus" in model.lower():
            params["thinking"] = {
                "type": "enabled",
                "budget_tokens": thinking_budget
            }

        # Make API call
        response = self.client.messages.create(**params)
        self.rate_limiter.record_success()

        # Parse response
        result = self._parse_response(response, model)

        return result

    def _parse_response(self, response, model: str) -> LLMResponse:
        """Parse API response into LLMResponse."""
        result = LLMResponse(
            model=model,
            raw_response=response
        )

        # Extract text and thinking
        web_search_count = 0
        for block in response.content:
            if hasattr(block, 'text'):
                result.text += block.text
            elif hasattr(block, 'thinking'):
                result.thinking += block.thinking
            elif hasattr(block, 'type') and block.type == 'tool_use':
                if getattr(block, 'name', '') == 'web_search':
                    web_search_count += 1

        # Token usage
        result.input_tokens = getattr(response.usage, 'input_tokens', 0)
        result.output_tokens = getattr(response.usage, 'output_tokens', 0)
        result.web_searches = web_search_count
        result.stop_reason = getattr(response, 'stop_reason', '')

        # Calculate and track cost
        result.cost = self.cost_tracker.add_call(
            model=model,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            web_searches=web_search_count
        )

        return result

    def complete_batch(
        self,
        prompts: List[str],
        system: str = None,
        model: str = None,
        delay_between: float = 2.0,
        **kwargs
    ) -> List[LLMResponse]:
        """
        Make multiple completion requests with delays.

        Args:
            prompts: List of prompts to process
            system: Shared system prompt
            model: Model to use
            delay_between: Seconds between requests
            **kwargs: Additional args passed to complete()

        Returns:
            List of LLMResponse objects
        """
        results = []

        for i, prompt in enumerate(prompts):
            if i > 0:
                time.sleep(delay_between)

            self.logger.info(f"Processing {i + 1}/{len(prompts)}...")

            try:
                response = self.complete(
                    prompt=prompt,
                    system=system,
                    model=model,
                    **kwargs
                )
                results.append(response)
            except Exception as e:
                self.logger.error(f"Error on prompt {i + 1}: {e}")
                results.append(LLMResponse(text=f"Error: {e}"))

        return results

    def get_total_cost(self) -> float:
        """Get total cost of all API calls."""
        return self.cost_tracker.total_cost

    def get_cost_summary(self) -> Dict:
        """Get detailed cost summary."""
        return self.cost_tracker.get_summary()

    def get_rate_limit_stats(self) -> Dict:
        """Get rate limiter statistics."""
        return self.rate_limiter.get_stats()

    def print_cost_summary(self) -> None:
        """Print formatted cost summary."""
        summary = self.cost_tracker.get_summary()
        print(f"\n{'=' * 50}")
        print("LLM Cost Summary")
        print('=' * 50)
        print(f"Total Cost: {summary['total_cost']}")
        print(f"API Calls: {summary['call_count']}")
        print(f"Input Tokens: {summary['total_input_tokens']:,}")
        print(f"Output Tokens: {summary['total_output_tokens']:,}")
        print(f"Web Searches: {summary['total_web_searches']}")

        if summary['by_model']:
            print("\nBy Model:")
            for model, stats in summary['by_model'].items():
                model_short = model.split('-')[-1][:10]
                print(f"  {model_short}: {stats['calls']} calls, {stats['cost']}")


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def estimate_cost(input_tokens: int, output_tokens: int, model: str) -> float:
    """
    Estimate cost for a given token count.

    Args:
        input_tokens: Input token count
        output_tokens: Output token count
        model: Model name

    Returns:
        Estimated cost in USD
    """
    input_cost = (input_tokens / 1_000_000) * COST_INPUT_PER_M.get(model, 3.0)
    output_cost = (output_tokens / 1_000_000) * COST_OUTPUT_PER_M.get(model, 15.0)
    return input_cost + output_cost


def create_client(model: str = None) -> LLMClient:
    """
    Factory function to create LLM client.

    Args:
        model: Default model (defaults to Sonnet)

    Returns:
        Configured LLMClient instance
    """
    return LLMClient(model=model or MODEL_SONNET)


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Test LLM client."""
    import argparse

    parser = argparse.ArgumentParser(description="LLM Client Test")
    parser.add_argument("--prompt", default="What is 2+2?", help="Test prompt")
    parser.add_argument("--model", default=MODEL_SONNET, help="Model to use")
    parser.add_argument("--web-search", action="store_true", help="Enable web search")

    args = parser.parse_args()

    print(f"Testing LLM Client with model: {args.model}")
    print(f"Prompt: {args.prompt}")
    print(f"Web Search: {args.web_search}")
    print("-" * 50)

    try:
        client = LLMClient(model=args.model)
        response = client.complete(
            prompt=args.prompt,
            web_search=args.web_search
        )

        print(f"\nResponse: {response.text[:500]}...")
        print(f"\nInput Tokens: {response.input_tokens}")
        print(f"Output Tokens: {response.output_tokens}")
        print(f"Cost: ${response.cost:.4f}")

        client.print_cost_summary()

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
