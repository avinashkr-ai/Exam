# app/models.py

from app.extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships - No cascade needed *from* User deletion typically
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
    duration = db.Column(db.Integer, nullable=False)
    # Define the ForeignKey to User here
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # ORM Relationships: Define cascades primarily for session management if needed,
    # but DB cascades will handle the deletion persistence.
    # Keeping 'delete-orphan' is good practice for managing children via the session.
    questions = db.relationship('Question', backref='exam', lazy='dynamic',
                                cascade="all, delete-orphan")
    responses = db.relationship('StudentResponse', backref='exam', lazy='dynamic',
                                cascade="all, delete-orphan") # Add cascade here too for completeness

    def __repr__(self):
        return f'<Exam {self.title}>'

class QuestionType(enum.Enum):
    MCQ = 'MCQ'
    SHORT_ANSWER = 'Short Answer'
    LONG_ANSWER = 'Long Answer'

class Question(db.Model):
    __tablename__ = 'questions'
    id = db.Column(db.Integer, primary_key=True)
    # *** ADD ON DELETE CASCADE ***
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id', ondelete='CASCADE'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.Enum(QuestionType), nullable=False)
    options = db.Column(db.JSON, nullable=True)
    correct_answer = db.Column(db.String(255), nullable=True)
    marks = db.Column(db.Integer, nullable=False)
    word_limit = db.Column(db.Integer, nullable=True)

    # Cascade needed here too for deleting Responses when a Question is deleted
    responses = db.relationship('StudentResponse', backref='question', lazy='dynamic',
                                cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Question {self.id} for Exam {self.exam_id}>'

class StudentResponse(db.Model):
    __tablename__ = 'student_responses'
    id = db.Column(db.Integer, primary_key=True)
    # Keep User FK without cascade (usually don't delete User data on Response delete)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    # *** ADD ON DELETE CASCADE *** (If Exam deleted, delete response)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id', ondelete='CASCADE'), nullable=False)
    # *** ADD ON DELETE CASCADE *** (If Question deleted, delete response)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id', ondelete='CASCADE'), nullable=False)
    response_text = db.Column(db.Text, nullable=True)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # The 'evaluation' attribute is added via backref from Evaluation model.
    # Cascade for this one-to-one is best handled on the Evaluation FK below.

    def __repr__(self):
         return f'<StudentResponse {self.id} by Student {self.student_id} for Exam {self.exam_id}>'

class Evaluation(db.Model):
    __tablename__ = 'evaluations'
    id = db.Column(db.Integer, primary_key=True)
    # *** ADD ON DELETE CASCADE *** (If StudentResponse deleted, delete evaluation)
    response_id = db.Column(db.Integer, db.ForeignKey('student_responses.id', ondelete='CASCADE'), unique=True, nullable=False)
    evaluated_by = db.Column(db.String(50), nullable=False)
    marks_awarded = db.Column(db.Float, nullable=False)
    feedback = db.Column(db.Text, nullable=True)
    evaluated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationship remains largely the same, backref creates 'evaluation' attribute.
    # ORM cascade 'delete-orphan' on the *owning* side (response) can be useful
    # if you ever remove an evaluation from a response object in the session.
    response = db.relationship('StudentResponse', backref=db.backref('evaluation', uselist=False,
                                                                     cascade="all, delete-orphan"))

    def __repr__(self):
        return f'<Evaluation for Response {self.response_id}>'