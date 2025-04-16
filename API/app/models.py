# models.py

from app.extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import enum
import pendulum  # Added for IST handling

# Define IST timezone
IST = pendulum.timezone('Asia/Kolkata')  # GMT+5:30

class UserRole(enum.Enum):
    ADMIN = 'Admin'
    TEACHER = 'Teacher'
    STUDENT = 'Student'

class User(db.Model):
    # ... (User model remains the same) ...
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(256))  # Ensure this column exists
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.STUDENT)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: pendulum.now(IST).naive())

    # Relationships
    created_exams = db.relationship('Exam', backref='creator', lazy='dynamic', foreign_keys='Exam.created_by')
    responses = db.relationship('StudentResponse', backref='student', lazy='dynamic')

    def set_password(self, password):
        """Hash and store the password."""
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        """Verify the password against the stored hash."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.email} ({self.role.name})>'


class Exam(db.Model):
    # ... (Exam model remains the same) ...
    __tablename__ = 'exams'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    scheduled_time = db.Column(db.DateTime, nullable=False)  # Will be parsed as IST
    duration = db.Column(db.Integer, nullable=False)  # Duration in minutes
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: pendulum.now(IST))  # Changed to IST
    questions = db.relationship('Question', backref='exam', lazy='dynamic', cascade="all, delete-orphan")
    responses = db.relationship('StudentResponse', backref='exam', lazy='dynamic')

    def __repr__(self):
        return f'<Exam {self.title}>'

class QuestionType(enum.Enum):
    MCQ = 'MCQ'
    SHORT_ANSWER = 'Short Answer'
    LONG_ANSWER = 'Long Answer'

class Question(db.Model):
    # ... (Question model remains the same) ...
    __tablename__ = 'questions'
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.Enum(QuestionType), nullable=False)
    options = db.Column(db.JSON, nullable=True)
    correct_answer = db.Column(db.String(255), nullable=True)
    marks = db.Column(db.Integer, nullable=False)
    word_limit = db.Column(db.Integer, nullable=True)
    responses = db.relationship('StudentResponse', backref='question', lazy='dynamic')

    def __repr__(self):
        return f'<Question {self.id} for Exam {self.exam_id}>'


class StudentResponse(db.Model):
    __tablename__ = 'student_responses'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    response_text = db.Column(db.Text, nullable=True)
    submitted_at = db.Column(db.DateTime, default=lambda: pendulum.now(IST).naive())

    # The 'evaluation' attribute will be added dynamically by the backref below

    def __repr__(self):
         return f'<StudentResponse {self.id} by Student {self.student_id} for Exam {self.exam_id}>'


class Evaluation(db.Model):
    __tablename__ = 'evaluations'
    id = db.Column(db.Integer, primary_key=True)
    # Ensure ForeignKey constraint name matches table/column if needed, usually auto-detected
    response_id = db.Column(db.Integer, db.ForeignKey('student_responses.id'), unique=True, nullable=False)
    evaluated_by = db.Column(db.String(50), nullable=False)
    marks_awarded = db.Column(db.Float, nullable=False)
    feedback = db.Column(db.Text, nullable=True)
    evaluated_at = db.Column(db.DateTime, default=lambda: pendulum.now(IST))

    # --- ADD THIS RELATIONSHIP DEFINITION ---
    # Defines the relationship to the StudentResponse this evaluation belongs to.
    # The backref creates the 'evaluation' attribute on the StudentResponse instance.
    # uselist=False makes it a one-to-one relationship access (student_response.evaluation).
    response = db.relationship('StudentResponse', backref=db.backref('evaluation', uselist=False))
    # --- END OF ADDITION ---

    def __repr__(self):
        return f'<Evaluation for Response {self.response_id}>'