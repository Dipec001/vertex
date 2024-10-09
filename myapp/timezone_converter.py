from datetime import datetime
from zoneinfo import ZoneInfo

def convert_to_utc(user_timezone_str, naive_datetime):
    """Convert a naive datetime to UTC using the user's timezone."""
    user_timezone = ZoneInfo(user_timezone_str)  # Get the user's timezone as ZoneInfo
    
    # Check if the datetime is naive
    if naive_datetime.tzinfo is None:  
        # Assign user's timezone if naive
        user_aware_datetime = naive_datetime.replace(tzinfo=user_timezone)
    else:
        # Convert to user's timezone if already aware
        user_aware_datetime = naive_datetime.astimezone(user_timezone)  
    
    # Convert to UTC
    utc_datetime = user_aware_datetime.astimezone(ZoneInfo('UTC'))  
    return utc_datetime  # Return UTC datetime

def convert_from_utc(user_timezone_str, utc_datetime):
    """Convert a UTC datetime to the user's local timezone."""
    user_timezone = ZoneInfo(user_timezone_str)  # Get the user's timezone as ZoneInfo
    
    # Convert UTC to local timezone
    local_datetime = utc_datetime.astimezone(user_timezone)  
    return local_datetime  # Return local datetime



# Example usage
user_timezone_str = 'Africa/Lagos'
naive_datetime = datetime(2024, 10, 9, 15, 0)  # Example naive datetime

# Convert naive datetime to UTC
utc_datetime = convert_to_utc(user_timezone_str, naive_datetime)
print("UTC Datetime:", utc_datetime)

# Convert back to user's local timezone
local_datetime = convert_from_utc(user_timezone_str, utc_datetime)
print("Local Datetime:", local_datetime)
