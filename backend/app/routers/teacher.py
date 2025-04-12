from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timezone
from ..models import db, User, Exam, Question, Submission, SubmittedAnswer, Result, ExamQuestion
from ..utils.decorators import teacher_required

teacher_bp = Blueprint('teacher', __name__)

# --- Question Management ---

@teacher_bp.route('/questions', methods=['POST'])
@teacher_required
def add_question():
    data = request.get_json()
    required_fields = ['question_text', 'question_type', 'points']
    if not all(field in data for field in required_fields):
        return jsonify(message="Missing required fields (question_text, question_type, points)"), 400

    question = Question(
        question_text=data['question_text'],
        question_type=data['question_type'],
        correct_answer_or_criteria=data.get('correct_answer_or_criteria'),
        points=data['points']
    )
    db.session.add(question)
    db.session.commit()
    return jsonify(message="Question added successfully", question_id=question.id), 201

@teacher_bp.route('/questions', methods=['GET'])
@teacher_required
def list_questions():
    questions = Question.query.all()
    output = [{
        'id': q.id,
        'question_text': q.question_text,
        'question_type': q.question_type,
        'points': q.points,
        'correct_answer_or_criteria': q.correct_answer_or_criteria # Include for teacher view
    } for q in questions]
    return jsonify(questions=output), 200

# --- Exam Management ---

@teacher_bp.route('/exams', methods=['POST'])
@teacher_required
def create_exam():
    data = request.get_json()
    user_id = get_jwt_identity()

    required_fields = ['title', 'duration_minutes', 'start_time', 'end_time', 'question_ids']
    if not all(field in data for field in required_fields):
        return jsonify(message="Missing required fields (title, duration_minutes, start_time, end_time, question_ids)"), 400

    if not isinstance(data['question_ids'], list) or not data['question_ids']:
        return jsonify(message="question_ids must be a non-empty list"), 400

    try:
        # Ensure questions exist
        questions = Question.query.filter(Question.id.in_(data['question_ids'])).all()
        if len(questions) != len(data['question_ids']):
             existing_ids = {q.id for q in questions}
             missing_ids = [qid for qid in data['question_ids'] if qid not in existing_ids]
             return jsonify(message=f"One or more question IDs not found: {missing_ids}"), 404

        # Parse datetimes (assuming ISO 8601 format from frontend)
        start_time_dt = datetime.fromisoformat(data['start_time'].replace('Z', '+00:00'))
        end_time_dt = datetime.fromisoformat(data['end_time'].replace('Z', '+00:00'))

        # Ensure datetimes are timezone-aware (UTC)
        if start_time_dt.tzinfo is None:
            start_time_dt = start_time_dt.replace(tzinfo=timezone.utc)
        if end_time_dt.tzinfo is None:
            end_time_dt = end_time_dt.replace(tzinfo=timezone.utc)

        new_exam = Exam(
            title=data['title'],
            description=data.get('description'),
            creator_id=user_id,
            duration_minutes=data['duration_minutes'],
            start_time=start_time_dt,
            end_time=end_time_dt
        )
        db.session.add(new_exam)
        # Flush to get the new_exam.id before creating ExamQuestion links
        db.session.flush()

        # Add questions to the exam using the association object
        for index, q_id in enumerate(data['question_ids']):
            exam_question_link = ExamQuestion(exam_id=new_exam.id, question_id=q_id, order=index)
            db.session.add(exam_question_link)

        db.session.commit()
        return jsonify(message="Exam created successfully", exam_id=new_exam.id), 201

    except ValueError as ve:
         return jsonify(message=f"Invalid date format: {ve}. Use ISO 8601 format (e.g., YYYY-MM-DDTHH:MM:SSZ)."), 400
    except Exception as e:
        db.session.rollback()
        print(f"Error creating exam: {e}")
        return jsonify(message="Failed to create exam due to server error"), 500


@teacher_bp.route('/exams', methods=['GET'])
@teacher_required
def list_teacher_exams():
    user_id = get_jwt_identity()
    exams = Exam.query.filter_by(creator_id=user_id).order_by(Exam.created_at.desc()).all()
    output = [{
        'id': exam.id,
        'title': exam.title,
        'description': exam.description,
        'duration_minutes': exam.duration_minutes,
        'start_time': exam.start_time.isoformat(),
        'end_time': exam.end_time.isoformat(),
        'created_at': exam.created_at.isoformat(),
        'question_count': len(exam.questions) # Use the relationship
    } for exam in exams]
    return jsonify(exams=output), 200

# --- Submission Viewing ---

@teacher_bp.route('/exams/<int:exam_id>/submissions', methods=['GET'])
@teacher_required
def view_exam_submissions(exam_id):
    user_id = get_jwt_identity()
    exam = Exam.query.get_or_404(exam_id)

    # Verify the teacher created this exam
    if exam.creator_id != user_id:
        return jsonify(message="Forbidden: You did not create this exam."), 403

    submissions = Submission.query.filter_by(exam_id=exam_id).order_by(Submission.submitted_at.desc()).all()

    output = []
    for sub in submissions:
        student = User.query.get(sub.student_id) # Fetch student details
        output.append({
            'submission_id': sub.id,
            'student_id': sub.student_id,
            'student_username': student.username if student else 'Unknown',
            'submitted_at': sub.submitted_at.isoformat(),
            'status': sub.status.value,
            'total_score': sub.total_score # This will be null until evaluated
        })

    return jsonify(submissions=output), 200


@teacher_bp.route('/submissions/<int:submission_id>/details', methods=['GET'])
@teacher_required
def view_submission_details(submission_id):
    # Optional: Allow teacher to see individual answers and results
    user_id = get_jwt_identity()
    submission = Submission.query.get_or_404(submission_id)
    exam = Exam.query.get_or_404(submission.exam_id)

    if exam.creator_id != user_id:
        return jsonify(message="Forbidden: You cannot view details for this submission."), 403

    answers = SubmittedAnswer.query.filter_by(submission_id=submission_id).all()
    results = Result.query.filter_by(submission_id=submission_id).all()
    results_map = {res.question_id: res for res in results} # For easy lookup

    answer_details = []
    for ans in answers:
        result = results_map.get(ans.question_id)
        answer_details.append({
            'question_id': ans.question_id,
            'question_text': ans.question.question_text,
            'student_answer': ans.student_answer_text,
            'evaluated_mark': result.evaluated_mark if result else None,
            'evaluation_feedback': result.evaluation_feedback if result else None,
            'max_points': ans.question.points
        })

    student = User.query.get(submission.student_id)
    return jsonify({
        'submission_id': submission.id,
        'exam_id': submission.exam_id,
        'exam_title': exam.title,
        'student_id': submission.student_id,
        'student_username': student.username if student else 'Unknown',
        'submitted_at': submission.submitted_at.isoformat(),
        'status': submission.status.value,
        'total_score': submission.total_score,
        'answers': answer_details
    }), 200