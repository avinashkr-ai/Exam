# app/routes/student.py
from flask import Blueprint, request, jsonify
# Ensure db is imported correctly
from app.extensions import db
from app.models import Exam, Question, StudentResponse, Evaluation, QuestionType, UserRole
from app.utils.decorators import student_required, verified_required
from flask_jwt_extended import jwt_required
from app.utils.helpers import get_current_user_id
# Import necessary datetime components
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import joinedload
# Removed pytz as timezone.utc is preferred and sufficient here
# import pytz # No longer needed

bp = Blueprint('student', __name__)

# --- Helper Function (Optional but recommended for clarity) ---
def ensure_aware_utc(dt):
    """Adds UTC timezone if datetime object is naive."""
    if dt and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    # If already aware, return as is (or convert to UTC if needed, though storing UTC is best)
    elif dt and dt.tzinfo is not None:
        return dt.astimezone(timezone.utc)
    return dt # Return None if input was None
# --- End Helper ---


@bp.route('/dashboard', methods=['GET'])
@jwt_required()
@student_required
@verified_required
def dashboard():
    student_id = get_current_user_id()
    if not student_id: return jsonify({"msg": "Invalid authentication token"}), 401
    try:
        completed_count = StudentResponse.query.filter_by(student_id=student_id).distinct(StudentResponse.exam_id).count()
        # Use timezone.utc for comparisons
        now_utc = datetime.now(timezone.utc)
        # Assuming Exam.scheduled_time is stored correctly (ideally as UTC)
        # The comparison '>' works correctly with timezone-aware datetimes
        upcoming_exams = Exam.query.filter(Exam.scheduled_time > now_utc).order_by(Exam.scheduled_time.asc()).limit(5).all()
        # Ensure output format is consistent ISO 8601 UTC
        upcoming_data = [{
            "id": e.id,
            "title": e.title,
            "scheduled_time": ensure_aware_utc(e.scheduled_time).isoformat() if e.scheduled_time else None
        } for e in upcoming_exams]

        return jsonify({
            "message": "Student Dashboard",
            "completed_exams_count": completed_count,
            "upcoming_exams": upcoming_data
        }), 200
    except Exception as e:
        print(f"Error fetching student dashboard for student {student_id}: {e}")
        return jsonify({"msg": "Error fetching dashboard data."}), 500


@bp.route('/exams/available', methods=['GET'])
@jwt_required()
@student_required
@verified_required
def get_available_exams():
    student_id = get_current_user_id()
    if not student_id:
        return jsonify({"msg": "Invalid authentication token"}), 401

    try:
        # Get current time in UTC, aware
        now_utc = datetime.now(timezone.utc)
        # Format for SQLite comparison if needed (YYYY-MM-DD HH:MM:SS)
        # Note: Using db functions might vary across DB engines (PostgreSQL handles intervals better)
        # It's often safer to filter broadly in DB and refine in Python
        now_db_string_format = now_utc.strftime('%Y-%m-%d %H:%M:%S')

        # Get IDs of exams already submitted by this student
        submitted_exam_ids = {
            resp.exam_id
            for resp in StudentResponse.query.filter_by(student_id=student_id).with_entities(StudentResponse.exam_id)
        }
        print(f"--- DEBUG: Student {student_id} submitted exams: {submitted_exam_ids} ---")

        # --- Database Query Filter ---
        # Attempt to filter exams where the calculated end time is after the current time.
        # This relies on specific DB functions (make_interval for PG, datetime modifier for SQLite).
        # Using the provided SQLite version for now, ensure `now_db_string_format` is correct.
        print(f"--- DEBUG: Filtering exams ending after: {now_db_string_format} ---")
        potential_exams = Exam.query.filter(
            # Assuming Exam.duration is stored as Integer (minutes)
            # This syntax is specific to SQLite for adding minutes
            db.func.datetime(Exam.scheduled_time, '+' + Exam.duration.cast(db.String) + ' minutes') > now_db_string_format
        ).order_by(Exam.scheduled_time.asc()).all()
        # --- End Database Query Filter ---

        print(f"--- DEBUG: potential_exams query found {len(potential_exams)} candidates. ---")

        exams_data = []
        for e in potential_exams:
            print(f"--- DEBUG: Checking exam ID {e.id} ('{e.title}') ---")
            # Skip if already submitted
            if e.id in submitted_exam_ids:
                print(f"--- DEBUG: Skipping exam ID {e.id} (already submitted). ---")
                continue

            # --- Python Timezone Handling & Status Check ---
            # Ensure start_time is timezone-aware UTC
            start_time_utc = ensure_aware_utc(e.scheduled_time)
            if not start_time_utc:
                 print(f"--- DEBUG: Skipping exam ID {e.id} due to invalid scheduled_time. ---")
                 continue # Skip if scheduled time is invalid

            end_time_utc = start_time_utc + timedelta(minutes=e.duration)

            # Determine status based on timezone-aware comparisons
            status = "Expired"
            if now_utc < start_time_utc:
                status = "Upcoming"
            elif start_time_utc <= now_utc < end_time_utc:
                status = "Active"

            print(f"--- DEBUG: Exam ID {e.id} Start: {start_time_utc}, End: {end_time_utc}, Now: {now_utc}, Status: {status} ---")
            # --- End Python Check ---

            # Add to results only if Upcoming or Active
            if status in ["Upcoming", "Active"]:
                print(f"--- DEBUG: Adding exam ID {e.id} to results. ---")
                exams_data.append({
                    "id": e.id,
                    "title": e.title,
                    "description": e.description,
                    "scheduled_time": start_time_utc.isoformat(), # Output aware UTC ISO string
                    "duration": e.duration,
                    "status": status
                })
            else:
                print(f"--- DEBUG: Excluding exam ID {e.id} (status {status}). ---")

        print(f"--- DEBUG: Final exams_data count: {len(exams_data)} ---")
        return jsonify(exams_data), 200

    except Exception as e:
        # Log the actual exception type and message for better debugging
        print(f"!!! ERROR in get_available_exams for student {student_id}: {type(e).__name__} - {e}")
        # import traceback; traceback.print_exc() # Uncomment for full traceback if needed
        return jsonify({"msg": "Error fetching available exams."}), 500


@bp.route('/exams/<int:exam_id>/take', methods=['GET'])
@jwt_required()
@student_required
@verified_required
def get_exam_questions_for_student(exam_id):
    student_id = get_current_user_id()
    if not student_id: return jsonify({"msg": "Invalid authentication token"}), 401
    # Get current time as aware UTC object
    now_utc = datetime.now(timezone.utc)

    try:
        exam = Exam.query.get_or_404(exam_id)

        # Check if already submitted
        existing_submission = StudentResponse.query.filter_by(student_id=student_id, exam_id=exam_id).first()
        if existing_submission:
            return jsonify({"msg": "You have already submitted responses for this exam."}), 403

        # Ensure exam times are aware UTC for comparison
        start_time_utc = ensure_aware_utc(exam.scheduled_time)
        if not start_time_utc:
            print(f"!!! ERROR: Exam {exam_id} has invalid scheduled_time.")
            return jsonify({"msg": "Exam schedule is invalid."}), 500
        end_time_utc = start_time_utc + timedelta(minutes=exam.duration)

        # Check if exam is active using aware times
        if not (start_time_utc <= now_utc < end_time_utc):
             print(f"--- DEBUG: Exam {exam_id} not active for taking. Now: {now_utc}, Start: {start_time_utc}, End: {end_time_utc} ---")
             return jsonify({"msg": "This exam is not currently active or has expired."}), 403

        # Fetch questions
        questions = Question.query.filter_by(exam_id=exam_id).order_by(Question.id).all()

        # Prepare data for student (exclude correct answers)
        questions_data = [{
            "id": q.id,
            "question_text": q.question_text,
            "question_type": q.question_type.value,
            "marks": q.marks,
            "options": q.options if q.question_type == QuestionType.MCQ else None,
            "word_limit": q.word_limit
        } for q in questions]

        # Calculate remaining time using aware times
        time_remaining_seconds = (end_time_utc - now_utc).total_seconds()

        return jsonify({
            "exam_id": exam.id,
            "exam_title": exam.title,
            "questions": questions_data,
            "time_remaining_seconds": max(0, int(time_remaining_seconds)) # Ensure non-negative
            }), 200
    except Exception as e:
         if hasattr(e, 'code') and e.code == 404:
             return jsonify({"msg": "Exam not found."}), 404
         print(f"Error fetching questions for exam {exam_id}, student {student_id}: {e}")
         return jsonify({"msg": "Error fetching exam questions."}), 500


@bp.route('/exams/<int:exam_id>/submit', methods=['POST'])
@jwt_required()
@student_required
@verified_required
def submit_exam(exam_id):
    student_id = get_current_user_id()
    if not student_id: return jsonify({"msg": "Invalid authentication token"}), 401

    # Use aware UTC time for submission timestamp and deadline check
    now_utc = datetime.now(timezone.utc)
    data = request.get_json()

    try:
        exam = Exam.query.get_or_404(exam_id)

        # --- Security & Time Checks ---
        existing_submission = StudentResponse.query.filter_by(student_id=student_id, exam_id=exam_id).first()
        if existing_submission:
            return jsonify({"msg": "You have already submitted responses for this exam."}), 403

        start_time_utc = ensure_aware_utc(exam.scheduled_time)
        if not start_time_utc:
             print(f"!!! ERROR: Cannot submit exam {exam_id}, invalid schedule.")
             return jsonify({"msg": "Exam schedule is invalid."}), 500
        end_time_utc = start_time_utc + timedelta(minutes=exam.duration)
        grace_period = timedelta(seconds=30)

        # Compare aware times for deadline check
        if now_utc > (end_time_utc + grace_period):
            print(f"--- DEBUG: Submission rejected for exam {exam_id}. Deadline passed. Now: {now_utc}, End+Grace: {end_time_utc + grace_period} ---")
            return jsonify({"msg": "Submission deadline has passed."}), 403
        # --- End Checks ---

        answers_data = data.get('answers')
        if not isinstance(answers_data, list):
            return jsonify({"msg": "Invalid submission format. Expected {'answers': [ ... ]}"}), 400

        # --- Process Answers (Logic remains the same) ---
        valid_question_ids = {q.id for q in Question.query.filter_by(exam_id=exam_id).with_entities(Question.id)}
        submitted_question_ids = set()
        responses_to_add = []
        for answer in answers_data:
            # (Validation logic as before)
            if not isinstance(answer, dict): continue
            q_id = answer.get('question_id')
            response_text = answer.get('response_text')
            if not isinstance(q_id, int): continue
            if q_id not in valid_question_ids: continue
            if q_id in submitted_question_ids: continue
            # Create response with aware UTC timestamp
            new_response = StudentResponse(
                student_id=student_id, exam_id=exam_id, question_id=q_id,
                response_text=response_text, submitted_at=now_utc
            )
            responses_to_add.append(new_response)
            submitted_question_ids.add(q_id)
        # --- End Process Answers ---

        if not responses_to_add:
            return jsonify({"msg": "No valid answers found in the submission."}), 400

        # --- Database Transaction ---
        db.session.add_all(responses_to_add)
        db.session.commit()
        # --- End Transaction ---

        print(f"--- Exam {exam_id} submitted successfully by student {student_id}. {len(responses_to_add)} responses saved. ---")
        return jsonify({"msg": "Exam submitted successfully."}), 200

    except Exception as e:
        db.session.rollback()
        if hasattr(e, 'code') and e.code == 404:
             return jsonify({"msg": "Exam not found."}), 404
        print(f"Error submitting exam {exam_id} for student {student_id}: {e}")
        return jsonify({"msg": "Failed to submit exam due to a server error."}), 500


# create a new route to get current user submitted exams 
@bp.route('/exams/submitted', methods=['GET'])
@jwt_required()
@student_required
@verified_required
def get_submitted_exams():
    student_id = get_current_user_id()
    if not student_id: return jsonify({"msg": "Invalid authentication token"}), 401

    try:
        submitted_exams = db.session.query(Exam).join(StudentResponse).filter(
            StudentResponse.student_id == student_id
        ).options(
            joinedload(Exam.questions)
        ).order_by(
            Exam.scheduled_time.desc()
        ).all()

        # Prepare data for response
        submitted_data = [{
            "id": e.id,
            "title": e.title,
            "scheduled_time": ensure_aware_utc(e.scheduled_time).isoformat() if e.scheduled_time else None,
            "submitted_at": ensure_aware_utc(resp.submitted_at).isoformat() if resp.submitted_at else None,
            "status": "Submitted"
        } for e in submitted_exams for resp in StudentResponse.query.filter_by(student_id=student_id, exam_id=e.id).all()]

        return jsonify(submitted_data), 200

    except Exception as e:
        print(f"Error fetching submitted exams for student {student_id}: {e}")
        return jsonify({"msg": "Error fetching submitted exams."}), 500


@bp.route('/results/my', methods=['GET'])
@jwt_required()
@student_required
@verified_required
def get_my_results():
    student_id = get_current_user_id()
    if not student_id: return jsonify({"msg": "Invalid authentication token"}), 401

    try:
        evaluations = db.session.query(Evaluation).join(StudentResponse).filter(
            StudentResponse.student_id == student_id
        ).options(
            joinedload(Evaluation.response)
                .joinedload(StudentResponse.question)
                    .joinedload(Question.exam)
        ).order_by(
            Exam.scheduled_time.desc(), # Order by exam date
            Question.id.asc()           # Then question ID
        ).all()

        # Group results by exam
        results_by_exam = {}
        for ev in evaluations:
            # --- Extract data (Logic mostly the same) ---
            resp = ev.response; question = resp.question if resp else None; exam = question.exam if question else None
            if not resp or not question or not exam: continue # Skip if related data missing

            exam_id = exam.id
            if exam_id not in results_by_exam:
                 # Ensure scheduled_time is output as aware ISO UTC
                 exam_scheduled_time_iso = ensure_aware_utc(exam.scheduled_time).isoformat() if exam.scheduled_time else None
                 results_by_exam[exam_id] = {
                    "exam_id": exam_id, "exam_title": exam.title,
                    "exam_scheduled_time": exam_scheduled_time_iso,
                    "total_marks_awarded": 0.0, "total_marks_possible": 0,
                    "questions": []
                 }

            marks_awarded = ev.marks_awarded # Keep None if not evaluated
            marks_possible = question.marks if question.marks is not None else 0
            # Ensure timestamps are output as aware ISO UTC
            submitted_at_iso = ensure_aware_utc(resp.submitted_at).isoformat() if resp.submitted_at else None
            evaluated_at_iso = ensure_aware_utc(ev.evaluated_at).isoformat() if ev.evaluated_at else None

            # Append question details
            results_by_exam[exam_id]['questions'].append({
                "question_id": question.id,
                "question_text": question.question_text,
                "question_type": question.question_type.value,
                "your_response": resp.response_text,
                "submitted_at": submitted_at_iso,
                "marks_awarded": marks_awarded,
                "marks_possible": marks_possible,
                "feedback": ev.feedback,
                "evaluated_at": evaluated_at_iso,
                "evaluated_by": ev.evaluated_by
            })
            # Add to totals
            results_by_exam[exam_id]['total_marks_possible'] += marks_possible
            if marks_awarded is not None:
                results_by_exam[exam_id]['total_marks_awarded'] += float(marks_awarded)
            # --- End Extract data ---

        final_results = list(results_by_exam.values())
        return jsonify(final_results), 200

    except Exception as e:
        print(f"Error fetching results for student {student_id}: {e}")
        return jsonify({"msg": "Error fetching results."}), 500