from flask import Blueprint, request, jsonify
from werkzeug.exceptions import BadRequest, NotFound, Forbidden
from marshmallow import ValidationError

from ..models import Exam, Question, Option
from ..schemas import QuestionSchema, QuestionCreateSchema, OptionCreateSchema
from ..extensions import db
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..utils import teacher_required, teacher_owns_exam

# Note: These routes are nested under /exams/<exam_id>/questions
bp = Blueprint('questions', __name__, url_prefix='/exams/<int:exam_id>/questions')

# --- Schemas ---
question_schema = QuestionSchema()
questions_schema = QuestionSchema(many=True)
question_create_schema = QuestionCreateSchema()
# Use QuestionCreateSchema for updates too, perhaps with partial=True

@bp.route('', methods=['POST'])
@jwt_required()
@teacher_owns_exam # Ensures teacher owns the parent exam, sets request.exam
def add_question_to_exam(exam_id):
    """Teacher: Add a new question to an exam."""
    exam = request.exam
    try:
        data = question_create_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 400

    # Check exam status - prevent adding questions to live/ended exams?
    if exam.status not in ['draft']:
        raise Forbidden(f"Cannot add questions to an exam with status '{exam.status}'.")

    new_question = Question(
        exam_id=exam_id,
        text=data['text'],
        type=data['type'],
        points=data.get('points', 1),
        order=data.get('order', 0) # Or calculate next order number
    )

    # Handle options if present (MCQ/MS)
    if data['type'] in ['multiple_choice', 'multiple_select'] and 'options' in data:
        for option_data in data['options']:
            new_option = Option(
                text=option_data['text'],
                is_correct=option_data['is_correct']
                # question relation set below
            )
            new_question.options.append(new_option) # Add to relationship

    db.session.add(new_question)
    db.session.commit()

    return question_schema.jsonify(new_question), 201

@bp.route('/<int:question_id>', methods=['PUT', 'PATCH'])
@jwt_required()
@teacher_owns_exam # Checks ownership of the parent exam
def update_question(exam_id, question_id):
    """Teacher: Update an existing question."""
    exam = request.exam
    question = Question.query.filter_by(id=question_id, exam_id=exam_id).first()
    if not question:
        raise NotFound("Question not found for this exam.")

    # Check exam status
    if exam.status not in ['draft']:
        raise Forbidden(f"Cannot modify questions for an exam with status '{exam.status}'.")

    try:
        # Use same schema, allow partial updates
        data = question_create_schema.load(request.get_json(), partial=True)
    except ValidationError as err:
        return jsonify(errors=err.messages), 400

    # Update question fields
    if 'text' in data: question.text = data['text']
    if 'type' in data: question.type = data['type'] # Be careful changing type - handle options
    if 'points' in data: question.points = data['points']
    if 'order' in data: question.order = data['order']

    # Handle options update (more complex: delete existing, add new?)
    if 'options' in data:
        # Simple approach: Delete existing options and add new ones
        Option.query.filter_by(question_id=question_id).delete()
        if question.type in ['multiple_choice', 'multiple_select']:
            for option_data in data['options']:
                new_option = Option(
                    question_id=question_id, # Explicitly set FK
                    text=option_data['text'],
                    is_correct=option_data['is_correct']
                )
                db.session.add(new_option)
        # Re-validate option constraints after potential type change
        try:
            question_create_schema.validate(question_schema.dump(question), session=db.session)
        except ValidationError as err:
             db.session.rollback() # Rollback changes if validation fails after update
             return jsonify(errors=err.messages), 400


    db.session.commit()
    # Query again to get updated options in the response
    updated_question = Question.query.get(question_id)
    return question_schema.jsonify(updated_question)


@bp.route('/<int:question_id>', methods=['DELETE'])
@jwt_required()
@teacher_owns_exam # Checks ownership of the parent exam
def delete_question(exam_id, question_id):
    """Teacher: Delete a question from an exam."""
    exam = request.exam
    question = Question.query.filter_by(id=question_id, exam_id=exam_id).first()
    if not question:
        raise NotFound("Question not found for this exam.")

     # Check exam status
    if exam.status not in ['draft']:
        raise Forbidden(f"Cannot delete questions from an exam with status '{exam.status}'.")

    db.session.delete(question) # Cascade should handle options
    db.session.commit()
    return '', 204

@bp.route('', methods=['GET'])
@jwt_required()
@teacher_owns_exam # Checks ownership of the parent exam
def get_exam_questions(exam_id):
    """Teacher: Get all questions for a specific exam."""
    exam = request.exam
    # Questions might already be loaded if using joinedload in the decorator or parent route
    # questions = Question.query.filter_by(exam_id=exam_id).order_by(Question.order).all()
    questions = exam.questions.order_by(Question.order).all()
    return questions_schema.jsonify(questions)