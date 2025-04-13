# app/services/ai_evaluation.py
import google.generativeai as genai
import os
import json
from tenacity import retry, stop_after_attempt, wait_random_exponential, RetryError # Added RetryError
from config import Config # Use Config consistently

# Configure Gemini Client
try:
    genai.configure(api_key=Config.GEMINI_API_KEY)
except Exception as e:
    print(f"FATAL: Failed to configure Gemini API: {e}")
    # Depending on app structure, might want to raise to prevent app start
    # raise RuntimeError("Gemini API key configuration failed") from e

# Configure the generative model
# Use Gemini 1.5 Flash if available and suitable, otherwise fallback to Pro
MODEL_NAME = "gemini-1.5-flash-latest" # Prioritize Flash
# MODEL_NAME = "gemini-pro" # Fallback or if Flash isn't available/performing well

generation_config = {
    "temperature": 0.3, # Slightly lower temp for more consistent evaluation
    "top_p": 1,
    "top_k": 32,
    "max_output_tokens": 300, # Increased slightly for potentially longer feedback
    # Ensure response_mime_type is supported by the model if forcing JSON
    # "response_mime_type": "application/json", # Try this if model supports it
}

safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

# Initialize the model (handle potential errors)
try:
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        generation_config=generation_config,
        safety_settings=safety_settings
    )
    print(f"Gemini model '{MODEL_NAME}' initialized successfully.")
except Exception as e:
    print(f"ERROR: Failed to initialize Gemini model '{MODEL_NAME}': {e}")
    # Fallback or define behavior if model init fails
    model = None # Mark model as unavailable

# Add retry mechanism for API calls
@retry(wait=wait_random_exponential(min=1, max=30), stop=stop_after_attempt(3))
def generate_gemini_response_with_retry(prompt):
    """Generates content using the configured Gemini model with retries."""
    if not model:
        raise RuntimeError("Gemini model is not initialized.")
    try:
        response = model.generate_content(prompt)
        # Add safety check - Did the response get blocked?
        if not response.parts:
             # Check finish_reason if available (might indicate safety block)
             finish_reason = getattr(response, 'prompt_feedback', None)
             block_reason = getattr(finish_reason, 'block_reason', None) if finish_reason else None
             if block_reason:
                 raise ValueError(f"Gemini response blocked due to safety settings: {block_reason}")
             else:
                 raise ValueError("Gemini response was empty or incomplete.")

        return response.text
    except Exception as e:
        print(f"Gemini API call attempt failed: {e}")
        # Add specific checks if needed (e.g., quota errors)
        # if "quota" in str(e).lower(): raise QuotaError(...)
        raise # Re-raise to trigger tenacity retry

def parse_evaluation_response(text_response, max_marks):
    """
    Parses the text response from Gemini, expecting a specific format.
    Improved robustness compared to simple line splitting.
    """
    try:
        # Attempt 1: Assume strict JSON output (if using response_mime_type or prompt enforces it)
        try:
            # Clean potential markdown code fences
            if text_response.strip().startswith("```json"):
                text_response = text_response.strip()[7:-3].strip()
            elif text_response.strip().startswith("```"):
                 text_response = text_response.strip()[3:-3].strip()

            data = json.loads(text_response)
            marks = data.get("marks_awarded")
            feedback = data.get("feedback")

            if isinstance(marks, (int, float)) and isinstance(feedback, str):
                 # Validate marks range AFTER parsing
                 if not (0 <= marks <= max_marks):
                    raise ValueError(f"Parsed marks '{marks}' are outside the valid range [0, {max_marks}]")
                 print(f"Successfully parsed JSON response. Marks: {marks}")
                 return float(marks), feedback.strip()
            else:
                 raise ValueError("Parsed JSON has incorrect types for 'marks_awarded' or 'feedback'")

        except json.JSONDecodeError:
            print("Gemini response was not valid JSON. Attempting structured text parsing...")
            # Attempt 2: Parse the structured text format as fallback
            marks = None
            feedback = ""
            marks_line_prefix = "Marks:"
            feedback_line_prefix = "Feedback:"

            lines = text_response.strip().split('\n')
            marks_found = False
            feedback_started = False

            processed_lines = [] # Collect lines relevant to parsing
            for line in lines:
                 line_stripped = line.strip()
                 if not line_stripped: continue # Skip empty lines

                 processed_lines.append(line_stripped)

                 if line_stripped.startswith(marks_line_prefix):
                     marks_str = line_stripped[len(marks_line_prefix):].strip()
                     try:
                         marks = float(marks_str)
                         marks_found = True
                         print(f"Found marks line: '{line_stripped}', parsed marks: {marks}")
                     except ValueError:
                         print(f"Warning: Could not parse marks value from line: '{line_stripped}'")
                         # Continue searching in case marks line appears later or is malformed
                 elif line_stripped.startswith(feedback_line_prefix):
                     # Start collecting feedback from this line onwards
                     feedback = line_stripped[len(feedback_line_prefix):].strip()
                     feedback_started = True
                     print(f"Found feedback line: '{line_stripped}'")
                 elif feedback_started:
                     # Append subsequent lines to feedback
                     feedback += "\n" + line_stripped

            if marks is None or not marks_found:
                 raise ValueError(f"Could not find or parse '{marks_line_prefix}' line in the response.")
            if not feedback.strip(): # Check if feedback is empty after processing
                 raise ValueError(f"Could not find or parse '{feedback_line_prefix}' content in the response.")

            # Final validation for parsed structured text
            if not (0 <= marks <= max_marks):
                 raise ValueError(f"Parsed marks '{marks}' from structured text are outside the valid range [0, {max_marks}]")

            print(f"Successfully parsed structured text response. Marks: {marks}")
            return float(marks), feedback.strip()

    except ValueError as ve:
         # Handle parsing errors (JSON or structured text)
         error_msg = f"Failed to parse Gemini response: {ve}. Raw response:\n---\n{text_response}\n---"
         print(error_msg)
         raise ValueError(error_msg) # Re-raise to be caught by the main function

    except Exception as e:
        # Catch any other unexpected errors during parsing
        error_msg = f"Unexpected error parsing Gemini response: {e}. Raw response:\n---\n{text_response}\n---"
        print(error_msg)
        raise ValueError(error_msg) # Re-raise


def evaluate_response_with_gemini(question_text, student_answer, word_limit, max_marks, question_type):
    """
    Evaluates a student's answer using Gemini with retry logic and improved parsing.

    Returns:
        tuple: (marks_awarded, feedback) or (None, error_message) if evaluation fails.
    """
    if not model:
         return None, "Gemini model not initialized. Cannot perform evaluation."

    # --- Construct the Prompt ---
    # Focused on clear instructions and requesting a specific output format.
    # Consider adding negative constraints (e.g., "Do not include introductory phrases...")
    # Using JSON format request for better parsing robustness.
    prompt_parts = [
        f"You are an AI evaluating a student's exam answer. The question is worth a maximum of {max_marks} marks.",
        f"Question: {question_text}",
    ]
    if word_limit:
        prompt_parts.append(f"Approximate Word Limit: {word_limit} words.")
    prompt_parts.append(f"Question Type: {question_type}")
    prompt_parts.append(f"Student's Answer: '{student_answer}'")

    prompt_parts.append("\nEvaluation Criteria:")
    prompt_parts.append("- Relevance and Accuracy: Is the answer correct and directly addresses the question?")
    prompt_parts.append("- Coherence and Clarity: Is the answer well-structured and understandable?")
    prompt_parts.append("- Grammar and Spelling: Assess the quality of writing.")
    if word_limit:
        prompt_parts.append(f"- Word Count Adherence: Consider if the answer respects the ~{word_limit} word limit (moderate deviation is acceptable).")

    # Explicitly ask for JSON output
    prompt_parts.append("\nOutput Instructions:")
    prompt_parts.append("Provide your evaluation ONLY in the following JSON format. Do not add any text before or after the JSON object:")
    prompt_parts.append("""
{
  "marks_awarded": <float between 0.0 and """ + str(float(max_marks)) + """, rounded to 1 decimal place if necessary>,
  "feedback": "<string containing constructive feedback (2-4 sentences) explaining the marks, mentioning strengths and areas for improvement>"
}""")
    prompt_parts.append(f"IMPORTANT: Ensure 'marks_awarded' is a number between 0 and {max_marks}, and 'feedback' is a non-empty string.")

    prompt = "\n".join(prompt_parts)

    # --- Call Gemini API ---
    try:
        print(f"--- Sending Prompt to Gemini for Q: {question_text[:50]}... ---")
        # print(prompt) # Uncomment for detailed prompt debugging
        raw_response = generate_gemini_response_with_retry(prompt)
        print(f"--- Received Raw Response from Gemini ---")
        # Limit printing potentially long responses in production logs
        print(raw_response[:500] + ("..." if len(raw_response) > 500 else ""))
        print("--- End Raw Response ---")

        # --- Process Response ---
        marks, feedback = parse_evaluation_response(raw_response, max_marks)
        return marks, feedback

    except RetryError as e:
        error_msg = f"Gemini API call failed after multiple retries: {e}"
        print(error_msg)
        return None, error_msg
    except ValueError as ve:
        # Catch parsing errors or safety blocks raised from helper functions
        error_msg = f"Error processing Gemini response: {ve}"
        # The error message from parse_evaluation_response already contains details
        # print(error_msg) # Already printed in the parser
        return None, error_msg # Pass the detailed error message back
    except Exception as e:
        # Catch any other unexpected errors (e.g., network issues not caught by retry, unexpected API errors)
        error_msg = f"An unexpected error occurred during AI evaluation: {e}"
        print(error_msg)
        # Optionally log traceback: import traceback; traceback.print_exc()
        return None, error_msg