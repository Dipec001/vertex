import calendar
import unittest
from datetime import datetime, timedelta

from myapp.utils import get_date_range


class MyTestCase(unittest.TestCase):
    # Tests
    def test_this_week(self):
        today = datetime.today().date()
        this_week_dates = get_date_range("this_week")
        assert len(this_week_dates) == 7, "Should return 7 dates for this week"
        assert this_week_dates[0] == today - timedelta(
            days=today.weekday()), "First date should be the start of the week"

    def test_this_month(self):
        today = datetime.today().date()
        this_month_dates = get_date_range("this_month")
        start_of_month = today.replace(day=1)
        _, last_day = calendar.monthrange(today.year, today.month)
        end_of_month = start_of_month + timedelta(days=last_day - 1)
        assert this_month_dates[0] == start_of_month, "First date should be the start of the month"
        assert this_month_dates[-1] == end_of_month, "Last date should be the end of the month"

    def test_last_week(self):
        today = datetime.today().date()
        last_week_dates = get_date_range("last_week")
        start_of_last_week = today - timedelta(days=today.weekday() + 7)
        assert len(last_week_dates) == 7, "Should return 7 dates for last week"
        assert last_week_dates[0] == start_of_last_week, "First date should be the start of the last week"

    def test_invalid_interval(self):
        try:
            get_date_range("invalid")
        except ValueError as e:
            assert str(e) == "Invalid interval. Choices are: 'this_week', 'this_month', 'last_week'."
        else:
            assert False, "Should raise ValueError for invalid interval"


if __name__ == '__main__':
    unittest.main()
