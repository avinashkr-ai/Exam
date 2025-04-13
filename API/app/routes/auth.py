# app/routes/auth.py
from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models import User, UserRole
from werkzeug.security import check_password_hash
from flask_jwt_extended import (
    create_access_token, jwt_required, get_jwt_identity, get_jwt
    # Removed create_refresh_token if not used, get_jwt needed for logout/claims
)
# from app.blocklist import BLOCKLIST # If using blocklist

bp = Blueprint('auth', __name__)

# ... (register function remains the same) ...
@bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    role_str = data.get('role', 'Student').capitalize()

    if not name or not email or not password:
        return jsonify({"msg": "Missing name, email, or password"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"msg": "Email already registered"}), 409

    try:
        role = UserRole[role_str.upper()]
    except KeyError:
        return jsonify({"msg": "Invalid role specified. Choose Admin, Teacher, or Student."}), 400

    is_verified = (role == UserRole.ADMIN)

    new_user = User(name=name, email=email, role=role, is_verified=is_verified)
    new_user.set_password(password)

    try:
        db.session.add(new_user)
        db.session.commit()
        return jsonify({
            "msg": "User registered successfully. Awaiting verification if applicable.",
            "user": {"id": new_user.id, "name": new_user.name, "email": new_user.email, "role": new_user.role.name}
            }), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error registering user {email}: {e}")
        return jsonify({"msg": "Failed to register user."}), 500


@bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"msg": "Missing email or password"}), 400

    user = User.query.filter_by(email=email).first()

    if user and user.check_password(password):
        if not user.is_verified:
             return jsonify({"msg": "Account not verified by admin yet. Please contact support."}), 403

        # --- BEGIN CHANGE ---
        # Define the custom payload (user claims)
        user_claims = {
            'id': user.id,
            'role': user.role.name
            # Add any other non-sensitive info needed frequently
        }

        # Set the primary identity to the STRING user ID
        access_token = create_access_token(
            identity=str(user.id),
            additional_claims={'user_info': user_claims} # Store custom claims under a key
        )
        # --- END CHANGE ---

        print(f"--- Login successful for user ID {user.id}. Token created. ---") # Add log
        return jsonify(access_token=access_token), 200

    return jsonify({"msg": "Invalid email or password"}), 401

# ... (refresh function - If used, needs similar claims logic) ...
# @bp.route('/refresh', methods=['POST'])
# @jwt_required(refresh=True)
# def refresh():
#     identity = get_jwt_identity() # This will be the string user ID
#     user = User.query.get(int(identity)) # Fetch user based on ID
#     if not user:
#          return jsonify({"msg": "User not found for refresh token"}), 401
#     # Recreate claims
#     user_claims = {'id': user.id, 'role': user.role.name}
#     new_access_token = create_access_token(
#         identity=str(user.id),
#         additional_claims={'user_info': user_claims}
#     )
#     return jsonify(access_token=new_access_token), 200


@bp.route('/me', methods=['GET'])
@jwt_required()
def get_me():
    # --- BEGIN CHANGE ---
    # get_jwt_identity() now returns the string ID
    # Get custom claims using get_jwt()
    jwt_payload = get_jwt()
    user_info = jwt_payload.get('user_info')

    if not user_info or 'id' not in user_info:
         # This means the token is valid but doesn't have our expected custom claims
         print(f"!!! '/me' endpoint: Missing 'user_info' in JWT payload: {jwt_payload}")
         return jsonify({"msg": "Invalid token structure."}), 401

    # Fetch user data based on ID from claims (optional, could just return claims)
    user = User.query.get(user_info['id'])
    if not user:
        print(f"!!! '/me' endpoint: User ID {user_info.get('id')} from token not found in DB.")
        return jsonify({"msg": "User associated with token not found."}), 404

    # Return data based on claims and/or fetched user
    return jsonify({
        "id": user_info.get('id'), # Use ID from claim
        "name": user.name,        # Use name from DB
        "email": user.email,       # Use email from DB
        "role": user_info.get('role'), # Use role from claim
        "is_verified": user.is_verified # Use status from DB
    }), 200
    # --- END CHANGE ---


@bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    # --- If using a blocklist (Recommended) ---
    # from app.blocklist import BLOCKLIST
    # jwt_data = get_jwt()
    # jti = jwt_data['jti']
    # BLOCKLIST.add(jti)
    # user_id = get_jwt_identity() # Get string ID
    # print(f"--- User {user_id} logged out. Token JTI {jti} blocklisted. ---")
    # return jsonify({"msg": "Successfully logged out. Token revoked."}), 200
    # --- End Blocklist ---

    # --- Basic version (Client responsibility) ---
    user_id = get_jwt_identity() # Get string ID
    print(f"--- User {user_id} initiated logout (token not blocklisted). ---")
    return jsonify({"msg": "Logout successful. Please discard your token."}), 200