# app/routes/auth.py

from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models import User, UserRole # Import necessary models
from werkzeug.security import check_password_hash # For checking passwords
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt # JWT functions
# Import the updated helper for formatting naive UTC datetimes
from app.utils.helpers import format_datetime
from datetime import datetime # Although not directly used for NOW, good practice to have if needed

bp = Blueprint('auth', __name__)

@bp.route('/register', methods=['POST'])
def register():
    """Handles new user registration."""
    data = request.get_json()
    if not data:
        return jsonify({"msg": "Missing JSON in request"}), 400

    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    # Default to 'Student' if role is not provided, ensure it's capitalized
    role_str = data.get('role', 'Student').strip().capitalize()

    # Validate required fields
    if not name or not email or not password:
        return jsonify({"msg": "Missing required fields: name, email, or password"}), 400

    # Validate email format (basic check)
    if '@' not in email or '.' not in email.split('@')[-1]:
         return jsonify({"msg": "Invalid email format"}), 400

    # Check if email already exists
    if User.query.filter_by(email=email).first():
        return jsonify({"msg": "Email address already registered"}), 409 # Conflict

    # Validate role string against UserRole enum
    try:
        # Convert role string (e.g., "Teacher") to enum member (UserRole.TEACHER)
        role = UserRole[role_str.upper()]
    except KeyError:
        valid_roles = [r.value for r in UserRole]
        return jsonify({"msg": f"Invalid role specified. Choose from: {', '.join(valid_roles)}"}), 400

    # Determine verification status (only Admin is auto-verified)
    is_verified = (role == UserRole.ADMIN)

    # Create new User instance
    new_user = User(name=name, email=email, role=role, is_verified=is_verified)
    new_user.set_password(password) # Hashes the password before saving

    try:
        # Add user to session and commit to database
        db.session.add(new_user)
        db.session.commit()
        print(f"--- User registered successfully: {email}, Role: {role.name}, Verified: {is_verified} ---")

        # Format the created_at timestamp (which is naive UTC from DB) using the helper
        created_at_iso = format_datetime(new_user.created_at)

        # Return success message and basic user info (excluding password hash)
        return jsonify({
            "msg": "User registered successfully. Verification may be required.",
            "user": {
                "id": new_user.id,
                "name": new_user.name,
                "email": new_user.email,
                "role": new_user.role.name,
                "is_verified": new_user.is_verified,
                "created_at_utc": created_at_iso # Indicate it's UTC
            }
        }), 201 # Status code for resource created
    except Exception as e:
        # Rollback database changes in case of error
        db.session.rollback()
        print(f"!!! Error during user registration for {email}: {e}")
        # Log the detailed error e for debugging
        return jsonify({"msg": "Failed to register user due to a server error."}), 500

@bp.route('/login', methods=['POST'])
def login():
    """Handles user login and JWT creation."""
    data = request.get_json()
    if not data:
        return jsonify({"msg": "Missing JSON in request"}), 400

    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"msg": "Missing email or password"}), 400

    # Find user by email
    user = User.query.filter_by(email=email).first()

    # Check if user exists and password is correct
    if user and user.check_password(password):
        # Check if the user account is verified (unless they are Admin)
        if not user.is_verified and user.role != UserRole.ADMIN:
            print(f"--- Login attempt failed for unverified user: {email} ---")
            return jsonify({"msg": "Account requires verification by an administrator. Please contact support."}), 403 # Forbidden

        # Create custom claims to include in the JWT payload
        user_claims = {
            'id': user.id, # Include user ID
            'role': user.role.name # Include user role string
            # Add other non-sensitive info if needed (e.g., 'name': user.name)
        }

        # Create the JWT access token including the custom claims
        # The identity can be the user ID (as string or int)
        access_token = create_access_token(
            identity=str(user.id), # Standard practice to use user ID as identity
            additional_claims={'user_info': user_claims} # Embed custom data
        )
        print(f"--- Login successful for user ID {user.id} ({user.email}). Token created. ---")
        # Return the access token to the client
        return jsonify(access_token=access_token), 200

    # If user not found or password incorrect
    print(f"--- Login attempt failed for email: {email} (Invalid credentials) ---")
    return jsonify({"msg": "Invalid email or password"}), 401 # Unauthorized

@bp.route('/me', methods=['GET'])
@jwt_required() # Ensures a valid JWT is present in the request header
def get_me():
    """Returns information about the currently authenticated user."""
    # Get the claims dictionary embedded in the token during login
    jwt_payload = get_jwt()
    user_info = jwt_payload.get('user_info') # Access our custom 'user_info' claim

    # Validate that our custom claims structure is present
    if not user_info or 'id' not in user_info or 'role' not in user_info:
        print(f"!!! '/me' endpoint: Missing or incomplete 'user_info' claim in JWT: {jwt_payload}")
        # This indicates an issue with token creation or a malformed token
        return jsonify({"msg": "Invalid token structure: Missing user information."}), 401

    # Fetch the full user object from the database using the ID from the token
    # It's good practice to re-fetch to ensure data is current and user hasn't been deleted/modified
    try:
        user = User.query.get(int(user_info['id'])) # Convert ID from claim if necessary
    except ValueError:
        print(f"!!! '/me' endpoint: Invalid user ID format in token: {user_info['id']}")
        return jsonify({"msg": "Invalid user identifier in token."}), 401
    except Exception as e:
        print(f"!!! '/me' endpoint: DB Error fetching user {user_info['id']}: {e}")
        return jsonify({"msg": "Error retrieving user data."}), 500

    if not user:
        # User existed when token was created, but is now deleted from DB
        print(f"!!! '/me' endpoint: User ID {user_info.get('id')} from token not found in DB.")
        return jsonify({"msg": "User associated with this token no longer exists."}), 404 # Not Found

    # Format the created_at timestamp (naive UTC) using the helper
    created_at_iso = format_datetime(user.created_at)

    # Return user details (combining info from token claims and fresh DB data)
    return jsonify({
        "id": user.id, # Use fresh ID from DB object
        "name": user.name, # Use fresh name from DB object
        "email": user.email, # Use fresh email from DB object
        "role": user.role.name, # Role from DB (should match token claim)
        "is_verified": user.is_verified, # Fresh verification status from DB
        "created_at_utc": created_at_iso # Formatted naive UTC timestamp
    }), 200

@bp.route('/logout', methods=['POST'])
@jwt_required() # Requires a valid token to "logout" (client just discards token)
def logout():
    """Handles logout request (server-side does nothing for stateless JWT)."""
    # For stateless JWTs, logout is primarily handled client-side by deleting the token.
    # Server-side blocklisting could be implemented here if needed using Flask-JWT-Extended features.
    user_id = get_jwt_identity() # Get the identity from the token being "logged out"
    print(f"--- User {user_id} initiated logout request. Client should discard token. ---")
    # A simple success message is sufficient.
    return jsonify({"msg": "Logout successful. Please discard your token."}), 200