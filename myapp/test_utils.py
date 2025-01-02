import calendar
import unittest
from datetime import datetime, timedelta

from myapp.utils import get_date_range, get_last_day_and_first_day_of_this_month


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

    def test_get_last_day_and_first_day_of_february_leap_year(self):
        # Mock datetime to control the current date
        with unittest.mock.patch('myapp.utils.datetime') as mock_datetime:
            # Set the date to a leap year February
            mock_datetime.now.return_value = datetime(2020, 2, 15)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            first_day, last_day = get_last_day_and_first_day_of_this_month()

            # Assert the first day is February 1st
            self.assertEqual(first_day, datetime(2020, 2, 1))

            # Assert the last day is February 29th
            self.assertEqual(last_day, datetime(2020, 2, 29))

    def test_get_last_day_and_first_day_of_january(self):
        # Mock datetime to control the current date
        with unittest.mock.patch('myapp.utils.datetime') as mock_datetime:
            # Set the date to a month with 31 days (e.g., January)
            mock_datetime.now.return_value = datetime(2023, 1, 15)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            first_day, last_day = get_last_day_and_first_day_of_this_month()

            # Assert the first day is January 1st
            self.assertEqual(first_day, datetime(2023, 1, 1))

            # Assert the last day is January 31st
            self.assertEqual(last_day, datetime(2023, 1, 31))

    def test_first_day_of_month_is_first(self):
        # Mock datetime to control the current date
        with unittest.mock.patch('myapp.utils.datetime') as mock_datetime:
            # Set the date to any day of a month
            mock_datetime.now.return_value = datetime(2023, 5, 15)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            first_day, _ = get_last_day_and_first_day_of_this_month()

            # Assert the first day is the 1st of the month
            self.assertEqual(first_day.day, 1, "First day of the month should be the 1st")

    def test_last_day_of_month_matches_expected(self):
        # Mock datetime to control the current date
        with unittest.mock.patch('myapp.utils.datetime') as mock_datetime:
            # Set the date to a month with 28 days (e.g., February in a non-leap year)
            mock_datetime.now.return_value = datetime(2021, 2, 15)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            first_day, last_day = get_last_day_and_first_day_of_this_month()

            # Assert the last day is February 28th
            self.assertEqual(last_day, datetime(2021, 2, 28))

    def test_transition_from_december_to_january(self):
        # Mock datetime to control the current date
        with unittest.mock.patch('myapp.utils.datetime') as mock_datetime:
            # Set the date to December 31st
            mock_datetime.now.return_value = datetime(2021, 12, 31)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            first_day, last_day = get_last_day_and_first_day_of_this_month()

            # Assert the first day is December 1st
            self.assertEqual(first_day, datetime(2021, 12, 1))

            # Assert the last day is December 31st
            self.assertEqual(last_day, datetime(2021, 12, 31))

    def test_transition_from_july_to_august(self):
        # Mock datetime to control the current date
        with unittest.mock.patch('myapp.utils.datetime') as mock_datetime:
            # Set the date to July 31st
            mock_datetime.now.return_value = datetime(2023, 7, 31)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            first_day, last_day = get_last_day_and_first_day_of_this_month()

            # Assert the first day is July 1st
            self.assertEqual(first_day, datetime(2023, 7, 1))

            # Assert the last day is July 31st
            self.assertEqual(last_day, datetime(2023, 7, 31))

    def test_transition_from_april_to_may(self):
        # Mock datetime to control the current date
        with unittest.mock.patch('myapp.utils.datetime') as mock_datetime:
            # Set the date to April 30th
            mock_datetime.now.return_value = datetime(2023, 4, 30)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            first_day, last_day = get_last_day_and_first_day_of_this_month()

            # Assert the first day is April 1st
            self.assertEqual(first_day, datetime(2023, 4, 1))

            # Assert the last day is April 30th
            self.assertEqual(last_day, datetime(2023, 4, 30))

    def test_function_on_last_day_of_month(self):
        # Mock datetime to control the current date
        with unittest.mock.patch('myapp.utils.datetime') as mock_datetime:
            # Set the date to the last day of a month with 31 days (e.g., January 31st)
            mock_datetime.now.return_value = datetime(2023, 1, 31)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            first_day, last_day = get_last_day_and_first_day_of_this_month()

            # Assert the first day is January 1st
            self.assertEqual(first_day, datetime(2023, 1, 1))

            # Assert the last day is January 31st
            self.assertEqual(last_day, datetime(2023, 1, 31))

    def test_get_last_day_and_first_day_of_april(self):
        # Mock datetime to control the current date
        with unittest.mock.patch('myapp.utils.datetime') as mock_datetime:
            # Set the date to April of a non-leap year
            mock_datetime.now.return_value = datetime(2021, 4, 15)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            first_day, last_day = get_last_day_and_first_day_of_this_month()

            # Assert the first day is April 1st
            self.assertEqual(first_day, datetime(2021, 4, 1))

            # Assert the last day is April 30th
            self.assertEqual(last_day, datetime(2021, 4, 30))

    def test_invalid_interval(self):
        try:
            get_date_range("invalid")
        except ValueError as e:
            assert str(e) == "Invalid interval. Choices are: 'this_week', 'this_month', 'last_week'."
        else:
            assert False, "Should raise ValueError for invalid interval"


if __name__ == '__main__':
    unittest.main()
