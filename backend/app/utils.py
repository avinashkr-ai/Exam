from functools import wraps
from flask import jsonify, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from .models import Exam, User
from .extensions import db
from datetime import datetime, timezone

def role_required(role_name):
    """Decorator to ensure user has the required role."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                verify_jwt_in_request()
                identity = get_jwt_identity()
                if not identity:
                    return jsonify(message="Missing JWT identity"), 401
                if identity.get('role') != role_name:
                    return jsonify(message=f"'{role_name.capitalize()}' access required"), 403
            except Exception as e:
                 # Handle potential JWT errors (expired, invalid, etc.)
                 return jsonify(message=f"JWT Error: {str(e)}"), 401
            return fn(*args, **kwargs)
        return wrapper
    return decorator

teacher_required = role_required('teacher')
student_required = role_required('student')


def get_current_user():
    """Helper to get the current user model instance from JWT identity."""
    verify_jwt_in_request() # Ensures token is valid
    identity = get_jwt_identity()
    if not identity or 'id' not in identity:
        return None
    return User.query.get(identity['id'])


# Example decorator to check if teacher owns the exam
def teacher_owns_exam(fn):
    @wraps(fn)
    @teacher_required # Ensure user is a teacher first
    def wrapper(*args, **kwargs):
        exam_id = kwargs.get('exam_id')
        if not exam_id:
            return jsonify(message="Exam ID missing in request"), 400

        exam = Exam.query.get(exam_id)
        if not exam:
            return jsonify(message="Exam not found"), 404

        identity = get_jwt_identity()
        if exam.creator_id != identity['id']:
            return jsonify(message="Forbidden: You do not own this exam"), 403

        # Pass the fetched exam object to the route function if needed
        request.exam = exam # Store exam in request context

        return fn(*args, **kwargs)
    return wrapper

# Example decorator to check if exam is live for student access
def exam_is_live_for_student(fn):
    @wraps(fn)
    @student_required # Ensure user is a student
    def wrapper(*args, **kwargs):
        exam_id = kwargs.get('exam_id')
        if not exam_id:
            return jsonify(message="Exam ID missing in request"), 400

        exam = Exam.query.get(exam_id)
        if not exam:
            return jsonify(message="Exam not found"), 404

        # Use the model's property or implement logic here
        now = datetime.now(timezone.utc)
        is_active = False
        if exam.status in ['scheduled', 'live']:
            start_ok = exam.scheduled_start_time and exam.scheduled_start_time <= now
            end_ok = not exam.scheduled_end_time or now < exam.scheduled_end_time
            if start_ok and end_ok:
                 is_active = True
                 # Optionally update status to 'live' if it was 'scheduled'
                 if exam.status == 'scheduled':
                     exam.status = 'live'
                     db.session.add(exam)
                     # Commit happens later in the request or needs explicit commit here
                     # db.session.commit() # Be careful with commits inside decorators

        if not is_active:
             # Check if it has ended based on time even if status is 'live'
             if exam.status == 'live' and exam.scheduled_end_time and now >= exam.scheduled_end_time:
                 exam.status = 'ended'
                 db.session.add(exam)
                 # db.session.commit()
                 return jsonify(message="Exam has ended"), 403
             return jsonify(message="Exam is not currently available"), 403


        # Check if student already submitted (logic moved to submission endpoint for clarity)

        request.exam = exam # Store exam in request context
        return fn(*args, **kwargs)
    return wrapper