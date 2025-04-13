# app/utils/decorators.py
from functools import wraps
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from flask import jsonify
from app.models import User, UserRole

# Helper to get user object from JWT identity
def get_user_from_jwt():
    user_id = get_jwt_identity()
    return User.query.get(user_id)

# Decorator to require a specific role
def role_required(required_role):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            user = get_user_from_jwt()
            if not user or user.role != required_role:
                return jsonify({"msg": f"Forbidden: {required_role.value} role required"}), 403
            # Optional: Check if user is verified (depends on your logic)
            # if not user.is_verified:
            #    return jsonify({"msg": "Forbidden: Account not verified"}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator

# Specific role decorators (easier to use)
admin_required = role_required(UserRole.ADMIN)
teacher_required = role_required(UserRole.TEACHER)
student_required = role_required(UserRole.STUDENT)

# Decorator to require verification (can be combined with role checks)
def verified_required(fn):
     @wraps(fn)
     def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user = get_user_from_jwt()
        if not user or not user.is_verified:
            return jsonify({"msg": "Forbidden: Account not verified"}), 403
        return fn(*args, **kwargs)
     return wrapper