# app/routes/teacher.py
from flask import Blueprint, request, jsonify
# Make sure db is imported correctly based on your project structure
# If using extensions.py: from app.extensions import db
# If db is initialized directly in __init__.py: from app import db
from app.extensions import db
from app.models import Exam, Question, QuestionType, StudentResponse, Evaluation, UserRole
from app.utils.decorators import teacher_required, verified_required
from flask_jwt_extended import jwt_required
from app.utils.helpers import get_current_user_id
from datetime import datetime, timezone, timedelta # Added timezone and timedelta
from sqlalchemy.orm import joinedload # Explicit import for clarity

bp = Blueprint('teacher', __name__)

@bp.route('/dashboard', methods=['GET'])
@jwt_required()
@teacher_required
@verified_required
def dashboard():
    teacher_id = get_current_user_id()
    if not teacher_id:
        return jsonify({"msg": "Invalid authentication token or unable to identify user."}), 401
    try:
        exam_count = Exam.query.filter_by(created_by=teacher_id).count()
        return jsonify({
            "message": "Teacher Dashboard",
            "my_exams_count": exam_count
        }), 200
    except Exception as e:
        print(f"Error fetching teacher dashboard data for teacher {teacher_id}: {e}")
        return jsonify({"msg": "Error fetching dashboard data."}), 500

# --- Exam Management ---

@bp.route('/exams', methods=['POST'])
@jwt_required()
@teacher_required
@verified_required
def create_exam():
    data = request.get_json()
    teacher_id = get_current_user_id()
    if not teacher_id:
        return jsonify({"msg": "Invalid authentication token or unable to identify user."}), 401

    title = data.get('title')
    description = data.get('description')
    scheduled_time_str = data.get('scheduled_time')
    duration = data.get('duration') # In minutes

    if not all([title, scheduled_time_str, duration]):
        return jsonify({"msg": "Missing required fields: title, scheduled_time, duration"}), 400

    try:
        if isinstance(scheduled_time_str, str):
            if scheduled_time_str.endswith('Z'):
                 scheduled_time_str = scheduled_time_str[:-1] + '+00:00'
            scheduled_time = datetime.fromisoformat(scheduled_time_str)
            if scheduled_time.tzinfo is None:
                scheduled_time = scheduled_time.replace(tzinfo=timezone.utc)
        else:
            raise ValueError("scheduled_time must be a string.")

        duration = int(duration)
        if duration <= 0:
            raise ValueError("Duration must be positive")
    except (ValueError, TypeError) as e:
        return jsonify({"msg": f"Invalid data format for scheduled_time (ISO format) or duration (positive integer): {e}"}), 400

    new_exam = Exam(
        title=title,
        description=description,
        scheduled_time=scheduled_time,
        duration=duration,
        created_by=teacher_id
    )
    try:
        db.session.add(new_exam)
        db.session.commit()
        return jsonify({
            "msg": "Exam created successfully",
            "exam_id": new_exam.id,
            "title": new_exam.title
            }), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error creating exam for teacher {teacher_id}: {e}")
        return jsonify({"msg": "Failed to create exam due to server error."}), 500


@bp.route('/exams', methods=['GET'])
@jwt_required()
@teacher_required
@verified_required
def get_my_exams():
    teacher_id = get_current_user_id()
    if not teacher_id:
        return jsonify({"msg": "Invalid authentication token or unable to identify user."}), 401
    try:
        exams = Exam.query.filter_by(created_by=teacher_id).order_by(Exam.scheduled_time.desc()).all()
        exams_data = [{
            "id": e.id,
            "title": e.title,
            "description": e.description,
            "scheduled_time": e.scheduled_time.isoformat() if e.scheduled_time else None,
            "duration": e.duration,
            "created_at": e.created_at.isoformat() if e.created_at else None
        } for e in exams]
        return jsonify(exams_data), 200
    except Exception as e:
        print(f"Error fetching exams for teacher {teacher_id}: {e}")
        return jsonify({"msg": "Error fetching exams."}), 500


@bp.route('/exams/<int:exam_id>', methods=['GET'])
@jwt_required()
@teacher_required
@verified_required
def get_exam_details(exam_id):
    teacher_id = get_current_user_id()
    if not teacher_id:
        return jsonify({"msg": "Invalid authentication token or unable to identify user."}), 401
    try:
        exam = Exam.query.filter_by(id=exam_id, created_by=teacher_id).first_or_404("Exam not found or access denied")
        exam_data = {
            "id": exam.id,
            "title": exam.title,
            "description": exam.description,
            "scheduled_time": exam.scheduled_time.isoformat() if exam.scheduled_time else None,
            "duration": exam.duration
        }
        return jsonify(exam_data), 200
    except Exception as e:
        if hasattr(e, 'code') and e.code == 404:
             return jsonify({"msg": "Exam not found or access denied"}), 404
        print(f"Error fetching details for exam {exam_id}, teacher {teacher_id}: {e}")
        return jsonify({"msg": "Error fetching exam details."}), 500


@bp.route('/exams/<int:exam_id>', methods=['PUT'])
@jwt_required()
@teacher_required
@verified_required
def update_exam(exam_id):
    teacher_id = get_current_user_id()
    if not teacher_id:
        return jsonify({"msg": "Invalid authentication token or unable to identify user."}), 401

    exam = Exam.query.filter_by(id=exam_id, created_by=teacher_id).first_or_404("Exam not found or access denied")
    data = request.get_json()
    updated = False

    if 'title' in data:
        exam.title = data['title']
        updated = True
    if 'description' in data:
        exam.description = data['description']
        updated = True
    if 'scheduled_time' in data:
        try:
            scheduled_time_str = data['scheduled_time']
            if isinstance(scheduled_time_str, str):
                if scheduled_time_str.endswith('Z'):
                    scheduled_time_str = scheduled_time_str[:-1] + '+00:00'
                scheduled_time = datetime.fromisoformat(scheduled_time_str)
                if scheduled_time.tzinfo is None:
                    scheduled_time = scheduled_time.replace(tzinfo=timezone.utc)
                exam.scheduled_time = scheduled_time
                updated = True
            else:
                 raise ValueError("scheduled_time must be a string.")
        except (ValueError, TypeError) as e:
            return jsonify({"msg": f"Invalid scheduled_time format (ISO format expected): {e}"}), 400
    if 'duration' in data:
        try:
             duration = int(data['duration'])
             if duration <= 0:
                 raise ValueError("Duration must be positive")
             exam.duration = duration
             updated = True
        except (ValueError, TypeError) as e:
            return jsonify({"msg": f"Invalid duration (must be positive integer): {e}"}), 400

    if not updated:
        return jsonify({"msg": "No valid fields provided for update."}), 400

    try:
        db.session.commit()
        return jsonify({"msg": "Exam updated successfully"}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error updating exam {exam_id} for teacher {teacher_id}: {e}")
        return jsonify({"msg": "Failed to update exam due to server error."}), 500


@bp.route('/exams/<int:exam_id>', methods=['DELETE'])
@jwt_required()
@teacher_required
@verified_required
def delete_exam(exam_id):
    teacher_id = get_current_user_id()
    if not teacher_id:
        return jsonify({"msg": "Invalid authentication token or unable to identify user."}), 401

    exam = Exam.query.filter_by(id=exam_id, created_by=teacher_id).first_or_404("Exam not found or access denied")

    try:
        db.session.delete(exam)
        db.session.commit()
        return jsonify({"msg": "Exam and associated data deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting exam {exam_id} for teacher {teacher_id}: {e}")
        return jsonify({"msg": "Failed to delete exam due to server error."}), 500


# --- Question Management ---

@bp.route('/exams/<int:exam_id>/questions', methods=['POST'])
@jwt_required()
@teacher_required
@verified_required
def add_question(exam_id):
    teacher_id = get_current_user_id()
    if not teacher_id:
        return jsonify({"msg": "Invalid authentication token or unable to identify user."}), 401
    exam = Exam.query.filter_by(id=exam_id, created_by=teacher_id).first_or_404("Exam not found or access denied")

    data = request.get_json()
    q_text = data.get('question_text')
    q_type_str = data.get('question_type')
    marks = data.get('marks')
    options = data.get('options')
    correct_answer = data.get('correct_answer')
    word_limit = data.get('word_limit')

    if not q_text or not q_type_str or marks is None:
        return jsonify({"msg": "Missing required fields: question_text, question_type, marks"}), 400

    try:
        q_type_enum_key = q_type_str.upper().replace(" ", "_")
        q_type = QuestionType[q_type_enum_key]
    except KeyError:
         valid_types = [qt.value for qt in QuestionType]
         return jsonify({"msg": f"Invalid question type '{q_type_str}'. Must be one of {valid_types}"}), 400

    try:
        marks = int(marks)
        if marks <= 0: raise ValueError("Marks must be positive")
    except (ValueError, TypeError) as e:
        return jsonify({"msg": f"Invalid marks: {e}"}), 400

    if q_type == QuestionType.MCQ:
        if not options or not isinstance(options, dict) or not options:
            return jsonify({"msg": "MCQ requires a non-empty 'options' dictionary."}), 400
        if not correct_answer or not isinstance(correct_answer, str) or correct_answer not in options:
             return jsonify({"msg": "MCQ requires a 'correct_answer' string that is one of the keys in the 'options' dictionary."}), 400
        word_limit = None
    else:
        options = None
        correct_answer = None
        try:
             word_limit_val = int(word_limit) if word_limit is not None else None
             if word_limit_val is not None and word_limit_val <= 0:
                 raise ValueError("Word limit must be positive if provided.")
             word_limit = word_limit_val
        except (ValueError, TypeError):
             return jsonify({"msg": "Invalid word limit (must be a positive integer or null/absent)."}), 400

    new_question = Question(
        exam_id=exam_id,
        question_text=q_text,
        question_type=q_type,
        marks=marks,
        options=options,
        correct_answer=correct_answer,
        word_limit=word_limit
    )
    try:
        db.session.add(new_question)
        db.session.commit()
        return jsonify({
            "msg": "Question added successfully",
            "question_id": new_question.id
            }), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error adding question to exam {exam_id} for teacher {teacher_id}: {e}")
        return jsonify({"msg": "Failed to add question due to server error."}), 500


@bp.route('/exams/<int:exam_id>/questions', methods=['GET'])
@jwt_required()
@teacher_required
@verified_required
def get_exam_questions(exam_id):
    teacher_id = get_current_user_id()
    if not teacher_id:
        return jsonify({"msg": "Invalid authentication token or unable to identify user."}), 401

    try:
        exam = Exam.query.filter_by(id=exam_id, created_by=teacher_id).first_or_404("Exam not found or access denied")
        questions = Question.query.filter_by(exam_id=exam_id).order_by(Question.id).all()

        questions_data = [{
            "id": q.id,
            "question_text": q.question_text,
            "question_type": q.question_type.value,
            "marks": q.marks,
            "options": q.options,
            "correct_answer": q.correct_answer,
            "word_limit": q.word_limit
        } for q in questions]

        return jsonify(questions_data), 200
    except Exception as e:
         if hasattr(e, 'code') and e.code == 404:
             return jsonify({"msg": "Exam not found or access denied"}), 404
         print(f"Error fetching questions for exam {exam_id}, teacher {teacher_id}: {e}")
         return jsonify({"msg": "Error fetching exam questions."}), 500


@bp.route('/exams/<int:exam_id>/questions/<int:question_id>', methods=['PUT'])
@jwt_required()
@teacher_required
@verified_required
def update_question(exam_id, question_id):
    teacher_id = get_current_user_id()
    if not teacher_id:
        return jsonify({"msg": "Invalid authentication token or unable to identify user."}), 401

    question = db.session.query(Question).join(Exam).filter(
        Question.id == question_id,
        Question.exam_id == exam_id,
        Exam.created_by == teacher_id
    ).first_or_404("Question not found or access denied")

    data = request.get_json()
    updated = False
    original_q_type = question.question_type

    if 'question_text' in data:
        if data['question_text'] != question.question_text:
            question.question_text = data['question_text']
            updated = True
    if 'marks' in data:
        try:
            marks = int(data['marks'])
            if marks <= 0: raise ValueError("Marks must be positive")
            if marks != question.marks:
                question.marks = marks
                updated = True
        except (ValueError, TypeError) as e:
            return jsonify({"msg": f"Invalid marks: {e}"}), 400

    new_q_type = question.question_type
    if 'question_type' in data:
        try:
            q_type_str = data['question_type']
            q_type_enum_key = q_type_str.upper().replace(" ", "_")
            new_q_type = QuestionType[q_type_enum_key]
            if new_q_type != question.question_type:
                 question.question_type = new_q_type
                 updated = True
        except KeyError:
            valid_types = [qt.value for qt in QuestionType]
            return jsonify({"msg": f"Invalid question type '{data['question_type']}'. Must be one of {valid_types}"}), 400

    if new_q_type == QuestionType.MCQ:
        options_updated = False
        if 'options' in data:
             options = data['options']
             if not options or not isinstance(options, dict) or not options:
                 return jsonify({"msg": "MCQ requires a non-empty 'options' dictionary."}), 400
             if options != question.options:
                 question.options = options
                 options_updated = True
                 updated = True

        if 'correct_answer' in data:
             correct_answer = data['correct_answer']
             current_options = question.options
             if not correct_answer or not isinstance(correct_answer, str) or correct_answer not in current_options:
                  return jsonify({"msg": f"MCQ 'correct_answer' ({correct_answer}) must be one of the keys in 'options' ({list(current_options.keys())})."}), 400
             if correct_answer != question.correct_answer:
                 question.correct_answer = correct_answer
                 updated = True
        elif options_updated:
             if question.correct_answer not in question.options:
                 return jsonify({"msg": f"Options updated, but existing correct answer '{question.correct_answer}' is no longer a valid option key. Please provide a new correct_answer."}), 400

        if question.word_limit is not None:
            question.word_limit = None
            if original_q_type != QuestionType.MCQ: updated = True
    else:
        if 'word_limit' in data:
             try:
                 word_limit = data['word_limit']
                 word_limit_val = int(word_limit) if word_limit is not None else None
                 if word_limit_val is not None and word_limit_val <= 0:
                     raise ValueError("Word limit must be positive if provided.")
                 if word_limit_val != question.word_limit:
                     question.word_limit = word_limit_val
                     updated = True
             except (ValueError, TypeError):
                 return jsonify({"msg": "Invalid word limit (must be a positive integer or null/absent)."}), 400
        if question.options is not None:
             question.options = None
             if original_q_type == QuestionType.MCQ: updated = True
        if question.correct_answer is not None:
             question.correct_answer = None
             if original_q_type == QuestionType.MCQ: updated = True

    if not updated:
        return jsonify({"msg": "No changes provided or values are the same."}), 400

    try:
        db.session.commit()
        return jsonify({"msg": "Question updated successfully"}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error updating question {question_id} in exam {exam_id} for teacher {teacher_id}: {e}")
        return jsonify({"msg": "Failed to update question due to server error."}), 500


@bp.route('/exams/<int:exam_id>/questions/<int:question_id>', methods=['DELETE'])
@jwt_required()
@teacher_required
@verified_required
def delete_question(exam_id, question_id):
    teacher_id = get_current_user_id()
    if not teacher_id:
        return jsonify({"msg": "Invalid authentication token or unable to identify user."}), 401

    question = db.session.query(Question).join(Exam).filter(
        Question.id == question_id,
        Question.exam_id == exam_id,
        Exam.created_by == teacher_id
    ).first_or_404("Question not found or access denied")

    try:
        db.session.delete(question)
        db.session.commit()
        return jsonify({"msg": "Question deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting question {question_id} from exam {exam_id} for teacher {teacher_id}: {e}")
        return jsonify({"msg": "Failed to delete question due to server error."}), 500


# --- View Results ---

@bp.route('/exams/results/<int:exam_id>', methods=['GET'])
@jwt_required()
@teacher_required
@verified_required
def get_exam_results(exam_id):
    teacher_id = get_current_user_id()
    if not teacher_id:
        return jsonify({"msg": "Invalid authentication token or unable to identify user."}), 401

    try:
        # Verify exam belongs to the teacher and eager load its questions
        exam = Exam.query.filter_by(id=exam_id, created_by=teacher_id)\
                         .options(joinedload(Exam.questions))\
                         .first_or_404("Exam not found or access denied")

        # Eager load related data for responses
        responses = StudentResponse.query.filter_by(exam_id=exam_id)\
                                        .options(
                                            joinedload(StudentResponse.student),
                                            joinedload(StudentResponse.question),
                                            joinedload(StudentResponse.evaluation)
                                        )\
                                        .join(Question)\
                                        .order_by(StudentResponse.student_id, Question.id)\
                                        .all()

        # --- Start of correctly indented block ---
        results_by_student = {}
        # Use the eager-loaded questions from the exam object
        total_possible_marks_exam = sum(q.marks for q in exam.questions if q.marks)

        for resp in responses:
            # --- Start of loop body (indented one level) ---
            student = resp.student
            if not student: continue

            student_id = student.id
            student_name = student.name

            if student_id not in results_by_student:
                results_by_student[student_id] = {
                    "student_id": student_id,
                    "student_name": student_name,
                    "total_marks_awarded": 0.0,
                    "total_marks_possible": total_possible_marks_exam,
                    "submission_status": "Submitted",
                    "details": []
                }

            evaluation = resp.evaluation
            marks_awarded = evaluation.marks_awarded if evaluation and evaluation.marks_awarded is not None else None
            feedback = evaluation.feedback if evaluation else "Not Evaluated Yet"
            evaluated_at = evaluation.evaluated_at.isoformat() if evaluation and evaluation.evaluated_at else None
            evaluated_by = evaluation.evaluated_by if evaluation else None

            question = resp.question
            if not question: continue

            question_text = question.question_text
            marks_possible = question.marks

            if marks_awarded is not None:
                 results_by_student[student_id]['total_marks_awarded'] += float(marks_awarded)

            results_by_student[student_id]['details'].append({
                "response_id": resp.id,
                "question_id": question.id,
                "question_text": question_text,
                "response_text": resp.response_text,
                "submitted_at": resp.submitted_at.isoformat() if resp.submitted_at else None,
                "marks_possible": marks_possible,
                "marks_awarded": marks_awarded,
                "feedback": feedback,
                "evaluated_at": evaluated_at,
                "evaluated_by": evaluated_by
            })
            # --- End of loop body ---

        # This return is outside the loop, but inside the try block
        return jsonify(list(results_by_student.values())), 200
        # --- End of correctly indented block ---

    # Except block aligns with try block
    except Exception as e:
         if hasattr(e, 'code') and e.code == 404:
             return jsonify({"msg": "Exam not found or access denied"}), 404
         print(f"Error fetching results for exam {exam_id}, teacher {teacher_id}: {e}")
         # Optionally add traceback: import traceback; traceback.print_exc()
         return jsonify({"msg": "Error fetching exam results."}), 500