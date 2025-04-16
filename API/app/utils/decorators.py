# app/utils/decorators.py

from functools import wraps
from flask_jwt_extended import verify_jwt_in_request # Verifies JWT presence and validity
from flask import jsonify
from app.models import User, UserRole # Import User model for DB lookups
# Import helper functions to get user details from verified JWT claims
from app.utils.helpers import get_current_user_id, get_current_user_role

# Helper function (internal to this module or could be moved to helpers if used elsewhere)
# to fetch the User object based on the ID found in the JWT claims.
def _get_user_from_verified_claims():
    """
    Retrieves the User object from DB based on the ID in verified JWT claims.
    Should only be called *after* verify_jwt_in_request().
    Returns User object or None.
    """
    user_id = get_current_user_id() # Get ID from claims
    if user_id is not None:
         try:
             # Attempt to query the database for the user
             # Ensure user_id type matches User.id type (e.g., handle int conversion if needed)
             user = User.query.get(int(user_id))
             if user:
                 print(f"--- Decorator helper: Found user {user.id} from claims ---")
                 return user
             else:
                 print(f"!!! Decorator helper: User with ID {user_id} from claims NOT found in DB.")
                 return None
         except ValueError:
             print(f"!!! Decorator helper: Could not convert user ID '{user_id}' from claims to integer.")
             return None
         except Exception as e:
             print(f"!!! Decorator helper: DB Error fetching user {user_id}: {e}")
             return None # Treat DB errors as failure to find user
    else:
         print(f"!!! Decorator helper: Failed to get user ID from claims.")
         return None

# --- Role Required Decorator ---
def role_required(required_role_enum):
    """
    Decorator factory to ensure a user has a specific role.
    Requires a valid JWT verified by verify_jwt_in_request() first.
    Args:
        required_role_enum (UserRole): The enum member (e.g., UserRole.ADMIN).
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            print(f"\n>>> Entering role_required decorator for: {required_role_enum.name}")
            # 1. Verify JWT is present and valid (signature, expiry)
            try:
                verify_jwt_in_request()
            except Exception as e:
                 # Handles errors like missing token, expired token, invalid signature etc.
                 print(f"!!! JWT verification failed in role_required: {e}")
                 # Customize message based on exception type if needed
                 return jsonify({"msg": "Authorization Error: Invalid or missing token."}), 401

            # 2. Get user's role from the verified JWT's claims
            user_role_str = get_current_user_role()
            print(f"--- Role from claims: {user_role_str} ---")

            if not user_role_str:
                 print(f"!!! Role missing in JWT claims.")
                 # This shouldn't happen if token creation includes the role claim
                 return jsonify({"msg": "Unauthorized: Role information missing."}), 401

            # 3. Check if the role matches the required role
            if user_role_str != required_role_enum.name:
                print(f"!!! Role mismatch. Required: {required_role_enum.name}, Found: {user_role_str}")
                return jsonify({"msg": f"Forbidden: Access restricted to {required_role_enum.value}."}), 403

            # 4. Role matches, proceed to the wrapped function
            print(f"<<< Role check PASSED ({required_role_enum.name}). Proceeding to: {fn.__name__}")
            return fn(*args, **kwargs)
        return wrapper
    return decorator

# --- Specific Role Decorators (using the factory) ---
admin_required = role_required(UserRole.ADMIN)
teacher_required = role_required(UserRole.TEACHER)
student_required = role_required(UserRole.STUDENT)

# --- Verified Account Required Decorator ---
def verified_required(fn):
    """
    Decorator to ensure the user associated with the JWT is verified in the database.
    Requires a valid JWT verified by verify_jwt_in_request() first.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        print(f"\n>>> Entering verified_required decorator")
        # 1. Verify JWT is present and valid
        try:
            verify_jwt_in_request()
        except Exception as e:
             print(f"!!! JWT verification failed in verified_required: {e}")
             return jsonify({"msg": "Authorization Error: Invalid or missing token."}), 401

        # 2. Get the user object from DB based on verified JWT claims
        user = _get_user_from_verified_claims()

        if not user:
            # This case handles:
            # - User ID missing/invalid in claims
            # - User ID in claims but user deleted from DB since token issuance
            # - DB error during lookup
            print(f"!!! User object could not be retrieved from DB in verified_required.")
            # Return 401 as the token might be valid but doesn't map to a current user
            return jsonify({"msg": "Unauthorized: User associated with token not found or invalid."}), 401

        # 3. Check the user's verification status
        if not user.is_verified:
            print(f"!!! User {user.email} (ID: {user.id}) is not verified.")
            return jsonify({"msg": "Forbidden: Your account requires verification by an administrator."}), 403

        # 4. User is verified, proceed to the wrapped function
        print(f"<<< Verification check PASSED for user {user.id}. Proceeding to: {fn.__name__}")
        return fn(*args, **kwargs)
    return wrapper

# No changes were required here as decorators operate on JWT claims and DB lookups,
# independent of the internal datetime storage format.