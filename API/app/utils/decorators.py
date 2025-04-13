# app/utils/decorators.py
from functools import wraps
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from flask import jsonify
# Ensure models are imported correctly
from app.models import User, UserRole

# Helper to get user object from JWT identity (with debug prints)
def get_user_from_jwt():
    # ---- DEBUG PRINT ----
    identity_in_get_user = None # Initialize
    try:
        identity_in_get_user = get_jwt_identity()
        print(f"\n--- Inside get_user_from_jwt ---")
        print(f"Identity type: {type(identity_in_get_user)}")
        print(f"Identity value: {identity_in_get_user}")
        print(f"------------------------------")
    except Exception as e:
        print(f"!!! Exception getting identity in get_user_from_jwt: {e}")
        return None # Return None on error getting identity
    # ---- END DEBUG ----

    if isinstance(identity_in_get_user, dict) and 'id' in identity_in_get_user:
        user_id = identity_in_get_user['id']
        # Query user by ID
        user = User.query.get(user_id)
        if not user:
             print(f"!!! User with ID {user_id} not found in database (called from get_user_from_jwt).")
        return user
    else:
        print(f"!!! Unexpected JWT identity format in get_user_from_jwt: {identity_in_get_user}")
        return None

# Decorator to require a specific role (with debug prints)
def role_required(required_role):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # ---- DEBUG PRINT ---
            print(f"\n>>> Entering role_required wrapper for role: {required_role.name}")
            # --- END DEBUG ---
            try:
                # verify_jwt_in_request() ensures token is valid and identity is loaded
                verify_jwt_in_request()
                # ---- DEBUG PRINT ----
                identity_in_role_required = None # Initialize
                try:
                    identity_in_role_required = get_jwt_identity()
                    print(f"--- Inside role_required ({required_role.name}) AFTER verify_jwt_in_request ---")
                    print(f"Identity type: {type(identity_in_role_required)}")
                    print(f"Identity value: {identity_in_role_required}")
                    print(f"-----------------------------------------------------------------------")
                except Exception as e:
                    print(f"!!! Exception getting identity in role_required ({required_role.name}): {e}")
                # ---- END DEBUG ----

                # Now get the user object using the helper
                user = get_user_from_jwt() # Calls the helper which also prints

                if not user:
                     # This could happen if token is valid but user deleted, or get_user_from_jwt failed
                     print(f"!!! User object not found or get_user_from_jwt failed in role_required ({required_role.name})")
                     # Return forbidden early if user couldn't be loaded
                     return jsonify({"msg": "Unauthorized: User not found or invalid token identity."}), 401

                # Check the role
                if user.role != required_role:
                    print(f"!!! Role mismatch in role_required ({required_role.name}). Expected: {required_role.name}, Found: {user.role.name}")
                    return jsonify({"msg": f"Forbidden: {required_role.value} role required"}), 403

                # Role check passed, proceed to the actual route function
                print(f"<<< Role check PASSED for {required_role.name}. Proceeding to wrapped function: {fn.__name__}")
                return fn(*args, **kwargs)

            except Exception as e:
                 # Catch potential errors from verify_jwt_in_request itself (e.g., invalid token format)
                 # Although the "Subject must be string" seems to happen later
                 print(f"!!! Exception during verify_jwt_in_request or user check in role_required ({required_role.name}): {e}")
                 # Provide a generic unauthorized error for JWT issues caught here
                 # Check specific exception types if needed (e.g., NoAuthorizationError, InvalidHeaderError from jwt lib)
                 # import traceback; traceback.print_exc() # Uncomment for detailed traceback
                 return jsonify({"msg": "Authorization error"}), 401

        return wrapper
    return decorator

# Specific role decorators (easier to use)
admin_required = role_required(UserRole.ADMIN)
teacher_required = role_required(UserRole.TEACHER)
student_required = role_required(UserRole.STUDENT)

# Decorator to require verification (with debug prints)
def verified_required(fn):
     @wraps(fn)
     def wrapper(*args, **kwargs):
        # ---- DEBUG PRINT ---
        print(f"\n>>> Entering verified_required wrapper")
        # --- END DEBUG ---
        try:
            # Ensure JWT is verified first (redundant if used after @jwt_required, but safe)
            verify_jwt_in_request()
            # ---- DEBUG PRINT ----
            identity_in_verified = None # Initialize
            try:
                identity_in_verified = get_jwt_identity()
                print(f"--- Inside verified_required AFTER verify_jwt_in_request ---")
                print(f"Identity type: {type(identity_in_verified)}")
                print(f"Identity value: {identity_in_verified}")
                print(f"---------------------------------------------------------")
            except Exception as e:
                print(f"!!! Exception getting identity in verified_required: {e}")
            # ---- END DEBUG ----

            user = get_user_from_jwt() # Calls the helper which also prints

            if not user:
                print(f"!!! User object not found or get_user_from_jwt failed in verified_required")
                return jsonify({"msg": "Unauthorized: User not found or invalid token identity."}), 401

            if not user.is_verified:
                print(f"!!! User {user.email} is not verified in verified_required")
                return jsonify({"msg": "Forbidden: Account not verified"}), 403

            # Verification check passed
            print(f"<<< Verification check PASSED. Proceeding to wrapped function: {fn.__name__}")
            return fn(*args, **kwargs)

        except Exception as e:
             print(f"!!! Exception during verify_jwt_in_request or user check in verified_required: {e}")
             # import traceback; traceback.print_exc() # Uncomment for detailed traceback
             return jsonify({"msg": "Authorization error"}), 401
     return wrapper