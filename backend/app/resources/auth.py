from flask import Blueprint, request, jsonify
from werkzeug.exceptions import BadRequest, Unauthorized, Conflict, NotFound
from ..models import User
from ..schemas import UserBasicSchema, RegisterSchema, LoginSchema
from ..extensions import db, bcrypt
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, current_user as jwt_current_user
from ..utils import get_current_user


bp = Blueprint('auth', __name__, url_prefix='/auth')

# Schemas
user_schema = UserBasicSchema()
register_schema = RegisterSchema()
login_schema = LoginSchema()

@bp.route('/register', methods=['POST'])
def register():
    """Register a new user (teacher or student)."""
    try:
        data = register_schema.load(request.get_json())
    except Exception as err: # Catch Marshmallow validation errors more specifically if possible
        return jsonify(errors=err.messages), 400

    username = data['username']
    email = data['email']
    password = data['password']
    role = data.get('role', 'student').lower() # Default to student

    if role not in ['student', 'teacher']:
         raise BadRequest("Invalid role specified. Must be 'student' or 'teacher'.")
    if User.query.filter((User.username == username) | (User.email == email)).first():
        raise Conflict("Username or email already exists")

    new_user = User(username=username, email=email, role=role)
    new_user.set_password(password)

    db.session.add(new_user)
    db.session.commit()

    return user_schema.jsonify(new_user), 201

@bp.route('/login', methods=['POST'])
def login():
    """Login a user and return JWT token."""
    try:
        data = login_schema.load(request.get_json())
    except Exception as err:
        return jsonify(errors=err.messages), 400

    username = data['username']
    password = data['password']

    user = User.query.filter_by(username=username).first()

    if user and user.check_password(password):
        # Create identity payload - include necessary info
        identity = {'id': user.id, 'username': user.username, 'role': user.role}
        access_token = create_access_token(identity=identity)
        # Return token and basic user info
        return jsonify(access_token=access_token, user=user_schema.dump(user))
    else:
        raise Unauthorized("Invalid credentials")

@bp.route('/profile', methods=['GET'])
@jwt_required()
def profile():
    """Get the profile of the currently logged-in user."""
    # get_jwt_identity() returns the identity payload set during login
    # current_user from flask_jwt_extended is a proxy to the identity
    user_id = get_jwt_identity()['id']
    user = User.query.get(user_id)
    if not user:
         raise NotFound("User not found")
    return user_schema.jsonify(user)

# Optional: Refresh token endpoint
# @bp.route('/refresh', methods=['POST'])
# @jwt_required(refresh=True)
# def refresh():
#     identity = get_jwt_identity()
#     access_token = create_access_token(identity=identity, fresh=False)
#     return jsonify(access_token=access_token)

# Example of using the utility function
@bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    """Get the current user model instance."""
    user = get_current_user()
    if not user:
        raise NotFound("Current user not found")
    return user_schema.jsonify(user)