# app/utils/decorators.py
from functools import wraps
from flask_jwt_extended import verify_jwt_in_request # Keep verify_jwt_in_request
# Removed get_jwt_identity as we now use custom claims via helpers
from flask import jsonify
from app.models import User, UserRole
# --- BEGIN FIX ---
# Import the updated helpers, including get_current_user_role
from app.utils.helpers import get_current_user_claims, get_current_user_id, get_current_user_role
# --- END FIX ---

# Helper to get user object using ID from claims
def get_user_from_claims():
    # ... (function body remains the same) ...
    user_id = get_current_user_id() # Use helper to get ID from claims
    if user_id is not None:
         print(f"--- Inside get_user_from_claims: Querying for user ID {user_id} ---")
         user = User.query.get(user_id) # Query using ID from claims
         if not user:
             print(f"!!! User with ID {user_id} from claims not found in database.")
         return user
    else:
         print(f"!!! Failed to get user ID from claims in get_user_from_claims.")
         return None

# Decorator to require a specific role (using claims)
def role_required(required_role_enum):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            print(f"\n>>> Entering role_required wrapper for role: {required_role_enum.name}")
            try:
                verify_jwt_in_request()

                # Get role string from custom claims using helper (Now imported)
                user_role_str = get_current_user_role()
                print(f"--- Inside role_required ({required_role_enum.name}): Role from claims: {user_role_str} ---")

                if not user_role_str:
                     print(f"!!! Role could not be determined from JWT claims.")
                     return jsonify({"msg": "Unauthorized: Role information missing in token."}), 401

                if user_role_str != required_role_enum.name:
                    print(f"!!! Role mismatch in role_required. Expected: {required_role_enum.name}, Found in claims: {user_role_str}")
                    return jsonify({"msg": f"Forbidden: {required_role_enum.value} role required"}), 403

                print(f"<<< Role check PASSED for {required_role_enum.name}. Proceeding to wrapped function: {fn.__name__}")
                return fn(*args, **kwargs)

            except Exception as e:
                 print(f"!!! Exception during role_required ({required_role_enum.name}): {e}")
                 # import traceback; traceback.print_exc()
                 return jsonify({"msg": "Authorization error"}), 401
        return wrapper
    return decorator

# Specific role decorators remain the same
admin_required = role_required(UserRole.ADMIN)
teacher_required = role_required(UserRole.TEACHER)
student_required = role_required(UserRole.STUDENT)

# Decorator to require verification (using claims to get user ID)
def verified_required(fn):
     @wraps(fn)
     def wrapper(*args, **kwargs):
        # ... (function body remains the same, using get_user_from_claims) ...
        print(f"\n>>> Entering verified_required wrapper")
        try:
            verify_jwt_in_request()
            user = get_user_from_claims()
            print(f"--- Inside verified_required: Fetched user object: {'Exists' if user else 'Not Found'} ---")

            if not user:
                print(f"!!! User object not found or get_user_from_claims failed in verified_required")
                return jsonify({"msg": "Unauthorized: User not found or invalid token."}), 401

            if not user.is_verified:
                print(f"!!! User {user.email} (ID: {user.id}) is not verified in verified_required")
                return jsonify({"msg": "Forbidden: Account not verified"}), 403

            print(f"<<< Verification check PASSED for user {user.id}. Proceeding to wrapped function: {fn.__name__}")
            return fn(*args, **kwargs)

        except Exception as e:
             print(f"!!! Exception during verified_required: {e}")
             # import traceback; traceback.print_exc()
             return jsonify({"msg": "Authorization error"}), 401
     return wrapper