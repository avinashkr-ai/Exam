from flask_jwt_extended import get_jwt
import pendulum

# Define IST timezone (kept for other uses, if needed)
IST = pendulum.timezone('Asia/Kolkata')

def format_datetime(dt):
    """Formats a datetime object as ISO string without timezone conversion."""
    if dt is None:
        return None
    # Return naive datetime as-is in ISO format
    return dt.isoformat()

# Existing JWT helper functions
def get_current_user_id():
    jwt = get_jwt()
    user_info = jwt.get('user_info', {})
    return user_info.get('id')

def get_current_user_role():
    jwt = get_jwt()
    user_info = jwt.get('user_info', {})
    return user_info.get('role')

def get_current_user_claims():
    return get_jwt().get('user_info', {})