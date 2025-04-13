from flask import Blueprint, request, jsonify
from werkzeug.exceptions import BadRequest, NotFound, Forbidden
from datetime import datetime, timezone
from marshmallow import ValidationError

from ..models import Exam, Question, Option, User, Submission
from ..schemas import (
    ExamSchema, ExamStudentSchema, ExamCreateSchema, ExamUpdateSchema,
    ExamScheduleSchema, QuestionSchema, QuestionCreateSchema, OptionCreateSchema
)
from ..extensions import db
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..utils import teacher_required, student_required, teacher_owns_exam, get_current_user

bp = Blueprint('exams', __name__, url_prefix='/exams')

# --- Schemas ---
exam_schema = ExamSchema()
exams_schema = ExamSchema(many=True)
exam_student_schema = ExamStudentSchema() # For student view
exam_create_schema = ExamCreateSchema()
exam_update_schema = ExamUpdateSchema()
exam_schedule_schema = ExamScheduleSchema()
question_schema = QuestionSchema()
questions_schema = QuestionSchema(many=True)
question_create_schema = QuestionCreateSchema()
option_create_schema = OptionCreateSchema()


# --- Teacher Routes ---

@bp.route('', methods=['POST'])
@jwt_required()
@teacher_required
def create_exam():
    """Teacher: Create a new exam."""
    current_user_id = get_jwt_identity()['id']
    try:
        data = exam_create_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 400

    new_exam = Exam(
        title=data['title'],
        description=data.get('description', ''),
        creator_id=current_user_id,
        status='draft'
    )
    db.session.add(new_exam)
    db.session.commit()
    return exam_schema.jsonify(new_exam), 201

@bp.route('/my-exams', methods=['GET'])
@jwt_required()
@teacher_required
def get_teacher_exams():
    """Teacher: Get all exams created by the current teacher."""
    current_user_id = get_jwt_identity()['id']
    exams = Exam.query.filter_by(creator_id=current_user_id).order_by(Exam.created_at.desc()).all()
    return exams_schema.jsonify(exams)


@bp.route('/<int:exam_id>', methods=['PUT', 'PATCH'])
@jwt_required()
@teacher_owns_exam # Checks ownership and sets request.exam
def update_exam_details(exam_id):
    """Teacher: Update basic exam details (title, description)."""
    exam = request.exam # Get exam from decorator
    try:
        # Allow partial updates with partial=True
        data = exam_update_schema.load(request.get_json(), partial=True)
    except ValidationError as err:
        return jsonify(errors=err.messages), 400

    if 'title' in data:
        exam.title = data['title']
    if 'description' in data:
        exam.description = data['description']

    # Prevent status change here - use scheduling/publishing endpoints
    if 'status' in data:
        raise BadRequest("Cannot update status directly. Use scheduling endpoints.")

    db.session.commit()
    return exam_schema.jsonify(exam)


@bp.route('/<int:exam_id>', methods=['DELETE'])
@jwt_required()
@teacher_owns_exam # Checks ownership
def delete_exam(exam_id):
    """Teacher: Delete an exam."""
    exam = request.exam
    # Add check: cannot delete if submissions exist or if live? Optional.
    # if exam.submissions.count() > 0:
    #    raise Forbidden("Cannot delete exam with existing submissions.")
    db.session.delete(exam)
    db.session.commit()
    return '', 204


@bp.route('/<int:exam_id>/schedule', methods=['POST'])
@jwt_required()
@teacher_owns_exam
def schedule_exam(exam_id):
    """Teacher: Schedule an exam by setting start/end times or duration."""
    exam = request.exam
    try:
        data = exam_schedule_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 400

    # Check if already live or ended? Maybe allow rescheduling?
    # if exam.status not in ['draft', 'scheduled']:
    #     raise BadRequest(f"Exam cannot be scheduled from status '{exam.status}'")

    exam.scheduled_start_time = data['scheduled_start_time']
    exam.scheduled_end_time = data.get('scheduled_end_time')
    exam.duration_minutes = data.get('duration_minutes')
    exam.status = 'scheduled'

    db.session.commit()
    return exam_schema.jsonify(exam)

@bp.route('/<int:exam_id>/publish', methods=['POST'])
@jwt_required()
@teacher_owns_exam
def publish_exam(exam_id):
    """Teacher: Manually set an exam to 'live' (if start time is now or past)."""
    exam = request.exam
    if not exam.scheduled_start_time:
         raise BadRequest("Exam must be scheduled before publishing.")

    now = datetime.now(timezone.utc)
    if exam.scheduled_start_time > now:
         raise BadRequest("Cannot publish an exam scheduled for the future.")
    if exam.scheduled_end_time and now >= exam.scheduled_end_time:
         raise BadRequest("Exam has already ended based on schedule.")

    # Check if it has questions
    if exam.questions.count() == 0:
         raise BadRequest("Cannot publish an exam with no questions.")

    exam.status = 'live'
    db.session.commit()
    return exam_schema.jsonify(exam)


@bp.route('/<int:exam_id>/unpublish', methods=['POST'])
@jwt_required()
@teacher_owns_exam
def unpublish_exam(exam_id):
    """Teacher: Revert a 'scheduled' or 'live' exam back to 'draft' (if no submissions)."""
    exam = request.exam
    if exam.status not in ['scheduled', 'live']:
         raise BadRequest(f"Cannot unpublish exam with status '{exam.status}'.")
    if exam.submissions.count() > 0:
         raise Forbidden("Cannot unpublish exam with existing submissions. Consider archiving instead.")

    exam.status = 'draft'
    exam.scheduled_start_time = None
    exam.scheduled_end_time = None
    exam.duration_minutes = None
    db.session.commit()
    return exam_schema.jsonify(exam)


# --- Routes Accessible by Both (with different views) ---

@bp.route('/<int:exam_id>', methods=['GET'])
@jwt_required()
def get_exam_details(exam_id):
    """Get details of a specific exam. Teacher sees full details, student sees exam-taking view."""
    exam = Exam.query.options(
        db.joinedload(Exam.questions).subqueryload(Question.options) # Eager load questions and options
    ).get(exam_id)

    if not exam:
        raise NotFound("Exam not found")

    identity = get_jwt_identity()
    user_role = identity.get('role')
    user_id = identity.get('id')

    if user_role == 'teacher':
        if exam.creator_id != user_id:
            raise Forbidden("You do not have permission to view this exam.")
        # Teacher sees full schema
        return exam_schema.jsonify(exam)

    elif user_role == 'student':
        # Student sees limited schema, check if available
        now = datetime.now(timezone.utc)
        is_active = False
        if exam.status in ['scheduled', 'live']:
             start_ok = exam.scheduled_start_time and exam.scheduled_start_time <= now
             end_ok = not exam.scheduled_end_time or now < exam.scheduled_end_time
             if start_ok and end_ok:
                 is_active = True

        if not is_active:
             # Check ended status properly
            if exam.status == 'ended' or (exam.scheduled_end_time and now >= exam.scheduled_end_time):
                 raise Forbidden("Exam has ended.")
            else:
                 raise Forbidden("Exam is not currently available.")

        # Check if student already submitted
        existing_submission = Submission.query.filter_by(exam_id=exam_id, student_id=user_id).first()
        if existing_submission:
             raise Forbidden("You have already submitted this exam.") # Or redirect to results

        # Use student-safe schema (hides correct answers)
        return exam_student_schema.jsonify(exam)

    else:
        raise Forbidden("Invalid user role")


# --- Student Routes ---

@bp.route('/available', methods=['GET'])
@jwt_required()
@student_required
def get_available_exams_for_student():
    """Student: Get list of exams currently available to take."""
    user_id = get_jwt_identity()['id']
    now = datetime.now(timezone.utc)

    # Find exams that are 'live' or 'scheduled' and within the time window
    available_exams_query = Exam.query.filter(
        Exam.status.in_(['scheduled', 'live']),
        Exam.scheduled_start_time <= now,
        (Exam.scheduled_end_time == None) | (Exam.scheduled_end_time > now)
    )

    # Filter out exams the student has already submitted
    submitted_exam_ids = db.session.query(Submission.exam_id).filter(Submission.student_id == user_id).subquery()
    available_exams = available_exams_query.filter(Exam.id.notin_(submitted_exam_ids)).order_by(Exam.scheduled_start_time).all()

    # Use a schema that doesn't include questions/answers for the list view
    exam_list_schema = ExamSchema(many=True, exclude=("questions", "creator")) # Example list schema
    return exam_list_schema.jsonify(available_exams)