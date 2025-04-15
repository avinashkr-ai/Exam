# app/routes/admin.py
from flask import Blueprint, request, jsonify
# Ensure db is imported correctly
from app.extensions import db
from app.models import User, UserRole, Exam, StudentResponse, Evaluation, Question
from app.utils.decorators import admin_required, verified_required
from app.utils.helpers import get_current_user_id
from flask_jwt_extended import jwt_required
# Import datetime components needed for timestamp handling
from datetime import timezone # Use standard library timezone

# Define blueprint only once
bp = Blueprint('admin', __name__)

# --- Helper Function (Optional but recommended for clarity) ---
# You could move this to helpers.py if used across multiple files
def ensure_aware_utc(dt):
    """Adds UTC timezone if datetime object is naive."""
    if dt and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    elif dt and dt.tzinfo is not None:
        return dt.astimezone(timezone.utc) # Convert existing aware to UTC
    return dt # Return None if input was None
# --- End Helper ---


@bp.route('/dashboard', methods=['GET'])
@jwt_required()
@admin_required
@verified_required
def dashboard():
    # ---- DEBUG PRINT ---
    print(f"\n*** Successfully reached admin dashboard endpoint execution ***")
    current_admin_id = get_current_user_id()
    print(f"Admin user ID confirmed in dashboard: {current_admin_id}")
    # --- END DEBUG ---
    if not current_admin_id:
        return jsonify({"msg": "Could not identify requesting admin user."}), 401

    try:
        # Stats calculation logic remains the same
        teacher_count = User.query.filter_by(role=UserRole.TEACHER, is_verified=True).count()
        student_count = User.query.filter_by(role=UserRole.STUDENT, is_verified=True).count()
        pending_users_count = User.query.filter_by(is_verified=False).filter(User.role != UserRole.ADMIN).count()
        exam_count = Exam.query.count()
        total_responses_count = StudentResponse.query.count()
        evaluated_responses_count = Evaluation.query.count()
        pending_evaluations_count = max(0, total_responses_count - evaluated_responses_count)

        # No timestamps directly returned here, so no changes needed for this response
        return jsonify({
            "message": "Admin Dashboard",
            "active_teachers": teacher_count,
            "active_students": student_count,
            "pending_verifications": pending_users_count,
            "total_exams": exam_count,
            "total_responses_submitted": total_responses_count,
            "responses_evaluated": evaluated_responses_count,
            "responses_pending_evaluation": pending_evaluations_count
        }), 200
    except Exception as e:
        print(f"!!! Error executing admin dashboard logic for admin {current_admin_id}: {e}")
        return jsonify({"msg": "An error occurred while retrieving dashboard statistics."}), 500


# --- User Management ---
@bp.route('/users/pending', methods=['GET'])
@jwt_required()
@admin_required
@verified_required
def get_pending_users():
    print(f"\n*** Reached get_pending_users endpoint ***")
    try:
        pending = User.query.filter_by(is_verified=False).filter(User.role != UserRole.ADMIN).order_by(User.created_at.asc()).all()
        # Format 'created_at' timestamp for output
        users_data = [{
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role.name,
            # Ensure created_at is aware UTC and formatted as ISO string
            "registered_at": ensure_aware_utc(u.created_at).isoformat() if u.created_at else None
        } for u in pending]
        return jsonify(users_data), 200
    except Exception as e:
        print(f"!!! Error fetching pending users: {e}")
        return jsonify({"msg": "Error fetching pending users."}), 500

@bp.route('/users/verify/<int:user_id>', methods=['POST'])
@jwt_required()
@admin_required
@verified_required
def verify_user(user_id):
    print(f"\n*** Reached verify_user endpoint for user_id: {user_id} ***")
    user = User.query.get(user_id)
    if not user: return jsonify({"msg": "User not found"}), 404
    if user.role == UserRole.ADMIN: return jsonify({"msg": "Cannot verify Admin role this way"}), 400
    if user.is_verified: return jsonify({"msg": "User already verified"}), 400

    try:
        user.is_verified = True
        db.session.commit()
        print(f"--- User {user.email} (ID: {user_id}) verified successfully by admin {get_current_user_id()} ---")
        # No timestamp returned in success message
        return jsonify({"msg": f"User {user.email} verified successfully"}), 200
    except Exception as e:
        db.session.rollback()
        print(f"!!! Error verifying user {user_id}: {e}")
        return jsonify({"msg": "Failed to verify user due to server error."}), 500


@bp.route('/teachers', methods=['GET'])
@jwt_required()
@admin_required
@verified_required
def get_all_teachers():
    print(f"\n*** Reached get_all_teachers endpoint ***")
    try:
        teachers = User.query.filter_by(role=UserRole.TEACHER).order_by(User.name).all()
        # No timestamps usually returned here, logic remains same
        teachers_data = [{"id": u.id, "name": u.name, "email": u.email, "is_verified": u.is_verified} for u in teachers]
        return jsonify(teachers_data), 200
    except Exception as e:
        print(f"!!! Error fetching teachers: {e}")
        return jsonify({"msg": "Error fetching teachers."}), 500


@bp.route('/students', methods=['GET'])
@jwt_required()
@admin_required
@verified_required
def get_all_students():
    print(f"\n*** Reached get_all_students endpoint ***")
    try:
        students = User.query.filter_by(role=UserRole.STUDENT).order_by(User.name).all()
        # No timestamps usually returned here, logic remains same
        students_data = [{"id": u.id, "name": u.name, "email": u.email, "is_verified": u.is_verified} for u in students]
        return jsonify(students_data), 200
    except Exception as e:
        print(f"!!! Error fetching students: {e}")
        return jsonify({"msg": "Error fetching students."}), 500


@bp.route('/users/<int:user_id>', methods=['DELETE'])
@jwt_required()
@admin_required
@verified_required
def delete_user(user_id):
    print(f"\n*** Reached delete_user endpoint for user_id: {user_id} ***")
    current_admin_id = get_current_user_id()
    if not current_admin_id: return jsonify({"msg": "Could not identify requesting admin user."}), 401
    if user_id == current_admin_id: return jsonify({"msg": "Admin cannot delete themselves"}), 403

    user = User.query.get(user_id)
    if not user: return jsonify({"msg": "User not found"}), 404
    if user.role == UserRole.ADMIN: return jsonify({"msg": "Deleting other Admins is restricted via this endpoint"}), 403

    try:
        email_deleted = user.email
        db.session.delete(user)
        db.session.commit()
        print(f"--- User {email_deleted} (ID: {user_id}) deleted successfully by admin {current_admin_id} ---")
        # No timestamp returned in success message
        return jsonify({"msg": f"User {email_deleted} deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        print(f"!!! Error deleting user {user_id}: {e}")
        return jsonify({"msg": "Failed to delete user due to server error."}), 500


# --- Results/Evaluation ---

@bp.route('/results/all', methods=['GET'])
@jwt_required()
@admin_required
@verified_required
def get_all_results():
    print(f"\n*** Reached get_all_results endpoint ***")
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        # Query logic remains the same
        evaluations_query = Evaluation.query.join(StudentResponse).join(User, StudentResponse.student_id == User.id)\
                                        .join(Exam, StudentResponse.exam_id == Exam.id)\
                                        .join(Question, StudentResponse.question_id == Question.id)\
                                        .add_columns(
                                            Evaluation.id.label("evaluation_id"),
                                            User.name.label("student_name"),
                                            User.email.label("student_email"),
                                            Exam.title.label("exam_title"),
                                            Question.question_text,
                                            Evaluation.marks_awarded,
                                            Evaluation.evaluated_by,
                                            Evaluation.evaluated_at # Fetch the timestamp
                                        ).order_by(Evaluation.evaluated_at.desc())

        paginated_evaluations = evaluations_query.paginate(page=page, per_page=per_page, error_out=False)
        evaluations = paginated_evaluations.items

        # Format 'evaluated_at' timestamp for output
        results_data = [{
            "evaluation_id": ev.evaluation_id,
            "student_name": ev.student_name,
            "student_email": ev.student_email,
            "exam_title": ev.exam_title,
            "question_text": ev.question_text[:100] + ("..." if len(ev.question_text) > 100 else ""),
            "marks_awarded": ev.marks_awarded,
            "evaluated_by": ev.evaluated_by,
            # Ensure evaluated_at is aware UTC and formatted as ISO string
            "evaluated_at": ensure_aware_utc(ev.evaluated_at).isoformat() if ev.evaluated_at else None
        } for ev in evaluations]

        return jsonify({
            "results": results_data,
            "total": paginated_evaluations.total,
            "pages": paginated_evaluations.pages,
            "current_page": page
        }), 200
    except Exception as e:
        print(f"!!! Error fetching all results: {e}")
        return jsonify({"msg": "Error fetching results."}), 500


@bp.route('/evaluate/response/<int:response_id>', methods=['POST'])
@jwt_required()
@admin_required
@verified_required
def trigger_ai_evaluation(response_id):
    print(f"\n*** Reached trigger_ai_evaluation endpoint for response_id: {response_id} ***")
    # Import only when needed
    from app.services.ai_evaluation import evaluate_response_with_gemini
    from sqlalchemy.orm import joinedload # Import joinedload if not already

    admin_id = get_current_user_id()
    if not admin_id: return jsonify({"msg": "Could not identify requesting admin user."}), 401

    # Eager load related data
    response = StudentResponse.query.options(
        joinedload(StudentResponse.question),
        joinedload(StudentResponse.evaluation)
    ).get(response_id)

    if not response: return jsonify({"msg": "Student response not found"}), 404
    if response.evaluation:
        print(f"--- Attempt to re-evaluate response {response_id} blocked (already evaluated). Admin: {admin_id} ---")
        return jsonify({"msg": f"This response (ID: {response_id}) has already been evaluated."}), 400

    question = response.question
    if not question:
         print(f"!!! Could not find question associated with response ID: {response_id}")
         return jsonify({"msg": f"Could not find question associated with response ID: {response_id}"}), 404

    # Handle empty response
    if not response.response_text or not response.response_text.strip():
        print(f"--- Evaluating response {response_id} as 0 marks (empty response text). Admin: {admin_id} ---")
        try:
            # Create evaluation with current UTC time implicitly added by default=datetime.utcnow
            evaluation = Evaluation(
                    response_id=response_id,
                    evaluated_by=f"System (Empty Response - Admin Trigger: {admin_id})",
                    marks_awarded=0.0,
                    feedback="Student response was empty."
                )
            db.session.add(evaluation)
            db.session.commit()
            # No timestamp explicitly returned in this specific JSON response
            return jsonify({
                    "msg": "AI evaluation skipped: Student response was empty. Marked as 0.",
                    "evaluation_id": evaluation.id,
                    "marks_awarded": 0.0,
                    "feedback": "Student response was empty."
                }), 200
        except Exception as e:
             db.session.rollback()
             print(f"!!! Error saving 0-mark evaluation for empty response {response_id}: {e}")
             return jsonify({"msg": "Failed to process empty response due to server error."}), 500

    # Call AI service
    try:
        print(f"--- Admin {admin_id} triggering AI evaluation via service for response {response_id} ---")
        marks, feedback = evaluate_response_with_gemini(
            question_text=question.question_text,
            student_answer=response.response_text,
            word_limit=question.word_limit,
            max_marks=question.marks,
            question_type=question.question_type.name
        )

        if marks is not None and feedback is not None:
            print(f"--- AI Service returned marks: {marks}, feedback snippet: '{feedback[:50]}...' for response {response_id} ---")
            # Create evaluation with current UTC time implicitly added by default=datetime.utcnow
            evaluation = Evaluation(
                response_id=response_id,
                evaluated_by=f"AI_Gemini (Admin Trigger: {admin_id})",
                marks_awarded=marks,
                feedback=feedback
            )
            db.session.add(evaluation)
            db.session.commit()
            print(f"--- Successfully evaluated and saved response {response_id}. Evaluation ID: {evaluation.id} ---")
            # No timestamp explicitly returned in this specific JSON response
            return jsonify({
                "msg": "AI evaluation successful",
                "evaluation_id": evaluation.id,
                "marks_awarded": marks,
                "feedback": feedback
            }), 200
        else:
            print(f"!!! AI evaluation service failed for response {response_id}. Returned None or partial data. Details: {feedback}")
            return jsonify({"msg": "AI evaluation failed. Check server logs.", "details": feedback or "Unknown evaluation service error"}), 500

    except Exception as e:
        db.session.rollback()
        print(f"!!! Exception during AI evaluation trigger endpoint for response {response_id}: {e}")
        # import traceback; traceback.print_exc()
        return jsonify({"msg": f"An internal server error occurred during AI evaluation trigger: {e}"}), 500