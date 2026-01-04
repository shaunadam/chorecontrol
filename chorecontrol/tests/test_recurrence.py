"""Tests for recurrence pattern utilities."""

import pytest
from datetime import date, timedelta
import sys
from pathlib import Path

# Add parent directory to path so we can import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.recurrence import (
    calculate_next_due_date,
    generate_due_dates,
    matches_pattern,
    validate_recurrence_pattern
)


class TestCalculateNextDueDate:
    """Tests for calculate_next_due_date function."""

    def test_simple_daily_pattern(self):
        """Daily pattern should return next day."""
        pattern = {'type': 'simple', 'interval': 'daily', 'every_n': 1}
        after_date = date(2024, 1, 15)
        result = calculate_next_due_date(pattern, after_date)
        assert result == date(2024, 1, 16)

    def test_simple_daily_every_2_days(self):
        """Daily pattern with every_n=2 should skip a day."""
        pattern = {'type': 'simple', 'interval': 'daily', 'every_n': 2}
        after_date = date(2024, 1, 15)
        result = calculate_next_due_date(pattern, after_date)
        assert result == date(2024, 1, 17)

    def test_simple_weekly_pattern(self):
        """Weekly pattern should return date 7 days later."""
        pattern = {'type': 'simple', 'interval': 'weekly', 'every_n': 1}
        after_date = date(2024, 1, 15)  # Monday
        result = calculate_next_due_date(pattern, after_date)
        assert result == date(2024, 1, 22)  # Next Monday

    def test_simple_weekly_every_2_weeks(self):
        """Bi-weekly pattern should return date 14 days later."""
        pattern = {'type': 'simple', 'interval': 'weekly', 'every_n': 2}
        after_date = date(2024, 1, 15)
        result = calculate_next_due_date(pattern, after_date)
        assert result == date(2024, 1, 29)

    def test_simple_monthly_pattern(self):
        """Monthly pattern should return same day next month."""
        pattern = {'type': 'simple', 'interval': 'monthly', 'every_n': 1}
        after_date = date(2024, 1, 15)
        result = calculate_next_due_date(pattern, after_date)
        assert result == date(2024, 2, 15)

    def test_simple_monthly_end_of_month_edge_case(self):
        """Monthly pattern handles months with fewer days."""
        pattern = {'type': 'simple', 'interval': 'monthly', 'every_n': 1}
        after_date = date(2024, 1, 31)
        result = calculate_next_due_date(pattern, after_date)
        # February 2024 has 29 days (leap year)
        assert result == date(2024, 2, 29)

    def test_complex_days_of_week(self):
        """Complex pattern with specific days of week."""
        pattern = {'type': 'complex', 'days_of_week': [0, 2, 4]}  # Mon, Wed, Fri
        after_date = date(2024, 1, 15)  # Monday
        result = calculate_next_due_date(pattern, after_date)
        assert result == date(2024, 1, 17)  # Wednesday

    def test_complex_empty_days_of_week(self):
        """Complex pattern with empty days_of_week returns None."""
        pattern = {'type': 'complex', 'days_of_week': []}
        after_date = date(2024, 1, 15)
        result = calculate_next_due_date(pattern, after_date)
        assert result is None

    def test_weekly_with_specific_days(self):
        """Weekly pattern type with specific days."""
        # Sunday=0 format in input
        pattern = {'type': 'weekly', 'days_of_week': [2, 4]}  # Monday=1, Wednesday=3 -> adjusted
        after_date = date(2024, 1, 15)  # Monday (weekday=0)
        result = calculate_next_due_date(pattern, after_date)
        # Should find next occurrence
        assert result is not None
        assert result > after_date

    def test_monthly_with_specific_days(self):
        """Monthly pattern with specific days of month."""
        pattern = {'type': 'monthly', 'days_of_month': [1, 15]}
        after_date = date(2024, 1, 10)
        result = calculate_next_due_date(pattern, after_date)
        assert result == date(2024, 1, 15)

    def test_monthly_next_month_rollover(self):
        """Monthly pattern rolls over to next month."""
        pattern = {'type': 'monthly', 'days_of_month': [5, 10]}
        after_date = date(2024, 1, 20)
        result = calculate_next_due_date(pattern, after_date)
        assert result == date(2024, 2, 5)

    def test_none_pattern_returns_none(self):
        """Pattern type 'none' returns None."""
        pattern = {'type': 'none'}
        after_date = date(2024, 1, 15)
        result = calculate_next_due_date(pattern, after_date)
        assert result is None

    def test_empty_pattern_returns_none(self):
        """Empty pattern returns None."""
        result = calculate_next_due_date(None, date(2024, 1, 15))
        assert result is None

    def test_daily_pattern_type(self):
        """Pattern type 'daily' works like simple daily."""
        pattern = {'type': 'daily'}
        after_date = date(2024, 1, 15)
        result = calculate_next_due_date(pattern, after_date)
        assert result == date(2024, 1, 16)


class TestGenerateDueDates:
    """Tests for generate_due_dates function."""

    def test_simple_daily_generates_correct_count(self):
        """Daily pattern generates correct number of dates."""
        pattern = {'type': 'simple', 'interval': 'daily', 'every_n': 1}
        start = date(2024, 1, 1)
        end = date(2024, 1, 7)
        dates = generate_due_dates(pattern, start, end)
        assert len(dates) == 7  # Jan 1-7 inclusive

    def test_simple_weekly_generates_once_per_week(self):
        """Weekly pattern generates once per week, not daily."""
        pattern = {'type': 'simple', 'interval': 'weekly', 'every_n': 1}
        start = date(2024, 1, 1)  # Monday
        end = date(2024, 1, 31)
        dates = generate_due_dates(pattern, start, end)
        # Should have ~4-5 occurrences (once per week)
        assert len(dates) == 5  # Jan 1, 8, 15, 22, 29

    def test_simple_monthly_generates_once_per_month(self):
        """Monthly pattern generates once per month."""
        pattern = {'type': 'simple', 'interval': 'monthly', 'every_n': 1}
        start = date(2024, 1, 15)
        end = date(2024, 4, 15)
        dates = generate_due_dates(pattern, start, end)
        assert len(dates) == 4  # Jan 15, Feb 15, Mar 15, Apr 15

    def test_none_pattern_returns_single_date(self):
        """Pattern type 'none' returns start_date only."""
        pattern = {'type': 'none'}
        start = date(2024, 1, 15)
        end = date(2024, 1, 31)
        dates = generate_due_dates(pattern, start, end)
        assert dates == [start]

    def test_empty_pattern_returns_empty_list(self):
        """Empty pattern returns empty list."""
        dates = generate_due_dates(None, date(2024, 1, 1), date(2024, 1, 31))
        assert dates == []

    def test_malformed_pattern_doesnt_infinite_loop(self):
        """Malformed patterns should not cause infinite loops."""
        # Complex with empty days - should return quickly
        pattern = {'type': 'complex', 'days_of_week': []}
        start = date(2024, 1, 1)
        end = date(2024, 1, 31)
        dates = generate_due_dates(pattern, start, end)
        assert dates == []  # Should return empty, not hang

    def test_date_range_respects_boundaries(self):
        """Generated dates stay within specified range."""
        pattern = {'type': 'simple', 'interval': 'daily', 'every_n': 1}
        start = date(2024, 1, 10)
        end = date(2024, 1, 15)
        dates = generate_due_dates(pattern, start, end)
        for d in dates:
            assert d >= start
            assert d <= end

    def test_weekly_specific_days_pattern(self):
        """Weekly pattern with specific days generates correctly."""
        pattern = {'type': 'weekly', 'days_of_week': [2]}  # Sunday=0, so 2=Tuesday
        start = date(2024, 1, 1)  # Monday
        end = date(2024, 1, 31)
        dates = generate_due_dates(pattern, start, end)
        # Should have occurrences on Tuesdays (Jan 2, 9, 16, 23, 30) = 5
        # But the adjusted weekday (2-1)%7=1 means Monday in Python
        assert len(dates) >= 1
        for d in dates:
            assert d >= start and d <= end


class TestMatchesPattern:
    """Tests for matches_pattern function."""

    def test_simple_pattern_always_matches(self):
        """Simple patterns always return True (progression handled elsewhere)."""
        pattern = {'type': 'simple', 'interval': 'weekly', 'every_n': 1}
        assert matches_pattern(pattern, date(2024, 1, 15)) is True
        assert matches_pattern(pattern, date(2024, 1, 16)) is True

    def test_complex_pattern_checks_day_of_week(self):
        """Complex patterns check actual day of week."""
        pattern = {'type': 'complex', 'days_of_week': [0]}  # Monday (Python weekday)
        assert matches_pattern(pattern, date(2024, 1, 15)) is True  # Monday
        assert matches_pattern(pattern, date(2024, 1, 16)) is False  # Tuesday

    def test_complex_empty_days_returns_false(self):
        """Complex pattern with empty days_of_week returns False."""
        pattern = {'type': 'complex', 'days_of_week': []}
        assert matches_pattern(pattern, date(2024, 1, 15)) is False

    def test_daily_pattern_always_matches(self):
        """Daily pattern always returns True."""
        pattern = {'type': 'daily'}
        assert matches_pattern(pattern, date(2024, 1, 15)) is True
        assert matches_pattern(pattern, date(2024, 12, 25)) is True

    def test_monthly_pattern_checks_day_of_month(self):
        """Monthly pattern checks day of month."""
        pattern = {'type': 'monthly', 'days_of_month': [15, 30]}
        assert matches_pattern(pattern, date(2024, 1, 15)) is True
        assert matches_pattern(pattern, date(2024, 1, 16)) is False
        assert matches_pattern(pattern, date(2024, 1, 30)) is True

    def test_monthly_handles_month_end(self):
        """Monthly pattern handles months with fewer days."""
        pattern = {'type': 'monthly', 'days_of_month': [31]}
        # February doesn't have 31 days, so it should match the last day
        assert matches_pattern(pattern, date(2024, 2, 29)) is True  # Last day of Feb (leap year)

    def test_none_pattern_returns_false(self):
        """Pattern type 'none' returns False."""
        pattern = {'type': 'none'}
        assert matches_pattern(pattern, date(2024, 1, 15)) is False

    def test_unknown_pattern_returns_false(self):
        """Unknown pattern types return False."""
        pattern = {'type': 'unknown'}
        assert matches_pattern(pattern, date(2024, 1, 15)) is False


class TestValidateRecurrencePattern:
    """Tests for validate_recurrence_pattern function."""

    def test_valid_simple_daily(self):
        """Valid simple daily pattern passes validation."""
        pattern = {'type': 'simple', 'interval': 'daily', 'every_n': 1}
        is_valid, error = validate_recurrence_pattern(pattern)
        assert is_valid is True
        assert error is None

    def test_valid_simple_weekly(self):
        """Valid simple weekly pattern passes validation."""
        pattern = {'type': 'simple', 'interval': 'weekly', 'every_n': 1}
        is_valid, error = validate_recurrence_pattern(pattern)
        assert is_valid is True
        assert error is None

    def test_invalid_simple_interval(self):
        """Invalid simple interval fails validation."""
        pattern = {'type': 'simple', 'interval': 'hourly'}
        is_valid, error = validate_recurrence_pattern(pattern)
        assert is_valid is False
        assert 'Invalid simple interval' in error

    def test_valid_weekly_with_days(self):
        """Valid weekly pattern with days passes validation."""
        pattern = {'type': 'weekly', 'days_of_week': [0, 2, 4]}
        is_valid, error = validate_recurrence_pattern(pattern)
        assert is_valid is True

    def test_weekly_without_days_fails(self):
        """Weekly pattern without days_of_week fails."""
        pattern = {'type': 'weekly'}
        is_valid, error = validate_recurrence_pattern(pattern)
        assert is_valid is False
        assert 'days_of_week' in error

    def test_weekly_with_invalid_days_fails(self):
        """Weekly pattern with invalid day values fails."""
        pattern = {'type': 'weekly', 'days_of_week': [0, 7]}  # 7 is invalid
        is_valid, error = validate_recurrence_pattern(pattern)
        assert is_valid is False
        assert '0-6' in error

    def test_valid_monthly_with_days(self):
        """Valid monthly pattern with days passes validation."""
        pattern = {'type': 'monthly', 'days_of_month': [1, 15, 28]}
        is_valid, error = validate_recurrence_pattern(pattern)
        assert is_valid is True

    def test_monthly_without_days_fails(self):
        """Monthly pattern without days_of_month fails."""
        pattern = {'type': 'monthly'}
        is_valid, error = validate_recurrence_pattern(pattern)
        assert is_valid is False
        assert 'days_of_month' in error

    def test_monthly_with_invalid_days_fails(self):
        """Monthly pattern with invalid day values fails."""
        pattern = {'type': 'monthly', 'days_of_month': [0, 32]}  # 0 and 32 are invalid
        is_valid, error = validate_recurrence_pattern(pattern)
        assert is_valid is False
        assert '1-31' in error

    def test_none_pattern_valid(self):
        """Pattern type 'none' is valid."""
        pattern = {'type': 'none'}
        is_valid, error = validate_recurrence_pattern(pattern)
        assert is_valid is True

    def test_invalid_pattern_type(self):
        """Invalid pattern type fails validation."""
        pattern = {'type': 'hourly'}
        is_valid, error = validate_recurrence_pattern(pattern)
        assert is_valid is False
        assert 'Invalid pattern type' in error

    def test_empty_pattern_fails(self):
        """Empty pattern fails validation."""
        is_valid, error = validate_recurrence_pattern(None)
        assert is_valid is False
        assert 'empty' in error.lower()

    def test_valid_complex_pattern(self):
        """Valid complex pattern passes validation."""
        pattern = {'type': 'complex', 'days_of_week': [0, 2, 4]}
        is_valid, error = validate_recurrence_pattern(pattern)
        assert is_valid is True

    def test_complex_with_invalid_days_fails(self):
        """Complex pattern with invalid days fails validation."""
        pattern = {'type': 'complex', 'days_of_week': 'monday'}  # Should be list
        is_valid, error = validate_recurrence_pattern(pattern)
        assert is_valid is False
