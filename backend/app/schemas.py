from marshmallow import fields, validate, ValidationError, validates_schema
from .extensions import ma
from .models import User, Exam, Question, Option, Submission, Answer

# --- Nested Schemas First ---

class UserBasicSchema(ma.SQLAlchemyAutoSchema):
    """Basic user info, safe to expose."""
    class Meta:
        model = User
        load_instance = True
        # Exclude sensitive fields
        exclude = ("password_hash", "created_at", "submissions", "exams_created")

class OptionSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Option
        load_instance = True
        include_fk = True # Include question_id

class OptionStudentSchema(ma.SQLAlchemyAutoSchema):
    """Option schema for students (hides is_correct)."""
    class Meta:
        model = Option
        load_instance = True
        include_fk = True
        exclude = ("is_correct",) # CRITICAL: Hide answer from student view

class QuestionSchema(ma.SQLAlchemyAutoSchema):
    options = ma.Nested(OptionSchema, many=True) # For teacher/full view
    class Meta:
        model = Question
        load_instance = True
        include_fk = True
        # exclude = ("answers",) # Exclude answers relationship by default if large

class QuestionStudentSchema(ma.SQLAlchemyAutoSchema):
    options = ma.Nested(OptionStudentSchema, many=True) # Use student-safe option schema
    class Meta:
        model = Question
        load_instance = True
        include_fk = True
        exclude = ("answers", "points") # Hide points during exam? Optional.

class AnswerSchema(ma.SQLAlchemyAutoSchema):
    selected_option = ma.Nested(OptionStudentSchema, only=("id", "text")) # Show basic info of selected option
    class Meta:
        model = Answer
        load_instance = True
        include_fk = True
        # Exclude submission link to prevent recursion if needed
        # exclude = ("submission",)

# --- Main Schemas ---

class ExamSchema(ma.SQLAlchemyAutoSchema):
    creator = ma.Nested(UserBasicSchema, only=("id", "username"))
    questions = ma.Nested(QuestionSchema, many=True)
    # Add calculated fields if needed, e.g., is_live status
    is_live = fields.Boolean(dump_only=True) # Use the model property

    class Meta:
        model = Exam
        load_instance = True
        include_fk = True
        # Exclude submissions by default for list views
        # exclude = ("submissions",)

class ExamStudentSchema(ma.SQLAlchemyAutoSchema):
    """Exam schema for students taking the exam."""
    creator = ma.Nested(UserBasicSchema, only=("id", "username"))
    questions = ma.Nested(QuestionStudentSchema, many=True) # Use student-safe question schema
    is_live = fields.Boolean(dump_only=True)

    class Meta:
        model = Exam
        load_instance = True
        # Only include fields relevant to the student taking the exam
        fields = ("id", "title", "description", "scheduled_start_time", "scheduled_end_time", "duration_minutes", "status", "creator", "questions", "is_live")
        # Alternatively, exclude fields: exclude = ("creator_id", "submissions", "created_at")


class SubmissionSchema(ma.SQLAlchemyAutoSchema):
    student = ma.Nested(UserBasicSchema)
    exam = ma.Nested(lambda: ExamSchema(only=("id", "title"))) # Basic exam info
    answers = ma.Nested(AnswerSchema, many=True)
    class Meta:
        model = Submission
        load_instance = True
        include_fk = True


# --- Input Validation Schemas ---

class RegisterSchema(ma.Schema):
    username = fields.Str(required=True, validate=validate.Length(min=3, max=80))
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=6))
    role = fields.Str(validate=validate.OneOf(["student", "teacher"]))

class LoginSchema(ma.Schema):
    username = fields.Str(required=True)
    password = fields.Str(required=True)

# --- Exam Creation/Update Schemas ---
class OptionCreateSchema(ma.Schema):
    text = fields.Str(required=True, validate=validate.Length(min=1, max=500))
    is_correct = fields.Bool(required=True)

class QuestionCreateSchema(ma.Schema):
    text = fields.Str(required=True)
    type = fields.Str(required=True, validate=validate.OneOf(['multiple_choice', 'short_answer', 'multiple_select']))
    points = fields.Int(missing=1, validate=validate.Range(min=0))
    order = fields.Int(missing=0)
    options = fields.List(fields.Nested(OptionCreateSchema), required=False) # Required only if type is MCQ/MS

    @validates_schema
    def validate_options(self, data, **kwargs):
        if data.get('type') in ['multiple_choice', 'multiple_select'] and not data.get('options'):
            raise ValidationError("Options are required for multiple_choice or multiple_select questions.", "options")
        if data.get('type') == 'multiple_choice':
            correct_options = [opt for opt in data.get('options', []) if opt.get('is_correct')]
            if len(correct_options) != 1:
                raise ValidationError("Multiple choice questions must have exactly one correct option.", "options")


class ExamCreateSchema(ma.Schema):
    title = fields.Str(required=True, validate=validate.Length(min=1, max=150))
    description = fields.Str(required=False, missing="")
    # Questions can be added separately or optionally included here
    # questions = fields.List(fields.Nested(QuestionCreateSchema), required=False)

class ExamUpdateSchema(ma.Schema):
    title = fields.Str(validate=validate.Length(min=1, max=150))
    description = fields.Str()
    # No status changes here, use schedule/publish endpoints

class ExamScheduleSchema(ma.Schema):
    # Expect ISO 8601 format strings from frontend
    scheduled_start_time = fields.DateTime(required=True, format='iso')
    scheduled_end_time = fields.DateTime(required=False, format='iso', allow_none=True)
    duration_minutes = fields.Int(required=False, validate=validate.Range(min=1), allow_none=True)

    @validates_schema
    def validate_times(self, data, **kwargs):
        start = data.get('scheduled_start_time')
        end = data.get('scheduled_end_time')
        duration = data.get('duration_minutes')

        if not end and not duration:
             raise ValidationError("Either scheduled_end_time or duration_minutes must be provided.")
        if end and start and end <= start:
            raise ValidationError("End time must be after start time.")
        if end and duration:
            # Optionally allow both, but maybe warn or prefer one?
            pass


# --- Submission Schemas ---
class AnswerSubmitSchema(ma.Schema):
    question_id = fields.Int(required=True)
    answer_text = fields.Str(required=False, allow_none=True) # For short answer
    selected_option_id = fields.Int(required=False, allow_none=True) # For MCQ

    @validates_schema
    def validate_answer_provided(self, data, **kwargs):
        if data.get('answer_text') is None and data.get('selected_option_id') is None:
            raise ValidationError("Either answer_text or selected_option_id must be provided.")
        # You might add further validation based on the actual question type fetched from DB

class SubmissionCreateSchema(ma.Schema):
    answers = fields.List(fields.Nested(AnswerSubmitSchema), required=True, validate=validate.Length(min=1))
    time_started = fields.DateTime(required=False, format='iso', allow_none=True) # Optional: Track start time