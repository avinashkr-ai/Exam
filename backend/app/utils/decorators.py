from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from ..models import User, UserRole

def role_required(required_role):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            user = User.query.get(user_id)
            if not user or user.role != required_role:
                return jsonify(message=f"Access forbidden: Requires '{required_role.value}' role."), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator

teacher_required = role_required(UserRole.TEACHER)
student_required = role_required(UserRole.STUDENT)