# app/utils/helpers.py

from flask_jwt_extended import get_jwt
# Standard datetime library (might be needed for parsing elsewhere, but format_datetime uses the object directly)
from datetime import datetime

# Removed pendulum and timezone imports

def format_datetime(dt):
    """Formats a naive datetime object as an ISO string. Returns None if dt is None."""
    if dt is None:
        return None
    if not isinstance(dt, datetime):
        # Add a check in case something else is passed
        print(f"!!! WARNING: format_datetime received non-datetime object: {type(dt)}. Returning None.")
        return None
    # isoformat() on a naive datetime produces a string without timezone info,
    # which is standard for representing naive UTC.
    # Example: 2023-10-27T10:30:00
    return dt.isoformat()

# --- JWT Helper Functions (No changes needed) ---

def get_current_user_id():
    """Extracts user ID from the 'user_info' claim in the JWT."""
    try:
        jwt_data = get_jwt()
        user_info = jwt_data.get('user_info', {})
        user_id = user_info.get('id')
        if user_id is not None:
             # Optionally convert to int if your model ID is integer
             # return int(user_id)
             return user_id # Assuming ID is stored/used as comes from token (usually int or string)
        else:
            print("!!! WARNING: User ID not found in JWT 'user_info' claim.")
            return None
    except Exception as e:
        # Catch potential errors during JWT processing, although flask_jwt_extended usually handles basic validation
        print(f"!!! ERROR: Exception while getting user ID from JWT: {e}")
        return None

def get_current_user_role():
    """Extracts user role from the 'user_info' claim in the JWT."""
    try:
        jwt_data = get_jwt()
        user_info = jwt_data.get('user_info', {})
        role = user_info.get('role')
        if role:
            return role # Returns the role string (e.g., 'Admin', 'Teacher')
        else:
            print("!!! WARNING: User role not found in JWT 'user_info' claim.")
            return None
    except Exception as e:
        print(f"!!! ERROR: Exception while getting user role from JWT: {e}")
        return None

def get_current_user_claims():
    """Returns the entire 'user_info' dictionary from the JWT claims."""
    try:
        jwt_data = get_jwt()
        return jwt_data.get('user_info', {})
    except Exception as e:
        print(f"!!! ERROR: Exception while getting user claims from JWT: {e}")
        return {} # Return empty dict on error