from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models import Exam, Question, StudentResponse, Evaluation, QuestionType, UserRole
from app.utils.decorators import student_required, verified_required
from flask_jwt_extended import jwt_required
from app.utils.helpers import get_current_user_id, format_datetime
from datetime import datetime, timedelta
from sqlalchemy.orm import joinedload
import pendulum

bp = Blueprint('student', __name__)

# Define IST timezone
IST = pendulum.timezone('Asia/Kolkata')


UTC = pendulum.timezone('UTC')

@bp.route('/dashboard', methods=['GET'])
@jwt_required()
@student_required
@verified_required
def dashboard():
    student_id = get_current_user_id()
    if not student_id:
        return jsonify({"msg": "Invalid authentication token"}), 401
    try:
        completed_count = StudentResponse.query.filter_by(student_id=student_id).distinct(StudentResponse.exam_id).count()
        now_ist = pendulum.now(IST)
        upcoming_exams = Exam.query.filter(Exam.scheduled_time > now_ist).order_by(Exam.scheduled_time.asc()).limit(5).all()
        upcoming_data = [{
            "id": e.id,
            "title": e.title,
            "scheduled_time": format_datetime(e.scheduled_time)
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
        now_ist = pendulum.now(IST).naive()  # Changed to naive
        submitted_exam_ids = {
            resp.exam_id
            for resp in StudentResponse.query.filter_by(student_id=student_id).with_entities(StudentResponse.exam_id)
        }

        potential_exams = Exam.query.all()
        exams_data = []
        for e in potential_exams:
            if e.id in submitted_exam_ids:
                continue

            start_time = e.scheduled_time  # Naive datetime
            if not start_time:
                continue

            end_time = start_time + timedelta(minutes=e.duration)
            status = "Expired"
            if now_ist < start_time:
                status = "Upcoming"
            elif start_time <= now_ist < end_time:
                status = "Active"

            if status in ["Upcoming", "Active"]:
                exams_data.append({
                    "id": e.id,
                    "title": e.title,
                    "description": e.description,
                    "scheduled_time": format_datetime(start_time),  # Changed
                    "duration": e.duration,
                    "status": status
                })

        return jsonify(exams_data), 200
    except Exception as e:
        print(f"!!! ERROR in get_available_exams for student {student_id}: {type(e).__name__} - {e}")
        return jsonify({"msg": "Error fetching available exams."}), 500


@bp.route('/exams/<int:exam_id>/submit', methods=['POST'])
@jwt_required()
@student_required
@verified_required
def submit_exam(exam_id):
    student_id = get_current_user_id()
    if not student_id:
        return jsonify({"msg": "Invalid authentication token"}), 401

    # Get current time in IST (aware)
    now_ist = pendulum.now(IST)
    data = request.get_json()

    try:
        exam = Exam.query.get(exam_id)
        if not exam:
            return jsonify({"msg": "Exam not found."}), 404

        # Check for existing submission (remains the same)
        existing_submission = StudentResponse.query.filter_by(
            student_id=student_id, exam_id=exam_id
        ).first()
        if existing_submission:
            return jsonify({"msg": "You have already submitted responses for this exam."}), 403

        # --- Corrected Time Validation Logic ---
        scheduled_time_naive = exam.scheduled_time
        if not scheduled_time_naive or not isinstance(scheduled_time_naive, datetime):
            print(f"!!! ERROR: Cannot submit exam {exam_id}, invalid schedule time in DB: {scheduled_time_naive}")
            return jsonify({"msg": "Exam schedule is invalid or missing."}), 500

        # Assume stored naive time is IST, make it timezone-aware IST
        try:
            start_time_ist = pendulum.instance(scheduled_time_naive, tz=IST)
        except Exception as e:
             print(f"!!! ERROR: Could not convert scheduled_time {scheduled_time_naive} to pendulum instance with IST for exam {exam_id} during submission: {e}")
             return jsonify({"msg": "Error processing exam schedule timezone."}), 500

        # Validate duration
        if not isinstance(exam.duration, int) or exam.duration <= 0:
            print(f"!!! ERROR: Exam {exam_id} has invalid duration during submission: {exam.duration}")
            return jsonify({"msg": "Invalid exam duration."}), 500

        # Calculate end time in IST (aware)
        end_time_ist = start_time_ist.add(minutes=exam.duration)

        # Define a grace period (e.g., 30 seconds)
        grace_period_seconds = 30
        submission_deadline_ist = end_time_ist.add(seconds=grace_period_seconds)

        # Compare current aware IST time with the aware IST deadline
        if now_ist > submission_deadline_ist:
            print(f"--- Submission rejected for exam {exam_id} by student {student_id}. Deadline passed. Now (IST): {now_ist}, Deadline (IST): {submission_deadline_ist} ---")
            return jsonify({"msg": f"Submission deadline ({submission_deadline_ist.format('YYYY-MM-DD HH:mm:ss Z')}) has passed."}), 403
        # --- End Corrected Time Validation Logic ---

        answers_data = data.get('answers')
        if not isinstance(answers_data, list):
            return jsonify({"msg": "Invalid submission format. Expected {'answers': [ ... ]}"}), 400

        valid_question_ids = {q.id for q in Question.query.filter_by(exam_id=exam_id).with_entities(Question.id)}
        submitted_question_ids = set()
        responses_to_add = []

        # Get the naive representation of the current time for saving, matching the model definition
        submitted_at_naive = now_ist.naive()

        for answer in answers_data:
            if not isinstance(answer, dict): continue
            q_id = answer.get('question_id')
            response_text = answer.get('response_text') # Can be None or empty string

            # Basic validation
            if not isinstance(q_id, int):
                print(f"--- Skipping answer due to invalid question_id type: {q_id} ---")
                continue
            if q_id not in valid_question_ids:
                print(f"--- Skipping answer for invalid question_id: {q_id} (not in exam {exam_id}) ---")
                continue
            if q_id in submitted_question_ids:
                print(f"--- Skipping duplicate answer for question_id: {q_id} in exam {exam_id} ---")
                continue # Prevent duplicate submissions for the same question

            # Create the response object
            new_response = StudentResponse(
                student_id=student_id,
                exam_id=exam_id,
                question_id=q_id,
                response_text=response_text, # Store whatever text is provided
                # Save the naive time, consistent with model's default
                submitted_at=submitted_at_naive
            )
            responses_to_add.append(new_response)
            submitted_question_ids.add(q_id)

        if not responses_to_add:
            print(f"--- Submission attempt for exam {exam_id} by student {student_id} had no valid answers. ---")
            return jsonify({"msg": "No valid answers found in the submission."}), 400

        # Add all valid responses to the session
        db.session.add_all(responses_to_add)
        db.session.commit()
        print(f"--- Exam {exam_id} submitted successfully by student {student_id}. {len(responses_to_add)} responses saved. ---")
        return jsonify({"msg": "Exam submitted successfully."}), 200

    except Exception as e:
        db.session.rollback()
        # Log the specific exception
        print(f"!!! EXCEPTION during submit_exam (Exam ID: {exam_id}, Student ID: {student_id}): {type(e).__name__}: {str(e)}")
        # import traceback; traceback.print_exc() # Uncomment for full trace
        return jsonify({"msg": "Failed to submit exam due to a server error."}), 500


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

        submitted_data = [{
            "id": e.id,
            "title": e.title,
            "scheduled_time": format_datetime(e.scheduled_time),  # Changed
            "submitted_at": format_datetime(resp.submitted_at),  # Changed
            "status": "Submitted"
        } for e in submitted_exams for resp in StudentResponse.query.filter_by(student_id=student_id, exam_id=e.id).all()]

        return jsonify(submitted_data), 200
    except Exception as e:
        print(f"Error fetching submitted exams for student {student_id}: {e}")
        return jsonify({"msg": "Error fetching submitted exams."}), 500



@bp.route('/exams/<int:exam_id>/take', methods=['GET'])
@jwt_required()
@student_required
@verified_required
def get_exam_questions_for_student(exam_id):
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

        # --- Timezone Corrected Logic ---
        scheduled_time_naive = exam.scheduled_time
        if not scheduled_time_naive or not isinstance(scheduled_time_naive, datetime):
            print(f"!!! ERROR: Exam {exam_id} has invalid scheduled_time in DB: {scheduled_time_naive}")
            return jsonify({"msg": "Exam schedule is invalid or missing."}), 500

        # Assume the stored naive time is IST, make it timezone-aware IST
        try:
            start_time_ist = pendulum.instance(scheduled_time_naive, tz=IST)
        except Exception as e:
             print(f"!!! ERROR: Could not convert scheduled_time {scheduled_time_naive} to pendulum instance with IST for exam {exam_id}: {e}")
             return jsonify({"msg": "Error processing exam schedule timezone."}), 500

        # Convert start time to UTC for reliable comparison
        start_time_utc = start_time_ist.in_timezone(UTC)

        # Validate duration
        if not isinstance(exam.duration, int) or exam.duration <= 0:
            print(f"!!! ERROR: Exam {exam_id} has invalid duration: {exam.duration}")
            return jsonify({"msg": "Invalid exam duration."}), 500

        # Calculate end time in UTC
        end_time_utc = start_time_utc.add(minutes=exam.duration)

        # Get current time in UTC
        now_utc = pendulum.now(UTC)

        # Check if the exam is currently active (using UTC times)
        if not (start_time_utc <= now_utc < end_time_utc):
            status = "Upcoming" if now_utc < start_time_utc else "Expired"
            print(f"--- Exam {exam_id} access denied for student {student_id}. Status: {status}. Now (UTC): {now_utc}, Start (UTC): {start_time_utc}, End (UTC): {end_time_utc} ---")
            return jsonify({"msg": f"This exam is not currently active. Status: {status}"}), 403
        # --- End Timezone Corrected Logic ---

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

        # Calculate remaining time in seconds
        time_remaining_seconds = max(0, int((end_time_utc - now_utc).total_seconds()))

        print(f"--- Student {student_id} starting exam {exam_id}. Time remaining: {time_remaining_seconds}s ---")

        return jsonify({
            "exam_id": exam.id,
            "exam_title": exam.title,
            # Return the original scheduled time (as IST representation)
            "scheduled_time_ist": format_datetime(exam.scheduled_time),
            "duration_minutes": exam.duration,
            "questions": questions_data,
            "time_remaining_seconds": time_remaining_seconds
        }), 200

    except Exception as e:
        # Catch specific exceptions if needed (e.g., DB errors)
        print(f"!!! EXCEPTION in get_exam_questions_for_student (Exam ID: {exam_id}, Student ID: {student_id}): {type(e).__name__}: {str(e)}")
        # import traceback; traceback.print_exc() # Uncomment for detailed stack trace in logs
        return jsonify({"msg": "An unexpected error occurred while fetching the exam questions."}), 500



@bp.route('/results/my', methods=['GET'])
@jwt_required()
@student_required
@verified_required
def get_my_results():
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
            # Load the evaluation if it exists (left outer join behavior)
            joinedload(StudentResponse.evaluation)
        ).order_by(
            # Order by exam schedule descending, then by question ID within the exam
            Exam.scheduled_time.desc(),
            StudentResponse.question_id.asc() # Order by question ID for consistency
        ).join(Question).join(Exam).all() # Explicit joins for ordering

        results_by_exam = {}
        for resp in responses:
            question = resp.question
            # If question relationship didn't load or is broken, skip
            if not question:
                 print(f"!!! WARNING: Skipping response ID {resp.id} for student {student_id} due to missing question link.")
                 continue
            exam = question.exam
            # If exam relationship didn't load, skip
            if not exam:
                 print(f"!!! WARNING: Skipping response ID {resp.id} for student {student_id} due to missing exam link (via question {question.id}).")
                 continue

            evaluation = resp.evaluation # This will be None if no evaluation exists yet

            exam_id = exam.id
            if exam_id not in results_by_exam:
                results_by_exam[exam_id] = {
                    "exam_id": exam_id,
                    "exam_title": exam.title,
                    # Format the scheduled time (naive IST representation)
                    "exam_scheduled_time_ist": format_datetime(exam.scheduled_time),
                    "total_marks_awarded": 0.0,
                    "total_marks_possible": 0,
                    # Default status, might change below
                    "overall_status": "Pending Evaluation",
                    "questions": [],
                    "_pending_count": 0 # Internal counter
                }

            # Get details for this specific question/response
            marks_possible = question.marks if question.marks is not None else 0
            marks_awarded = None
            feedback = "Not evaluated yet"
            evaluated_at_iso = None
            evaluated_by = None
            question_status = "Pending Evaluation"

            if evaluation:
                marks_awarded = evaluation.marks_awarded # Could still be None if evaluation record exists but marks weren't assigned? Assume float if exists.
                feedback = evaluation.feedback if evaluation.feedback else "Evaluation submitted, no feedback provided."
                evaluated_at_iso = format_datetime(evaluation.evaluated_at) # Format evaluation time
                evaluated_by = evaluation.evaluated_by
                question_status = "Evaluated"
            else:
                 results_by_exam[exam_id]['_pending_count'] += 1 # Increment pending counter for this exam

            # Format submission time
            submitted_at_iso = format_datetime(resp.submitted_at)

            results_by_exam[exam_id]['questions'].append({
                "question_id": question.id,
                "question_text": question.question_text,
                "question_type": question.question_type.value,
                "your_response": resp.response_text,
                "submitted_at_ist": submitted_at_iso, # Assuming submitted_at is also naive IST
                "marks_awarded": marks_awarded,
                "marks_possible": marks_possible,
                "feedback": feedback,
                "evaluated_at_ist": evaluated_at_iso, # Assuming evaluated_at is also naive IST
                "evaluated_by": evaluated_by,
                "status": question_status
            })

            # Update exam totals
            results_by_exam[exam_id]['total_marks_possible'] += marks_possible
            if marks_awarded is not None:
                # Use try-except for robust float conversion
                try:
                    results_by_exam[exam_id]['total_marks_awarded'] += float(marks_awarded)
                except (ValueError, TypeError):
                     print(f"!!! WARNING: Could not convert marks_awarded '{marks_awarded}' to float for response ID {resp.id}. Skipping addition.")

        # Post-process to set final exam status and remove internal counter
        final_results = []
        for exam_id, data in results_by_exam.items():
            if data['_pending_count'] == 0:
                 data['overall_status'] = "Results Declared"
            else:
                 # You could add "Partially Evaluated" if needed based on counts
                 data['overall_status'] = f"Pending Evaluation ({data['_pending_count']} questions)"

            del data['_pending_count'] # Remove internal counter
            final_results.append(data)

        return jsonify(final_results), 200

    except Exception as e:
        print(f"!!! EXCEPTION in get_my_results (Student ID: {student_id}): {type(e).__name__}: {str(e)}")
        # import traceback; traceback.print_exc() # Uncomment for detailed stack trace
        return jsonify({"msg": "An unexpected error occurred while fetching your results."}), 500
