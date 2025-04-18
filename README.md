Here is the updated API documentation, incorporating the details from your code, the previous documentation structure, and the specific requirements we discussed (like naive UTC, JWT claims, Admin CLI creation, and specific endpoint responses).

---

## Online Exam Portal API Documentation

**Version:** 1.1 *(Updated based on code review and clarifications)*
**Base URL (Development):** `http://localhost:5000` (Replace with your deployment URL)

### Introduction

This document provides details on the RESTful API endpoints for the Online Exam Portal. The API facilitates interactions for Administrators, Teachers, and Students, enabling exam management, participation, and evaluation.

### Authentication

*   **Method:** JSON Web Tokens (JWT) using `Flask-JWT-Extended`.
*   **Login:** Users obtain a JWT by sending valid credentials to `POST /auth/login`.
*   **Token Usage:** The obtained `access_token` must be included in the `Authorization` header for all protected endpoints using the `Bearer` scheme:
    ```
    Authorization: Bearer <your_access_token>
    ```
*   **Token Claims:** The JWT payload contains a `user_info` claim dictionary: `{"id": user_id, "role": "RoleName"}` (e.g., `"Admin"`, `"Teacher"`, `"Student"`). Backend decorators use this `id` and `role` for authorization checks.
*   **Account Verification:** Most endpoints (excluding Admin login/actions and initial registration) require the user's account to be verified (`is_verified=True` in the `users` table).
    *   Admins are created verified via the CLI.
    *   Teachers and Students require Admin approval via `POST /admin/users/verify/{user_id}` after registration. Unverified users attempting login will receive a `403 Forbidden` error.

### Data Formats

*   **Request/Response Bodies:** Primarily JSON (`application/json`).
*   **Datetimes:**
    *   All datetime values exchanged with the API (in request bodies or response bodies) **must be represented as strings in ISO 8601 format and assumed to be naive UTC**.
    *   **Example Request:** `"scheduled_time_utc": "2025-04-20T10:00:00"`
    *   **Example Response:** `"created_at_utc": "2025-04-17T15:30:00"`
    *   The server stores and processes all times internally as naive Python `datetime` objects representing UTC (`datetime.utcnow()`).
    *   Response datetime fields are consistently named with a `_utc` suffix for clarity.
    *   **The frontend client is solely responsible for converting these naive UTC times to the user's local timezone for display.**

### Error Handling

Common HTTP status codes:

*   `200 OK`: Request successful. Response body usually contains data.
*   `201 Created`: Resource created successfully. Response body contains details of the created resource.
*   `400 Bad Request`: Invalid request format, missing required fields, invalid data types, or validation failed (e.g., invalid role, negative duration, already verified user). Response body contains `{"msg": "Error description"}`.
*   `401 Unauthorized`: Invalid, expired, missing, or malformed JWT. Failed JWT verification.
*   `403 Forbidden`: Authenticated user lacks permission for the requested action. Reasons include:
    *   Incorrect role (e.g., Student trying Teacher endpoint).
    *   Account not verified (when required).
    *   Trying to access/modify data not owned by the user (e.g., Teacher modifying another Teacher's exam).
    *   Attempting forbidden actions (e.g., Admin deleting self).
    *   Attempting to access an exam outside its active window.
    *   Attempting to submit/retake an already submitted exam.
*   `404 Not Found`: Requested resource (user, exam, question, response) does not exist.
*   `409 Conflict`: Resource creation failed because a unique constraint would be violated (e.g., registering with an existing email).
*   `500 Internal Server Error`: An unexpected error occurred on the server (e.g., database error during commit, unhandled exception in code). Response body may contain `{"msg": "Error description"}`. Check server logs.
*   `503 Service Unavailable`: A required external service is down or unavailable (e.g., the AI Evaluation service failed to initialize or respond).

---

### Admin Account Creation

**Important:** Administrator accounts **cannot** be created via the `/auth/register` API endpoint. They must be created using the command-line interface (CLI) on the server where the backend application is running.

**Steps:**

1.  Ensure the database is set up and migrations are applied (`flask db upgrade`).
2.  Activate the Python virtual environment.
3.  Navigate to the project's root directory in the terminal.
4.  Run the command: `flask create-admin`
5.  Follow the interactive prompts to enter the Admin's Name, Email, and Password.
6.  The created Admin user will have `role=UserRole.ADMIN` and `is_verified=True`.

---

### Authentication Endpoints (`/auth`)

#### 1. Register User

*   **Endpoint:** `POST /auth/register`
*   **Description:** Registers a new Teacher or Student. Requires subsequent Admin verification.
*   **Authentication:** None required.
*   **Request Body:**
    ```json
    {
        "name": "string (required)",
        "email": "string (required, valid email format, unique)",
        "password": "string (required)",
        "role": "string (optional, 'Teacher' or 'Student', defaults to 'Student')"
    }
    ```
*   **Success Response (201 Created):**
    ```json
    {
        "msg": "User registered successfully. Verification may be required.",
        "user": {
            "id": integer,
            "name": "string",
            "email": "string",
            "role": "string", // 'Teacher' or 'Student'
            "is_verified": false, // Always false on registration
            "created_at_utc": "string (ISO 8601 format, naive UTC)"
        }
    }
    ```
*   **Error Responses:** `400` (Missing fields, invalid role, invalid email), `409` (Email exists), `500`.

#### 2. Login User

*   **Endpoint:** `POST /auth/login`
*   **Description:** Authenticates a user and returns a JWT access token. Requires the user account to be verified (unless the user is an Admin).
*   **Authentication:** None required.
*   **Request Body:**
    ```json
    {
        "email": "string (required)",
        "password": "string (required)"
    }
    ```
*   **Success Response (200 OK):**
    ```json
    {
        "access_token": "string (JWT)" // Contains user_info claim: {"id": X, "role": "Y"}
    }
    ```
*   **Error Responses:** `400` (Missing fields), `401` (Invalid email or password), `403` (Account requires verification), `500`.

#### 3. Get Current User

*   **Endpoint:** `GET /auth/me`
*   **Description:** Retrieves details of the currently authenticated user based on the JWT in the `Authorization` header.
*   **Authentication:** JWT Required (Any Role).
*   **Request Body:** None.
*   **Success Response (200 OK):**
    ```json
    {
        "id": integer,
        "name": "string",
        "email": "string",
        "role": "string", // Role from DB (should match token)
        "is_verified": boolean, // Current status from DB
        "created_at_utc": "string (ISO 8601 format, naive UTC)"
    }
    ```
*   **Error Responses:** `401` (Invalid/missing token, invalid claims), `404` (User ID from token not found in DB), `500`.

#### 4. Logout User

*   **Endpoint:** `POST /auth/logout`
*   **Description:** Placeholder endpoint. For stateless JWTs, logout is handled client-side by discarding the token.
*   **Authentication:** JWT Required (Any Role).
*   **Request Body:** None.
*   **Success Response (200 OK):**
    ```json
    {
        "msg": "Logout successful. Please discard your token."
    }
    ```
*   **Error Responses:** `401`.

---

### Admin Endpoints (`/admin`)

*   **Authentication:** All endpoints require a valid JWT for a user with `role='Admin'` whose account `is_verified=True`.

#### 1. Get Admin Dashboard Stats

*   **Endpoint:** `GET /admin/dashboard`
*   **Description:** Retrieves summary statistics relevant to the administrator.
*   **Request Body:** None.
*   **Success Response (200 OK):**
    ```json
    {
        "message": "Admin Dashboard Data",
        "active_teachers": integer, // Count of verified teachers
        "active_students": integer, // Count of verified students
        "pending_verifications": integer, // Count of unverified teachers/students
        "total_exams": integer,
        "total_responses_submitted": integer,
        "responses_evaluated": integer, // Count of records in Evaluations table
        "responses_pending_evaluation": integer // total_responses - responses_evaluated
    }
    ```
*   **Error Responses:** `401`, `403`, `500`.

#### 2. Get Pending Verification Users

*   **Endpoint:** `GET /admin/users/pending`
*   **Description:** Lists unverified Teacher and Student accounts, ordered by registration time.
*   **Request Body:** None.
*   **Success Response (200 OK):**
    ```json
    [
        {
            "id": integer,
            "name": "string",
            "email": "string",
            "role": "string ('Teacher' or 'Student')",
            "registered_at_utc": "string (ISO 8601 format, naive UTC)"
        },
        // ... more users
    ]
    ```
*   **Error Responses:** `401`, `403`, `500`.

#### 3. Verify User Account

*   **Endpoint:** `POST /admin/users/verify/{user_id}`
*   **Description:** Sets the `is_verified` flag to `True` for a specific Teacher or Student.
*   **Path Parameters:**
    *   `user_id` (integer): The ID of the user (Teacher/Student) to verify.
*   **Request Body:** None.
*   **Success Response (200 OK):**
    ```json
    {
        "msg": "User '<user_email>' verified successfully"
    }
    ```
*   **Error Responses:** `400` (Cannot verify Admin role, User is already verified), `401`, `403`, `404` (User not found), `500`.

#### 4. Get All Teachers

*   **Endpoint:** `GET /admin/teachers`
*   **Description:** Retrieves a list of all users with the Teacher role.
*   **Request Body:** None.
*   **Success Response (200 OK):**
    ```json
    [
        {
            "id": integer,
            "name": "string",
            "email": "string",
            "is_verified": boolean,
            "created_at_utc": "string (ISO 8601 format, naive UTC)"
        },
        // ... more teachers
    ]
    ```
*   **Error Responses:** `401`, `403`, `500`.

#### 5. Get All Students

*   **Endpoint:** `GET /admin/students`
*   **Description:** Retrieves a list of all users with the Student role.
*   **Request Body:** None.
*   **Success Response (200 OK):**
    ```json
    [
        {
            "id": integer,
            "name": "string",
            "email": "string",
            "is_verified": boolean,
            "created_at_utc": "string (ISO 8601 format, naive UTC)"
        },
        // ... more students
    ]
    ```
*   **Error Responses:** `401`, `403`, `500`.

#### 6. Delete User

*   **Endpoint:** `DELETE /admin/users/{user_id}`
*   **Description:** Deletes a specific Teacher or Student account. Admins cannot delete themselves or other Admins via this endpoint.
*   **Path Parameters:**
    *   `user_id` (integer): The ID of the Teacher or Student user to delete.
*   **Request Body:** None.
*   **Success Response (200 OK):**
    ```json
    {
        "msg": "User '<user_email>' deleted successfully"
    }
    ```
*   **Error Responses:** `401`, `403` (Attempting to delete self or another Admin), `404` (User not found), `500` (Database constraint violation if user has associated records not handled by cascade).

#### 7. Get All Evaluated Results (Paginated)

*   **Endpoint:** `GET /admin/results/all`
*   **Description:** Retrieves a paginated list of all evaluation records, joined with relevant user, exam, and question details. Sorted by evaluation time descending.
*   **Query Parameters:**
    *   `page` (integer, optional, default=1): Page number to retrieve.
    *   `per_page` (integer, optional, default=20): Number of results per page.
*   **Request Body:** None.
*   **Success Response (200 OK):**
    ```json
    {
        "results": [
            {
                "evaluation_id": integer,
                "student_name": "string",
                "student_email": "string",
                "exam_title": "string",
                "question_text": "string (truncated if long)",
                "student_response": "string (truncated if long)",
                "marks_awarded": float,
                "marks_possible": integer, // Max marks for the question
                "feedback": "string", // AI or system feedback
                "evaluated_by": "string", // e.g., "AI_Gemini (Admin Trigger: 1)", "System (Empty Response - Admin Trigger: 1)"
                "evaluated_at_utc": "string (ISO 8601 format, naive UTC)"
            },
            // ... more results up to per_page limit
        ],
        "total_results": integer, // Total number of evaluated responses
        "total_pages": integer,
        "current_page": integer,
        "per_page": integer
    }
    ```
*   **Error Responses:** `401`, `403`, `500`.

#### 8. Trigger AI Evaluation

*   **Endpoint:** `POST /admin/evaluate/response/{response_id}`
*   **Description:** Initiates the AI evaluation process for a specific, unevaluated student response. Handles empty responses directly.
*   **Path Parameters:**
    *   `response_id` (integer): The ID of the `StudentResponse` record to evaluate.
*   **Request Body:** None.
*   **Success Response (200 OK):**
    *   If successful AI evaluation:
        ```json
        {
            "msg": "AI evaluation successful",
            "evaluation_id": integer, // ID of the created Evaluation record
            "marks_awarded": float, // Marks returned by AI
            "feedback": "string" // Feedback returned by AI
        }
        ```
    *   If response was empty:
        ```json
        {
            "msg": "AI evaluation skipped: Student response was empty. Marked as 0.",
            "evaluation_id": integer, // ID of the created Evaluation record
            "marks_awarded": 0.0,
            "feedback": "Student response was empty."
        }
        ```
*   **Error Responses:** `400` (Response already evaluated), `401`, `403`, `404` (StudentResponse not found), `500` (AI service call failed, DB error saving evaluation, associated Question not found), `503` (AI Evaluation service module not found or failed to initialize).

---

### Teacher Endpoints (`/teacher`)

*   **Authentication:** All endpoints require a valid JWT for a user with `role='Teacher'` whose account `is_verified=True`. Actions are scoped to exams/questions created by the authenticated teacher.

#### 1. Get Teacher Dashboard Stats

*   **Endpoint:** `GET /teacher/dashboard`
*   **Description:** Retrieves basic statistics for the logged-in teacher.
*   **Request Body:** None.
*   **Success Response (200 OK):**
    ```json
    {
        "message": "Teacher Dashboard",
        "my_exams_count": integer // Number of exams created by this teacher
        // Add more stats if implemented
    }
    ```
*   **Error Responses:** `401`, `403`, `500`.

#### 2. Create Exam

*   **Endpoint:** `POST /teacher/exams`
*   **Description:** Creates a new exam scheduled in UTC.
*   **Request Body:**
    ```json
    {
        "title": "string (required)",
        "description": "string (optional, nullable)",
        "scheduled_time_utc": "string (required, ISO 8601 format, naive UTC)",
        "duration_minutes": integer (required, must be positive)
    }
    ```
*   **Success Response (201 Created):**
    ```json
    {
        "msg": "Exam created successfully",
        "exam": {
            "id": integer,
            "title": "string",
            "description": "string", // or null
            "scheduled_time_utc": "string (ISO 8601 format, naive UTC)",
            "duration_minutes": integer,
            "created_at_utc": "string (ISO 8601 format, naive UTC)"
        }
    }
    ```
*   **Error Responses:** `400` (Missing/invalid fields, invalid duration, invalid datetime format), `401`, `403`, `500`.

#### 3. Get Teacher's Exams

*   **Endpoint:** `GET /teacher/exams`
*   **Description:** Lists all exams created by the authenticated teacher, ordered by schedule time descending.
*   **Request Body:** None.
*   **Success Response (200 OK):**
    ```json
    [
        {
            "id": integer,
            "title": "string",
            "description": "string", // or null
            "scheduled_time_utc": "string (ISO 8601 format, naive UTC)",
            "duration_minutes": integer,
            "created_at_utc": "string (ISO 8601 format, naive UTC)"
        },
        // ... more exams
    ]
    ```
*   **Error Responses:** `401`, `403`, `500`.

#### 4. Get Exam Details

*   **Endpoint:** `GET /teacher/exams/{exam_id}`
*   **Description:** Retrieves details for a specific exam created by the authenticated teacher.
*   **Path Parameters:**
    *   `exam_id` (integer): The ID of the exam.
*   **Request Body:** None.
*   **Success Response (200 OK):** (Single exam object, same structure as in the list response from GET `/teacher/exams`)
*   **Error Responses:** `401`, `403`, `404` (Exam not found or not owned by this teacher), `500`.

#### 5. Update Exam

*   **Endpoint:** `PUT /teacher/exams/{exam_id}`
*   **Description:** Updates specified details of an exam owned by the authenticated teacher.
*   **Path Parameters:**
    *   `exam_id` (integer): The ID of the exam to update.
*   **Request Body:** (Include only the fields to be updated)
    ```json
    {
        "title": "string (optional)",
        "description": "string (optional)",
        "scheduled_time_utc": "string (optional, ISO 8601 format, naive UTC)",
        "duration_minutes": integer (optional, must be positive)
    }
    ```
*   **Success Response (200 OK):** (Single exam object with updated details, same structure as GET `/teacher/exams/{exam_id}`)
*   **Error Responses:** `400` (Invalid field values, invalid format, no valid fields provided), `401`, `403`, `404` (Exam not found or not owned), `500`.

#### 6. Delete Exam

*   **Endpoint:** `DELETE /teacher/exams/{exam_id}`
*   **Description:** Deletes an exam owned by the teacher. Associated Questions and StudentResponses are deleted via database cascade. Ensure cascade settings are correct, especially if Evaluations have FK constraints.
*   **Path Parameters:**
    *   `exam_id` (integer): The ID of the exam to delete.
*   **Request Body:** None.
*   **Success Response (200 OK):**
    ```json
    {
        "msg": "Exam '<exam_title>' deleted successfully"
    }
    ```
*   **Error Responses:** `401`, `403`, `404` (Exam not found or not owned), `500` (Potential DB constraint errors if cascade is incomplete).

#### 7. Add Question to Exam

*   **Endpoint:** `POST /teacher/exams/{exam_id}/questions`
*   **Description:** Adds a new question to an exam owned by the teacher.
*   **Path Parameters:**
    *   `exam_id` (integer): The ID of the exam.
*   **Request Body:**
    ```json
    {
        "question_text": "string (required)",
        "question_type": "string (required, one of 'MCQ', 'Short Answer', 'Long Answer')",
        "marks": integer (required, must be positive),
        // --- MCQ Only ---
        "options": { // Required and must be non-empty dict if question_type is 'MCQ'
            "option_key1": "Option Text 1", // Key can be any string (e.g., "A", "B", "1", "2")
            "option_key2": "Option Text 2"
            // ... more options
        },
        "correct_answer": "string (Required if question_type is 'MCQ', must exactly match one of the keys in 'options')",
        // --- Short Answer / Long Answer Only ---
        "word_limit": integer (optional, positive, applicable to 'Short Answer'/'Long Answer')
    }
    ```
*   **Success Response (201 Created):**
    ```json
    {
        "msg": "Question added successfully",
        "question": {
            "id": integer,
            "question_text": "string",
            "question_type": "string", // e.g., "MCQ"
            "marks": integer,
            "options": {}, // object if MCQ, null otherwise
            "correct_answer": "string", // string (key) if MCQ, null otherwise
            "word_limit": integer // integer if provided for subjective, null otherwise
        }
    }
    ```
*   **Error Responses:** `400` (Missing required fields, invalid question type, invalid marks, missing/invalid MCQ options/answer, invalid word limit), `401`, `403`, `404` (Exam not found or not owned), `500`.

#### 8. Get Exam Questions

*   **Endpoint:** `GET /teacher/exams/{exam_id}/questions`
*   **Description:** Retrieves all questions (including answers/options) for a specific exam owned by the teacher.
*   **Path Parameters:**
    *   `exam_id` (integer): The ID of the exam.
*   **Request Body:** None.
*   **Success Response (200 OK):**
    ```json
    [
        {
            "id": integer,
            "question_text": "string",
            "question_type": "string",
            "marks": integer,
            "options": {}, // object if MCQ, null otherwise
            "correct_answer": "string", // string (key) if MCQ, null otherwise
            "word_limit": integer // integer or null
        },
        // ... more questions
    ]
    ```
*   **Error Responses:** `401`, `403`, `404` (Exam not found or not owned), `500`.

#### 9. Get Single Question Details

*   **Endpoint:** `GET /teacher/exams/{exam_id}/questions/{question_id}`
*   **Description:** Retrieves details of a single question within an exam owned by the teacher.
*   **Path Parameters:**
    *   `exam_id` (integer): The ID of the exam.
    *   `question_id` (integer): The ID of the question.
*   **Request Body:** None.
*   **Success Response (200 OK):** (Single question object, same structure as in the list from GET `/exams/{exam_id}/questions`)
*   **Error Responses:** `401`, `403`, `404` (Exam or Question not found, or question not part of the specified exam, or exam not owned), `500`.

#### 10. Update Question

*   **Endpoint:** `PUT /teacher/exams/{exam_id}/questions/{question_id}`
*   **Description:** Updates specified fields of an existing question within an exam owned by the teacher. Handles validation complexity when changing question types (e.g., ensuring MCQ fields are present if changing *to* MCQ, or nullifying them if changing *from* MCQ).
*   **Path Parameters:**
    *   `exam_id` (integer): The ID of the exam.
    *   `question_id` (integer): The ID of the question to update.
*   **Request Body:** (Include only the fields to be updated)
    ```json
    {
        "question_text": "string (optional)",
        "question_type": "string (optional, 'MCQ', 'Short Answer', 'Long Answer')",
        "marks": integer (optional, must be positive),
        "options": {} (optional, provide if changing type to MCQ or modifying options),
        "correct_answer": "string (optional, provide if changing type to MCQ or modifying answer/options)",
        "word_limit": integer (optional, positive or null)
    }
    ```
*   **Success Response (200 OK):** (Single question object with updated details)
*   **Error Responses:** `400` (Invalid field values, type change validation failed, no valid fields provided), `401`, `403`, `404` (Exam/Question not found or owned), `500`.

#### 11. Delete Question

*   **Endpoint:** `DELETE /teacher/exams/{exam_id}/questions/{question_id}`
*   **Description:** Deletes a specific question from an exam owned by the teacher. Associated StudentResponses will be deleted via cascade.
*   **Path Parameters:**
    *   `exam_id` (integer): The ID of the exam.
    *   `question_id` (integer): The ID of the question to delete.
*   **Request Body:** None.
*   **Success Response (200 OK):**
    ```json
    {
        "msg": "Question deleted successfully"
    }
    ```
*   **Error Responses:** `401`, `403`, `404` (Exam/Question not found or owned), `500`.

#### 12. Get Exam Results (Teacher View)

*   **Endpoint:** `GET /teacher/exams/results/{exam_id}`
*   **Description:** Retrieves aggregated and detailed results for all students who have submitted responses for a specific exam owned by the teacher.
*   **Path Parameters:**
    *   `exam_id` (integer): The ID of the exam.
*   **Request Body:** None.
*   **Success Response (200 OK):**
    ```json
    [ // List, one entry per student who submitted
        {
            "student_id": integer,
            "student_name": "string",
            "student_email": "string",
            "total_marks_awarded": float, // Sum of awarded marks for evaluated questions
            "total_marks_possible": integer, // Sum of max marks for all questions in the exam
            "submission_status": "string", // e.g., "Fully Evaluated", "Partially Evaluated (evaluated_count/total_questions)", "Submitted" (if none evaluated yet)
            "details": [ // List, one entry per question response from this student
                {
                    "response_id": integer,
                    "question_id": integer,
                    "question_text": "string",
                    "question_type": "string",
                    "response_text": "string", // Student's actual answer
                    "submitted_at_utc": "string (ISO 8601 format, naive UTC)",
                    "marks_possible": integer, // Max marks for this question
                    "marks_awarded": float, // Awarded marks (null if not evaluated)
                    "feedback": "string", // Evaluation feedback (null or "Not Evaluated Yet" if pending)
                    "evaluated_at_utc": "string (ISO 8601 format, naive UTC)", // Null if not evaluated
                    "evaluated_by": "string", // e.g., "AI_Gemini (Admin Trigger: 1)", null if pending
                    "evaluation_status": "string" // e.g., "Evaluated", "Pending Evaluation"
                },
                // ... more response details for other questions
            ]
        },
        // ... more students
    ]
    ```
    *Note: If a student submitted but has no responses recorded (edge case), they might not appear.*
*   **Error Responses:** `401`, `403`, `404` (Exam not found or not owned), `500`.

---

### Student Endpoints (`/student`)

*   **Authentication:** All endpoints require a valid JWT for a user with `role='Student'` whose account `is_verified=True`.

#### 1. Get Student Dashboard Stats

*   **Endpoint:** `GET /student/dashboard`
*   **Description:** Retrieves dashboard information for the authenticated student.
*   **Request Body:** None.
*   **Success Response (200 OK):**
    ```json
    {
        "message": "Student Dashboard",
        "completed_exams_count": integer, // Count of distinct exams submitted by the student
        "upcoming_exams": [ // List of max 5 upcoming exams (not submitted)
            {
                "id": integer,
                "title": "string",
                "scheduled_time_utc": "string (ISO 8601 format, naive UTC)"
            },
            // ... up to 5 exams
        ]
    }
    ```
*   **Error Responses:** `401`, `403`, `500`.

#### 2. Get Available Exams

*   **Endpoint:** `GET /student/exams/available`
*   **Description:** Lists exams that the student has *not* yet submitted responses for and are currently "Upcoming" or "Active" based on server's naive UTC time.
*   **Request Body:** None.
*   **Success Response (200 OK):**
    ```json
    [
        {
            "id": integer,
            "title": "string",
            "description": "string", // or null
            "scheduled_time_utc": "string (ISO 8601 format, naive UTC)",
            "duration_minutes": integer,
            "status": "string" // "Upcoming" or "Active"
        },
        // ... more available exams
    ]
    ```
*   **Error Responses:** `401`, `403`, `500`.

#### 3. Take Exam (Get Questions)

*   **Endpoint:** `GET /student/exams/{exam_id}/take`
*   **Description:** Allows a student to start taking an **Active** exam. Retrieves exam details, questions (without correct MCQ answers), and remaining time. Fails if the exam is not active, already submitted, or not found.
*   **Path Parameters:**
    *   `exam_id` (integer): The ID of the exam to take.
*   **Request Body:** None.
*   **Success Response (200 OK):** *(Only if exam is Active and not submitted)*
    ```json
    {
        "exam_id": integer,
        "exam_title": "string",
        "scheduled_time_utc": "string (ISO 8601 format, naive UTC)", // Exam start time
        "duration_minutes": integer,
        "questions": [
            {
                "id": integer,
                "question_text": "string",
                "question_type": "string", // e.g., "MCQ", "Short Answer"
                "marks": integer,
                "options": {}, // Object with key-value pairs if MCQ, null otherwise
                "word_limit": integer // Integer if Short/Long Answer, null otherwise
                // Note: correct_answer for MCQ is NOT included here
            },
            // ... more questions
        ],
        "time_remaining_seconds": integer // Calculated remaining time based on server's UTC time
    }
    ```
*   **Error Responses:**
    *   `401`, `403` (Account not verified).
    *   `403` (Exam already submitted): `{"msg": "You have already submitted responses for this exam."}`
    *   `403` (Exam not Active):
        ```json
        // If Upcoming
        {
            "msg": "This exam is not currently active. Status: Upcoming",
            "scheduled_time_utc": "string (ISO 8601 format, naive UTC)" // Exam start time
        }
        // If Expired
        {
            "msg": "This exam is not currently active. Status: Expired",
            "scheduled_time_utc": "string (ISO 8601 format, naive UTC)" // Exam start time
        }
        ```
    *   `404` (Exam not found).
    *   `500` (Internal error, e.g., invalid schedule/duration in DB).

#### 4. Submit Exam Answers

*   **Endpoint:** `POST /student/exams/{exam_id}/submit`
*   **Description:** Submits the student's collected answers for a specific exam. Must be called before the submission deadline (exam end time + grace period, checked using server's naive UTC time). Fails if already submitted.
*   **Path Parameters:**
    *   `exam_id` (integer): The ID of the exam being submitted.
*   **Request Body:**
    ```json
    {
        // Array of answers provided by the student
        "answers": [
            {
                "question_id": integer (required),
                // For MCQ, this should be the key of the selected option.
                // For subjective, this is the typed answer text.
                "response_text": "string (required, may be empty)"
            },
            // ... one entry for each answered question
        ]
    }
    ```
*   **Success Response (200 OK):**
    ```json
    {
        "msg": "Exam submitted successfully."
    }
    ```
*   **Error Responses:** `400` (Invalid request format, missing 'answers' key, invalid answer structure, no valid answers provided), `401`, `403` (Submission deadline passed, Exam already submitted), `404` (Exam not found), `500`.

#### 5. Get Submitted Exams List

*   **Endpoint:** `GET /student/exams/submitted`
*   **Description:** Lists exams for which the authenticated student has already submitted responses.
*   **Request Body:** None.
*   **Success Response (200 OK):**
    ```json
    [
        {
            "id": integer, // Exam ID
            "title": "string", // Exam Title
            "scheduled_time_utc": "string (ISO 8601 format, naive UTC)", // When the exam was scheduled
            "submitted_at_utc": "string (ISO 8601 format, naive UTC)", // When the student submitted (first response's time for this exam)
            "status": "Submitted"
        },
        // ... more submitted exams, typically ordered by submission time descending
    ]
    ```
*   **Error Responses:** `401`, `403`, `500`.

#### 6. Get My Results

*   **Endpoint:** `GET /student/results/my`
*   **Description:** Retrieves the results (including marks and feedback where available) for all exams submitted by the authenticated student.
*   **Request Body:** None.
*   **Success Response (200 OK):**
    ```json
    [ // List, one entry per submitted exam
        {
            "exam_id": integer,
            "exam_title": "string",
            "exam_scheduled_time_utc": "string (ISO 8601 format, naive UTC)",
            "total_marks_awarded": float, // Sum of awarded marks for evaluated questions in this exam
            "total_marks_possible": integer, // Sum of max marks for all questions in this exam
            "overall_status": "string", // e.g., "Results Declared" (all evaluated), "Pending Evaluation" (some/all pending)
            "questions": [ // List, one entry for each question in this exam the student responded to
                {
                    "question_id": integer,
                    "question_text": "string",
                    "question_type": "string",
                    "your_response": "string", // The student's actual response text/key
                    "submitted_at_utc": "string (ISO 8601 format, naive UTC)", // Time this specific response was saved
                    "marks_awarded": float, // Awarded marks (null if not evaluated yet)
                    "marks_possible": integer, // Max marks for this question
                    "feedback": "string", // Feedback (null or placeholder if not evaluated yet)
                    "evaluated_at_utc": "string (ISO 8601 format, naive UTC)", // Null if not evaluated
                    "evaluated_by": "string", // Who/what evaluated (null if not evaluated)
                    "status": "string" // "Evaluated" or "Pending Evaluation"
                },
                // ... more questions for this exam
            ]
        },
        // ... more submitted exams
    ]
    ```
*   **Error Responses:** `401`, `403`, `500`.

---

### Database Setup Commands (Flask-Migrate)

Run these commands in your terminal from the **root directory** of your Flask project (where your `wsgi.py` or main app file is located).

**1. Initialize the Migrations Directory (Run ONCE per project)**

*   If you are starting the project from scratch and **don't** have a `migrations` directory yet, run this command.
*   If you cloned the repository and it *already* contains a `migrations` directory, **SKIP** this step.

    ```bash
    flask db init
    ```
    *   This creates the `migrations/` directory and configuration files (`alembic.ini`, `migrations/env.py`, etc.). You should commit this directory to version control.

**2. Generate the Initial Migration Script**

*   This command inspects your SQLAlchemy models (in `app/models.py`) and compares them to the (currently empty or non-existent) database schema state tracked by Alembic. It generates a Python script representing the changes needed to create all your tables.

    ```bash
    flask db migrate -m "Initial database schema"
    ```
    *   Replace `"Initial database schema"` with a short, descriptive message about the migration.
    *   This creates a new file inside `migrations/versions/` (e.g., `migrations/versions/xxxx_initial_database_schema.py`).
    *   **Best Practice:** Always inspect the generated migration script to ensure it looks correct before applying it.

**3. Apply the Migration to the Database**

*   This command executes the generated migration script(s) against the actual database specified in your `DATABASE_URL`. It runs the SQL commands to create the tables, columns, constraints, etc., defined in your models.

    ```bash
    flask db upgrade
    ```
    *   This applies *all* pending migrations found in the `migrations/versions/` directory that haven't been applied yet (tracked in the `alembic_version` table within your database).

---

**Summary for First-Time Setup:**

Assuming a clean database and project structure:

1.  Manually `CREATE DATABASE your_db_name;`
2.  Configure `.env` with the correct `DATABASE_URL`.
3.  `flask db init` (if `migrations/` doesn't exist)
4.  `flask db migrate -m "Initial database schema"`
5.  (Optional but recommended) Check the generated script in `migrations/versions/`.
6.  `flask db upgrade`

Your database schema should now match your SQLAlchemy models. You can then proceed to create the initial admin user (`flask create-admin`).


---

Okay, based on the code provided in your `app/__init__.py` file, the command to create the initial administrator user is:

```bash
flask create-admin
```

**Here's a breakdown of how to use it and the necessary steps:**

1.  **Prerequisites:**
    *   **Database Setup:** Make sure your database is created and the tables are up-to-date by running the migrations:
        ```bash
        flask db upgrade
        ```
    *   **Terminal Access:** Open a terminal or command prompt.
    *   **Navigate to Project Root:** Change your directory (`cd`) to the root folder of your Flask project (where the `wsgi.py` or the main `app` directory is located).
    *   **Activate Virtual Environment:** If you're using a virtual environment (highly recommended), activate it:
        *   Linux/macOS: `source venv/bin/activate` (adjust `venv` if your environment has a different name)
        *   Windows: `.\venv\Scripts\activate`

2.  **Run the Command:**
    Execute the command in your terminal:
    ```bash
    flask create-admin
    ```

3.  **Follow the Interactive Prompts:**
    The script will ask you to enter the details for the new admin user:
    ```
    --- Create Admin User ---
    Enter Admin Name: [Type the desired full name here and press Enter]
    Enter Admin Email: [Type the admin's email address here and press Enter]
    Enter Admin Password: [Type a strong password here and press Enter]
    ```
    *(Note: The password you type might not be visible on the screen for security reasons)*

4.  **Check the Output:**
    *   **Success:** If the user is created successfully, you'll see a confirmation message:
        ```
        Admin user '[Admin Name]' ([Admin Email]) created successfully.
        ```
    *   **Error (e.g., Email Exists):** If the email address is already registered, you'll get an error:
        ```
        Error: User with email '[Admin Email]' already exists (Role: Admin).
        ```
    *   **Error (Empty Input):** If you leave any field blank:
        ```
        Error: Name, email, and password cannot be empty.
        ```

This command directly adds the user to your database with the `role` set to `ADMIN` and `is_verified` set to `True`. You can then use these credentials to log in via the `POST /auth/login` API endpoint.