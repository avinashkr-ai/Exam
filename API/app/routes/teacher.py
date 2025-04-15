# app/routes/teacher.py
from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models import Exam, Question, QuestionType, StudentResponse, Evaluation, UserRole
from app.utils.decorators import teacher_required, verified_required
from flask_jwt_extended import jwt_required
from app.utils.helpers import get_current_user_id, ensure_aware_utc  # Added ensure_aware_utc
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import joinedload, Session

bp = Blueprint('teacher', __name__)

# --- Dashboard and Exam Management ---

@bp.route('/dashboard', methods=['GET'])
@jwt_required()
@teacher_required
@verified_required
def dashboard():
    teacher_id = get_current_user_id()
    if not teacher_id:
        return jsonify({"msg": "Invalid authentication token"}), 401
    try:
        exam_count = Exam.query.filter_by(created_by=teacher_id).count()
        return jsonify({"message": "Teacher Dashboard", "my_exams_count": exam_count}), 200
    except Exception as e:
        print(f"Error teacher dashboard: {e}")
        return jsonify({"msg": "Error fetching data."}), 500

@bp.route('/exams', methods=['POST'])
@jwt_required()
@teacher_required
@verified_required
def create_exam():
    data = request.get_json()
    teacher_id = get_current_user_id()
    if not teacher_id:
        return jsonify({"msg": "Invalid authentication token"}), 401

    title = data.get('title')
    description = data.get('description')
    scheduled_time_str = data.get('scheduled_time')
    duration = data.get('duration')

    if not all([title, scheduled_time_str, duration]):
        return jsonify({"msg": "Missing fields"}), 400

    try:
        if isinstance(scheduled_time_str, str):
            if scheduled_time_str.endswith('Z'):
                scheduled_time_str = scheduled_time_str[:-1] + '+00:00'
            scheduled_time = datetime.fromisoformat(scheduled_time_str)
            if scheduled_time.tzinfo is None:
                scheduled_time = scheduled_time.replace(tzinfo=timezone.utc)
        else:
            raise ValueError("scheduled_time must be string")

        duration = int(duration)
        assert duration > 0
    except (ValueError, TypeError, AssertionError) as e:
        return jsonify({"msg": f"Invalid format: {e}"}), 400

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
            "msg": "Exam created",
            "exam": {
                "id": new_exam.id,
                "title": new_exam.title,
                "scheduled_time": ensure_aware_utc(new_exam.scheduled_time).isoformat() if new_exam.scheduled_time else None,
                "created_at": ensure_aware_utc(new_exam.created_at).isoformat() if new_exam.created_at else None
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error create exam: {e}")
        return jsonify({"msg": "Create failed"}), 500

@bp.route('/exams', methods=['GET'])
@jwt_required()
@teacher_required
@verified_required
def get_my_exams():
    teacher_id = get_current_user_id()
    if not teacher_id:
        return jsonify({"msg": "Invalid authentication token"}), 401
    try:
        exams = Exam.query.filter_by(created_by=teacher_id).order_by(Exam.scheduled_time.desc()).all()
        exams_data = [{
            "id": e.id,
            "title": e.title,
            "description": e.description,
            "scheduled_time": ensure_aware_utc(e.scheduled_time).isoformat() if e.scheduled_time else None,
            "duration": e.duration,
            "created_at": ensure_aware_utc(e.created_at).isoformat() if e.created_at else None
        } for e in exams]
        return jsonify(exams_data), 200
    except Exception as e:
        print(f"Error fetching exams: {e}")
        return jsonify({"msg": "Error fetching exams."}), 500

@bp.route('/exams/<int:exam_id>', methods=['GET'])
@jwt_required()
@teacher_required
@verified_required
def get_exam_details(exam_id):
    teacher_id = get_current_user_id()
    if not teacher_id:
        return jsonify({"msg": "Invalid authentication token"}), 401
    try:
        exam = Exam.query.filter_by(id=exam_id, created_by=teacher_id).first_or_404("Exam not found or access denied")
        exam_data = {
            "id": exam.id,
            "title": exam.title,
            "description": exam.description,
            "scheduled_time": ensure_aware_utc(exam.scheduled_time).isoformat() if exam.scheduled_time else None,
            "duration": exam.duration,
            "created_at": ensure_aware_utc(exam.created_at).isoformat() if exam.created_at else None
        }
        return jsonify(exam_data), 200
    except Exception as e:
        if hasattr(e, 'code') and e.code == 404:
            return jsonify({"msg": "Exam not found or access denied"}), 404
        print(f"Error fetching exam details: {e}")
        return jsonify({"msg": "Error fetching exam details."}), 500

@bp.route('/exams/<int:exam_id>', methods=['PUT'])
@jwt_required()
@teacher_required
@verified_required
def update_exam(exam_id):
    teacher_id = get_current_user_id()
    data = request.get_json()
    updated = False

    if not teacher_id:
        return jsonify({"msg": "Invalid authentication token"}), 401

    exam = Exam.query.filter_by(id=exam_id, created_by=teacher_id).first_or_404("Exam not found or access denied")

    if 'title' in data:
        exam.title = data['title']
        updated = True
    if 'description' in data:
        exam.description = data['description']
        updated = True
    if 'scheduled_time' in data:
        try:
            stime_str = data['scheduled_time']
            if isinstance(stime_str, str):
                if stime_str.endswith('Z'):
                    stime_str = stime_str[:-1] + '+00:00'
                stime = datetime.fromisoformat(stime_str)
                if stime.tzinfo is None:
                    stime = stime.replace(tzinfo=timezone.utc)
                exam.scheduled_time = stime
                updated = True
            else:
                raise ValueError("scheduled_time must be string")
        except (ValueError, TypeError) as e:
            return jsonify({"msg": f"Invalid scheduled_time: {e}"}), 400
    if 'duration' in data:
        try:
            dur = int(data['duration'])
            assert dur > 0
            exam.duration = dur
            updated = True
        except (ValueError, TypeError, AssertionError):
            return jsonify({"msg": "Invalid duration"}), 400

    if not updated:
        return jsonify({"msg": "No fields provided"}), 400

    try:
        db.session.commit()
        return jsonify({
            "msg": "Exam updated",
            "exam": {
                "id": exam.id,
                "title": exam.title,
                "description": exam.description,
                "scheduled_time": ensure_aware_utc(exam.scheduled_time).isoformat() if exam.scheduled_time else None,
                "duration": exam.duration,
                "created_at": ensure_aware_utc(exam.created_at).isoformat() if exam.created_at else None
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error update exam: {e}")
        return jsonify({"msg": "Update failed"}), 500

@bp.route('/exams/<int:exam_id>', methods=['DELETE'])
@jwt_required()
@teacher_required
@verified_required
def delete_exam(exam_id):
    teacher_id = get_current_user_id()
    if not teacher_id:
        return jsonify({"msg": "Invalid authentication token"}), 401

    exam = Exam.query.filter_by(id=exam_id, created_by=teacher_id).first_or_404("Exam not found or access denied")

    try:
        db.session.delete(exam)
        db.session.commit()
        return jsonify({"msg": "Exam deleted"}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting exam: {e}")
        return jsonify({"msg": "Delete failed"}), 500

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
        q_type_enum = next((qt for qt in QuestionType if qt.value == q_type_str), None)
        if q_type_enum is None:
            raise ValueError("Invalid question type specified.")
    except ValueError as e:
        valid_types = [qt.value for qt in QuestionType]
        return jsonify({"msg": f"Invalid question type '{q_type_str}'. Must be one of {valid_types}"}), 400

    try:
        marks = int(marks)
        if marks <= 0: raise ValueError("Marks must be positive")
    except (ValueError, TypeError) as e:
        return jsonify({"msg": f"Invalid marks: {e}"}), 400

    validated_options = None
    validated_correct_answer = None
    validated_word_limit = None

    if q_type_enum == QuestionType.MCQ:
        if not options or not isinstance(options, dict) or not options:
            return jsonify({"msg": "MCQ requires a non-empty 'options' dictionary."}), 400
        if not correct_answer or not isinstance(correct_answer, str):
            return jsonify({"msg": "MCQ requires a 'correct_answer' string."}), 400
        if correct_answer not in options:
            return jsonify({"msg": f"MCQ 'correct_answer' ('{correct_answer}') must be one of the keys provided in 'options'."}), 400

        validated_options = options
        validated_correct_answer = correct_answer

    elif q_type_enum in [QuestionType.SHORT_ANSWER, QuestionType.LONG_ANSWER]:
        if word_limit is not None:
            try:
                word_limit_val = int(word_limit)
                if word_limit_val <= 0:
                    raise ValueError("Word limit must be positive if provided.")
                validated_word_limit = word_limit_val
            except (ValueError, TypeError):
                return jsonify({"msg": "Invalid word_limit (must be a positive integer or null/absent)."}), 400
        else:
            validated_word_limit = None

    else:
        return jsonify({"msg": "Unhandled question type during validation."}), 500

    new_question = Question(
        exam_id=exam_id,
        question_text=q_text,
        question_type=q_type_enum,
        marks=marks,
        options=validated_options,
        correct_answer=validated_correct_answer,
        word_limit=validated_word_limit
    )

    try:
        db.session.add(new_question)
        db.session.commit()
        return jsonify({
            "msg": "Question added successfully",
            "question": {
                "id": new_question.id,
                "question_text": new_question.question_text,
                "question_type": new_question.question_type.value,
                "marks": new_question.marks,
                "options": new_question.options,
                "correct_answer": new_question.correct_answer,
                "word_limit": new_question.word_limit
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error saving question to exam {exam_id}: {e}")
        return jsonify({"msg": "Failed to save question due to server error."}), 500

@bp.route('/exams/<int:exam_id>/questions', methods=['GET'])
@jwt_required()
@teacher_required
@verified_required
def get_exam_questions(exam_id):
    teacher_id = get_current_user_id()
    if not teacher_id:
        return jsonify({"msg": "Invalid authentication token"}), 401
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
        print(f"Error fetching questions: {e}")
        return jsonify({"msg": "Error fetching questions."}), 500

@bp.route('/exams/<int:exam_id>/questions/<int:question_id>', methods=['GET'])
@jwt_required()
@teacher_required
@verified_required
def get_single_question(exam_id, question_id):
    teacher_id = get_current_user_id()
    if not teacher_id:
        return jsonify({"msg": "Invalid authentication token"}), 401

    try:
        question = db.session.query(Question).join(Exam).filter(
            Question.id == question_id,
            Question.exam_id == exam_id,
            Exam.created_by == teacher_id
        ).first_or_404("Question not found or access denied")

        question_data = {
            "id": question.id,
            "question_text": question.question_text,
            "question_type": question.question_type.value,
            "marks": question.marks,
            "options": question.options,
            "correct_answer": question.correct_answer,
            "word_limit": question.word_limit
        }
        return jsonify(question_data), 200

    except Exception as e:
        if hasattr(e, 'code') and e.code == 404:
            return jsonify({"msg": "Question not found or access denied"}), 404
        print(f"Error fetching single question {question_id} for exam {exam_id}: {e}")
        return jsonify({"msg": "Error fetching question details."}), 500

@bp.route('/exams/<int:exam_id>/questions/<int:question_id>', methods=['PUT'])
@jwt_required()
@teacher_required
@verified_required
def update_question(exam_id, question_id):
    teacher_id = get_current_user_id()
    if not teacher_id:
        return jsonify({"msg": "Invalid authentication token"}), 401

    question = db.session.query(Question).join(Exam).filter(
        Question.id == question_id,
        Question.exam_id == exam_id,
        Exam.created_by == teacher_id
    ).first_or_404("Question not found or access denied")

    data = request.get_json()
    updated = False
    original_q_type = question.question_type

    if 'question_text' in data and data['question_text'] != question.question_text:
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

    final_q_type_enum = question.question_type
    if 'question_type' in data:
        q_type_str = data['question_type']
        try:
            matched_q_type = next((qt for qt in QuestionType if qt.value == q_type_str), None)
            if matched_q_type is None: raise ValueError("Invalid question type provided.")
            if matched_q_type != question.question_type:
                final_q_type_enum = matched_q_type
                question.question_type = final_q_type_enum
                updated = True
        except ValueError as e:
            valid_types = [qt.value for qt in QuestionType]
            return jsonify({"msg": f"Invalid question type '{q_type_str}'. Must be one of {valid_types}"}), 400

    if final_q_type_enum == QuestionType.MCQ:
        options_from_request = data.get('options')
        correct_answer_from_request = data.get('correct_answer')
        options_changed = False

        if 'options' in data:
            if not options_from_request or not isinstance(options_from_request, dict) or not options_from_request:
                return jsonify({"msg": "MCQ update requires a non-empty 'options' dictionary if provided."}), 400
            if options_from_request != question.options:
                question.options = options_from_request
                options_changed = True
                updated = True

        final_correct_answer = None
        if 'correct_answer' in data:
            if not correct_answer_from_request or not isinstance(correct_answer_from_request, str):
                return jsonify({"msg": "MCQ update requires a 'correct_answer' string if provided."}), 400
            final_correct_answer = correct_answer_from_request
        else:
            if original_q_type == QuestionType.MCQ:
                final_correct_answer = question.correct_answer
            elif not options_changed:
                return jsonify({"msg": "Changing type to MCQ requires 'correct_answer' field."}), 400

        final_options = question.options
        if final_correct_answer is not None:
            if final_correct_answer not in final_options:
                return jsonify({"msg": f"The determined 'correct_answer' ('{final_correct_answer}') must be a key in the final 'options'."}), 400
            if final_correct_answer != question.correct_answer:
                question.correct_answer = final_correct_answer
                updated = True
        elif final_q_type_enum == QuestionType.MCQ:
            return jsonify({"msg": "Could not determine a valid 'correct_answer' for the MCQ update."}), 400

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
                return jsonify({"msg": "Invalid word_limit (must be a positive integer or null/absent)."}), 400

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
        return jsonify({
            "msg": "Question updated successfully",
            "question": {
                "id": question.id,
                "question_text": question.question_text,
                "question_type": question.question_type.value,
                "marks": question.marks,
                "options": question.options,
                "correct_answer": question.correct_answer,
                "word_limit": question.word_limit
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error updating question {question_id}: {e}")
        return jsonify({"msg": "Failed to update question due to server error."}), 500

@bp.route('/exams/<int:exam_id>/questions/<int:question_id>', methods=['DELETE'])
@jwt_required()
@teacher_required
@verified_required
def delete_question(exam_id, question_id):
    teacher_id = get_current_user_id()
    if not teacher_id:
        return jsonify({"msg": "Invalid authentication token"}), 401

    question = db.session.query(Question).join(Exam).filter(
        Question.id == question_id,
        Question.exam_id == exam_id,
        Exam.created_by == teacher_id
    ).first_or_404("Question not found or access denied")

    try:
        db.session.delete(question)
        db.session.commit()
        return jsonify({"msg": "Question deleted"}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting question: {e}")
        return jsonify({"msg": "Delete failed"}), 500

# --- View Results ---

@bp.route('/exams/results/<int:exam_id>', methods=['GET'])
@jwt_required()
@teacher_required
@verified_required
def get_exam_results(exam_id):
    teacher_id = get_current_user_id()
    if not teacher_id:
        return jsonify({"msg": "Invalid authentication token"}), 401
    try:
        exam = Exam.query.filter_by(id=exam_id, created_by=teacher_id).options(
            joinedload(Exam.questions)
        ).first_or_404("Exam not found or access denied")

        responses = StudentResponse.query.filter_by(exam_id=exam_id).options(
            joinedload(StudentResponse.student),
            joinedload(StudentResponse.question),
            joinedload(StudentResponse.evaluation)
        ).join(Question).order_by(
            StudentResponse.student_id, Question.id
        ).all()

        results_by_student = {}
        total_possible_marks_exam = sum(q.marks for q in exam.questions if q.marks)

        for resp in responses:
            student = resp.student
            question = resp.question
            evaluation = resp.evaluation

            if not student or not question:
                continue

            student_id = student.id
            if student_id not in results_by_student:
                results_by_student[student_id] = {
                    "student_id": student_id,
                    "student_name": student.name,
                    "total_marks_awarded": 0.0,
                    "total_marks_possible": total_possible_marks_exam,
                    "submission_status": "Submitted",
                    "details": []
                }

            marks_awarded = evaluation.marks_awarded if evaluation and evaluation.marks_awarded is not None else None
            feedback = evaluation.feedback if evaluation else "Not Evaluated Yet"
            evaluated_at = ensure_aware_utc(evaluation.evaluated_at).isoformat() if evaluation and evaluation.evaluated_at else None
            evaluated_by = evaluation.evaluated_by if evaluation else None
            submitted_at = ensure_aware_utc(resp.submitted_at).isoformat() if resp.submitted_at else None

            if marks_awarded is not None:
                results_by_student[student_id]['total_marks_awarded'] += float(marks_awarded)

            results_by_student[student_id]['details'].append({
                "response_id": resp.id,
                "question_id": question.id,
                "question_text": question.question_text,
                "question_type": question.question_type.value,
                "response_text": resp.response_text,
                "submitted_at": submitted_at,
                "marks_possible": question.marks,
                "marks_awarded": marks_awarded,
                "feedback": feedback,
                "evaluated_at": evaluated_at,
                "evaluated_by": evaluated_by
            })
        return jsonify(list(results_by_student.values())), 200
    except Exception as e:
        if hasattr(e, 'code') and e.code == 404:
            return jsonify({"msg": "Exam not found or access denied"}), 404
        print(f"Error fetching results: {e}")
        return jsonify({"msg": "Error fetching exam results."}), 500