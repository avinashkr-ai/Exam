# app/utils/helpers.py
from flask_jwt_extended import get_jwt # Import get_jwt
from flask import jsonify
# Import datetime components needed for timestamp handling
from datetime import datetime, timezone

# --- Helper Function for Timezone Awareness ---
def ensure_aware_utc(dt):
    """Adds UTC timezone if datetime object is naive, or converts existing timezone to UTC."""
    if dt and dt.tzinfo is None:
        # If naive, assume it's UTC (since models use datetime.utcnow)
        return dt.replace(tzinfo=timezone.utc)
    elif dt and dt.tzinfo is not None:
        # If already aware, convert to UTC
        return dt.astimezone(timezone.utc)
    # Return None if input was None or invalid
    return dt
# --- End Helper ---


def get_current_user_claims():
    """Helper to safely get the custom 'user_info' claims dictionary from the JWT."""
    try:
        jwt_payload = get_jwt()
        user_claims = jwt_payload.get('user_info')
        if isinstance(user_claims, dict):
            return user_claims
        else:
            print(f"!!! 'user_info' claim missing or not a dict in JWT: {jwt_payload}")
            return None
    except Exception as e:
        print(f"!!! Exception getting JWT payload in get_current_user_claims: {e}")
        return None

def get_current_user_id():
    """Gets the user ID specifically from the custom claims."""
    claims = get_current_user_claims()
    if claims and 'id' in claims:
        return claims['id']
    return None

def get_current_user_role():
    """Gets the user role string specifically from the custom claims."""
    claims = get_current_user_claims()
    if claims and 'role' in claims:
        return claims['role'] # Returns 'Admin', 'Teacher', 'Student'
    return None