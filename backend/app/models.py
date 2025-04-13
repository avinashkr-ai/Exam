from .extensions import db, bcrypt
from datetime import datetime, timezone

# Helper table for many-to-many relationship between students and exams they are allowed to take
# (Optional - if you want explicit assignment rather than just filtering by status/time)
# student_exams = db.Table('student_exams',
#     db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
#     db.Column('exam_id', db.Integer, db.ForeignKey('exam.id'), primary_key=True)
# )

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(10), nullable=False, default='student') # 'student' or 'teacher'
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    exams_created = db.relationship('Exam', back_populates='creator', lazy='dynamic', foreign_keys='Exam.creator_id')
    submissions = db.relationship('Submission', back_populates='student', lazy='dynamic', foreign_keys='Submission.student_id')
    # exams_assigned = db.relationship('Exam', secondary=student_exams, lazy='subquery', backref=db.backref('assigned_students', lazy=True)) # For explicit assignment

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'

class Exam(db.Model):
    __tablename__ = 'exam'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    scheduled_start_time = db.Column(db.DateTime(timezone=True), nullable=True) # Store timezone-aware
    scheduled_end_time = db.Column(db.DateTime(timezone=True), nullable=True)   # Store timezone-aware
    duration_minutes = db.Column(db.Integer, nullable=True) # Alternative or addition to end_time
    status = db.Column(db.String(20), nullable=False, default='draft') # draft, scheduled, live, ended, archived

    # Relationships
    creator = db.relationship('User', back_populates='exams_created')
    questions = db.relationship('Question', back_populates='exam', lazy='dynamic', cascade="all, delete-orphan")
    submissions = db.relationship('Submission', back_populates='exam', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Exam {self.title}>'

    # Add a property to check if the exam is currently live
    @property
    def is_live(self):
        now = datetime.now(timezone.utc)
        is_scheduled_or_live = self.status in ['scheduled', 'live']
        started = self.scheduled_start_time and self.scheduled_start_time <= now
        not_ended = not self.scheduled_end_time or now < self.scheduled_end_time

        # If status is already live, respect that unless explicitly ended by time
        if self.status == 'live':
            return not_ended

        # If scheduled, check time window
        if self.status == 'scheduled':
             return started and not_ended

        return False

    # You might need a background task or endpoint hit to update status from 'scheduled' to 'live' and 'live' to 'ended'


class Question(db.Model):
    __tablename__ = 'question'
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(20), nullable=False) # 'multiple_choice', 'short_answer', 'multiple_select'
    points = db.Column(db.Integer, default=1, nullable=False)
    order = db.Column(db.Integer, default=0, nullable=False) # For question order within the exam

    # Relationships
    exam = db.relationship('Exam', back_populates='questions')
    options = db.relationship('Option', back_populates='question', lazy='dynamic', cascade="all, delete-orphan", order_by='Option.id') # Keep options ordered if needed
    answers = db.relationship('Answer', back_populates='question', lazy='dynamic')

    def __repr__(self):
        return f'<Question {self.id} for Exam {self.exam_id}>'

class Option(db.Model): # For multiple choice / multiple select questions
    __tablename__ = 'option'
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    text = db.Column(db.String(500), nullable=False) # Increased length
    is_correct = db.Column(db.Boolean, default=False, nullable=False)

    # Relationships
    question = db.relationship('Question', back_populates='options')

    def __repr__(self):
        return f'<Option {self.id} for Question {self.question_id}>'

class Submission(db.Model):
    __tablename__ = 'submission'
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    submitted_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    score = db.Column(db.Float, nullable=True) # Calculated score (can be calculated on submission or later)
    time_started = db.Column(db.DateTime(timezone=True), nullable=True) # Track when student started
    time_finished = db.Column(db.DateTime(timezone=True), nullable=True) # Alias for submitted_at or separate if draft saves allowed

    # Relationships
    exam = db.relationship('Exam', back_populates='submissions')
    student = db.relationship('User', back_populates='submissions')
    answers = db.relationship('Answer', back_populates='submission', lazy='dynamic', cascade="all, delete-orphan")

    # Ensure a student can only submit once per exam
    __table_args__ = (db.UniqueConstraint('exam_id', 'student_id', name='_exam_student_uc'),)

    def __repr__(self):
        return f'<Submission {self.id} by Student {self.student_id} for Exam {self.exam_id}>'

class Answer(db.Model):
    __tablename__ = 'answer'
    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey('submission.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)

    # Store the answer itself
    answer_text = db.Column(db.Text, nullable=True) # For short answer type
    # Store selected option(s) - Use a separate table for multi-select if needed, or store JSON/CSV
    selected_option_id = db.Column(db.Integer, db.ForeignKey('option.id'), nullable=True) # For single MCQ

    # Relationships
    submission = db.relationship('Submission', back_populates='answers')
    question = db.relationship('Question', back_populates='answers')
    selected_option = db.relationship('Option', lazy='joined') # Eager load selected option if needed

    # Add a field to store if the answer was correct (evaluated)
    is_correct = db.Column(db.Boolean, nullable=True)
    points_awarded = db.Column(db.Float, nullable=True)

    def __repr__(self):
        return f'<Answer {self.id} for Question {self.question_id} in Submission {self.submission_id}>'