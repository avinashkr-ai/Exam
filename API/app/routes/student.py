# app/routes/student.py

from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models import Exam, Question, StudentResponse, Evaluation, QuestionType, UserRole
from app.utils.decorators import student_required, verified_required
from flask_jwt_extended import jwt_required
# Make sure helpers uses standard datetime and formats naive UTC correctly
from app.utils.helpers import get_current_user_id, format_datetime
# Use standard Python datetime and timedelta
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import joinedload
# Removed pendulum import

bp = Blueprint('student', __name__)

# No specific timezone definitions needed here when using naive UTC consistently

@bp.route('/dashboard', methods=['GET'])
@jwt_required()
@student_required
@verified_required
def dashboard():
    """Provides dashboard information for the logged-in student."""
    student_id = get_current_user_id()
    if not student_id:
        return jsonify({"msg": "Invalid authentication token"}), 401

    try:
        # Count distinct exams the student has submitted responses for
        completed_count = db.session.query(StudentResponse.exam_id).filter_by(
            student_id=student_id
        ).distinct().count()

        # Get current time in naive UTC
        now_naive_utc = datetime.utcnow()

        # Find upcoming exams (scheduled time > now)
        # Comparison works correctly between naive UTC datetimes
        upcoming_exams = Exam.query.filter(
            Exam.scheduled_time > now_naive_utc
        ).order_by(Exam.scheduled_time.asc()).limit(5).all()

        # Format upcoming exams data
        upcoming_data = [{
            "id": e.id,
            "title": e.title,
            # Format naive UTC time using helper
            "scheduled_time_utc": format_datetime(e.scheduled_time)
        } for e in upcoming_exams]

        print(f"--- Student {student_id} dashboard generated. Completed: {completed_count} ---")
        return jsonify({
            "message": "Student Dashboard",
            "completed_exams_count": completed_count,
            "upcoming_exams": upcoming_data # List of upcoming exams
        }), 200
    except Exception as e:
        print(f"!!! Error fetching student dashboard for student {student_id}: {e}")
        return jsonify({"msg": "Error fetching dashboard data."}), 500

@bp.route('/exams/available', methods=['GET'])
@jwt_required()
@student_required
@verified_required
def get_available_exams():
    """Lists exams available for the student to take (upcoming or active)."""
    student_id = get_current_user_id()
    if not student_id:
        return jsonify({"msg": "Invalid authentication token"}), 401

    try:
        # Get current time in naive UTC
        now_naive_utc = datetime.utcnow()

        # Get IDs of exams already submitted by this student
        submitted_exam_ids = {
            resp.exam_id for resp in
            db.session.query(StudentResponse.exam_id).filter_by(student_id=student_id)
        }
        print(f"--- Student {student_id} has submitted exams: {submitted_exam_ids} ---")

        # Get all potential exams
        # TODO: Optimization - Could filter exams by schedule time relevance here if needed
        potential_exams = Exam.query.order_by(Exam.scheduled_time.asc()).all()
        available_exams_data = []

        for exam in potential_exams:
            # Skip if already submitted
            if exam.id in submitted_exam_ids:
                continue

            # Get naive UTC start time from DB
            start_time_naive_utc = exam.scheduled_time
            if not start_time_naive_utc or not isinstance(start_time_naive_utc, datetime):
                print(f"!!! WARNING: Skipping exam {exam.id} due to invalid scheduled_time: {start_time_naive_utc}")
                continue
            if not isinstance(exam.duration, int) or exam.duration <= 0:
                print(f"!!! WARNING: Skipping exam {exam.id} due to invalid duration: {exam.duration}")
                continue

            # Calculate naive UTC end time
            try:
                end_time_naive_utc = start_time_naive_utc + timedelta(minutes=exam.duration)
            except TypeError:
                print(f"!!! WARNING: Skipping exam {exam.id} due to error calculating end time (start={start_time_naive_utc}, duration={exam.duration})")
                continue

            # Determine exam status based on naive UTC comparison
            status = "Expired"
            if now_naive_utc < start_time_naive_utc:
                status = "Upcoming"
            elif start_time_naive_utc <= now_naive_utc < end_time_naive_utc:
                status = "Active"

            # Include only upcoming or active exams
            if status in ["Upcoming", "Active"]:
                available_exams_data.append({
                    "id": exam.id,
                    "title": exam.title,
                    "description": exam.description,
                    # Format naive UTC time using helper
                    "scheduled_time_utc": format_datetime(start_time_naive_utc),
                    "duration_minutes": exam.duration,
                    "status": status
                })

        print(f"--- Found {len(available_exams_data)} available exams for student {student_id} ---")
        return jsonify(available_exams_data), 200

    except Exception as e:
        print(f"!!! ERROR in get_available_exams for student {student_id}: {type(e).__name__} - {e}")
        return jsonify({"msg": "Error fetching available exams."}), 500

@bp.route('/exams/<int:exam_id>/take', methods=['GET'])
@jwt_required()
@student_required
@verified_required
def get_exam_questions_for_student(exam_id):
    """Allows a student to start an active exam and retrieves its questions."""
    student_id = get_current_user_id()
    if not student_id:
        return jsonify({"msg": "Invalid authentication token"}), 401

    try:
        # Fetch the exam
        exam = Exam.query.get(exam_id)
        if not exam:
            return jsonify({"msg": "Exam not found."}), 404

        # Check if student has already submitted for this exam
        existing_submission = StudentResponse.query.filter_by(
            student_id=student_id, exam_id=exam_id
        ).first()
        if existing_submission:
            print(f"--- Student {student_id} attempted to retake exam {exam_id} ---")
            return jsonify({"msg": "You have already submitted responses for this exam."}), 403

        # --- Naive UTC Time Validation Logic ---
        start_time_naive_utc = exam.scheduled_time
        if not start_time_naive_utc or not isinstance(start_time_naive_utc, datetime):
            print(f"!!! ERROR: Exam {exam_id} has invalid scheduled_time in DB: {start_time_naive_utc}")
            return jsonify({"msg": "Exam schedule is invalid or missing."}), 500

        if not isinstance(exam.duration, int) or exam.duration <= 0:
            print(f"!!! ERROR: Exam {exam_id} has invalid duration: {exam.duration}")
            return jsonify({"msg": "Invalid exam duration."}), 500

        # Calculate end time in naive UTC
        try:
             end_time_naive_utc = start_time_naive_utc + timedelta(minutes=exam.duration)
        except TypeError:
             print(f"!!! ERROR: Could not calculate end time for exam {exam_id} (start={start_time_naive_utc}, duration={exam.duration})")
             return jsonify({"msg": "Error processing exam duration."}), 500

        # Get current time in naive UTC
        now_naive_utc = datetime.utcnow()

        # Check if the exam is currently active (using naive UTC times)
        if not (start_time_naive_utc <= now_naive_utc < end_time_naive_utc):
            status = "Upcoming" if now_naive_utc < start_time_naive_utc else "Expired"
            print(f"--- Exam {exam_id} access denied for student {student_id}. Status: {status}. Now (UTC): {now_naive_utc}, Start (UTC): {start_time_naive_utc}, End (UTC): {end_time_naive_utc} ---")
            return jsonify({"msg": f"This exam is not currently active. Status: {status}"}), 403
        # --- End Naive UTC Time Validation ---

        # Fetch questions (excluding sensitive info like correct_answer)
        questions = Question.query.filter_by(exam_id=exam_id).order_by(Question.id).all()
        questions_data = [{
            "id": q.id,
            "question_text": q.question_text,
            "question_type": q.question_type.value,
            "marks": q.marks,
            # Only include options for MCQ, exclude correct_answer
            "options": q.options if q.question_type == QuestionType.MCQ else None,
            "word_limit": q.word_limit if q.question_type != QuestionType.MCQ else None
        } for q in questions]

        # Calculate remaining time in seconds using naive UTC times
        time_remaining_seconds = max(0, int((end_time_naive_utc - now_naive_utc).total_seconds()))

        print(f"--- Student {student_id} starting exam {exam_id}. Time remaining: {time_remaining_seconds}s ---")

        return jsonify({
            "exam_id": exam.id,
            "exam_title": exam.title,
            # Return the original scheduled time (naive UTC) formatted
            "scheduled_time_utc": format_datetime(exam.scheduled_time),
            "duration_minutes": exam.duration,
            "questions": questions_data,
            "time_remaining_seconds": time_remaining_seconds
        }), 200

    except Exception as e:
        print(f"!!! EXCEPTION in get_exam_questions_for_student (Exam ID: {exam_id}, Student ID: {student_id}): {type(e).__name__}: {str(e)}")
        # import traceback; traceback.print_exc() # For detailed debugging
        return jsonify({"msg": "An unexpected error occurred while fetching the exam questions."}), 500

@bp.route('/exams/<int:exam_id>/submit', methods=['POST'])
@jwt_required()
@student_required
@verified_required
def submit_exam(exam_id):
    """Handles the submission of answers for an exam."""
    student_id = get_current_user_id()
    if not student_id:
        return jsonify({"msg": "Invalid authentication token"}), 401

    # Get current time in naive UTC
    now_naive_utc = datetime.utcnow()
    data = request.get_json()
    if not data:
        return jsonify({"msg": "Missing JSON data in request."}), 400

    try:
        exam = Exam.query.get(exam_id)
        if not exam:
            return jsonify({"msg": "Exam not found."}), 404

        # Check for existing submission
        existing_submission = StudentResponse.query.filter_by(
            student_id=student_id, exam_id=exam_id
        ).first()
        if existing_submission:
            return jsonify({"msg": "You have already submitted responses for this exam."}), 403

        # --- Naive UTC Time Validation Logic for Submission Deadline ---
        start_time_naive_utc = exam.scheduled_time
        if not start_time_naive_utc or not isinstance(start_time_naive_utc, datetime):
            print(f"!!! ERROR: Cannot submit exam {exam_id}, invalid schedule time in DB: {start_time_naive_utc}")
            return jsonify({"msg": "Exam schedule is invalid or missing."}), 500

        if not isinstance(exam.duration, int) or exam.duration <= 0:
            print(f"!!! ERROR: Exam {exam_id} has invalid duration during submission: {exam.duration}")
            return jsonify({"msg": "Invalid exam duration."}), 500

        # Calculate end time and deadline in naive UTC
        try:
            end_time_naive_utc = start_time_naive_utc + timedelta(minutes=exam.duration)
            grace_period_seconds = 30 # Define a grace period (e.g., 30 seconds)
            submission_deadline_naive_utc = end_time_naive_utc + timedelta(seconds=grace_period_seconds)
        except TypeError:
             print(f"!!! ERROR: Could not calculate deadline for exam {exam_id}")
             return jsonify({"msg": "Error processing exam deadline."}), 500

        # Compare current naive UTC time with the naive UTC deadline
        if now_naive_utc > submission_deadline_naive_utc:
            deadline_str = format_datetime(submission_deadline_naive_utc) # Format for message
            print(f"--- Submission rejected for exam {exam_id} by student {student_id}. Deadline passed. Now (UTC): {now_naive_utc}, Deadline (UTC): {submission_deadline_naive_utc} ---")
            return jsonify({"msg": f"Submission deadline ({deadline_str} UTC) has passed."}), 403
        # --- End Naive UTC Time Validation ---

        answers_data = data.get('answers')
        if not isinstance(answers_data, list):
            return jsonify({"msg": "Invalid submission format. Expected {'answers': [ ... ]}"}), 400

        # Get valid question IDs for this exam
        valid_question_ids = {q.id for q in Question.query.filter_by(exam_id=exam_id).with_entities(Question.id)}
        submitted_question_ids = set() # Track submitted Qs to prevent duplicates
        responses_to_add = []

        # Process submitted answers
        for answer in answers_data:
            if not isinstance(answer, dict): continue # Skip invalid answer formats

            q_id = answer.get('question_id')
            response_text = answer.get('response_text') # Can be None or empty string

            # Validate question ID
            if not isinstance(q_id, int):
                print(f"--- Skipping answer due to invalid question_id type: {q_id} ---")
                continue
            if q_id not in valid_question_ids:
                print(f"--- Skipping answer for invalid question_id: {q_id} (not in exam {exam_id}) ---")
                continue
            if q_id in submitted_question_ids:
                print(f"--- Skipping duplicate answer for question_id: {q_id} in exam {exam_id} ---")
                continue

            # Create the response object - submitted_at will use the default datetime.utcnow()
            new_response = StudentResponse(
                student_id=student_id,
                exam_id=exam_id,
                question_id=q_id,
                response_text=response_text,
                submitted_at=now_naive_utc # Explicitly set submission time to current UTC
            )
            responses_to_add.append(new_response)
            submitted_question_ids.add(q_id) # Mark question as processed

        if not responses_to_add:
            print(f"--- Submission attempt for exam {exam_id} by student {student_id} had no valid answers. ---")
            return jsonify({"msg": "No valid answers found in the submission."}), 400

        # Add all valid responses to the session and commit
        db.session.add_all(responses_to_add)
        db.session.commit()
        print(f"--- Exam {exam_id} submitted successfully by student {student_id}. {len(responses_to_add)} responses saved. ---")
        return jsonify({"msg": "Exam submitted successfully."}), 200

    except Exception as e:
        db.session.rollback()
        print(f"!!! EXCEPTION during submit_exam (Exam ID: {exam_id}, Student ID: {student_id}): {type(e).__name__}: {str(e)}")
        # import traceback; traceback.print_exc() # For detailed trace
        return jsonify({"msg": "Failed to submit exam due to a server error."}), 500

@bp.route('/exams/submitted', methods=['GET'])
@jwt_required()
@student_required
@verified_required
def get_submitted_exams():
    """Lists exams the student has already submitted."""
    student_id = get_current_user_id()
    if not student_id: return jsonify({"msg": "Invalid authentication token"}), 401

    try:
        # Find all responses submitted by the student
        submissions = db.session.query(StudentResponse).filter(
            StudentResponse.student_id == student_id
        ).options(
            joinedload(StudentResponse.exam) # Load the related exam info
        ).order_by(
            StudentResponse.submitted_at.desc() # Order by most recent submission
        ).all()

        # Use a dictionary to group by exam_id and get the latest submission time per exam
        submitted_exams_info = {}
        for sub in submissions:
            if sub.exam and sub.exam_id not in submitted_exams_info:
                submitted_exams_info[sub.exam_id] = {
                    "id": sub.exam.id,
                    "title": sub.exam.title,
                    # Format naive UTC scheduled time
                    "scheduled_time_utc": format_datetime(sub.exam.scheduled_time),
                    # Format naive UTC submission time
                    "submitted_at_utc": format_datetime(sub.submitted_at),
                    "status": "Submitted"
                }

        submitted_data = list(submitted_exams_info.values())
        # Optionally re-sort if needed, e.g., by scheduled_time desc
        submitted_data.sort(key=lambda x: x.get("scheduled_time_utc") or "", reverse=True)

        print(f"--- Found {len(submitted_data)} submitted exams for student {student_id} ---")
        return jsonify(submitted_data), 200
    except Exception as e:
        print(f"!!! Error fetching submitted exams for student {student_id}: {e}")
        return jsonify({"msg": "Error fetching submitted exams list."}), 500

@bp.route('/results/my', methods=['GET'])
@jwt_required()
@student_required
@verified_required
def get_my_results():
    """Retrieves the results for all exams submitted by the student."""
    student_id = get_current_user_id()
    if not student_id:
        return jsonify({"msg": "Invalid authentication token"}), 401

    try:
        # Fetch all student responses, joining related data including optional evaluation
        responses = db.session.query(StudentResponse).filter(
            StudentResponse.student_id == student_id
        ).options(
            # Load question and the exam it belongs to
            joinedload(StudentResponse.question).joinedload(Question.exam),
            # Load the evaluation if it exists
            joinedload(StudentResponse.evaluation)
        ).order_by(
            # Order by exam schedule descending, then by question ID
            Exam.scheduled_time.desc(),
            StudentResponse.question_id.asc()
        ).join(Question).join(Exam).all() # Explicit joins needed for ordering by Exam field

        results_by_exam = {}
        for resp in responses:
            question = resp.question
            if not question:
                 print(f"!!! WARNING: Skipping response ID {resp.id} for student {student_id} due to missing question link.")
                 continue
            exam = question.exam
            if not exam:
                 print(f"!!! WARNING: Skipping response ID {resp.id} for student {student_id} due to missing exam link (via question {question.id}).")
                 continue

            evaluation = resp.evaluation # Will be None if no evaluation exists

            exam_id = exam.id
            if exam_id not in results_by_exam:
                # Initialize structure for this exam
                results_by_exam[exam_id] = {
                    "exam_id": exam_id,
                    "exam_title": exam.title,
                    # Format naive UTC scheduled time
                    "exam_scheduled_time_utc": format_datetime(exam.scheduled_time),
                    "total_marks_awarded": 0.0,
                    "total_marks_possible": 0,
                    "overall_status": "Pending Evaluation", # Default status
                    "questions": [],
                    "_pending_count": 0 # Internal counter for unevaluated questions
                }

            # Process details for this specific question/response
            marks_possible = question.marks if question.marks is not None else 0
            marks_awarded = None
            feedback = "Not evaluated yet"
            evaluated_at_utc_iso = None
            evaluated_by = None
            question_status = "Pending Evaluation"

            if evaluation:
                # If an evaluation exists, extract its details
                marks_awarded = evaluation.marks_awarded # Assume float if exists
                feedback = evaluation.feedback if evaluation.feedback else "Evaluation submitted, no feedback provided."
                evaluated_at_utc_iso = format_datetime(evaluation.evaluated_at) # Format naive UTC
                evaluated_by = evaluation.evaluated_by
                question_status = "Evaluated"
            else:
                 # Increment pending counter if no evaluation exists for this response
                 results_by_exam[exam_id]['_pending_count'] += 1

            # Format naive UTC submission time
            submitted_at_utc_iso = format_datetime(resp.submitted_at)

            # Add question details to the exam's list
            results_by_exam[exam_id]['questions'].append({
                "question_id": question.id,
                "question_text": question.question_text,
                "question_type": question.question_type.value,
                "your_response": resp.response_text,
                "submitted_at_utc": submitted_at_utc_iso,
                "marks_awarded": marks_awarded,
                "marks_possible": marks_possible,
                "feedback": feedback,
                "evaluated_at_utc": evaluated_at_utc_iso,
                "evaluated_by": evaluated_by,
                "status": question_status
            })

            # Update exam totals
            results_by_exam[exam_id]['total_marks_possible'] += marks_possible
            if marks_awarded is not None:
                try:
                    results_by_exam[exam_id]['total_marks_awarded'] += float(marks_awarded)
                except (ValueError, TypeError):
                     print(f"!!! WARNING: Could not convert marks_awarded '{marks_awarded}' to float for response ID {resp.id}. Skipping addition.")

        # Post-process to set final exam status and remove internal counter
        final_results = []
        for exam_id, data in results_by_exam.items():
            if data['_pending_count'] == 0:
                 data['overall_status'] = "Results Declared" # All questions evaluated
            # Keep "Pending Evaluation" if count > 0, or add "Partially Evaluated" if needed
            # else: data['overall_status'] = f"Pending Evaluation ({data['_pending_count']} questions)"

            del data['_pending_count'] # Remove internal counter from final output
            final_results.append(data)

        print(f"--- Generated results for {len(final_results)} exams for student {student_id} ---")
        return jsonify(final_results), 200

    except Exception as e:
        print(f"!!! EXCEPTION in get_my_results (Student ID: {student_id}): {type(e).__name__}: {str(e)}")
        # import traceback; traceback.print_exc() # For detailed trace
        return jsonify({"msg": "An unexpected error occurred while fetching your results."}), 500