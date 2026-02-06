# tests/test_safeguards.py
# Phase 10: MASTER_TODO.md Compliance - Unit Tests for Safeguards

"""
Unit tests for Sterling Signals safeguard functions.

These tests ensure:
1. Losing positions never appear in public content
2. Stopped positions never appear in public content
3. Tweet character limits enforced correctly
4. Age-based thresholds work as specified
5. SPY comparison safeguards function properly
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from distribution.signal_tracker import filter_public_positions, has_enough_wins, should_post_beat_spy
from content.tweet_generator import validate_tweet_length, get_tweet_char_count
from config import get_highlight_threshold


class TestFilterPublicPositions:
    """Tests for filter_public_positions() - CRITICAL safeguard."""

    def test_filter_removes_losers(self):
        """Positions with negative P&L should never appear publicly."""
        positions = [
            {'ticker': 'WIN', 'pnl_pct': 25.0, 'status': 'OPEN'},
            {'ticker': 'LOSE', 'pnl_pct': -10.0, 'status': 'OPEN'},
        ]
        filtered = filter_public_positions(positions)
        assert len(filtered) == 1
        assert filtered[0]['ticker'] == 'WIN'

    def test_filter_removes_stopped(self):
        """STOPPED positions should never appear publicly, even with positive P&L."""
        positions = [
            {'ticker': 'WIN', 'pnl_pct': 25.0, 'status': 'OPEN'},
            {'ticker': 'STOP', 'pnl_pct': -20.0, 'status': 'STOPPED'},
        ]
        filtered = filter_public_positions(positions)
        assert len(filtered) == 1
        assert 'STOP' not in [p['ticker'] for p in filtered]

    def test_filter_removes_stopped_even_if_profitable(self):
        """A STOPPED position with positive P&L should still be filtered out."""
        positions = [
            {'ticker': 'STOPPED_WINNER', 'pnl_pct': 10.0, 'status': 'STOPPED'},
            {'ticker': 'OPEN_WINNER', 'pnl_pct': 15.0, 'status': 'OPEN'},
        ]
        filtered = filter_public_positions(positions)
        assert len(filtered) == 1
        assert filtered[0]['ticker'] == 'OPEN_WINNER'

    def test_filter_includes_breakeven(self):
        """Positions at exactly 0% should be included (not negative)."""
        positions = [
            {'ticker': 'EVEN', 'pnl_pct': 0.0, 'status': 'OPEN'},
        ]
        filtered = filter_public_positions(positions)
        assert len(filtered) == 1

    def test_filter_handles_empty_list(self):
        """Empty input should return empty list, not crash."""
        filtered = filter_public_positions([])
        assert filtered == []

    def test_filter_handles_all_losers(self):
        """All losers should return empty list."""
        positions = [
            {'ticker': 'A', 'pnl_pct': -5.0, 'status': 'OPEN'},
            {'ticker': 'B', 'pnl_pct': -10.0, 'status': 'OPEN'},
            {'ticker': 'C', 'pnl_pct': -15.0, 'status': 'OPEN'},
        ]
        filtered = filter_public_positions(positions)
        assert len(filtered) == 0


class TestHasEnoughWins:
    """Tests for has_enough_wins() safeguard."""

    def test_has_enough_wins_passes_threshold(self):
        """Should return True when enough winners exist."""
        positions = [
            {'ticker': 'A', 'pnl_pct': 20.0},
            {'ticker': 'B', 'pnl_pct': 18.0},
            {'ticker': 'C', 'pnl_pct': 5.0},
        ]
        # With default threshold 15% and min_winners 2
        result = has_enough_wins(positions, min_pnl=15.0, min_winners=2)
        assert result == True

    def test_has_enough_wins_fails_threshold(self):
        """Should return False when not enough winners."""
        positions = [
            {'ticker': 'A', 'pnl_pct': 20.0},
            {'ticker': 'B', 'pnl_pct': 10.0},  # Below 15%
        ]
        result = has_enough_wins(positions, min_pnl=15.0, min_winners=2)
        assert result == False

    def test_has_enough_wins_exactly_at_threshold(self):
        """Position at exactly threshold should be included."""
        positions = [
            {'ticker': 'A', 'pnl_pct': 15.0},  # Exactly at threshold
            {'ticker': 'B', 'pnl_pct': 15.0},  # Exactly at threshold
        ]
        result = has_enough_wins(positions, min_pnl=15.0, min_winners=2)
        assert result == True

    def test_has_enough_wins_empty_list(self):
        """Empty list should return False."""
        result = has_enough_wins([], min_pnl=15.0, min_winners=2)
        assert result == False


class TestSPYComparisonSafeguard:
    """Tests for should_post_beat_spy() safeguard.

    should_post_beat_spy() takes no arguments — it calls calculate_portfolio_vs_spy()
    internally and checks the 'should_post_beat_spy' key in the result dict.
    We mock calculate_portfolio_vs_spy to control the return value.
    """

    @patch("distribution.signal_tracker.calculate_portfolio_vs_spy")
    def test_spy_comparison_below_threshold(self, mock_calc):
        """Should not post if alpha is below 5%."""
        mock_calc.return_value = {'should_post_beat_spy': False}
        result = should_post_beat_spy()
        assert result == False

    @patch("distribution.signal_tracker.calculate_portfolio_vs_spy")
    def test_spy_comparison_above_threshold(self, mock_calc):
        """Should post if alpha is above 5%."""
        mock_calc.return_value = {'should_post_beat_spy': True}
        result = should_post_beat_spy()
        assert result == True

    @patch("distribution.signal_tracker.calculate_portfolio_vs_spy")
    def test_spy_comparison_exactly_at_threshold(self, mock_calc):
        """Should post if alpha is exactly at threshold."""
        mock_calc.return_value = {'should_post_beat_spy': True}
        result = should_post_beat_spy()
        assert result == True

    @patch("distribution.signal_tracker.calculate_portfolio_vs_spy")
    def test_spy_comparison_invalid(self, mock_calc):
        """No comparable positions should return False."""
        mock_calc.return_value = {'should_post_beat_spy': False, 'can_compare': False}
        result = should_post_beat_spy()
        assert result == False

    @patch("distribution.signal_tracker.calculate_portfolio_vs_spy")
    def test_spy_comparison_missing_alpha(self, mock_calc):
        """When calculate returns False for posting, should return False."""
        mock_calc.return_value = {'should_post_beat_spy': False}
        result = should_post_beat_spy()
        assert result == False

    @patch("distribution.signal_tracker.calculate_portfolio_vs_spy")
    def test_spy_comparison_missing_key_returns_false(self, mock_calc):
        """If calculate_portfolio_vs_spy returns dict without 'should_post_beat_spy' key, should default False."""
        mock_calc.return_value = {'error': 'price_fetch_failed'}
        result = should_post_beat_spy()
        assert result == False


class TestTweetLengthValidation:
    """Tests for validate_tweet_length() function."""

    def test_short_tweet_valid(self):
        """Short tweet should pass."""
        short = "This is a short tweet"
        assert validate_tweet_length(short) == True

    def test_long_tweet_invalid(self):
        """Tweet over 280 chars should fail."""
        long = "x" * 300
        assert validate_tweet_length(long) == False

    def test_exactly_280_chars_valid(self):
        """Tweet at exactly 280 chars should pass."""
        exact = "x" * 280
        assert validate_tweet_length(exact) == True

    def test_emojis_count_as_two(self):
        """Emojis should count as 2 characters."""
        # 141 emojis = 282 chars (over limit)
        emoji_tweet = "🚀" * 141
        assert validate_tweet_length(emoji_tweet) == False

    def test_140_emojis_valid(self):
        """140 emojis = 280 chars, should pass."""
        emoji_tweet = "🚀" * 140
        assert validate_tweet_length(emoji_tweet) == True

    def test_mixed_content(self):
        """Mixed ASCII and emoji should count correctly."""
        # 100 chars + 90 emojis (180 chars) = 280
        mixed = "x" * 100 + "🚀" * 90
        assert validate_tweet_length(mixed) == True

    def test_char_count_function(self):
        """get_tweet_char_count should return correct count."""
        text = "Hello 🚀"  # 6 chars + 2 = 8
        count = get_tweet_char_count(text)
        assert count == 8


class TestAgeBasedThresholds:
    """Tests for get_highlight_threshold() function."""

    def test_new_position_7_days(self):
        """7-day position should have 3% threshold."""
        assert get_highlight_threshold(7) == 3.0

    def test_two_week_position(self):
        """14-day position should have 5% threshold."""
        assert get_highlight_threshold(14) == 5.0

    def test_one_month_position(self):
        """30-day position should have 10% threshold."""
        assert get_highlight_threshold(30) == 10.0

    def test_two_month_position(self):
        """60-day position should have 15% threshold."""
        assert get_highlight_threshold(60) == 15.0

    def test_mature_position_90_days(self):
        """90-day position should have 20% threshold."""
        assert get_highlight_threshold(90) == 20.0

    def test_very_new_position_1_day(self):
        """1-day position should have 3% threshold."""
        assert get_highlight_threshold(1) == 3.0

    def test_boundary_8_days(self):
        """8-day position should have 5% threshold (next tier)."""
        assert get_highlight_threshold(8) == 5.0

    def test_boundary_15_days(self):
        """15-day position should have 10% threshold (next tier)."""
        assert get_highlight_threshold(15) == 10.0


class TestNoLosersInPublicContent:
    """Integration tests verifying no losers ever appear publicly."""

    def test_comprehensive_loser_filtering(self):
        """Comprehensive test: no losers in any scenario."""
        test_cases = [
            # Small loss
            [{'ticker': 'SMALL_LOSS', 'pnl_pct': -0.1, 'status': 'OPEN'}],
            # Exact zero (should be included as it's not negative)
            [{'ticker': 'ZERO', 'pnl_pct': 0.0, 'status': 'OPEN'}],
            # Large loss
            [{'ticker': 'BIG_LOSS', 'pnl_pct': -50.0, 'status': 'OPEN'}],
            # Stopped with loss
            [{'ticker': 'STOPPED_LOSS', 'pnl_pct': -20.0, 'status': 'STOPPED'}],
        ]

        for i, positions in enumerate(test_cases):
            filtered = filter_public_positions(positions)
            for pos in filtered:
                assert pos['pnl_pct'] >= 0, f"Case {i}: Loser found in public content: {pos}"
                assert pos.get('status') != 'STOPPED', f"Case {i}: Stopped position found: {pos}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
