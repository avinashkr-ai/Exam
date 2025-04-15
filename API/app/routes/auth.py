# app/routes/auth.py
from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models import User, UserRole
from werkzeug.security import check_password_hash
from flask_jwt_extended import (
    create_access_token, jwt_required, get_jwt_identity, get_jwt
)
# Import the helper function for timestamp formatting
from app.utils.helpers import ensure_aware_utc

bp = Blueprint('auth', __name__)

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
        # Format created_at timestamp before returning
        created_at_iso = ensure_aware_utc(new_user.created_at).isoformat() if new_user.created_at else None
        return jsonify({
            "msg": "User registered successfully. Awaiting verification if applicable.",
            "user": {
                "id": new_user.id,
                "name": new_user.name,
                "email": new_user.email,
                "role": new_user.role.name,
                # Include formatted timestamp if needed by frontend
                # "created_at": created_at_iso
            }
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

        user_claims = {
            'id': user.id,
            'role': user.role.name
        }
        access_token = create_access_token(
            identity=str(user.id),
            additional_claims={'user_info': user_claims}
        )
        print(f"--- Login successful for user ID {user.id}. Token created. ---")
        # Login response typically only includes the token
        return jsonify(access_token=access_token), 200

    return jsonify({"msg": "Invalid email or password"}), 401


# Refresh endpoint - Assuming standard implementation if needed
# @bp.route('/refresh', methods=['POST'])
# @jwt_required(refresh=True)
# def refresh():
#     identity = get_jwt_identity() # String user ID
#     user = User.query.get(int(identity))
#     if not user: return jsonify({"msg": "User not found"}), 401
#     user_claims = {'id': user.id, 'role': user.role.name}
#     new_access_token = create_access_token(identity=str(user.id), additional_claims={'user_info': user_claims})
#     return jsonify(access_token=new_access_token), 200


@bp.route('/me', methods=['GET'])
@jwt_required()
def get_me():
    jwt_payload = get_jwt()
    user_info = jwt_payload.get('user_info')

    if not user_info or 'id' not in user_info:
         print(f"!!! '/me' endpoint: Missing 'user_info' in JWT payload: {jwt_payload}")
         return jsonify({"msg": "Invalid token structure."}), 401

    user = User.query.get(user_info['id'])
    if not user:
        print(f"!!! '/me' endpoint: User ID {user_info.get('id')} from token not found in DB.")
        return jsonify({"msg": "User associated with token not found."}), 404

    # Format created_at before returning response
    created_at_iso = ensure_aware_utc(user.created_at).isoformat() if user.created_at else None

    # Return data including formatted timestamp if needed
    return jsonify({
        "id": user_info.get('id'),
        "name": user.name,
        "email": user.email,
        "role": user_info.get('role'),
        "is_verified": user.is_verified,
        # Include formatted timestamp if needed
        "created_at": created_at_iso
    }), 200


@bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    # Basic logout - no timestamp involved in response
    user_id = get_jwt_identity()
    print(f"--- User {user_id} initiated logout (token not blocklisted). ---")
    return jsonify({"msg": "Logout successful. Please discard your token."}), 200