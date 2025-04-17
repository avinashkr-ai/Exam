# app/routes/admin.py

from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models import User, UserRole, Exam, StudentResponse, Evaluation, Question # Import necessary models
from app.utils.decorators import admin_required, verified_required # Import custom decorators
from app.utils.helpers import get_current_user_id, format_datetime # Import helper functions
from flask_jwt_extended import jwt_required # For protecting routes
from sqlalchemy.orm import joinedload # For efficient loading of related objects
from datetime import datetime # Standard datetime library (mainly for type hints or potential parsing)
from app.services.ai_evaluation import evaluate_response_with_gemini # Import AI evaluation service

# Removed pendulum import as it's no longer needed

bp = Blueprint('admin', __name__)

# No specific timezone definitions needed here anymore

@bp.route('/dashboard', methods=['GET'])
@jwt_required()
@admin_required
@verified_required
def dashboard():
    """Provides summary statistics for the admin dashboard."""
    print(f"\n*** Admin Dashboard Endpoint Reached ***")
    admin_id = get_current_user_id() # For logging/context if needed
    if not admin_id:
        # This case should ideally be caught by jwt_required/decorators, but good practice
        return jsonify({"msg": "Unauthorized: Could not identify admin user."}), 401

    try:
        # Count verified teachers and students
        teacher_count = User.query.filter_by(role=UserRole.TEACHER, is_verified=True).count()
        student_count = User.query.filter_by(role=UserRole.STUDENT, is_verified=True).count()

        # Count users (non-admins) awaiting verification
        pending_users_count = User.query.filter(
            User.is_verified == False,
            User.role != UserRole.ADMIN
        ).count()

        # Count total exams
        exam_count = Exam.query.count()

        # Count total and evaluated responses
        total_responses_count = StudentResponse.query.count()
        evaluated_responses_count = Evaluation.query.count()
        # Calculate pending evaluations (ensure non-negative)
        pending_evaluations_count = max(0, total_responses_count - evaluated_responses_count)

        print(f"--- Admin {admin_id} dashboard data retrieved ---")
        return jsonify({
            "message": "Admin Dashboard Data",
            "active_teachers": teacher_count,
            "active_students": student_count,
            "pending_verifications": pending_users_count,
            "total_exams": exam_count,
            "total_responses_submitted": total_responses_count,
            "responses_evaluated": evaluated_responses_count,
            "responses_pending_evaluation": pending_evaluations_count
        }), 200
    except Exception as e:
        print(f"!!! Error generating admin dashboard data for admin {admin_id}: {e}")
        return jsonify({"msg": "An error occurred while retrieving dashboard statistics."}), 500

@bp.route('/users/pending', methods=['GET'])
@jwt_required()
@admin_required
@verified_required
def get_pending_users():
    """Retrieves a list of users awaiting verification."""
    print(f"\n*** Get Pending Users Endpoint Reached ***")
    try:
        # Query for non-verified users who are not Admins, order by registration time
        pending_users = User.query.filter(
            User.is_verified == False,
            User.role != UserRole.ADMIN
        ).order_by(User.created_at.asc()).all()

        # Format user data for the response
        users_data = [{
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role.name,
            # Format the naive UTC datetime using the helper
            "registered_at_utc": format_datetime(u.created_at)
        } for u in pending_users]

        print(f"--- Found {len(users_data)} pending users ---")
        return jsonify(users_data), 200
    except Exception as e:
        print(f"!!! Error fetching pending users: {e}")
        return jsonify({"msg": "Error fetching pending users."}), 500

@bp.route('/users/verify/<int:user_id>', methods=['POST'])
@jwt_required()
@admin_required
@verified_required
def verify_user(user_id):
    """Verifies a specific user account."""
    print(f"\n*** Verify User Endpoint Reached for User ID: {user_id} ***")
    admin_id = get_current_user_id()

    # Find the user to verify
    user = User.query.get(user_id)

    # --- Validation Checks ---
    if not user:
        return jsonify({"msg": "User not found"}), 404
    if user.role == UserRole.ADMIN:
        # Prevent admins from verifying other admins via this endpoint
        return jsonify({"msg": "Cannot verify Admin role using this method"}), 400
    if user.is_verified:
        return jsonify({"msg": "User is already verified"}), 400
    # --- End Validation ---

    try:
        # Set verification flag and commit
        user.is_verified = True
        db.session.commit()
        print(f"--- User {user.email} (ID: {user_id}) verified successfully by admin {admin_id} ---")
        return jsonify({"msg": f"User '{user.email}' verified successfully"}), 200
    except Exception as e:
        db.session.rollback() # Rollback changes on error
        print(f"!!! Error verifying user {user_id} by admin {admin_id}: {e}")
        return jsonify({"msg": "Failed to verify user due to a server error."}), 500

@bp.route('/teachers', methods=['GET'])
@jwt_required()
@admin_required
@verified_required
def get_all_teachers():
    """Retrieves a list of all registered teachers."""
    print(f"\n*** Get All Teachers Endpoint Reached ***")
    try:
        # Query for all users with the Teacher role, order by name
        teachers = User.query.filter_by(role=UserRole.TEACHER).order_by(User.name.asc()).all()

        # Format data for response
        teachers_data = [{
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "is_verified": u.is_verified,
            # Format the naive UTC datetime
            "created_at_utc": format_datetime(u.created_at)
        } for u in teachers]

        print(f"--- Found {len(teachers_data)} teachers ---")
        return jsonify(teachers_data), 200
    except Exception as e:
        print(f"!!! Error fetching teachers: {e}")
        return jsonify({"msg": "Error fetching teacher list."}), 500

@bp.route('/students', methods=['GET'])
@jwt_required()
@admin_required
@verified_required
def get_all_students():
    """Retrieves a list of all registered students."""
    print(f"\n*** Get All Students Endpoint Reached ***")
    try:
        # Query for all users with the Student role, order by name
        students = User.query.filter_by(role=UserRole.STUDENT).order_by(User.name.asc()).all()

        # Format data for response
        students_data = [{
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "is_verified": u.is_verified,
            # Format the naive UTC datetime
            "created_at_utc": format_datetime(u.created_at)
        } for u in students]

        print(f"--- Found {len(students_data)} students ---")
        return jsonify(students_data), 200
    except Exception as e:
        print(f"!!! Error fetching students: {e}")
        return jsonify({"msg": "Error fetching student list."}), 500

@bp.route('/users/<int:user_id>', methods=['DELETE'])
@jwt_required()
@admin_required
@verified_required
def delete_user(user_id):
    """Deletes a specific user (non-admin)."""
    print(f"\n*** Delete User Endpoint Reached for User ID: {user_id} ***")
    current_admin_id = get_current_user_id()

    # --- Validation Checks ---
    if not current_admin_id: # Should be caught by decorators, but double-check
       return jsonify({"msg": "Could not identify requesting admin user."}), 401
    if user_id == current_admin_id:
       # Prevent self-deletion
       return jsonify({"msg": "Admin cannot delete their own account via this endpoint"}), 403

    user_to_delete = User.query.get(user_id)

    if not user_to_delete:
       return jsonify({"msg": "User not found"}), 404
    if user_to_delete.role == UserRole.ADMIN:
       # Restrict deletion of other admins
       return jsonify({"msg": "Deleting other Admin users is restricted"}), 403
    # --- End Validation ---

    try:
        email_deleted = user_to_delete.email # Store email for logging before deletion
        # Delete the user and commit
        db.session.delete(user_to_delete)
        db.session.commit()
        print(f"--- User {email_deleted} (ID: {user_id}) deleted successfully by admin {current_admin_id} ---")
        return jsonify({"msg": f"User '{email_deleted}' deleted successfully"}), 200
    except Exception as e:
        db.session.rollback() # Rollback on error
        print(f"!!! Error deleting user {user_id} by admin {current_admin_id}: {e}")
        # Consider implications: deleting a user might require cascading deletes or nullifying foreign keys
        # depending on relationships (e.g., exams created, responses submitted).
        # Current setup might raise IntegrityError if related records exist and constraints are enforced.
        return jsonify({"msg": "Failed to delete user due to a server error or constraint violation."}), 500

@bp.route('/results/all', methods=['GET'])
@jwt_required()
@admin_required
@verified_required
def get_all_results():
    """Retrieves all evaluated results, possibly paginated."""
    print(f"\n*** Get All Results Endpoint Reached ***")
    try:
        # Pagination parameters from query string
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        # Base query for Evaluations, joining related tables for details
        evaluations_query = Evaluation.query.join(
            StudentResponse, Evaluation.response_id == StudentResponse.id
        ).join(
            User, StudentResponse.student_id == User.id
        ).join(
            Exam, StudentResponse.exam_id == Exam.id
        ).join(
            Question, StudentResponse.question_id == Question.id
        ).add_columns(
            Evaluation.id.label("evaluation_id"),
            User.name.label("student_name"),
            User.email.label("student_email"),
            Exam.title.label("exam_title"),
            Question.question_text,
            StudentResponse.response_text, # Include student's response text
            Evaluation.marks_awarded,
            Question.marks.label("marks_possible"), # Include max marks for context
            Evaluation.evaluated_by,
            Evaluation.feedback,
            Evaluation.evaluated_at
        ).order_by(Evaluation.evaluated_at.desc()) # Order by most recent evaluation

        # Paginate the query results
        paginated_evaluations = evaluations_query.paginate(page=page, per_page=per_page, error_out=False)
        evaluations = paginated_evaluations.items

        # Format results for JSON response
        results_data = [{
            "evaluation_id": ev.evaluation_id,
            "student_name": ev.student_name,
            "student_email": ev.student_email,
            "exam_title": ev.exam_title,
            "question_text": ev.question_text[:100] + ("..." if len(ev.question_text or "") > 100 else ""), # Truncate long text
            "student_response": ev.response_text[:150] + ("..." if len(ev.response_text or "") > 150 else ""), # Truncate response
            "marks_awarded": ev.marks_awarded,
            "marks_possible": ev.marks_possible,
            "feedback": ev.feedback,
            "evaluated_by": ev.evaluated_by,
            # Format the naive UTC datetime
            "evaluated_at_utc": format_datetime(ev.evaluated_at)
        } for ev in evaluations]

        print(f"--- Retrieved page {page} of all results ({len(results_data)} items) ---")
        # Return paginated results structure
        return jsonify({
            "results": results_data,
            "total_results": paginated_evaluations.total,
            "total_pages": paginated_evaluations.pages,
            "current_page": page,
            "per_page": per_page
        }), 200
    except Exception as e:
        print(f"!!! Error fetching all results: {e}")
        return jsonify({"msg": "Error fetching results list."}), 500

@bp.route('/evaluate/response/<int:response_id>', methods=['POST'])
@jwt_required()
@admin_required
@verified_required
def trigger_ai_evaluation(response_id):
    """Triggers AI evaluation for a specific student response."""
    print(f"\n*** Trigger AI Evaluation Endpoint for Response ID: {response_id} ***")
    # # Import the AI evaluation service function locally to avoid circular imports if service uses models
    # try:
    # except ImportError:
    #      print("!!! FATAL ERROR: AI evaluation service (app.services.ai_evaluation) not found.")
    #      return jsonify({"msg": "AI Evaluation service is unavailable."}), 503 # Service Unavailable

    admin_id = get_current_user_id()
    if not admin_id: return jsonify({"msg": "Could not identify requesting admin user."}), 401

    # Fetch the response, preloading related question and checking for existing evaluation
    response = StudentResponse.query.options(
        joinedload(StudentResponse.question), # Load the related Question
        joinedload(StudentResponse.evaluation) # Load the related Evaluation (if exists)
    ).get(response_id)

    # --- Validation Checks ---
    if not response:
        return jsonify({"msg": "Student response not found"}), 404
    if response.evaluation:
        # Prevent re-evaluation via this endpoint if already evaluated
        print(f"--- Attempt to re-evaluate response {response_id} blocked (already evaluated by {response.evaluation.evaluated_by}). Admin: {admin_id} ---")
        return jsonify({"msg": f"This response (ID: {response_id}) has already been evaluated."}), 400

    question = response.question
    if not question:
        # Data integrity issue if response exists but question doesn't
        print(f"!!! CRITICAL ERROR: Question not found for existing response ID: {response_id}")
        return jsonify({"msg": f"Data Error: Could not find question associated with response ID: {response_id}"}), 500
    # --- End Validation ---

    # Handle empty responses directly without calling AI
    if not response.response_text or not response.response_text.strip():
        print(f"--- Evaluating response {response_id} as 0 marks (empty response text). Admin: {admin_id} ---")
        try:
            # Create evaluation record for empty response
            evaluation = Evaluation(
                response_id=response_id,
                evaluated_by=f"System (Empty Response - Admin Trigger: {admin_id})",
                marks_awarded=0.0,
                feedback="Student response was empty.",
                # evaluated_at default is handled by model (datetime.utcnow)
            )
            db.session.add(evaluation)
            db.session.commit()
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

    # Proceed with AI evaluation for non-empty responses
    try:
        print(f"--- Admin {admin_id} triggering AI evaluation service for response {response_id} ---")
        marks, feedback = evaluate_response_with_gemini(
            question_text=question.question_text,
            student_answer=response.response_text,
            word_limit=question.word_limit,
            max_marks=question.marks,
            question_type=question.question_type.name # Pass question type name
        )

        # Check if AI evaluation was successful
        if marks is not None and feedback is not None:
            print(f"--- AI Service returned marks: {marks}, feedback snippet: '{feedback[:60]}...' for response {response_id} ---")
            # Create and save the Evaluation record
            evaluation = Evaluation(
                response_id=response_id,
                evaluated_by=f"AI_Gemini (Admin Trigger: {admin_id})",
                marks_awarded=float(marks), # Ensure marks are float
                feedback=feedback
                # evaluated_at default is handled by model
            )
            db.session.add(evaluation)
            db.session.commit()
            print(f"--- Successfully evaluated and saved response {response_id}. Evaluation ID: {evaluation.id} ---")
            return jsonify({
                "msg": "AI evaluation successful",
                "evaluation_id": evaluation.id,
                "marks_awarded": marks,
                "feedback": feedback
            }), 200
        else:
            # AI service failed (returned None or partial data)
            error_detail = feedback or "Unknown evaluation service error or model issue."
            print(f"!!! AI evaluation service failed for response {response_id}. Details: {error_detail}")
            return jsonify({"msg": "AI evaluation service failed. Check server logs.", "details": error_detail}), 500 # Internal Server Error or Service Unavailable (503) might be appropriate

    except Exception as e:
        # Catch any other unexpected errors during the AI call or DB save
        db.session.rollback()
        print(f"!!! Exception during AI evaluation trigger endpoint for response {response_id}: {e}")
        # import traceback; traceback.print_exc() # For detailed debugging
        return jsonify({"msg": f"An internal server error occurred during the AI evaluation process: {str(e)}"}), 500