from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timezone
import random # For placeholder evaluation
# import google.generativeai as genai # Import if using Gemini directly here
# from config import Config # Import if using Gemini directly here

from ..models import (
    db, User, Exam, Question, Submission, SubmittedAnswer, Result,
    ExamQuestion, SubmissionStatus
)
from ..utils.decorators import student_required

student_bp = Blueprint('student', __name__)

# --- Exam Taking ---

@student_bp.route('/exams/available', methods=['GET'])
@student_required
def list_available_exams():
    user_id = get_jwt_identity()
    now = datetime.now(timezone.utc)

    # Find exams within the availability window
    available_exams_query = Exam.query.filter(
        Exam.start_time <= now,
        Exam.end_time >= now
    )

    # Find exams the student has already submitted
    submitted_exam_ids = db.session.query(Submission.exam_id).filter(
        Submission.student_id == user_id
    ).subquery()

    # Filter out submitted exams
    exams_to_take = available_exams_query.filter(
        Exam.id.notin_(submitted_exam_ids)
    ).order_by(Exam.end_time.asc()).all()

    output = [{
        'id': exam.id,
        'title': exam.title,
        'description': exam.description,
        'duration_minutes': exam.duration_minutes,
        'end_time': exam.end_time.isoformat(), # Show when it closes
        'question_count': len(exam.questions)
    } for exam in exams_to_take]

    return jsonify(exams=output), 200

@student_bp.route('/exams/<int:exam_id>/start', methods=['GET'])
@student_required
def get_exam_questions(exam_id):
    user_id = get_jwt_identity()
    now = datetime.now(timezone.utc)
    exam = Exam.query.get_or_404(exam_id)

    # Verify exam is available
    if not (exam.start_time <= now <= exam.end_time):
        return jsonify(message="Exam is not currently available."), 403

    # Verify student hasn't submitted already
    existing_submission = Submission.query.filter_by(student_id=user_id, exam_id=exam_id).first()
    if existing_submission:
        return jsonify(message="You have already submitted this exam."), 403

    # Fetch questions associated with the exam via ExamQuestion, ordered
    exam_questions = ExamQuestion.query.filter_by(exam_id=exam_id).order_by(ExamQuestion.order).all()

    questions_output = []
    for eq in exam_questions:
        q = eq.question # Access the actual Question object
        questions_output.append({
            'id': q.id,
            'question_text': q.question_text,
            'question_type': q.question_type,
            'points': q.points,
            'order': eq.order
            # DO NOT SEND correct_answer_or_criteria to student
        })

    return jsonify({
        'exam_id': exam.id,
        'title': exam.title,
        'duration_minutes': exam.duration_minutes,
        'questions': questions_output
    }), 200


@student_bp.route('/exams/<int:exam_id>/submit', methods=['POST'])
@student_required
def submit_exam(exam_id):
    user_id = get_jwt_identity()
    now = datetime.now(timezone.utc)
    data = request.get_json()

    exam = Exam.query.get_or_404(exam_id)

    # Basic checks (time window, already submitted)
    if not (exam.start_time <= now <= exam.end_time):
         # Allow a small grace period maybe? For now, strict check.
        return jsonify(message="Exam submission window has closed."), 403

    existing_submission = Submission.query.filter_by(student_id=user_id, exam_id=exam_id).first()
    if existing_submission:
        return jsonify(message="You have already submitted this exam."), 403

    answers_data = data.get('answers')
    if not isinstance(answers_data, list):
        return jsonify(message="'answers' must be a list of {'question_id': id, 'answer_text': text}"), 400

    # --- Create Submission Record ---
    submission = Submission(
        student_id=user_id,
        exam_id=exam_id,
        submitted_at=now,
        status=SubmissionStatus.SUBMITTED # Start as submitted
    )
    db.session.add(submission)
    db.session.flush() # Get submission.id

    # --- Store Submitted Answers ---
    submitted_q_ids = set()
    for answer in answers_data:
        q_id = answer.get('question_id')
        ans_text = answer.get('answer_text')
        if q_id is None:
            db.session.rollback()
            return jsonify(message="Each answer must have a 'question_id'"), 400

        # Optional: Verify q_id actually belongs to this exam
        # exam_question = ExamQuestion.query.filter_by(exam_id=exam_id, question_id=q_id).first()
        # if not exam_question:
        #     db.session.rollback()
        #     return jsonify(message=f"Question ID {q_id} does not belong to this exam."), 400

        submitted_answer = SubmittedAnswer(
            submission_id=submission.id,
            question_id=q_id,
            student_answer_text=ans_text
        )
        db.session.add(submitted_answer)
        submitted_q_ids.add(q_id)

    # --- Placeholder/Simulated Evaluation (Replace with Async Task + Gemini) ---
    # In a real app, you'd trigger an async task here: evaluate_submission.delay(submission.id)
    # For now, let's simulate immediate evaluation with random scores.

    total_score = 0
    exam_questions = ExamQuestion.query.filter_by(exam_id=exam_id).all()
    evaluation_time = datetime.now(timezone.utc)

    for eq in exam_questions:
        q = eq.question
        # Check if an answer was submitted for this question
        if q.id in submitted_q_ids:
            # Simulate score (e.g., random score for non-MCQ, check answer for MCQ)
            if q.question_type == 'mcq':
                # Placeholder: Assume correct_answer_or_criteria holds the correct index/value
                # submitted_ans_text = next((a['answer_text'] for a in answers_data if a['question_id'] == q.id), None)
                # score = q.points if submitted_ans_text == q.correct_answer_or_criteria else 0
                score = random.uniform(0, q.points) # Random for now
            else:
                # Placeholder for Gemini: Random score
                score = random.uniform(0, q.points * 0.9) # Simulate AI not always giving full marks
        else:
            # No answer submitted for this question
            score = 0

        # Round score to reasonable precision
        evaluated_mark = round(score, 2)
        total_score += evaluated_mark

        result = Result(
            submission_id=submission.id,
            question_id=q.id,
            evaluated_mark=evaluated_mark,
            evaluation_feedback="Placeholder evaluation." if q.id in submitted_q_ids else "No answer submitted.",
            evaluated_at=evaluation_time
        )
        db.session.add(result)

    # Update submission status and total score
    submission.status = SubmissionStatus.EVALUATED
    submission.total_score = round(total_score, 2)
    db.session.add(submission) # Add again to update status/score

    # --- End Placeholder Evaluation ---

    try:
        db.session.commit()
        return jsonify(message="Exam submitted and evaluated successfully (placeholder).", submission_id=submission.id), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error submitting exam: {e}")
        return jsonify(message="Failed to submit exam due to server error"), 500


# --- Results Viewing ---

@student_bp.route('/results', methods=['GET'])
@student_required
def view_results():
    user_id = get_jwt_identity()

    # Get evaluated submissions for the student
    evaluated_submissions = Submission.query.filter(
        Submission.student_id == user_id,
        Submission.status == SubmissionStatus.EVALUATED
    ).order_by(Submission.submitted_at.desc()).all()

    output = []
    for sub in evaluated_submissions:
        exam = Exam.query.get(sub.exam_id) # Get exam details
        if not exam: continue # Should not happen if DB is consistent

        # Calculate max possible score for the exam
        max_score = sum(eq.question.points for eq in exam.questions)

        output.append({
            'submission_id': sub.id,
            'exam_id': sub.exam_id,
            'exam_title': exam.title,
            'submitted_at': sub.submitted_at.isoformat(),
            'evaluated_at': sub.results.first().evaluated_at.isoformat() if sub.results.first() else None, # Approx eval time
            'score': sub.total_score,
            'max_score': max_score,
            'status': sub.status.value
        })

    return jsonify(results=output), 200


@student_bp.route('/results/<int:submission_id>/details', methods=['GET'])
@student_required
def view_result_details(submission_id):
    user_id = get_jwt_identity()
    submission = Submission.query.get_or_404(submission_id)

    # Verify this submission belongs to the logged-in student
    if submission.student_id != user_id:
        return jsonify(message="Forbidden: You can only view your own results."), 403

    if submission.status != SubmissionStatus.EVALUATED:
         return jsonify(message="Results are not yet available for this submission."), 404

    exam = Exam.query.get_or_404(submission.exam_id)
    results = Result.query.filter_by(submission_id=submission_id).all()
    answers = SubmittedAnswer.query.filter_by(submission_id=submission_id).all()
    answers_map = {ans.question_id: ans for ans in answers} # For easy lookup

    details = []
    for res in results:
        question = res.question
        answer = answers_map.get(res.question_id)
        details.append({
            'question_id': res.question_id,
            'question_text': question.question_text,
            'student_answer': answer.student_answer_text if answer else "[No Answer Submitted]",
            'evaluated_mark': res.evaluated_mark,
            'max_points': question.points,
            'feedback': res.evaluation_feedback
        })

    return jsonify({
        'submission_id': submission.id,
        'exam_id': submission.exam_id,
        'exam_title': exam.title,
        'total_score': submission.total_score,
         'max_score': sum(eq.question.points for eq in exam.questions),
        'details': details
    }), 200