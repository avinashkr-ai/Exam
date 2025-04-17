# app/routes/teacher.py

from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models import Exam, Question, QuestionType, StudentResponse, Evaluation, UserRole, User # Import User for student details
from app.utils.decorators import teacher_required, verified_required # Import custom decorators
from flask_jwt_extended import jwt_required # For protecting routes
# Import helper functions (format_datetime now handles naive UTC)
from app.utils.helpers import get_current_user_id, format_datetime
# Use standard Python datetime and timedelta
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import joinedload # For efficient loading
# Removed pendulum import

bp = Blueprint('teacher', __name__)

# No specific timezone definitions needed here anymore

# --- Dashboard ---
@bp.route('/dashboard', methods=['GET'])
@jwt_required()
@teacher_required
@verified_required
def dashboard():
    """Provides basic dashboard info for the logged-in teacher."""
    teacher_id = get_current_user_id()
    if not teacher_id:
        return jsonify({"msg": "Invalid authentication token"}), 401 # Should be caught by decorators

    try:
        # Count exams created by this teacher
        exam_count = Exam.query.filter_by(created_by=teacher_id).count()
        # Potentially add more stats: total questions, recent evaluations, etc.
        print(f"--- Teacher {teacher_id} dashboard requested. Exam count: {exam_count} ---")
        return jsonify({
            "message": "Teacher Dashboard",
            "my_exams_count": exam_count
            # Add more relevant stats here
        }), 200
    except Exception as e:
        print(f"!!! Error generating teacher dashboard for teacher {teacher_id}: {e}")
        return jsonify({"msg": "Error fetching dashboard data."}), 500

# --- Exam Management ---

@bp.route('/exams', methods=['POST'])
@jwt_required()
@teacher_required
@verified_required
def create_exam():
    """Creates a new exam."""
    data = request.get_json()
    teacher_id = get_current_user_id()
    if not teacher_id: return jsonify({"msg": "Invalid authentication token"}), 401
    if not data: return jsonify({"msg": "Missing JSON data"}), 400

    title = data.get('title')
    description = data.get('description')
    # Expect scheduled_time as an ISO 8601 string representing UTC
    scheduled_time_str = data.get('scheduled_time_utc') # Expect key like 'scheduled_time_utc'
    duration_minutes = data.get('duration_minutes')

    if not all([title, scheduled_time_str, duration_minutes]):
        return jsonify({"msg": "Missing required fields: title, scheduled_time_utc, duration_minutes"}), 400

    try:
        # Parse the ISO 8601 string into a datetime object.
        # IMPORTANT: Assume the frontend sends UTC. fromisoformat handles 'Z' but not offsets directly without more logic.
        # If the string might have timezone info, strip it or use a library that handles it robustly if needed.
        # For simplicity, we assume a format like "YYYY-MM-DDTHH:MM:SS" or "YYYY-MM-DDTHH:MM:SSZ"
        if scheduled_time_str.endswith('Z'):
             scheduled_time_str = scheduled_time_str[:-1] # Remove trailing Z for naive parsing
        # Add more robust parsing if needed based on frontend format
        scheduled_time_naive_utc = datetime.fromisoformat(scheduled_time_str)

        duration = int(duration_minutes)
        if duration <= 0:
            raise ValueError("Duration must be a positive integer")

        # Validate that scheduled time is in the future (optional, but good practice)
        if scheduled_time_naive_utc <= datetime.utcnow():
             print(f"--- Warning: Exam created with schedule time in the past: {scheduled_time_naive_utc} UTC ---")
             # Decide if this should be an error:
             # return jsonify({"msg": "Scheduled time must be in the future"}), 400

    except ValueError as e:
        return jsonify({"msg": f"Invalid format for scheduled_time_utc or duration_minutes: {e}. Expected ISO 8601 UTC (e.g., YYYY-MM-DDTHH:MM:SS) and positive integer minutes."}), 400
    except TypeError as e:
         return jsonify({"msg": f"Invalid data type for scheduled_time_utc or duration_minutes: {e}"}), 400

    # Create new Exam instance with naive UTC time
    new_exam = Exam(
        title=title,
        description=description,
        scheduled_time=scheduled_time_naive_utc, # Store naive UTC
        duration=duration,
        created_by=teacher_id,
        created_at=datetime.utcnow()
    )
    try:
        db.session.add(new_exam)
        db.session.commit()
        print(f"--- Exam '{title}' (ID: {new_exam.id}) created by teacher {teacher_id} ---")
        return jsonify({
            "msg": "Exam created successfully",
            "exam": {
                "id": new_exam.id,
                "title": new_exam.title,
                "description": new_exam.description,
                # Format naive UTC for response
                "scheduled_time_utc": format_datetime(new_exam.scheduled_time),
                "duration_minutes": new_exam.duration,
                "created_at_utc": format_datetime(new_exam.created_at)
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        print(f"!!! Error creating exam '{title}' for teacher {teacher_id}: {e}")
        return jsonify({"msg": "Failed to create exam due to a server error."}), 500

@bp.route('/exams', methods=['GET'])
@jwt_required()
@teacher_required
@verified_required
def get_my_exams():
    """Retrieves all exams created by the logged-in teacher."""
    teacher_id = get_current_user_id()
    if not teacher_id: return jsonify({"msg": "Invalid authentication token"}), 401

    try:
        # Fetch exams created by this teacher, order by schedule time descending
        exams = Exam.query.filter_by(created_by=teacher_id).order_by(Exam.scheduled_time.desc()).all()

        # Format data for response
        exams_data = [{
            "id": e.id,
            "title": e.title,
            "description": e.description,
            # Format naive UTC times
            "scheduled_time_utc": format_datetime(e.scheduled_time),
            "duration_minutes": e.duration,
            "created_at_utc": format_datetime(e.created_at)
        } for e in exams]

        print(f"--- Retrieved {len(exams_data)} exams for teacher {teacher_id} ---")
        return jsonify(exams_data), 200
    except Exception as e:
        print(f"!!! Error fetching exams for teacher {teacher_id}: {e}")
        return jsonify({"msg": "Error fetching exams list."}), 500

@bp.route('/exams/<int:exam_id>', methods=['GET'])
@jwt_required()
@teacher_required
@verified_required
def get_exam_details(exam_id):
    """Retrieves details for a specific exam created by the teacher."""
    teacher_id = get_current_user_id()
    if not teacher_id: return jsonify({"msg": "Invalid authentication token"}), 401

    try:
        # Fetch the specific exam, ensuring it belongs to the teacher
        exam = Exam.query.filter_by(id=exam_id, created_by=teacher_id).first()
        if not exam:
            return jsonify({"msg": "Exam not found or access denied"}), 404

        # Format data for response
        exam_data = {
            "id": exam.id,
            "title": exam.title,
            "description": exam.description,
            # Format naive UTC times
            "scheduled_time_utc": format_datetime(exam.scheduled_time),
            "duration_minutes": exam.duration,
            "created_at_utc": format_datetime(exam.created_at)
            # Consider adding question count: "question_count": exam.questions.count()
        }
        print(f"--- Retrieved details for exam {exam_id} by teacher {teacher_id} ---")
        return jsonify(exam_data), 200
    except Exception as e:
        print(f"!!! Error fetching details for exam {exam_id} by teacher {teacher_id}: {e}")
        return jsonify({"msg": "Error fetching exam details."}), 500

@bp.route('/exams/<int:exam_id>', methods=['PUT'])
@jwt_required()
@teacher_required
@verified_required
def update_exam(exam_id):
    """Updates details of an existing exam."""
    teacher_id = get_current_user_id()
    data = request.get_json()
    if not teacher_id: return jsonify({"msg": "Invalid authentication token"}), 401
    if not data: return jsonify({"msg": "Missing JSON data"}), 400

    # Fetch the exam, ensuring ownership
    exam = Exam.query.filter_by(id=exam_id, created_by=teacher_id).first()
    if not exam:
        return jsonify({"msg": "Exam not found or access denied"}), 404

    updated_fields = [] # Track which fields were updated

    # Update fields if provided in the request data
    if 'title' in data:
        exam.title = data['title']
        updated_fields.append('title')
    if 'description' in data:
        exam.description = data['description']
        updated_fields.append('description')
    if 'scheduled_time_utc' in data:
        try:
            stime_str = data['scheduled_time_utc']
            # Similar parsing as in create_exam, assuming UTC ISO string
            if stime_str.endswith('Z'):
                stime_str = stime_str[:-1]
            stime_naive_utc = datetime.fromisoformat(stime_str)
            # Optional: Validate if time is in the past
            # if stime_naive_utc <= datetime.utcnow():
            #     return jsonify({"msg": "Scheduled time must be in the future"}), 400
            exam.scheduled_time = stime_naive_utc
            updated_fields.append('scheduled_time')
        except (ValueError, TypeError) as e:
            return jsonify({"msg": f"Invalid format for scheduled_time_utc: {e}. Expected ISO 8601 UTC."}), 400
    if 'duration_minutes' in data:
        try:
            dur = int(data['duration_minutes'])
            if dur <= 0:
                raise ValueError("Duration must be positive")
            exam.duration = dur
            updated_fields.append('duration')
        except (ValueError, TypeError):
            return jsonify({"msg": "Invalid duration_minutes: Must be a positive integer."}), 400

    if not updated_fields:
        return jsonify({"msg": "No valid fields provided for update"}), 400

    try:
        db.session.commit()
        print(f"--- Exam {exam_id} updated by teacher {teacher_id}. Fields: {', '.join(updated_fields)} ---")
        # Return the updated exam data
        return jsonify({
            "msg": "Exam updated successfully",
            "exam": {
                "id": exam.id,
                "title": exam.title,
                "description": exam.description,
                "scheduled_time_utc": format_datetime(exam.scheduled_time),
                "duration_minutes": exam.duration,
                "created_at_utc": format_datetime(exam.created_at)
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        print(f"!!! Error updating exam {exam_id} by teacher {teacher_id}: {e}")
        return jsonify({"msg": "Exam update failed due to a server error."}), 500

@bp.route('/exams/<int:exam_id>', methods=['DELETE'])
@jwt_required()
@teacher_required
@verified_required
def delete_exam(exam_id):
    """Deletes an exam and its associated questions/responses."""
    teacher_id = get_current_user_id()
    if not teacher_id: return jsonify({"msg": "Invalid authentication token"}), 401

    # Fetch the exam, ensuring ownership
    exam = Exam.query.filter_by(id=exam_id, created_by=teacher_id).first()
    if not exam:
        return jsonify({"msg": "Exam not found or access denied"}), 404

    # Note: Cascading delete for Questions and StudentResponses should be handled
    # by the 'cascade="all, delete-orphan"' option on the relationships in models.py.
    # If evaluations have FK constraints, deleting responses might fail if evaluations exist.
    # Consider adding cascade delete to Evaluation relationship or deleting evaluations manually first.
    try:
        exam_title = exam.title # Get title for logging before delete
        db.session.delete(exam)
        db.session.commit()
        print(f"--- Exam '{exam_title}' (ID: {exam_id}) deleted successfully by teacher {teacher_id} ---")
        return jsonify({"msg": f"Exam '{exam_title}' deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        print(f"!!! Error deleting exam {exam_id} by teacher {teacher_id}: {e}")
        # Check for potential IntegrityErrors if cascade isn't fully set up
        return jsonify({"msg": "Exam deletion failed. Check for related records or server errors."}), 500

# --- Question Management ---

@bp.route('/exams/<int:exam_id>/questions', methods=['POST'])
@jwt_required()
@teacher_required
@verified_required
def add_question(exam_id):
    """Adds a new question to a specific exam."""
    teacher_id = get_current_user_id()
    if not teacher_id: return jsonify({"msg": "Invalid authentication token."}), 401

    # Verify exam exists and belongs to the teacher
    exam = Exam.query.filter_by(id=exam_id, created_by=teacher_id).first()
    if not exam: return jsonify({"msg": "Exam not found or access denied"}), 404

    data = request.get_json()
    if not data: return jsonify({"msg": "Missing JSON data"}), 400

    # Extract question details from request
    q_text = data.get('question_text')
    q_type_str = data.get('question_type') # e.g., "MCQ", "Short Answer"
    marks = data.get('marks')
    options = data.get('options') # Expected for MCQ: {"key1": "text1", "key2": "text2"}
    correct_answer = data.get('correct_answer') # Expected for MCQ: "key1"
    word_limit = data.get('word_limit') # Expected for Short/Long

    # Basic validation
    if not q_text or not q_type_str or marks is None:
        return jsonify({"msg": "Missing required fields: question_text, question_type, marks"}), 400

    # Validate question type
    try:
        # Convert string type to enum
        q_type_enum = QuestionType(q_type_str)
    except ValueError:
        valid_types = [qt.value for qt in QuestionType]
        return jsonify({"msg": f"Invalid question type '{q_type_str}'. Must be one of: {', '.join(valid_types)}"}), 400

    # Validate marks
    try:
        marks_int = int(marks)
        if marks_int <= 0: raise ValueError("Marks must be positive")
    except (ValueError, TypeError):
        return jsonify({"msg": f"Invalid marks value: '{marks}'. Must be a positive integer."}), 400

    # Type-specific validation
    validated_options = None
    validated_correct_answer = None
    validated_word_limit = None

    if q_type_enum == QuestionType.MCQ:
        if not options or not isinstance(options, dict) or not options:
            return jsonify({"msg": "MCQ requires a non-empty 'options' dictionary (key-value pairs)."}), 400
        if not correct_answer or not isinstance(correct_answer, str):
            return jsonify({"msg": "MCQ requires a 'correct_answer' string (the key of the correct option)."}), 400
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
                return jsonify({"msg": "Invalid word_limit. Must be a positive integer or null/absent."}), 400
        # else: validated_word_limit remains None
    else:
        # Should not happen if enum validation works
        return jsonify({"msg": "Unhandled question type during validation."}), 500

    # Create new Question instance
    new_question = Question(
        exam_id=exam_id,
        question_text=q_text,
        question_type=q_type_enum,
        marks=marks_int,
        options=validated_options,
        correct_answer=validated_correct_answer,
        word_limit=validated_word_limit
    )

    try:
        db.session.add(new_question)
        db.session.commit()
        print(f"--- Question {new_question.id} added to exam {exam_id} by teacher {teacher_id} ---")
        # Return the created question details
        return jsonify({
            "msg": "Question added successfully",
            "question": {
                "id": new_question.id,
                "question_text": new_question.question_text,
                "question_type": new_question.question_type.value,
                "marks": new_question.marks,
                "options": new_question.options,
                "correct_answer": new_question.correct_answer, # Consider hiding this? Teacher already knows.
                "word_limit": new_question.word_limit
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        print(f"!!! Error saving question to exam {exam_id} for teacher {teacher_id}: {e}")
        return jsonify({"msg": "Failed to add question due to a server error."}), 500

@bp.route('/exams/<int:exam_id>/questions', methods=['GET'])
@jwt_required()
@teacher_required
@verified_required
def get_exam_questions(exam_id):
    """Retrieves all questions for a specific exam owned by the teacher."""
    teacher_id = get_current_user_id()
    if not teacher_id: return jsonify({"msg": "Invalid authentication token"}), 401

    # Verify exam exists and belongs to the teacher
    exam = Exam.query.filter_by(id=exam_id, created_by=teacher_id).first()
    if not exam: return jsonify({"msg": "Exam not found or access denied"}), 404

    try:
        # Fetch all questions for this exam
        questions = Question.query.filter_by(exam_id=exam_id).order_by(Question.id).all()

        # Format data for response
        questions_data = [{
            "id": q.id,
            "question_text": q.question_text,
            "question_type": q.question_type.value,
            "marks": q.marks,
            "options": q.options, # Include options for teacher review
            "correct_answer": q.correct_answer, # Include correct answer for teacher review
            "word_limit": q.word_limit
        } for q in questions]

        print(f"--- Retrieved {len(questions_data)} questions for exam {exam_id} for teacher {teacher_id} ---")
        return jsonify(questions_data), 200
    except Exception as e:
        print(f"!!! Error fetching questions for exam {exam_id} by teacher {teacher_id}: {e}")
        return jsonify({"msg": "Error fetching questions."}), 500

@bp.route('/exams/<int:exam_id>/questions/<int:question_id>', methods=['GET'])
@jwt_required()
@teacher_required
@verified_required
def get_single_question(exam_id, question_id):
    """Retrieves details of a single question within an exam owned by the teacher."""
    teacher_id = get_current_user_id()
    if not teacher_id: return jsonify({"msg": "Invalid authentication token"}), 401

    try:
        # Query for the specific question, ensuring it belongs to the correct exam and teacher
        question = db.session.query(Question).join(Exam).filter(
            Question.id == question_id,
            Question.exam_id == exam_id,
            Exam.created_by == teacher_id # Correct comparison operator
        ).first()

        if not question:
            return jsonify({"msg": "Question not found or access denied"}), 404

        # Format data for response
        question_data = {
            "id": question.id,
            "question_text": question.question_text,
            "question_type": question.question_type.value,
            "marks": question.marks,
            "options": question.options,
            "correct_answer": question.correct_answer,
            "word_limit": question.word_limit
        }
        print(f"--- Retrieved question {question_id} for exam {exam_id} by teacher {teacher_id} ---")
        return jsonify(question_data), 200

    except Exception as e:
        print(f"!!! Error fetching single question {question_id} (Exam {exam_id}) by teacher {teacher_id}: {e}")
        return jsonify({"msg": "Error fetching question details."}), 500

@bp.route('/exams/<int:exam_id>/questions/<int:question_id>', methods=['PUT'])
@jwt_required()
@teacher_required
@verified_required
def update_question(exam_id, question_id):
    """Updates an existing question."""
    teacher_id = get_current_user_id()
    if not teacher_id: return jsonify({"msg": "Invalid authentication token"}), 401

    data = request.get_json()
    if not data: return jsonify({"msg": "Missing JSON data"}), 400

    # Fetch the question ensuring ownership via the exam
    question = db.session.query(Question).join(Exam).filter(
        Question.id == question_id,
        Question.exam_id == exam_id,
        Exam.created_by == teacher_id
    ).first()

    if not question: return jsonify({"msg": "Question not found or access denied"}), 404

    updated_fields = []
    original_q_type = question.question_type # Store original type for logic checks

    # --- Update Logic ---
    # Update text
    if 'question_text' in data and data['question_text'] != question.question_text:
        question.question_text = data['question_text']
        updated_fields.append('question_text')

    # Update marks
    if 'marks' in data:
        try:
            marks = int(data['marks'])
            if marks <= 0: raise ValueError("Marks must be positive")
            if marks != question.marks:
                question.marks = marks
                updated_fields.append('marks')
        except (ValueError, TypeError):
            return jsonify({"msg": "Invalid marks value. Must be a positive integer."}), 400

    # Update question type (more complex validation)
    new_q_type_enum = question.question_type
    if 'question_type' in data:
        q_type_str = data['question_type']
        try:
            matched_q_type = QuestionType(q_type_str) # Convert string to enum
            if matched_q_type != question.question_type:
                new_q_type_enum = matched_q_type # Tentatively update type
                updated_fields.append('question_type')
        except ValueError:
            valid_types = [qt.value for qt in QuestionType]
            return jsonify({"msg": f"Invalid question type '{q_type_str}'. Must be one of: {', '.join(valid_types)}"}), 400

    # Type-specific updates and validation based on the *final* intended type
    if new_q_type_enum == QuestionType.MCQ:
        options_updated = False
        # Update options if provided
        if 'options' in data:
            new_options = data['options']
            if not new_options or not isinstance(new_options, dict) or not new_options:
                return jsonify({"msg": "MCQ update requires a non-empty 'options' dictionary if 'options' field is provided."}), 400
            if new_options != question.options:
                question.options = new_options
                if 'options' not in updated_fields: updated_fields.append('options')
                options_updated = True

        # Determine correct answer: must be present if type changes TO MCQ, or if options change, or if correct_answer itself changes
        new_correct_answer = data.get('correct_answer', question.correct_answer if original_q_type == QuestionType.MCQ else None)

        if new_correct_answer is None and new_q_type_enum == QuestionType.MCQ:
             # If ending up as MCQ, we need a correct answer.
              return jsonify({"msg": "Changing type to MCQ or updating MCQ options requires the 'correct_answer' field."}), 400

        if new_correct_answer is not None:
             if not isinstance(new_correct_answer, str):
                  return jsonify({"msg": "MCQ 'correct_answer' must be a string."}), 400
             current_options = question.options # Use potentially updated options
             if new_correct_answer not in current_options:
                  return jsonify({"msg": f"The 'correct_answer' ('{new_correct_answer}') must be a key in the final 'options' dictionary."}), 400
             if new_correct_answer != question.correct_answer:
                 question.correct_answer = new_correct_answer
                 if 'correct_answer' not in updated_fields: updated_fields.append('correct_answer')

        # Nullify subjective fields if switching to MCQ
        if question.word_limit is not None:
            question.word_limit = None
            if 'word_limit' not in updated_fields and original_q_type != QuestionType.MCQ: updated_fields.append('word_limit (removed)')
        # Apply the type change now that validation passed
        if new_q_type_enum != original_q_type: question.question_type = new_q_type_enum

    elif new_q_type_enum in [QuestionType.SHORT_ANSWER, QuestionType.LONG_ANSWER]:
        # Update word limit if provided
        if 'word_limit' in data:
            new_word_limit = data['word_limit']
            try:
                limit_val = int(new_word_limit) if new_word_limit is not None else None
                if limit_val is not None and limit_val <= 0:
                    raise ValueError("Word limit must be positive if provided.")
                if limit_val != question.word_limit:
                    question.word_limit = limit_val
                    if 'word_limit' not in updated_fields: updated_fields.append('word_limit')
            except (ValueError, TypeError):
                return jsonify({"msg": "Invalid word_limit. Must be a positive integer or null/absent."}), 400

        # Nullify MCQ fields if switching away from MCQ
        if question.options is not None:
            question.options = None
            if 'options' not in updated_fields and original_q_type == QuestionType.MCQ: updated_fields.append('options (removed)')
        if question.correct_answer is not None:
            question.correct_answer = None
            if 'correct_answer' not in updated_fields and original_q_type == QuestionType.MCQ: updated_fields.append('correct_answer (removed)')
        # Apply the type change
        if new_q_type_enum != original_q_type: question.question_type = new_q_type_enum

    # --- End Update Logic ---

    if not updated_fields:
        return jsonify({"msg": "No changes detected or no valid fields provided for update."}), 400

    try:
        db.session.commit()
        print(f"--- Question {question_id} (Exam {exam_id}) updated by teacher {teacher_id}. Fields: {', '.join(updated_fields)} ---")
        # Return updated question details
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
        print(f"!!! Error updating question {question_id} (Exam {exam_id}) by teacher {teacher_id}: {e}")
        return jsonify({"msg": "Failed to update question due to a server error."}), 500

@bp.route('/exams/<int:exam_id>/questions/<int:question_id>', methods=['DELETE'])
@jwt_required()
@teacher_required
@verified_required
def delete_question(exam_id, question_id):
    """Deletes a specific question from an exam."""
    teacher_id = get_current_user_id()
    if not teacher_id: return jsonify({"msg": "Invalid authentication token"}), 401

    # Fetch the question ensuring ownership via the exam
    question = db.session.query(Question).join(Exam).filter(
        Question.id == question_id,
        Question.exam_id == exam_id,
        Exam.created_by == teacher_id
    ).first()

    if not question: return jsonify({"msg": "Question not found or access denied"}), 404

    # Associated StudentResponses and Evaluations might need consideration.
    # Current model setup cascades Question deletion to StudentResponses.
    # Check if Evaluations should also be deleted or handled.
    try:
        db.session.delete(question)
        db.session.commit()
        print(f"--- Question {question_id} deleted from exam {exam_id} by teacher {teacher_id} ---")
        return jsonify({"msg": "Question deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        print(f"!!! Error deleting question {question_id} (Exam {exam_id}) by teacher {teacher_id}: {e}")
        return jsonify({"msg": "Question deletion failed. Check related responses/evaluations or server logs."}), 500

# --- Result Viewing ---

@bp.route('/exams/results/<int:exam_id>', methods=['GET'])
@jwt_required()
@teacher_required
@verified_required
def get_exam_results(exam_id):
    """Retrieves aggregated and detailed results for a specific exam owned by the teacher."""
    teacher_id = get_current_user_id()
    if not teacher_id: return jsonify({"msg": "Invalid authentication token"}), 401

    try:
        # Fetch the exam with its questions, ensuring ownership
        exam = Exam.query.filter_by(id=exam_id, created_by=teacher_id).options(
            joinedload(Exam.questions) # Eager load questions for total marks calculation
        ).first()
        if not exam: return jsonify({"msg": "Exam not found or access denied"}), 404

        # Fetch all responses for this exam, joining related student, question, and evaluation data
        responses = StudentResponse.query.filter_by(exam_id=exam_id).options(
            joinedload(StudentResponse.student),    # Load student details
            joinedload(StudentResponse.question),   # Load question details
            joinedload(StudentResponse.evaluation)  # Load evaluation (if exists)
        ).join(Question).order_by( # Join needed for ordering by student name/id if desired
            StudentResponse.student_id, Question.id # Order by student, then question order
        ).all()

        # Process results, grouping by student
        results_by_student = {}
        # Calculate total possible marks accurately from loaded questions
        total_possible_marks_exam = sum(q.marks for q in exam.questions if q.marks)

        for resp in responses:
            student = resp.student
            question = resp.question
            evaluation = resp.evaluation # Will be None if not evaluated

            # Skip if data integrity issue (shouldn't happen with FKs)
            if not student or not question:
                print(f"!!! WARNING: Skipping response {resp.id} due to missing student/question link.")
                continue

            student_id = student.id
            if student_id not in results_by_student:
                # Initialize structure for this student
                results_by_student[student_id] = {
                    "student_id": student_id,
                    "student_name": student.name,
                    "student_email": student.email, # Add email for easier identification
                    "total_marks_awarded": 0.0,
                    "total_marks_possible": total_possible_marks_exam,
                    "submission_status": "Submitted", # Initial status
                    "_pending_eval_count": 0, # Counter for unevaluated responses
                    "details": [] # List to hold response/evaluation details
                }

            # Extract evaluation details safely
            marks_awarded = None
            feedback = "Not Evaluated Yet"
            evaluated_at_utc = None
            evaluated_by = None
            eval_status = "Pending Evaluation"

            if evaluation:
                marks_awarded = evaluation.marks_awarded
                feedback = evaluation.feedback if evaluation.feedback else "Evaluation submitted, no feedback provided."
                evaluated_at_utc = format_datetime(evaluation.evaluated_at) # Format naive UTC
                evaluated_by = evaluation.evaluated_by
                eval_status = "Evaluated"
            else:
                results_by_student[student_id]['_pending_eval_count'] += 1

            # Format submission time (naive UTC)
            submitted_at_utc = format_datetime(resp.submitted_at)

            # Add detailed info for this response
            results_by_student[student_id]['details'].append({
                "response_id": resp.id,
                "question_id": question.id,
                "question_text": question.question_text,
                "question_type": question.question_type.value,
                "response_text": resp.response_text,
                "submitted_at_utc": submitted_at_utc,
                "marks_possible": question.marks,
                "marks_awarded": marks_awarded,
                "feedback": feedback,
                "evaluated_at_utc": evaluated_at_utc,
                "evaluated_by": evaluated_by,
                "evaluation_status": eval_status
            })

            # Accumulate awarded marks for the student
            if marks_awarded is not None:
                try:
                    results_by_student[student_id]['total_marks_awarded'] += float(marks_awarded)
                except (ValueError, TypeError):
                    print(f"!!! WARNING: Could not add marks_awarded '{marks_awarded}' for response {resp.id}")


        # Post-process to finalize overall status and remove counter
        final_results = []
        for student_id, data in results_by_student.items():
            if data['_pending_eval_count'] == 0:
                 data['submission_status'] = "Fully Evaluated"
            else:
                 total_q = len(data['details'])
                 evaluated_q = total_q - data['_pending_eval_count']
                 data['submission_status'] = f"Partially Evaluated ({evaluated_q}/{total_q})"

            del data['_pending_eval_count'] # Remove internal counter
            final_results.append(data)

        print(f"--- Generated results for {len(final_results)} students for exam {exam_id} (Teacher: {teacher_id}) ---")
        return jsonify(list(final_results)), 200 # Return list of student results

    except Exception as e:
        # Handle specific errors like 404 if needed
        # if isinstance(e, NotFound): return jsonify({"msg": "Exam not found or access denied"}), 404
        print(f"!!! Error fetching results for exam {exam_id} by teacher {teacher_id}: {e}")
        # import traceback; traceback.print_exc() # For debug
        return jsonify({"msg": "Error fetching exam results."}), 500