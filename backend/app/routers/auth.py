from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from ..models import User, UserRole
from .. import db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    role_str = data.get('role', 'student').lower() # Default to student

    if not username or not password:
        return jsonify(message="Username and password are required"), 400

    if User.query.filter_by(username=username).first():
        return jsonify(message="Username already exists"), 409

    try:
        role = UserRole(role_str)
    except ValueError:
        return jsonify(message="Invalid role specified. Use 'teacher' or 'student'."), 400

    user = User(username=username, role=role)
    user.set_password(password)

    try:
        db.session.add(user)
        db.session.commit()
        return jsonify(message="User registered successfully", user_id=user.id), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error during registration: {e}") # Log the error
        return jsonify(message="Registration failed due to server error"), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify(message="Username and password are required"), 400

    user = User.query.filter_by(username=username).first()

    if user and user.check_password(password):
        access_token = create_access_token(identity=user.id)
        return jsonify(access_token=access_token, role=user.role.value, user_id=user.id), 200
    else:
        return jsonify(message="Invalid username or password"), 401

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_me():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
         return jsonify(message="User not found"), 404
    return jsonify(id=user.id, username=user.username, role=user.role.value), 200