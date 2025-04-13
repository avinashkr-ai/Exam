from flask import Blueprint, request, jsonify
from werkzeug.exceptions import BadRequest, NotFound, Forbidden, Conflict
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone

from ..models import Exam, Submission, Answer, Question, Option, User
from ..schemas import SubmissionSchema, SubmissionCreateSchema, AnswerSchema
from ..extensions import db
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..utils import student_required, teacher_required, get_current_user, exam_is_live_for_student, teacher_owns_exam

bp = Blueprint('submissions', __name__, url_prefix='/submissions')

# --- Schemas ---
submission_schema = SubmissionSchema()
submissions_schema = SubmissionSchema(many=True)
submission_create_schema = SubmissionCreateSchema()
answer_schema = AnswerSchema(many=True) # For viewing answers of a submission


# --- Student Route ---

# Note: Submission creation is nested under exams route for context
@bp.route('/exam/<int:exam_id>', methods=['POST']) # Changed prefix slightly
@jwt_required()
@exam_is_live_for_student # Checks student role, exam liveness, sets request.exam
def create_submission(exam_id):
    """Student: Submit answers for an exam."""
    exam = request.exam # Get exam from decorator
    student = get_current_user()
    if not student:
        raise Forbidden("Cannot identify student.") # Should not happen if jwt_required passed

    # Double-check if already submitted (although decorator might check, belt and suspenders)
    existing_submission = Submission.query.filter_by(exam_id=exam_id, student_id=student.id).first()
    if existing_submission:
        raise Conflict("You have already submitted answers for this exam.")

    try:
        data = submission_create_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 400

    submitted_at = datetime.now(timezone.utc)

    # Check deadline again just before creating submission
    if exam.scheduled_end_time and submitted_at >= exam.scheduled_end_time:
         raise Forbidden("The deadline for this exam has passed.")

    new_submission = Submission(
        exam_id=exam_id,
        student_id=student.id,
        submitted_at=submitted_at,
        time_started=data.get('time_started'), # Optional start time from client
        time_finished=submitted_at
    )
    db.session.add(new_submission)

    # Process answers
    total_score = 0
    total_possible_points = 0

    # Get all questions for this exam with their correct options eagerly loaded
    questions = Question.query.options(db.joinedload(Question.options)).filter_by(exam_id=exam_id).all()
    questions_dict = {q.id: q for q in questions}

    submitted_question_ids = set()

    for answer_data in data['answers']:
        question_id = answer_data['question_id']
        submitted_question_ids.add(question_id)

        question = questions_dict.get(question_id)
        if not question:
             db.session.rollback() # Important: rollback if any part fails
             raise BadRequest(f"Invalid question_id {question_id} provided in submission.")

        total_possible_points += question.points
        answer_is_correct = None
        points_awarded = 0

        # Create Answer object
        new_answer = Answer(
            # submission relation set below
            question_id=question_id,
            answer_text=answer_data.get('answer_text'),
            selected_option_id=answer_data.get('selected_option_id')
        )

        # Auto-grade simple types (MCQ)
        if question.type == 'multiple_choice' and new_answer.selected_option_id is not None:
            correct_option = next((opt for opt in question.options if opt.is_correct), None)
            if correct_option and new_answer.selected_option_id == correct_option.id:
                answer_is_correct = True
                points_awarded = question.points
            else:
                answer_is_correct = False
                points_awarded = 0
        elif question.type == 'short_answer':
            # Needs manual grading or more complex auto-grading logic
            answer_is_correct = None # Mark as ungraded
            points_awarded = None
        # Add logic for 'multiple_select' if implemented

        new_answer.is_correct = answer_is_correct
        new_answer.points_awarded = points_awarded
        new_submission.answers.append(new_answer) # Add to relationship

        if answer_is_correct:
             total_score += question.points


    # Check if all questions were answered (optional)
    # all_question_ids = set(questions_dict.keys())
    # if submitted_question_ids != all_question_ids:
    #     # Handle partially submitted exams? Or reject?
    #     pass

    # Update submission score (for auto-graded parts)
    new_submission.score = total_score if total_possible_points > 0 else 0 # Handle division by zero if no points

    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        # Could be the unique constraint violation if a race condition occurred
        if "UNIQUE constraint failed" in str(e) or "_exam_student_uc" in str(e):
             raise Conflict("Submission already exists (potential race condition).")
        else:
             raise BadRequest(f"Database error during submission: {str(e)}") # General DB error
    except Exception as e:
        db.session.rollback()
        raise BadRequest(f"An error occurred during submission: {str(e)}") # Catch other errors

    # Return limited info, maybe just the ID or confirmation
    return jsonify({"message": "Submission successful", "submission_id": new_submission.id}), 201


# --- Teacher Routes ---

@bp.route('/exam/<int:exam_id>', methods=['GET'])
@jwt_required()
@teacher_owns_exam # Checks teacher owns the exam
def get_submissions_for_exam(exam_id):
    """Teacher: Get all submissions for a specific exam they own."""
    exam = request.exam
    # Eager load student info for efficiency
    submissions = Submission.query.options(
            db.joinedload(Submission.student)
        ).filter_by(exam_id=exam_id).order_by(Submission.submitted_at.desc()).all()
    return submissions_schema.jsonify(submissions)


@bp.route('/<int:submission_id>', methods=['GET'])
@jwt_required()
def get_submission_details(submission_id):
    """Get details of a specific submission. Accessible by teacher owner or the student submitter."""
    submission = Submission.query.options(
        db.joinedload(Submission.student), # Load student info
        db.joinedload(Submission.exam).joinedload(Exam.creator), # Load exam and its creator
        db.joinedload(Submission.answers).joinedload(Answer.question).joinedload(Question.options) # Load answers->question->options
        ).get(submission_id)

    if not submission:
        raise NotFound("Submission not found.")

    identity = get_jwt_identity()
    user_id = identity['id']
    user_role = identity['role']

    # Check permissions
    is_teacher_owner = user_role == 'teacher' and submission.exam.creator_id == user_id
    is_student_submitter = user_role == 'student' and submission.student_id == user_id

    if not is_teacher_owner and not is_student_submitter:
        raise Forbidden("You do not have permission to view this submission.")

    return submission_schema.jsonify(submission)


# Optional: Endpoint for teacher to manually grade/update score
@bp.route('/<int:submission_id>/grade', methods=['PATCH'])
@jwt_required()
@teacher_required # Ensure user is a teacher
def grade_submission(submission_id):
    """Teacher: Manually update grades for answers and the total score."""
    submission = Submission.query.options(
         db.joinedload(Submission.exam) # Need exam to check ownership
        ).get(submission_id)
    if not submission:
        raise NotFound("Submission not found.")

    # Verify teacher owns the parent exam
    identity = get_jwt_identity()
    if submission.exam.creator_id != identity['id']:
         raise Forbidden("You do not own the exam for this submission.")

    data = request.get_json()
    if not data or 'answers' not in data:
         raise BadRequest("Missing 'answers' data for grading.")

    # Map answer IDs to their grade data
    grades_data = {item['answer_id']: item for item in data['answers']}
    updated_total_score = 0
    has_manual_grades = False

    # Fetch answers for this submission
    answers = Answer.query.options(db.joinedload(Answer.question)).filter_by(submission_id=submission_id).all()

    for answer in answers:
        if answer.id in grades_data:
            grade_info = grades_data[answer.id]
            points = grade_info.get('points_awarded')
            is_correct = grade_info.get('is_correct') # Optional override

            if points is not None:
                 # Validate points against question max points
                if points > answer.question.points or points < 0:
                    db.session.rollback()
                    raise BadRequest(f"Points awarded ({points}) for answer {answer.id} exceed question max ({answer.question.points}) or are negative.")
                answer.points_awarded = points
                updated_total_score += points
                has_manual_grades = True # Mark that manual grading occurred

            if is_correct is not None and isinstance(is_correct, bool):
                 answer.is_correct = is_correct

            db.session.add(answer) # Mark answer as dirty

    if has_manual_grades:
         submission.score = updated_total_score
         db.session.add(submission) # Mark submission as dirty

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise BadRequest(f"Error updating grades: {str(e)}")

    # Return the updated submission
    updated_submission = Submission.query.get(submission_id)
    return submission_schema.jsonify(updated_submission)

# --- Student Routes ---

@bp.route('/my-submissions', methods=['GET'])
@jwt_required()
@student_required
def get_my_submissions():
    """Student: Get all submissions made by the current student."""
    student_id = get_jwt_identity()['id']
    submissions = Submission.query.options(
         db.joinedload(Submission.exam) # Load basic exam info
        ).filter_by(student_id=student_id).order_by(Submission.submitted_at.desc()).all()

    # Use schema that excludes answers maybe? Or includes basic score.
    list_schema = SubmissionSchema(many=True, exclude=("answers",))
    return list_schema.jsonify(submissions)