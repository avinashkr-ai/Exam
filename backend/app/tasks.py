# backend/app/tasks.py

import os
import time
import json
import logging
from celery import Celery
# NOTE: Do NOT import create_app at the top level here to avoid circular imports
from .models import db, Submission, SubmittedAnswer, Question, Result
import google.generativeai as genai

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create a Celery instance (will be configured by the app factory in __init__.py)
# The broker/backend URLs should be set via Flask app config loaded from .env
celery_app = Celery(__name__)


# Function to create app context for tasks
# This ensures tasks run within the Flask application context, having access to config, db, etc.
def create_task_app():
    """Creates a Flask app instance for the Celery task context."""
    # Import create_app *inside* the function to break the circular import
    from . import create_app
    app = create_app(os.getenv('FLASK_ENV') or 'default')
    app.app_context().push()
    # Celery configuration should ideally be updated when the main app is created (__init__.py)
    # If celery_app.conf.update(app.config) is reliably called in __init__.py,
    # you might not strictly need it here, but it doesn't hurt to ensure it's set.
    # celery_app.conf.update(app.config)
    return app


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60) # bind=True gives access to self (the task instance)
def evaluate_submission_task(self, submission_id):
    """
    Celery background task to evaluate a student's exam submission using Gemini API.

    Args:
        submission_id (int): The ID of the Submission record to evaluate.
    """
    app = create_task_app() # Create app context for this task run
    with app.app_context():
        logger.info(f"Starting evaluation for submission_id: {submission_id}")
        submission = Submission.query.get(submission_id)
        if not submission:
            logger.error(f"Submission {submission_id} not found.")
            return # Cannot proceed

        if submission.status == 'evaluated' or submission.status == 'evaluated_with_errors':
             logger.warning(f"Submission {submission_id} is already evaluated (status: {submission.status}). Skipping.")
             return # Avoid re-evaluation unless explicitly intended

        # Configure Gemini API
        api_key = app.config.get('GEMINI_API_KEY')
        if not api_key:
            logger.error(f"GEMINI_API_KEY not configured for submission {submission_id}.")
            submission.status = 'evaluation_failed' # Mark as failed
            db.session.commit()
            return # Cannot proceed

        try:
            genai.configure(api_key=api_key)
            # Consider making the model name configurable via app.config
            model = genai.GenerativeModel(app.config.get('GEMINI_MODEL_NAME', 'gemini-pro'))
            logger.info(f"Using Gemini model: {model.model_name}")
        except Exception as e:
             logger.error(f"Failed to configure Gemini for submission {submission_id}: {e}")
             submission.status = 'evaluation_failed'
             db.session.commit()
             return # Cannot proceed

        total_score = 0.0
        all_evaluations_successful = True # Track if any part fails

        # Fetch answers and their associated questions efficiently
        # joinedload ensures the related Question object is fetched in the same query
        answers = SubmittedAnswer.query.filter_by(submission_id=submission_id)\
                                     .options(db.joinedload(SubmittedAnswer.question))\
                                     .all()

        if not answers:
             logger.warning(f"No answers found for submission {submission_id}. Marking as evaluated with 0 score.")
             submission.total_score = 0.0
             submission.status = 'evaluated' # Or perhaps a specific status like 'evaluated_empty'
             db.session.commit()
             return

        # Process each answer
        for answer in answers:
            question = answer.question
            if not question:
                logger.warning(f"Question data missing for answer ID {answer.id} in submission {submission_id}, skipping this answer.")
                all_evaluations_successful = False # Mark as problematic
                continue

            # --- Evaluation Logic ---
            evaluated_mark = 0.0
            feedback = None
            evaluation_method = "skipped" # Track how evaluation was done

            # --- Gemini Evaluation for specific types ---
            if question.question_type in ['short_answer', 'essay'] and answer.student_answer_text and answer.student_answer_text.strip():
                evaluation_method = "gemini"
                # --- !!! CRITICAL: PROMPT ENGINEERING !!! ---
                prompt = f"""
                Objective: Evaluate the student's answer based on the provided question and criteria. Assign a score between 0 and {question.points}.

                Question:
                {question.question_text}

                Maximum Points: {question.points}

                Marking Criteria / Expected Context (Use this to guide scoring):
                {question.correct_answer_or_criteria or 'Evaluate based on general correctness, relevance, and clarity.'}

                Student's Answer:
                {answer.student_answer_text}

                Instructions:
                1. Analyze the student's answer for correctness, completeness, relevance to the question, and adherence to any provided criteria.
                2. Determine a fair score based on the analysis, ensuring it does not exceed {question.points}.
                3. Provide a brief, constructive feedback explaining the score.
                4. Respond ONLY with a valid JSON object containing the 'score' (float or integer) and 'feedback' (string) keys. Example: {{"score": {question.points}, "feedback": "Excellent understanding shown."}}

                JSON Response:
                """
                logger.info(f"Submitting Q{question.id} (AnsID:{answer.id}, SubID:{submission_id}) to Gemini.")
                try:
                    # Consider adding safety_settings if needed
                    # safety_settings = [...]
                    # response = model.generate_content(prompt, safety_settings=safety_settings)
                    response = model.generate_content(prompt)

                    # --- !!! CRITICAL: RESPONSE PARSING & VALIDATION !!! ---
                    response_text = response.text.strip().replace('```json', '').replace('```', '').strip()
                    logger.debug(f"Gemini raw response for Q{question.id}: {response_text}")

                    try:
                        eval_result = json.loads(response_text)
                        score_raw = eval_result.get('score')
                        feedback = eval_result.get('feedback', 'No feedback provided by AI.') # Default feedback

                        # Validate score type and range
                        if isinstance(score_raw, (int, float)):
                            score = float(score_raw)
                            if 0 <= score <= question.points:
                                evaluated_mark = score
                                logger.info(f"Gemini evaluation successful for Q{question.id}: Score={evaluated_mark}")
                            else:
                                logger.warning(f"Score {score} from Gemini for Q{question.id} is out of range (0-{question.points}). Clamping score.")
                                evaluated_mark = max(0.0, min(float(question.points), score)) # Clamp score
                                feedback += f" (Note: Original AI score {score} was outside the valid range and was adjusted.)"
                                all_evaluations_successful = False # Indicate potential issue
                        else:
                            logger.warning(f"Invalid score type received from Gemini for Q{question.id}: {score_raw} ({type(score_raw)}). Defaulting to 0.")
                            evaluated_mark = 0.0
                            feedback = f"Evaluation Error: Invalid score type received ({score_raw}). {feedback or ''}".strip()
                            all_evaluations_successful = False

                    except json.JSONDecodeError as json_err:
                        logger.error(f"Failed to parse Gemini JSON response for Q{question.id}: {json_err}. Response was: {response_text}")
                        evaluated_mark = 0.0
                        feedback = "Evaluation Error: Failed to parse AI response."
                        all_evaluations_successful = False
                    except Exception as parse_err:
                        logger.error(f"Error processing Gemini response content for Q{question.id}: {parse_err}")
                        evaluated_mark = 0.0
                        feedback = "Evaluation Error: Unexpected issue processing AI response content."
                        all_evaluations_successful = False

                except Exception as api_err:
                    logger.error(f"Gemini API call failed for Q{question.id} during submission {submission_id}: {api_err}")
                    # Use Celery's retry mechanism
                    try:
                        logger.warning(f"Retrying task for submission {submission_id} due to API error (attempt {self.request.retries + 1}/{self.max_retries}).")
                        # The 'exc' argument passes the exception to the next retry attempt if needed
                        self.retry(exc=api_err, countdown=int(self.default_retry_delay * (1.5 ** self.request.retries))) # Exponential backoff
                        return # Stop current execution after scheduling retry
                    except self.MaxRetriesExceededError:
                        logger.error(f"Max retries exceeded for submission {submission_id}. Marking submission as failed.")
                        submission.status = 'evaluation_failed'
                        db.session.commit()
                        return # Stop processing this submission entirely

                # --- Rate limiting delay ---
                # Adjust sleep time based on Gemini API quotas and your expected load
                # Consider more sophisticated rate limiting if needed (e.g., using Redis)
                time.sleep(app.config.get('GEMINI_API_DELAY', 1.5)) # Configurable delay (default 1.5s)

            # --- Auto-grading for Multiple Choice Questions (MCQ) ---
            elif question.question_type == 'mcq':
                evaluation_method = "auto_mcq"
                correct_answer = question.correct_answer_or_criteria
                student_answer = answer.student_answer_text

                if correct_answer and student_answer:
                    # Simple case-insensitive comparison, trim whitespace
                    if student_answer.strip().lower() == correct_answer.strip().lower():
                        evaluated_mark = float(question.points)
                        feedback = "Correct"
                    else:
                        evaluated_mark = 0.0
                        feedback = f"Incorrect. The correct answer was: {correct_answer}"
                elif not student_answer:
                     evaluated_mark = 0.0
                     feedback = "Not answered."
                else: # Correct answer not defined in DB
                     evaluated_mark = 0.0
                     feedback = "Cannot auto-grade: Correct answer not defined for this question."
                     logger.warning(f"MCQ Question {question.id} lacks a correct answer in the database.")
                     all_evaluations_successful = False # Cannot reliably grade

            # --- Placeholder for other question types ---
            # elif question.question_type == 'some_other_type':
            #    evaluation_method = "custom_logic"
            #    # Implement specific logic here
            #    pass

            else: # Question type not handled or answer was empty for Gemini types
                logger.info(f"Skipping evaluation for Q{question.id} (Type: {question.question_type}, Answer Empty: {not answer.student_answer_text})")
                evaluated_mark = 0.0
                feedback = "Evaluation skipped (e.g., unsupported type or no answer provided)."
                # Don't necessarily mark this as unsuccessful unless it's an error state

            # --- Store the Result ---
            # Check if a result already exists for this answer (e.g., from a previous failed run)
            existing_result = Result.query.filter_by(submission_id=submission.id, question_id=question.id).first()
            if existing_result:
                 logger.warning(f"Updating existing result for Q{question.id}, SubID {submission.id}")
                 existing_result.evaluated_mark = evaluated_mark
                 existing_result.evaluation_feedback = feedback
                 existing_result.evaluated_at = db.func.now() # Update timestamp
            else:
                 result = Result(
                     submission_id=submission.id,
                     student_id=submission.student_id,
                     exam_id=submission.exam_id,
                     question_id=question.id,
                     evaluated_mark=evaluated_mark,
                     evaluation_feedback=feedback
                     # evaluated_at defaults to now()
                 )
                 db.session.add(result)

            total_score += evaluated_mark
            # Flush session periodically? Maybe not needed unless very long exams.
            # if i % 10 == 0: db.session.flush()

        # --- Finalize Submission Status ---
        try:
            submission.total_score = total_score
            submission.status = 'evaluated' if all_evaluations_successful else 'evaluated_with_errors'
            db.session.commit()
            logger.info(f"Evaluation complete for submission_id: {submission_id}. Total Score: {total_score}. Final Status: {submission.status}")
        except Exception as db_err:
             logger.error(f"Failed to update final submission status/score for {submission_id}: {db_err}")
             db.session.rollback()
             # Consider retrying the final commit or marking as failed
             try:
                 logger.warning(f"Retrying final commit for submission {submission_id}...")
                 self.retry(exc=db_err, countdown=15)
             except self.MaxRetriesExceededError:
                 logger.error(f"Max retries exceeded trying to save final status for {submission_id}. Leaving status potentially inconsistent.")
                 # The status might remain 'evaluating' or partially updated. Manual check might be needed.


# Example of how to potentially add other tasks
# @celery_app.task
# def notify_student_of_results(submission_id):
#     app = create_task_app()
#     with app.app_context():
#         # Logic to fetch submission details and send an email/notification
#         logger.info(f"Placeholder: Notifying student about results for submission {submission_id}")
#         pass