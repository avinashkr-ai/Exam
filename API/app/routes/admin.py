# app/routes/admin.py
from flask import Blueprint, request, jsonify
from app import db
from app.models import User, UserRole, Exam, StudentResponse, Evaluation, Question # Added Question
from app.utils.decorators import admin_required, verified_required
from app.utils.helpers import get_current_user_id
from flask_jwt_extended import jwt_required

# Define blueprint only once
bp = Blueprint('admin', __name__)

@bp.route('/dashboard', methods=['GET'])
@jwt_required()
@admin_required
@verified_required
def dashboard():
    # Enhanced stats
    teacher_count = User.query.filter_by(role=UserRole.TEACHER, is_verified=True).count()
    student_count = User.query.filter_by(role=UserRole.STUDENT, is_verified=True).count()
    pending_users_count = User.query.filter_by(is_verified=False).filter(User.role != UserRole.ADMIN).count()
    exam_count = Exam.query.count()
    total_responses_count = StudentResponse.query.count()
    evaluated_responses_count = Evaluation.query.count()
    pending_evaluations_count = total_responses_count - evaluated_responses_count

    # Optional: Add count of MCQs vs Subjective questions if needed
    # mcq_count = Question.query.filter_by(question_type=QuestionType.MCQ).count()
    # subjective_count = Question.query.filter(Question.question_type != QuestionType.MCQ).count()

    return jsonify({
        "message": "Admin Dashboard",
        "active_teachers": teacher_count,
        "active_students": student_count,
        "pending_verifications": pending_users_count,
        "total_exams": exam_count,
        "total_responses_submitted": total_responses_count,
        "responses_evaluated": evaluated_responses_count,
        "responses_pending_evaluation": pending_evaluations_count
        # "mcq_questions": mcq_count,
        # "subjective_questions": subjective_count
    }), 200

# --- User Management ---
@bp.route('/users/pending', methods=['GET'])
@jwt_required()
@admin_required
@verified_required
def get_pending_users():
    pending = User.query.filter_by(is_verified=False).filter(User.role != UserRole.ADMIN).order_by(User.created_at.asc()).all() # Added ordering
    users_data = [{"id": u.id, "name": u.name, "email": u.email, "role": u.role.name, "registered_at": u.created_at.isoformat()} for u in pending]
    return jsonify(users_data), 200

@bp.route('/users/verify/<int:user_id>', methods=['POST'])
@jwt_required()
@admin_required
@verified_required
def verify_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404
    if user.role == UserRole.ADMIN:
         return jsonify({"msg": "Cannot verify Admin role this way"}), 400
    if user.is_verified:
        return jsonify({"msg": "User already verified"}), 400

    user.is_verified = True
    db.session.commit()
    # Optional: Add notification logic here later (e.g., email the user)
    return jsonify({"msg": f"User {user.email} verified successfully"}), 200

@bp.route('/teachers', methods=['GET'])
@jwt_required()
@admin_required
@verified_required
def get_all_teachers():
    teachers = User.query.filter_by(role=UserRole.TEACHER).order_by(User.name).all()
    teachers_data = [{"id": u.id, "name": u.name, "email": u.email, "is_verified": u.is_verified} for u in teachers]
    return jsonify(teachers_data), 200

@bp.route('/students', methods=['GET'])
@admin_required
@jwt_required()
@verified_required
def get_all_students():
    # Removed duplicate query
    students = User.query.filter_by(role=UserRole.STUDENT).order_by(User.name).all()
    students_data = [{"id": u.id, "name": u.name, "email": u.email, "is_verified": u.is_verified} for u in students]
    return jsonify(students_data), 200

@bp.route('/users/<int:user_id>', methods=['DELETE'])
@admin_required
@jwt_required()
@verified_required
def delete_user(user_id):
    # Ensure admin cannot delete themselves - get current admin ID
    current_admin_id = get_current_user_id()
    if user_id == current_admin_id:
        return jsonify({"msg": "Admin cannot delete themselves"}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404
    if user.role == UserRole.ADMIN:
        # Additional check just in case
        return jsonify({"msg": "Deleting other Admins is restricted via this endpoint"}), 403

    # Handle related data - cascade should work based on models.py settings
    # If cascade isn't set correctly, you might need manual deletion of related records
    # e.g., exams created by a teacher, responses by a student
    email_deleted = user.email # Store email for message before deleting
    db.session.delete(user)
    db.session.commit()
    return jsonify({"msg": f"User {email_deleted} deleted successfully"}), 200

# --- Results/Evaluation ---

@bp.route('/results/all', methods=['GET'])
@admin_required
@jwt_required()
@verified_required
def get_all_results():
    # Consider adding pagination args: request.args.get('page', 1, type=int), request.args.get('per_page', 20, type=int)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    evaluations_query = Evaluation.query.join(StudentResponse).join(User, StudentResponse.student_id == User.id)\
                                     .join(Exam, StudentResponse.exam_id == Exam.id)\
                                     .join(Question, StudentResponse.question_id == Question.id)\
                                     .add_columns(
                                         Evaluation.id,
                                         User.name.label("student_name"),
                                         User.email.label("student_email"),
                                         Exam.title.label("exam_title"),
                                         Question.question_text,
                                         Evaluation.marks_awarded,
                                         Evaluation.evaluated_by,
                                         Evaluation.evaluated_at
                                     ).order_by(Evaluation.evaluated_at.desc())

    paginated_evaluations = evaluations_query.paginate(page=page, per_page=per_page, error_out=False)
    evaluations = paginated_evaluations.items

    results_data = [{
        "evaluation_id": ev.id,
        "student_name": ev.student_name,
        "student_email": ev.student_email,
        "exam_title": ev.exam_title,
        "question_text": ev.question_text[:100] + "...", # Truncate more reasonably
        "marks_awarded": ev.marks_awarded,
        "evaluated_by": ev.evaluated_by,
        "evaluated_at": ev.evaluated_at.isoformat() if ev.evaluated_at else None
    } for ev in evaluations]

    return jsonify({
        "results": results_data,
        "total": paginated_evaluations.total,
        "pages": paginated_evaluations.pages,
        "current_page": page
     }), 200


@bp.route('/evaluate/response/<int:response_id>', methods=['POST'])
@verified_required
@admin_required
@jwt_required()
def trigger_ai_evaluation(response_id):
    # Import moved inside to avoid potential circular dependency issues at startup
    # Consider structuring services differently if this becomes a problem
    from app.services.ai_evaluation import evaluate_response_with_gemini

    admin_id = get_current_user_id()
    # Handle case where get_current_user_id might return None (though unlikely if JWT is valid)
    if not admin_id:
        return jsonify({"msg": "Could not identify requesting admin user."}), 401

    response = StudentResponse.query.get(response_id)

    if not response:
        return jsonify({"msg": "Student response not found"}), 404
    if response.evaluation:
        # Allow re-evaluation? Maybe add a flag/parameter to force it?
        # For now, prevent re-evaluation.
        return jsonify({"msg": f"This response (ID: {response_id}) has already been evaluated."}), 400

    question = response.question
    if not question:
         return jsonify({"msg": f"Could not find question associated with response ID: {response_id}"}), 404

    # Ensure response text is not empty or null before sending to AI
    if not response.response_text or not response.response_text.strip():
        # Automatically assign 0 marks? Or just return error?
        # Let's assign 0 marks and note it was empty.
        evaluation = Evaluation(
                response_id=response_id,
                evaluated_by=f"System (Empty Response - Admin Trigger: {admin_id})",
                marks_awarded=0.0,
                feedback="Student response was empty."
            )
        db.session.add(evaluation)
        db.session.commit()
        return jsonify({
                "msg": "AI evaluation skipped: Student response was empty. Marked as 0.",
                "evaluation_id": evaluation.id,
                "marks_awarded": 0.0,
                "feedback": "Student response was empty."
            }), 200


    # Call the evaluation service function
    try:
        print(f"Admin {admin_id} triggering AI evaluation for response {response_id}")
        marks, feedback = evaluate_response_with_gemini(
            question_text=question.question_text,
            student_answer=response.response_text, # Use student_answer consistently
            word_limit=question.word_limit,
            max_marks=question.marks,
            question_type=question.question_type.name
        )

        if marks is not None and feedback is not None:
             # Store the evaluation
            evaluation = Evaluation(
                response_id=response_id,
                evaluated_by=f"AI_Gemini (Admin Trigger: {admin_id})",
                marks_awarded=marks,
                feedback=feedback
                # evaluated_at is set by default
            )
            db.session.add(evaluation)
            db.session.commit()
            print(f"Successfully evaluated response {response_id}. Marks: {marks}")
            return jsonify({
                "msg": "AI evaluation successful",
                "evaluation_id": evaluation.id,
                "marks_awarded": marks,
                "feedback": feedback
            }), 200
        else:
            # The service function returned None or partial data, indicating an error during evaluation
            # Feedback might contain the error message from the service layer
            print(f"AI evaluation failed for response {response_id}. Details: {feedback}")
            return jsonify({"msg": "AI evaluation failed. Check logs.", "details": feedback or "Unknown evaluation service error"}), 500

    except Exception as e:
        # Log the exception e
        print(f"Error during AI evaluation trigger endpoint for response {response_id}: {e}")
        # Optionally log traceback: import traceback; traceback.print_exc()
        db.session.rollback() # Rollback any potential partial transaction
        return jsonify({"msg": f"An internal server error occurred during AI evaluation trigger: {e}"}), 500