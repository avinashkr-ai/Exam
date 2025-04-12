import enum
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from . import db # Import db from app package __init__

class UserRole(enum.Enum):
    TEACHER = 'teacher'
    STUDENT = 'student'

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.STUDENT)
    created_exams = db.relationship('Exam', backref='creator', lazy='dynamic', foreign_keys='Exam.creator_id')
    submissions = db.relationship('Submission', backref='student', lazy='dynamic', foreign_keys='Submission.student_id')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username} ({self.role.value})>'

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_text = db.Column(db.Text, nullable=False)
    # Example: 'mcq', 'short_answer', 'essay'
    question_type = db.Column(db.String(50), nullable=False, default='short_answer')
    # For MCQs store correct option index/value; for others store criteria/keywords
    correct_answer_or_criteria = db.Column(db.Text, nullable=True)
    points = db.Column(db.Integer, nullable=False, default=1)
    # Relationship added for ExamQuestion backref
    exams = db.relationship('ExamQuestion', back_populates='question')


    def __repr__(self):
        return f'<Question {self.id}: {self.question_text[:30]}...>'

class Exam(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, nullable=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False) # Exam duration once started
    start_time = db.Column(db.DateTime, nullable=False) # Availability window start
    end_time = db.Column(db.DateTime, nullable=False)   # Availability window end
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    # Relationship using ExamQuestion association object
    questions = db.relationship('ExamQuestion', back_populates='exam', cascade="all, delete-orphan")
    submissions = db.relationship('Submission', backref='exam', lazy='dynamic', foreign_keys='Submission.exam_id')


    def __repr__(self):
        return f'<Exam {self.id}: {self.title}>'

# Association object for the many-to-many relationship between Exam and Question
# This allows storing additional data like the order of questions in an exam
class ExamQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True) # Explicit primary key
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    order = db.Column(db.Integer) # Optional: order of the question in the exam

    exam = db.relationship('Exam', back_populates='questions')
    question = db.relationship('Question', back_populates='exams')

    def __repr__(self):
        return f'<ExamQuestion exam:{self.exam_id} question:{self.question_id}>'


class SubmissionStatus(enum.Enum):
    SUBMITTED = 'submitted'
    EVALUATING = 'evaluating'
    EVALUATED = 'evaluated'

class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=False)
    submitted_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    status = db.Column(db.Enum(SubmissionStatus), nullable=False, default=SubmissionStatus.SUBMITTED)
    total_score = db.Column(db.Float, nullable=True) # Store aggregated score after evaluation

    answers = db.relationship('SubmittedAnswer', backref='submission', lazy='dynamic', cascade="all, delete-orphan")
    results = db.relationship('Result', backref='submission', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Submission {self.id} by Student {self.student_id} for Exam {self.exam_id}>'

class SubmittedAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey('submission.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    student_answer_text = db.Column(db.Text, nullable=True)

    question = db.relationship('Question') # To easily access question details

    def __repr__(self):
        return f'<SubmittedAnswer {self.id} for Question {self.question_id} in Submission {self.submission_id}>'

class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey('submission.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    # No need for student_id and exam_id here, can get via submission_id
    evaluated_mark = db.Column(db.Float, nullable=False)
    evaluation_feedback = db.Column(db.Text, nullable=True) # Optional feedback from Gemini/Teacher
    evaluated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    question = db.relationship('Question') # To easily access question details

    def __repr__(self):
        return f'<Result {self.id} for Q {self.question_id} Sub {self.submission_id} Mark: {self.evaluated_mark}>'