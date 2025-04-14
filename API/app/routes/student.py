# app/routes/student.py
from flask import Blueprint, request, jsonify
# Ensure db is imported correctly
from app.extensions import db
from app.models import Exam, Question, StudentResponse, Evaluation, QuestionType, UserRole
from app.utils.decorators import student_required, verified_required
from flask_jwt_extended import jwt_required
from app.utils.helpers import get_current_user_id
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import joinedload # Import joinedload
from sqlalchemy import Interval, cast, Integer, text # Import text for the interval fix
from datetime import datetime, timezone, timedelta
import pytz

bp = Blueprint('student', __name__)

@bp.route('/dashboard', methods=['GET'])
@jwt_required()
@student_required
@verified_required
def dashboard():
    student_id = get_current_user_id()
    if not student_id: return jsonify({"msg": "Invalid authentication token"}), 401
    try:
        completed_count = StudentResponse.query.filter_by(student_id=student_id).distinct(StudentResponse.exam_id).count()
        now = datetime.now(timezone.utc)
        upcoming_exams = Exam.query.filter(Exam.scheduled_time > now).order_by(Exam.scheduled_time.asc()).limit(5).all()
        upcoming_data = [{"id": e.id, "title": e.title, "scheduled_time": e.scheduled_time.isoformat()} for e in upcoming_exams]

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
        now_utc_datetime = datetime.now(timezone.utc)
        now_iso_string = now_utc_datetime.isoformat()

        submitted_exam_ids = {
            resp.exam_id
            for resp in StudentResponse.query.filter_by(student_id=student_id).with_entities(StudentResponse.exam_id)
        }
        print(f"--- DEBUG: Student {student_id} submitted exams: {submitted_exam_ids} ---")

        print("\n--- DEBUG: About to query potential_exams using SQLite datetime functions ---")

        potential_exams = Exam.query.filter(
            db.func.datetime(Exam.scheduled_time, '+' + Exam.duration.cast(db.String) + ' minutes') > now_iso_string
        ).order_by(Exam.scheduled_time.asc()).all()

        print(f"--- DEBUG: potential_exams query executed. Found {len(potential_exams) if potential_exams is not None else 'None'} potential exams. ---")

        exams_data = []
        for e in potential_exams:
            print(f"--- DEBUG: Checking exam ID {e.id} ('{e.title}') ---")
            if e.id in submitted_exam_ids:
                print(f"--- DEBUG: Skipping exam ID {e.id} (already submitted). ---")
                continue

            # Fix applied here
            start_time = e.scheduled_time.replace(tzinfo=timezone.utc) if e.scheduled_time.tzinfo is None else e.scheduled_time
            end_time = start_time + timedelta(minutes=e.duration)
            now_py = datetime.now(timezone.utc)

            status = "Expired"
            if now_py < start_time:
                status = "Upcoming"
                print(f"--- DEBUG: Exam ID {e.id} status: Upcoming ---")
            elif start_time <= now_py < end_time:
                status = "Active"
                print(f"--- DEBUG: Exam ID {e.id} status: Active ---")
            else:
                print(f"--- DEBUG: Exam ID {e.id} status: Expired (now >= end_time) ---")

            if status in ["Upcoming", "Active"]:
                print(f"--- DEBUG: Adding exam ID {e.id} to results. ---")
                exams_data.append({
                    "id": e.id,
                    "title": e.title,
                    "description": e.description,
                    "scheduled_time": start_time.isoformat(),
                    "duration": e.duration,
                    "status": status
                })
            else:
                print(f"--- DEBUG: Excluding exam ID {e.id} (status {status}). ---")

        print(f"--- DEBUG: Final exams_data count: {len(exams_data)} ---")
        return jsonify(exams_data), 200

    except Exception as e:
        print(f"!!! DEBUG: Exception caught in get_available_exams: {type(e).__name__} - {e}")
        print(f"Error fetching available exams for student {student_id}: {e}")
        return jsonify({"msg": "Error fetching available exams."}), 500


@bp.route('/exams/<int:exam_id>/take', methods=['GET'])
@jwt_required()
@student_required
@verified_required
def get_exam_questions_for_student(exam_id):
    student_id = get_current_user_id()
    if not student_id:
        return jsonify({"msg": "Invalid authentication token"}), 401

    try:
        exam = Exam.query.get_or_404(exam_id)

        # Check if already submitted
        existing_submission = StudentResponse.query.filter_by(student_id=student_id, exam_id=exam_id).first()
        if existing_submission:
            print(f"--- DEBUG: Student {student_id} already submitted exam {exam_id} ---")
            return jsonify({"msg": "You have already submitted responses for this exam."}), 403

        # Use a valid timezone, e.g., 'UTC' or 'Asia/Kolkata'
        local_tz = pytz.timezone("UTC")  # Replace with your actual timezone if needed

        # Ensure the scheduled_time is timezone-aware and convert to UTC if needed
        if exam.scheduled_time.tzinfo is None:
            exam_scheduled_time = local_tz.localize(exam.scheduled_time)
        else:
            exam_scheduled_time = exam.scheduled_time.astimezone(local_tz)

        # Calculate the exam's end time
        end_time = exam_scheduled_time + timedelta(minutes=exam.duration)

        # Get current time in UTC and convert to the same timezone
        now_utc = datetime.now(pytz.utc)

        # Check if the exam is active based on scheduled time
        if not (exam_scheduled_time <= now_utc < end_time):
            print(f"--- DEBUG: Exam {exam_id} not active. Now: {now_utc}, Start: {exam_scheduled_time}, End: {end_time}")
            return jsonify({"msg": "This exam is not currently active or has expired."}), 403

        # Fetch questions
        exam = db.session.query(Exam).filter(Exam.id == exam_id).first()
        questions = db.session.query(Question).filter(Question.exam_id == exam_id).all()

        questions_data = [{
            "id": q.id,
            "question_text": q.question_text,
            "question_type": q.question_type.value,
            "marks": q.marks,
            "options": q.options if q.question_type == QuestionType.MCQ else None,
            "word_limit": q.word_limit
        } for q in questions]

        # Calculate the remaining time
        time_remaining = (end_time - now_utc).total_seconds()

        return jsonify({
            "exam_id": exam.id,
            "exam_title": exam.title,
            "questions": questions_data,
            "time_remaining_seconds": max(0, int(time_remaining))
        }), 200

    except Exception as e:
        print(f"Error fetching questions for exam {exam_id}, student {student_id}: {e}")
        return jsonify({"msg": "Error fetching exam questions."}), 500


@bp.route('/exams/<int:exam_id>/submit', methods=['POST'])
@jwt_required()
@student_required
@verified_required
def submit_exam(exam_id):
    student_id = get_current_user_id()
    if not student_id: return jsonify({"msg": "Invalid authentication token"}), 401

    now = datetime.now(timezone.utc)
    data = request.get_json() # Expect {"answers": [...]}

    try:
        exam = Exam.query.get_or_404(exam_id)

        existing_submission = StudentResponse.query.filter_by(student_id=student_id, exam_id=exam_id).first()
        if existing_submission:
            return jsonify({"msg": "You have already submitted responses for this exam."}), 403

        start_time = exam.scheduled_time.replace(tzinfo=timezone.utc)
        end_time = start_time + timedelta(minutes=exam.duration)
        grace_period = timedelta(seconds=30)
        if now > (end_time + grace_period):
            return jsonify({"msg": "Submission deadline has passed."}), 403

        answers_data = data.get('answers')
        if not isinstance(answers_data, list):
            return jsonify({"msg": "Invalid submission format. Expected {'answers': [ ... ]}"}), 400

        valid_question_ids = {q.id for q in Question.query.filter_by(exam_id=exam_id).with_entities(Question.id)}
        submitted_question_ids = set()
        responses_to_add = []

        for answer in answers_data:
            if not isinstance(answer, dict):
                 print(f"Warning: Skipping invalid answer item (not a dict): {answer}")
                 continue

            q_id = answer.get('question_id')
            response_text = answer.get('response_text')

            if not isinstance(q_id, int):
                print(f"Warning: Skipping answer with non-integer question_id: {q_id}")
                continue
            if q_id not in valid_question_ids:
                print(f"Warning: Received answer for invalid/unknown question_id {q_id} in exam {exam_id}")
                continue
            if q_id in submitted_question_ids:
                 print(f"Warning: Duplicate answer submitted for question_id {q_id} in exam {exam_id}. Using first one.")
                 continue

            new_response = StudentResponse(
                student_id=student_id,
                exam_id=exam_id,
                question_id=q_id,
                response_text=response_text,
                submitted_at=now
            )
            responses_to_add.append(new_response)
            submitted_question_ids.add(q_id)

        if not responses_to_add:
            return jsonify({"msg": "No valid answers found in the submission."}), 400

        db.session.add_all(responses_to_add)
        db.session.commit()

        print(f"--- Exam {exam_id} submitted successfully by student {student_id}. {len(responses_to_add)} responses saved. ---")
        return jsonify({"msg": "Exam submitted successfully."}), 200

    except Exception as e:
        db.session.rollback()
        if hasattr(e, 'code') and e.code == 404:
             return jsonify({"msg": "Exam not found."}), 404
        print(f"Error submitting exam {exam_id} for student {student_id}: {e}")
        # import traceback; traceback.print_exc()
        return jsonify({"msg": "Failed to submit exam due to a server error."}), 500


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
            Exam.scheduled_time.desc(),
            Question.id.asc()
        ).all()

        results_by_exam = {}
        for ev in evaluations:
            resp = ev.response
            if not resp: continue
            question = resp.question
            if not question: continue
            exam = question.exam
            if not exam: continue

            exam_id = exam.id
            if exam_id not in results_by_exam:
                 results_by_exam[exam_id] = {
                    "exam_id": exam_id,
                    "exam_title": exam.title,
                    "exam_scheduled_time": exam.scheduled_time.isoformat(),
                    "total_marks_awarded": 0.0,
                    "total_marks_possible": 0,
                    "questions": []
                 }

            marks_awarded = ev.marks_awarded
            marks_possible = question.marks if question.marks is not None else 0

            results_by_exam[exam_id]['questions'].append({
                "question_id": question.id,
                "question_text": question.question_text,
                "question_type": question.question_type.value,
                "your_response": resp.response_text,
                "submitted_at": resp.submitted_at.isoformat() if resp.submitted_at else None,
                "marks_awarded": marks_awarded,
                "marks_possible": marks_possible,
                "feedback": ev.feedback,
                "evaluated_at": ev.evaluated_at.isoformat() if ev.evaluated_at else None,
                "evaluated_by": ev.evaluated_by
            })

            results_by_exam[exam_id]['total_marks_possible'] += marks_possible
            if marks_awarded is not None:
                results_by_exam[exam_id]['total_marks_awarded'] += float(marks_awarded)

        final_results = list(results_by_exam.values())
        return jsonify(final_results), 200

    except Exception as e:
        print(f"Error fetching results for student {student_id}: {e}")
        # import traceback; traceback.print_exc()
        return jsonify({"msg": "Error fetching results."}), 500