# app/models.py
from app.extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import enum

class UserRole(enum.Enum):
    ADMIN = 'Admin'
    TEACHER = 'Teacher'
    STUDENT = 'Student'

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.STUDENT)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    created_exams = db.relationship('Exam', backref='creator', lazy='dynamic', foreign_keys='Exam.created_by')
    responses = db.relationship('StudentResponse', backref='student', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.email} ({self.role.name})>'

class Exam(db.Model):
    __tablename__ = 'exams'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    scheduled_time = db.Column(db.DateTime, nullable=False)
    duration = db.Column(db.Integer, nullable=False) # Duration in minutes
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False) # Teacher ID
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    questions = db.relationship('Question', backref='exam', lazy='dynamic', cascade="all, delete-orphan")
    responses = db.relationship('StudentResponse', backref='exam', lazy='dynamic')

    def __repr__(self):
        return f'<Exam {self.title}>'

class QuestionType(enum.Enum):
    MCQ = 'MCQ'
    SHORT_ANSWER = 'Short Answer'
    LONG_ANSWER = 'Long Answer'

class Question(db.Model):
    __tablename__ = 'questions'
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.Enum(QuestionType), nullable=False)
    options = db.Column(db.JSON, nullable=True) # For MCQ: {'A': 'Option 1', 'B': 'Option 2', ...}
    correct_answer = db.Column(db.String(255), nullable=True) # For MCQ: 'A', 'B', etc. or text for auto-check short
    marks = db.Column(db.Integer, nullable=False)
    word_limit = db.Column(db.Integer, nullable=True) # For short/long answers

    # Relationships
    responses = db.relationship('StudentResponse', backref='question', lazy='dynamic')

    def __repr__(self):
        return f'<Question {self.id} for Exam {self.exam_id}>'

class StudentResponse(db.Model):
    __tablename__ = 'student_responses'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    response_text = db.Column(db.Text, nullable=True) # Nullable if student skips
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    evaluation = db.relationship('Evaluation', backref='response', uselist=False, cascade="all, delete-orphan") # One-to-one

    def __repr__(self):
        return f'<Response by Student {self.student_id} for Question {self.question_id}>'

class Evaluation(db.Model):
    __tablename__ = 'evaluations'
    id = db.Column(db.Integer, primary_key=True)
    response_id = db.Column(db.Integer, db.ForeignKey('student_responses.id'), unique=True, nullable=False)
    evaluated_by = db.Column(db.String(50), nullable=False) # 'AI_Gemini' or 'Admin_ID_X' or 'Teacher_ID_Y'
    marks_awarded = db.Column(db.Float, nullable=False)
    feedback = db.Column(db.Text, nullable=True)
    evaluated_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Evaluation for Response {self.response_id}>'