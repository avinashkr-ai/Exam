# app/routes/auth.py
from flask import Blueprint, request, jsonify
from app import db # Corrected: Import db from app
from app.models import User, UserRole
from werkzeug.security import check_password_hash
from flask_jwt_extended import (
    create_access_token, jwt_required, get_jwt_identity,
    # If using refresh tokens and blocklist:
    # create_refresh_token, get_jwt, JWTManager
)
# If using blocklist:
# from app.blocklist import BLOCKLIST # Assuming you create a blocklist.py

bp = Blueprint('auth', __name__)

# ... (register, login, refresh, get_me functions remain the same as your provided file) ...
# Ensure login uses: from app.extensions import db
# Ensure register uses: from app.extensions import db

@bp.route('/register', methods=['POST'])
def register():
    # Use code from your provided file, ensuring db is imported correctly
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    role_str = data.get('role', 'Student').capitalize() # Default to Student

    if not name or not email or not password:
        return jsonify({"msg": "Missing name, email, or password"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"msg": "Email already registered"}), 409

    try:
        # Ensure UserRole is imported
        role = UserRole[role_str.upper()]
    except KeyError:
        return jsonify({"msg": "Invalid role specified. Choose Admin, Teacher, or Student."}), 400

    is_verified = (role == UserRole.ADMIN) # Auto-verify admin

    new_user = User(name=name, email=email, role=role, is_verified=is_verified)
    new_user.set_password(password) # Ensure set_password uses correct hashing

    # Make sure db is imported correctly, e.g., from app.extensions import db
    db.session.add(new_user)
    db.session.commit()

    # Return user details on registration might be a security risk, just confirm.
    return jsonify({
        "msg": "User registered successfully. Awaiting verification if applicable.",
        "user": {"id": new_user.id, "name": new_user.name, "email": new_user.email, "role": new_user.role.name} # Optional: return basic info
        }), 201


@bp.route('/login', methods=['POST'])
def login():
    # Use code from your provided file, ensuring db is imported correctly
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"msg": "Missing email or password"}), 400

    user = User.query.filter_by(email=email).first()

    if user and user.check_password(password):
        if not user.is_verified:
             return jsonify({"msg": "Account not verified by admin yet. Please contact support."}), 403 # Changed message slightly

        # Create identity including role
        identity = {
            'id': user.id,
            'role': user.role.name
        }
        access_token = create_access_token(identity=identity)
        # refresh_token = create_refresh_token(identity=identity) # If using refresh tokens

        return jsonify(access_token=access_token), 200
        # return jsonify(access_token=access_token, refresh_token=refresh_token), 200

    return jsonify({"msg": "Invalid email or password"}), 401


@bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True) # Ensure refresh=True if using refresh tokens
def refresh():
    identity = get_jwt_identity()
    # Recreate the same identity structure used in login if needed elsewhere
    new_access_token = create_access_token(identity=identity)
    return jsonify(access_token=new_access_token), 200


@bp.route('/me', methods=['GET'])
@jwt_required()
def get_me():
    # Use the fixed get_current_user_id helper is better practice
    # current_user_id = get_current_user_id() # Requires importing helper
    # Or get identity directly and fetch user
    user_identity = get_jwt_identity()
    if not isinstance(user_identity, dict) or 'id' not in user_identity:
         return jsonify({"msg": "Invalid token identity."}), 401

    user = User.query.get(user_identity['id'])
    if not user:
        # This might happen if user deleted after token issued
        return jsonify({"msg": "User not found for this token."}), 404

    return jsonify({
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role.name,
        "is_verified": user.is_verified
    }), 200


@bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """
    Basic logout endpoint. For true stateless logout, implement a token blocklist.
    This basic version just confirms the client should discard the token.
    """
    # --- If using a blocklist (Recommended) ---
    # from app.blocklist import BLOCKLIST # Assumes you have blocklist.py
    # jwt_data = get_jwt()
    # jti = jwt_data['jti']
    # BLOCKLIST.add(jti)
    # return jsonify({"msg": "Successfully logged out. Token revoked."}), 200
    # --- End Blocklist ---

    # --- Basic version (Client responsibility) ---
    # You can optionally get user identity to log the logout action
    user_identity = get_jwt_identity()
    user_id = user_identity.get('id') if isinstance(user_identity, dict) else None
    print(f"User {user_id} initiated logout.") # Server-side logging

    return jsonify({"msg": "Logout successful. Please discard your token."}), 200