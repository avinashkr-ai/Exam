# app/services/ai_evaluation.py

import google.generativeai as genai
import os
import json
from tenacity import retry, stop_after_attempt, wait_random_exponential, RetryError
from config import Config # Use Config for API Key

# Configure Gemini Client using the API key from Config
try:
    # Ensure the API key is loaded correctly
    api_key = Config.GEMINI_API_KEY
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set in the environment or .env file.")
    genai.configure(api_key=api_key)
    print("Gemini API configured successfully.")
except ValueError as ve:
    print(f"FATAL CONFIGURATION ERROR: {ve}")
    # Depending on desired behavior, you might exit or raise a more specific exception
    # For now, we'll print the error and let model initialization fail later if API key is missing
    pass
except Exception as e:
    print(f"FATAL: Unexpected error configuring Gemini API: {e}")
    # Handle other potential configuration errors
    pass

# Configure the generative model details
# ***** CORRECTED MODEL NAME *****
MODEL_NAME = "gemini-1.5-flash-latest"
# MODEL_NAME = "gemini-pro" # Fallback option (if needed)

generation_config = {
    "temperature": 0.3,       # Lower temperature for more deterministic evaluation
    "top_p": 1,
    "top_k": 32,
    "max_output_tokens": 400, # Slightly increased for potentially richer feedback
    # "response_mime_type": "application/json", # Keep commented unless sure model supports it reliably
}

# Define safety settings to block potentially harmful content
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

# Initialize the generative model instance
model = None # Initialize model as None
try:
    # Check if API key was successfully loaded before attempting initialization
    if Config.GEMINI_API_KEY:
        print(f"--- Initializing Gemini Model: {MODEL_NAME} ---") # Added print statement
        model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        print(f"Gemini model '{MODEL_NAME}' initialized successfully.")
    else:
        # This condition is met if the API key was missing during configuration
        print(f"ERROR: Cannot initialize Gemini model '{MODEL_NAME}' because GEMINI_API_KEY is missing.")

except Exception as e:
    # Catch errors during model initialization (e.g., invalid model name, API issues)
    # ***** MORE SPECIFIC ERROR LOGGING *****
    print(f"ERROR: Failed to initialize Gemini model '{MODEL_NAME}'. Check if the model name is valid and the API key is correct. Error: {e}")
    # model remains None

# Retry decorator for robustness against transient API issues
@retry(wait=wait_random_exponential(min=1, max=30), stop=stop_after_attempt(3))
def generate_gemini_response_with_retry(prompt):
    """Generates content using the configured Gemini model with retries."""
    if not model:
        # Fail fast if the model couldn't be initialized
        raise RuntimeError("Gemini model is not available or not initialized.")
    try:
        print("--- Attempting to generate content with Gemini ---")
        response = model.generate_content(prompt)
        # Check for blocked responses or empty content
        if not response.parts:
             feedback = getattr(response, 'prompt_feedback', None)
             block_reason = getattr(feedback, 'block_reason', None) if feedback else None
             if block_reason:
                 # ***** CLEARER BLOCK REASON LOGGING *****
                 print(f"!!! Gemini response blocked by safety settings. Reason: {block_reason}")
                 raise ValueError(f"Gemini response blocked due to safety settings: {block_reason}")
             else:
                 # Check if candidate data exists but is empty (less common)
                 candidates = getattr(response, 'candidates', [])
                 if not candidates or not getattr(candidates[0], 'content', None):
                    print("!!! Gemini response appears empty or incomplete (no parts/content).")
                    raise ValueError("Gemini response was empty or incomplete (no parts/content).")
                 else:
                     # Handle cases where parts is empty but candidates might have info (unlikely with default settings)
                     # For simplicity, we primarily rely on response.text below which uses parts.
                     pass # Fall through to text extraction attempt

        # Extract text content
        response_text = response.text
        print("--- Successfully received response text from Gemini ---")
        return response_text

    except ValueError as ve:
        # Re-raise ValueErrors related to blocking or empty responses
        print(f"!!! Gemini Value Error: {ve}")
        raise
    except Exception as e:
        # Catch other API call errors (network, authentication, etc.)
        print(f"!!! Gemini API call attempt failed: {e}")
        # Consider logging the prompt here for debugging, carefully handling sensitive data
        # print(f"Failed prompt snippet: {prompt[:200]}...")
        raise # Re-raise to trigger tenacity retry or fail after retries

def parse_evaluation_response(text_response, max_marks):
    """
    Parses the text response from Gemini, expecting JSON or a specific structured format.
    Returns: (marks, feedback) or raises ValueError on failure.
    """
    if not text_response or not text_response.strip():
        raise ValueError("Received empty text response from Gemini.")

    cleaned_response = text_response.strip()

    # Attempt 1: Parse as strict JSON
    try:
        # Remove potential markdown code fences (```json ... ``` or ``` ... ```)
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:-3].strip()
        elif cleaned_response.startswith("```"):
            cleaned_response = cleaned_response[3:-3].strip()

        data = json.loads(cleaned_response)
        marks = data.get("marks_awarded")
        feedback = data.get("feedback")

        # Validate types and marks range
        if isinstance(marks, (int, float)) and isinstance(feedback, str) and feedback.strip():
             validated_marks = float(marks)
             if not (0 <= validated_marks <= max_marks):
                # ***** CLEARER RANGE ERROR *****
                print(f"!!! Parsed marks '{validated_marks}' are outside the valid range [0, {max_marks}]")
                raise ValueError(f"Parsed marks '{validated_marks}' are outside the valid range [0, {max_marks}]")
             print(f"Successfully parsed JSON response. Marks: {validated_marks}")
             return validated_marks, feedback.strip()
        else:
             missing_or_invalid = []
             if not isinstance(marks, (int, float)): missing_or_invalid.append("'marks_awarded' (number)")
             if not isinstance(feedback, str) or not feedback.strip(): missing_or_invalid.append("'feedback' (non-empty string)")
             # ***** CLEARER TYPE ERROR *****
             print(f"!!! Parsed JSON has missing or invalid types for: {', '.join(missing_or_invalid)}. JSON: {data}")
             raise ValueError(f"Parsed JSON has missing or invalid types for: {', '.join(missing_or_invalid)}")

    except json.JSONDecodeError:
        print("--- Gemini response was not valid JSON. Attempting structured text parsing... ---")
        # Attempt 2: Parse structured text fallback (Marks: ..., Feedback: ...)
        marks = None
        feedback_lines = []
        marks_line_prefix = "Marks:"
        feedback_line_prefix = "Feedback:"
        marks_found = False
        in_feedback_section = False

        lines = cleaned_response.split('\n')
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped: continue

            if line_stripped.startswith(marks_line_prefix) and not marks_found:
                marks_str = line_stripped[len(marks_line_prefix):].strip()
                try:
                    marks = float(marks_str)
                    # Validate marks range immediately
                    if not (0 <= marks <= max_marks):
                        # ***** CLEARER RANGE ERROR (Fallback) *****
                        print(f"!!! Parsed marks '{marks}' from structured text are outside valid range [0, {max_marks}]")
                        raise ValueError(f"Parsed marks '{marks}' from structured text are outside valid range [0, {max_marks}]")
                    marks_found = True
                    print(f"Found marks line, parsed marks: {marks}")
                except ValueError as e:
                    print(f"Warning: Could not parse marks value from line: '{line_stripped}'. Error: {e}")
                    # Reset marks if parsing failed, continue searching
                    marks = None
                    marks_found = False
            elif line_stripped.startswith(feedback_line_prefix):
                # Start collecting feedback from this line onwards
                feedback_lines.append(line_stripped[len(feedback_line_prefix):].strip())
                in_feedback_section = True
                print("Found feedback start line.")
            elif in_feedback_section:
                # Append subsequent non-empty lines to feedback
                feedback_lines.append(line_stripped)

        # Assemble feedback and validate results
        final_feedback = "\n".join(feedback_lines).strip()

        if not marks_found:
             # ***** CLEARER FALLBACK ERROR *****
             print(f"!!! Could not find/parse valid '{marks_line_prefix}' line in range [0, {max_marks}] in fallback.")
             raise ValueError(f"Could not find or parse a valid '{marks_line_prefix}' line within range [0, {max_marks}].")
        if not final_feedback:
             # ***** CLEARER FALLBACK ERROR *****
             print(f"!!! Could not find/parse '{feedback_line_prefix}' content in fallback.")
             raise ValueError(f"Could not find or parse '{feedback_line_prefix}' content.")

        print(f"Successfully parsed structured text response. Marks: {marks}")
        return marks, final_feedback # Already validated marks range

    except ValueError as ve:
         # Re-raise ValueErrors from parsing or validation
         error_msg = f"Failed to parse Gemini response: {ve}. Raw response snippet:\n---\n{text_response[:300]}...\n---"
         print(f"!!! {error_msg}") # Print detailed message before raising
         raise ValueError(error_msg) # Keep original error type

    except Exception as e:
        # Catch any other unexpected errors during parsing
        error_msg = f"Unexpected error parsing Gemini response: {e}. Raw response snippet:\n---\n{text_response[:300]}...\n---"
        print(f"!!! {error_msg}") # Print detailed message before raising
        raise ValueError(error_msg) # Wrap as ValueError


def evaluate_response_with_gemini(question_text, student_answer, word_limit, max_marks, question_type):
    """
    Evaluates a student's answer using Gemini, handling retries and parsing.

    Returns:
        tuple: (marks_awarded, feedback) on success.
        tuple: (None, error_message) on failure (API error, parsing error, etc.).
    """
    if not model:
         # Added check here as well for safety
         print("!!! AI EVALUATION SKIPPED: Gemini model not initialized. Check logs for initialization errors. !!!")
         return None, "AI Evaluation Service Error: Model not available."

    # Ensure max_marks is a number for prompt generation
    try:
        max_marks_float = float(max_marks)
    except (ValueError, TypeError):
         # ***** CLEARER MARKS ERROR *****
         print(f"!!! Invalid max_marks value '{max_marks}' provided for evaluation.")
         return None, f"Invalid max_marks value '{max_marks}' provided for evaluation."

    # --- Construct the Prompt ---
    prompt_parts = [
        f"You are an AI Assistant evaluating an exam answer.",
        f"Maximum Marks for this question: {max_marks_float}",
        f"Question Type: {question_type}",
        f"Question: {question_text}",
    ]
    if word_limit:
        try:
            wl = int(word_limit)
            if wl > 0:
               prompt_parts.append(f"Suggested Word Limit: Approximately {wl} words.")
        except (ValueError, TypeError):
            print(f"Warning: Invalid word_limit '{word_limit}' ignored during prompt construction.")

    # Include student answer safely
    prompt_parts.append(f"Student's Answer:\n```\n{student_answer if student_answer else '(No answer provided)'}\n```") # Use code fence

    # Define evaluation criteria clearly
    prompt_parts.append("\nEvaluation Criteria:")
    prompt_parts.append("- Relevance & Accuracy: How well does the answer address the question? Is it factually correct?")
    prompt_parts.append("- Completeness: Does the answer cover the key aspects required by the question?")
    prompt_parts.append("- Coherence & Clarity: Is the answer well-organized, easy to understand, with proper grammar?")
    try: # Add try-except for word limit check during criteria description
        if word_limit and int(word_limit) > 0:
            prompt_parts.append(f"- Word Count: Consider if the answer is reasonably close to the ~{int(word_limit)} word limit. Significant deviations might affect clarity or completeness.")
    except (ValueError, TypeError):
        pass # Ignore invalid word limit here too

    # Explicitly request JSON output format
    prompt_parts.append("\nOutput Format Instructions:")
    prompt_parts.append("Provide your evaluation ONLY in the following valid JSON format. Do not include any text before or after the JSON object:")
    prompt_parts.append(f"""
```json
{{
  "marks_awarded": <float number between 0.0 and {max_marks_float}>,
  "feedback": "<string containing constructive feedback (2-4 sentences) explaining the score, mentioning strengths and areas for improvement. Be specific.>"
}}
```""")
    prompt_parts.append(f"IMPORTANT: Ensure 'marks_awarded' is a number from 0 to {max_marks_float} (inclusive), and 'feedback' is a non-empty string detailing the rationale.")

    prompt = "\n\n".join(prompt_parts) # Use double newline for better separation

    # --- Call Gemini API and Process Response ---
    try:
        print(f"--- Sending Prompt to Gemini for evaluation (Max Marks: {max_marks_float}) ---")
        # print(f"Prompt Snippet:\n{prompt[:500]}...\n---") # Uncomment for debugging

        raw_response = generate_gemini_response_with_retry(prompt)

        print(f"--- Received Raw Response from Gemini ---\n{raw_response[:500]}{'...' if len(raw_response) > 500 else ''}\n--- End Raw Response ---")

        # Parse the response using the dedicated function
        marks, feedback = parse_evaluation_response(raw_response, max_marks_float)
        print(f"--- Evaluation successful. Marks: {marks}, Feedback: {feedback[:100]}... ---")
        return marks, feedback

    except RetryError as e:
        # Error after multiple retries
        error_msg = f"AI Evaluation Failed: API call unsuccessful after multiple retries. Last error: {e}"
        print(f"!!! {error_msg}")
        return None, error_msg
    except ValueError as ve:
        # Error during response parsing or validation (includes safety blocks)
        error_msg = f"AI Evaluation Failed: Error processing AI response. Details: {ve}"
        # Logging is handled within parse_evaluation_response or generate_gemini_response_with_retry
        print(f"!!! AI Evaluation Value Error: {ve}") # Ensure it's logged here too
        return None, error_msg # Pass the detailed error message back
    except RuntimeError as rterr:
        # Handle case where model wasn't initialized
         error_msg = f"AI Evaluation Failed: {rterr}"
         print(f"!!! {error_msg}")
         return None, error_msg
    except Exception as e:
        # Catch any other unexpected errors during the process
        error_msg = f"AI Evaluation Failed: An unexpected error occurred. Error: {type(e).__name__}: {e}"
        print(f"!!! {error_msg}")
        # Optionally log full traceback for unexpected errors
        import traceback; traceback.print_exc()
        return None, error_msg