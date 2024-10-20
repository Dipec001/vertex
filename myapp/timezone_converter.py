from datetime import datetime
from zoneinfo import ZoneInfo
import pytz

def convert_to_utc(user_timezone_str, naive_datetime):
    """Convert a naive datetime to UTC using the user's timezone."""
    try:
        # Get the user's timezone
        user_timezone = pytz.timezone(user_timezone_str)

        # Check if the datetime is naive (no timezone info)
        if naive_datetime.tzinfo is None:
            # Use `localize` to handle daylight saving time properly
            user_aware_datetime = user_timezone.localize(naive_datetime)
        else:
            # If already aware, convert to the user's timezone
            user_aware_datetime = naive_datetime.astimezone(user_timezone)

        # Convert to UTC
        utc_datetime = user_aware_datetime.astimezone(pytz.UTC)
        
        return utc_datetime
    except Exception as e:
        # Handle errors gracefully
        print(f"Error converting to UTC: {str(e)}")
        return None


def convert_from_utc(user_timezone_str, utc_datetime):
    """Convert a UTC datetime to the user's local timezone."""
    try:
        # Use ZoneInfo if available, fallback to pytz for Python <3.9
        try:
            user_timezone = ZoneInfo(user_timezone_str)  # Get user's timezone as ZoneInfo
        except Exception:
            user_timezone = pytz.timezone(user_timezone_str)  # Fallback to pytz
        
        # Ensure the datetime is aware and in UTC before conversion
        if utc_datetime.tzinfo is None:
            raise ValueError("UTC datetime is naive. It should be timezone-aware.")
        
        # Convert UTC to local timezone
        local_datetime = utc_datetime.astimezone(user_timezone)  
        return local_datetime

    except Exception as e:
        # Handle errors gracefully, such as invalid timezone or datetime
        print(f"Error converting from UTC: {str(e)}")
        return None


# Example usage
# user_timezone_str = 'Africa/Lagos'
# naive_datetime_str = "2024-10-13T06:10:00"  # Example naive datetime

# # Convert the string to a datetime object
# naive_datetime = datetime.strptime(naive_datetime_str, "%Y-%m-%dT%H:%M:%S")
# print(naive_datetime)
# print(type(naive_datetime))

# # Convert naive datetime to UTC
# utc_datetime = convert_to_utc(user_timezone_str, naive_datetime)
# print("UTC Datetime:", utc_datetime)

# # Convert back to user's local timezone
# local_datetime = convert_from_utc(user_timezone_str, utc_datetime)
# print("Local Datetime:", local_datetime)
