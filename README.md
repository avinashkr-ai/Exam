Okay, here is the comprehensive API documentation for your Online Exam Portal, reflecting the use of naive UTC datetimes and JWT authentication with custom claims.

---

## Online Exam Portal API Documentation

**Version:** 1.0
**Base URL (Development):** `http://localhost:5000` (Replace with your deployment URL)

### Introduction

This document provides details on the RESTful API endpoints for the Online Exam Portal. The API facilitates interactions for Administrators, Teachers, and Students.

### Authentication

*   **Method:** JSON Web Tokens (JWT)
*   **Login:** Users obtain a JWT by sending credentials to `POST /auth/login`.
*   **Token Usage:** The obtained `access_token` must be included in the `Authorization` header for all protected endpoints using the `Bearer` scheme:
    ```
    Authorization: Bearer <your_access_token>
    ```
*   **Token Claims:** The JWT contains a `user_info` claim with the user's `id` and `role` (e.g., `'Admin'`, `'Teacher'`, `'Student'`). Decorators use this information for role-based access control.
*   **Verification:** Most endpoints require the user's account to be verified (`is_verified=True` in the database). Admins are verified by default; others require Admin approval via `POST /admin/users/verify/{user_id}`.

### Data Formats

*   **Request/Response Bodies:** JSON (`application/json`)
*   **Datetimes:** All datetime strings exchanged with the API (in request bodies or response bodies) **must be in ISO 8601 format representing naive UTC**.
    *   Example: `YYYY-MM-DDTHH:MM:SS` (e.g., `"2025-04-17T15:30:00"`)
    *   The server stores and processes all times internally as naive UTC.
    *   Response datetime fields are explicitly named with a `_utc` suffix (e.g., `created_at_utc`).
    *   The frontend is responsible for converting these UTC times to the user's local timezone for display.

### Error Handling

Common HTTP status codes used:

*   `200 OK`: Request successful.
*   `201 Created`: Resource created successfully.
*   `204 No Content`: Request successful, no response body (rarely used here).
*   `400 Bad Request`: Invalid request format, missing fields, or validation error. Response body contains `{"msg": "Error description"}`.
*   `401 Unauthorized`: Invalid, expired, or missing JWT.
*   `403 Forbidden`: Authenticated user lacks permission (wrong role, not verified, trying to access others' data).
*   `404 Not Found`: Requested resource (user, exam, question) does not exist.
*   `409 Conflict`: Resource creation failed because it already exists (e.g., duplicate email).
*   `500 Internal Server Error`: Unexpected server error. Response body may contain `{"msg": "Error description"}`.
*   `503 Service Unavailable`: A required external service (like AI evaluation) is down.

---

### Authentication Endpoints (`/auth`)

#### 1. Register User

*   **Endpoint:** `POST /auth/register`
*   **Description:** Registers a new Teacher or Student. Admins must be created via the CLI command (`flask create-admin`).
*   **Authentication:** None required.
*   **Request Body:**
    ```json
    {
        "name": "string (required)",
        "email": "string (required, valid email format)",
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
            "role": "string",
            "is_verified": boolean,
            "created_at_utc": "string (ISO 8601 format, naive UTC)"
        }
    }
    ```
*   **Error Responses:** `400` (Missing fields, invalid role, invalid email), `409` (Email exists), `500`.

#### 2. Login User

*   **Endpoint:** `POST /auth/login`
*   **Description:** Authenticates a user and returns a JWT access token. Requires the user account to be verified (unless Admin).
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
        "access_token": "string (JWT)"
    }
    ```
*   **Error Responses:** `400` (Missing fields), `401` (Invalid credentials), `403` (Account not verified), `500`.

#### 3. Get Current User

*   **Endpoint:** `GET /auth/me`
*   **Description:** Retrieves details of the currently authenticated user based on the JWT.
*   **Authentication:** JWT Required (Any verified role).
*   **Request Body:** None.
*   **Success Response (200 OK):**
    ```json
    {
        "id": integer,
        "name": "string",
        "email": "string",
        "role": "string",
        "is_verified": boolean,
        "created_at_utc": "string (ISO 8601 format, naive UTC)"
    }
    ```
*   **Error Responses:** `401` (Invalid/missing token), `404` (User associated with token not found in DB), `500`.

#### 4. Logout User

*   **Endpoint:** `POST /auth/logout`
*   **Description:** Placeholder for logout. Since JWTs are stateless, the client should discard the token. Server-side blocklisting is not implemented by default.
*   **Authentication:** JWT Required (Any role).
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

*   **Authentication:** All endpoints require a valid JWT for an `Admin` user whose account `is_verified`.

#### 1. Get Admin Dashboard Stats

*   **Endpoint:** `GET /admin/dashboard`
*   **Description:** Retrieves summary statistics for the admin dashboard.
*   **Request Body:** None.
*   **Success Response (200 OK):**
    ```json
    {
        "message": "Admin Dashboard Data",
        "active_teachers": integer,
        "active_students": integer,
        "pending_verifications": integer,
        "total_exams": integer,
        "total_responses_submitted": integer,
        "responses_evaluated": integer,
        "responses_pending_evaluation": integer
    }
    ```
*   **Error Responses:** `401`, `403`, `500`.

#### 2. Get Pending Verification Users

*   **Endpoint:** `GET /admin/users/pending`
*   **Description:** Lists users (Teachers/Students) awaiting verification.
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
*   **Description:** Marks a specific user account as verified.
*   **Path Parameters:**
    *   `user_id` (integer): The ID of the user to verify.
*   **Request Body:** None.
*   **Success Response (200 OK):**
    ```json
    {
        "msg": "User '<user_email>' verified successfully"
    }
    ```
*   **Error Responses:** `400` (Cannot verify Admin, Already verified), `401`, `403`, `404` (User not found), `500`.

#### 4. Get All Teachers

*   **Endpoint:** `GET /admin/teachers`
*   **Description:** Retrieves a list of all registered teachers.
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
*   **Description:** Retrieves a list of all registered students.
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
*   **Description:** Deletes a specific Teacher or Student account. Cannot delete Admins or self.
*   **Path Parameters:**
    *   `user_id` (integer): The ID of the user to delete.
*   **Request Body:** None.
*   **Success Response (200 OK):**
    ```json
    {
        "msg": "User '<user_email>' deleted successfully"
    }
    ```
*   **Error Responses:** `401`, `403` (Cannot delete self, Cannot delete Admin), `404` (User not found), `500` (Constraint violation possible).

#### 7. Get All Evaluated Results (Paginated)

*   **Endpoint:** `GET /admin/results/all`
*   **Description:** Retrieves a paginated list of all evaluated student responses across all exams.
*   **Query Parameters:**
    *   `page` (integer, optional, default=1): Page number.
    *   `per_page` (integer, optional, default=20): Results per page.
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
                "question_text": "string (truncated)",
                "student_response": "string (truncated)",
                "marks_awarded": float,
                "marks_possible": integer,
                "feedback": "string",
                "evaluated_by": "string",
                "evaluated_at_utc": "string (ISO 8601 format, naive UTC)"
            },
            // ... more results
        ],
        "total_results": integer,
        "total_pages": integer,
        "current_page": integer,
        "per_page": integer
    }
    ```
*   **Error Responses:** `401`, `403`, `500`.

#### 8. Trigger AI Evaluation

*   **Endpoint:** `POST /admin/evaluate/response/{response_id}`
*   **Description:** Triggers the Gemini AI evaluation for a specific student response ID. Skips if the response is empty or already evaluated.
*   **Path Parameters:**
    *   `response_id` (integer): The ID of the `StudentResponse` to evaluate.
*   **Request Body:** None.
*   **Success Response (200 OK):**
    *   If successful AI evaluation:
        ```json
        {
            "msg": "AI evaluation successful",
            "evaluation_id": integer,
            "marks_awarded": float,
            "feedback": "string"
        }
        ```
    *   If response was empty:
        ```json
        {
            "msg": "AI evaluation skipped: Student response was empty. Marked as 0.",
            "evaluation_id": integer,
            "marks_awarded": 0.0,
            "feedback": "Student response was empty."
        }
        ```
*   **Error Responses:** `400` (Already evaluated), `401`, `403`, `404` (Response not found), `500` (AI service failure, DB error, Data integrity issue), `503` (AI Service unavailable).

---

### Teacher Endpoints (`/teacher`)

*   **Authentication:** All endpoints require a valid JWT for a `Teacher` user whose account `is_verified`. Actions are generally restricted to exams/questions created by the logged-in teacher.

#### 1. Get Teacher Dashboard Stats

*   **Endpoint:** `GET /teacher/dashboard`
*   **Description:** Retrieves basic dashboard info for the teacher.
*   **Request Body:** None.
*   **Success Response (200 OK):**
    ```json
    {
        "message": "Teacher Dashboard",
        "my_exams_count": integer
    }
    ```
*   **Error Responses:** `401`, `403`, `500`.

#### 2. Create Exam

*   **Endpoint:** `POST /teacher/exams`
*   **Description:** Creates a new exam owned by the teacher.
*   **Request Body:**
    ```json
    {
        "title": "string (required)",
        "description": "string (optional)",
        "scheduled_time_utc": "string (required, ISO 8601 format, naive UTC)",
        "duration_minutes": integer (required, positive)
    }
    ```
*   **Success Response (201 Created):**
    ```json
    {
        "msg": "Exam created successfully",
        "exam": {
            "id": integer,
            "title": "string",
            "description": "string",
            "scheduled_time_utc": "string (ISO 8601 format, naive UTC)",
            "duration_minutes": integer,
            "created_at_utc": "string (ISO 8601 format, naive UTC)"
        }
    }
    ```
*   **Error Responses:** `400` (Missing/invalid fields, past schedule time if enforced), `401`, `403`, `500`.

#### 3. Get Teacher's Exams

*   **Endpoint:** `GET /teacher/exams`
*   **Description:** Lists all exams created by the logged-in teacher.
*   **Request Body:** None.
*   **Success Response (200 OK):**
    ```json
    [
        {
            "id": integer,
            "title": "string",
            "description": "string",
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
*   **Description:** Retrieves details for a specific exam owned by the teacher.
*   **Path Parameters:**
    *   `exam_id` (integer): The ID of the exam.
*   **Request Body:** None.
*   **Success Response (200 OK):** (Same structure as success response for POST /teacher/exams)
*   **Error Responses:** `401`, `403`, `404` (Not found or not owned), `500`.

#### 5. Update Exam

*   **Endpoint:** `PUT /teacher/exams/{exam_id}`
*   **Description:** Updates details of an exam owned by the teacher.
*   **Path Parameters:**
    *   `exam_id` (integer): The ID of the exam.
*   **Request Body:** (Include only fields to update)
    ```json
    {
        "title": "string (optional)",
        "description": "string (optional)",
        "scheduled_time_utc": "string (optional, ISO 8601 format, naive UTC)",
        "duration_minutes": integer (optional, positive)
    }
    ```
*   **Success Response (200 OK):** (Same structure as success response for POST /teacher/exams, showing updated data)
*   **Error Responses:** `400` (Invalid fields, No fields provided), `401`, `403`, `404`, `500`.

#### 6. Delete Exam

*   **Endpoint:** `DELETE /teacher/exams/{exam_id}`
*   **Description:** Deletes an exam owned by the teacher and its associated questions/responses (cascading).
*   **Path Parameters:**
    *   `exam_id` (integer): The ID of the exam.
*   **Request Body:** None.
*   **Success Response (200 OK):**
    ```json
    {
        "msg": "Exam '<exam_title>' deleted successfully"
    }
    ```
*   **Error Responses:** `401`, `403`, `404`, `500` (Check cascade setup).

#### 7. Add Question to Exam

*   **Endpoint:** `POST /teacher/exams/{exam_id}/questions`
*   **Description:** Adds a new question to an exam owned by the teacher.
*   **Path Parameters:**
    *   `exam_id` (integer): The ID of the exam.
*   **Request Body:**
    ```json
    {
        "question_text": "string (required)",
        "question_type": "string (required, 'MCQ', 'Short Answer', or 'Long Answer')",
        "marks": integer (required, positive),
        // --- MCQ Only ---
        "options": { // required if question_type is 'MCQ'
            "option_key1": "Option Text 1",
            "option_key2": "Option Text 2",
            // ... more options
        },
        "correct_answer": "string (required if question_type is 'MCQ', must be a key from 'options')",
        // --- Short Answer / Long Answer Only ---
        "word_limit": integer (optional, positive, for 'Short Answer'/'Long Answer')
    }
    ```
*   **Success Response (201 Created):**
    ```json
    {
        "msg": "Question added successfully",
        "question": {
            "id": integer,
            "question_text": "string",
            "question_type": "string",
            "marks": integer,
            "options": {}, // or null
            "correct_answer": "string", // or null
            "word_limit": integer // or null
        }
    }
    ```
*   **Error Responses:** `400` (Missing/invalid fields, type mismatches), `401`, `403`, `404` (Exam not found), `500`.

#### 8. Get Exam Questions

*   **Endpoint:** `GET /teacher/exams/{exam_id}/questions`
*   **Description:** Retrieves all questions for an exam owned by the teacher.
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
            "options": {}, // or null
            "correct_answer": "string", // or null
            "word_limit": integer // or null
        },
        // ... more questions
    ]
    ```
*   **Error Responses:** `401`, `403`, `404`, `500`.

#### 9. Get Single Question Details

*   **Endpoint:** `GET /teacher/exams/{exam_id}/questions/{question_id}`
*   **Description:** Retrieves details of a specific question within an exam owned by the teacher.
*   **Path Parameters:**
    *   `exam_id` (integer): The ID of the exam.
    *   `question_id` (integer): The ID of the question.
*   **Request Body:** None.
*   **Success Response (200 OK):** (Single question object, same structure as in the list from GET `/exams/{exam_id}/questions`)
*   **Error Responses:** `401`, `403`, `404` (Exam or Question not found/owned), `500`.

#### 10. Update Question

*   **Endpoint:** `PUT /teacher/exams/{exam_id}/questions/{question_id}`
*   **Description:** Updates an existing question within an exam owned by the teacher. Handles validation based on question type changes.
*   **Path Parameters:**
    *   `exam_id` (integer): The ID of the exam.
    *   `question_id` (integer): The ID of the question.
*   **Request Body:** (Include only fields to update)
    ```json
    {
        "question_text": "string (optional)",
        "question_type": "string (optional, 'MCQ', 'Short Answer', 'Long Answer')",
        "marks": integer (optional, positive),
        "options": {} (optional, required if changing to MCQ or updating MCQ options),
        "correct_answer": "string (optional, required if changing to MCQ or updating MCQ options)",
        "word_limit": integer (optional, positive or null)
    }
    ```
*   **Success Response (200 OK):** (Single question object showing updated data)
*   **Error Responses:** `400` (Invalid fields, validation errors based on type), `401`, `403`, `404`, `500`.

#### 11. Delete Question

*   **Endpoint:** `DELETE /teacher/exams/{exam_id}/questions/{question_id}`
*   **Description:** Deletes a specific question from an exam owned by the teacher.
*   **Path Parameters:**
    *   `exam_id` (integer): The ID of the exam.
    *   `question_id` (integer): The ID of the question.
*   **Request Body:** None.
*   **Success Response (200 OK):**
    ```json
    {
        "msg": "Question deleted successfully"
    }
    ```
*   **Error Responses:** `401`, `403`, `404`, `500`.

#### 12. Get Exam Results (Teacher View)

*   **Endpoint:** `GET /teacher/exams/results/{exam_id}`
*   **Description:** Retrieves detailed results for all students who took a specific exam owned by the teacher.
*   **Path Parameters:**
    *   `exam_id` (integer): The ID of the exam.
*   **Request Body:** None.
*   **Success Response (200 OK):**
    ```json
    [ // List of students
        {
            "student_id": integer,
            "student_name": "string",
            "student_email": "string",
            "total_marks_awarded": float,
            "total_marks_possible": integer,
            "submission_status": "string ('Fully Evaluated' or 'Partially Evaluated (X/Y)')",
            "details": [ // List of responses/evaluations for this student
                {
                    "response_id": integer,
                    "question_id": integer,
                    "question_text": "string",
                    "question_type": "string",
                    "response_text": "string",
                    "submitted_at_utc": "string (ISO 8601 format, naive UTC)",
                    "marks_possible": integer,
                    "marks_awarded": float, // or null
                    "feedback": "string", // or "Not Evaluated Yet"
                    "evaluated_at_utc": "string (ISO 8601 format, naive UTC)", // or null
                    "evaluated_by": "string", // or null
                    "evaluation_status": "string ('Evaluated' or 'Pending Evaluation')"
                },
                // ... more details for other questions
            ]
        },
        // ... more students
    ]
    ```
*   **Error Responses:** `401`, `403`, `404` (Exam not found/owned), `500`.

---

### Student Endpoints (`/student`)

*   **Authentication:** All endpoints require a valid JWT for a `Student` user whose account `is_verified`.

#### 1. Get Student Dashboard Stats

*   **Endpoint:** `GET /student/dashboard`
*   **Description:** Retrieves dashboard info for the student, including completed exams and upcoming exams.
*   **Request Body:** None.
*   **Success Response (200 OK):**
    ```json
    {
        "message": "Student Dashboard",
        "completed_exams_count": integer,
        "upcoming_exams": [
            {
                "id": integer,
                "title": "string",
                "scheduled_time_utc": "string (ISO 8601 format, naive UTC)"
            },
            // ... up to 5 upcoming exams
        ]
    }
    ```
*   **Error Responses:** `401`, `403`, `500`.

#### 2. Get Available Exams

*   **Endpoint:** `GET /student/exams/available`
*   **Description:** Lists exams that the student has *not* yet submitted and are either "Upcoming" or "Active".
*   **Request Body:** None.
*   **Success Response (200 OK):**
    ```json
    [
        {
            "id": integer,
            "title": "string",
            "description": "string",
            "scheduled_time_utc": "string (ISO 8601 format, naive UTC)",
            "duration_minutes": integer,
            "status": "string ('Upcoming' or 'Active')"
        },
        // ... more available exams
    ]
    ```
*   **Error Responses:** `401`, `403`, `500`.

#### 3. Take Exam (Get Questions)

*   **Endpoint:** `GET /student/exams/{exam_id}/take`
*   **Description:** Allows a student to start an "Active" exam and retrieve its questions and remaining time. Fails if the exam is not active or already submitted.
*   **Path Parameters:**
    *   `exam_id` (integer): The ID of the exam to take.
*   **Request Body:** None.
*   **Success Response (200 OK):**
    ```json
    {
        "exam_id": integer,
        "exam_title": "string",
        "scheduled_time_utc": "string (ISO 8601 format, naive UTC)",
        "duration_minutes": integer,
        "questions": [
            {
                "id": integer,
                "question_text": "string",
                "question_type": "string",
                "marks": integer,
                "options": {}, // Present only for MCQ, null otherwise
                "word_limit": integer // Present only for Short/Long Answer, null otherwise
                // CORRECT ANSWER IS NOT INCLUDED
            },
            // ... more questions
        ],
        "time_remaining_seconds": integer
    }
    ```
*   **Error Responses:** `401`, `403` (Not active, Already submitted), `404` (Exam not found), `500`.

#### 4. Submit Exam Answers

*   **Endpoint:** `POST /student/exams/{exam_id}/submit`
*   **Description:** Submits the student's answers for a specific exam. Fails if the deadline (including grace period) has passed or if already submitted.
*   **Path Parameters:**
    *   `exam_id` (integer): The ID of the exam being submitted.
*   **Request Body:**
    ```json
    {
        "answers": [
            {
                "question_id": integer (required),
                "response_text": "string (required, can be empty string or answer text/key)"
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
*   **Error Responses:** `400` (Invalid format, No valid answers), `401`, `403` (Deadline passed, Already submitted), `404` (Exam not found), `500`.

#### 5. Get Submitted Exams List

*   **Endpoint:** `GET /student/exams/submitted`
*   **Description:** Lists exams for which the student has submitted answers.
*   **Request Body:** None.
*   **Success Response (200 OK):**
    ```json
    [
        {
            "id": integer,
            "title": "string",
            "scheduled_time_utc": "string (ISO 8601 format, naive UTC)",
            "submitted_at_utc": "string (ISO 8601 format, naive UTC)",
            "status": "Submitted"
        },
        // ... more submitted exams
    ]
    ```
*   **Error Responses:** `401`, `403`, `500`.

#### 6. Get My Results

*   **Endpoint:** `GET /student/results/my`
*   **Description:** Retrieves the student's results for all submitted exams, including marks and feedback where available.
*   **Request Body:** None.
*   **Success Response (200 OK):**
    ```json
    [ // List of exams student submitted
        {
            "exam_id": integer,
            "exam_title": "string",
            "exam_scheduled_time_utc": "string (ISO 8601 format, naive UTC)",
            "total_marks_awarded": float,
            "total_marks_possible": integer,
            "overall_status": "string ('Results Declared' or 'Pending Evaluation')",
            "questions": [ // List of responses/evaluations for this exam
                {
                    "question_id": integer,
                    "question_text": "string",
                    "question_type": "string",
                    "your_response": "string",
                    "submitted_at_utc": "string (ISO 8601 format, naive UTC)",
                    "marks_awarded": float, // or null if pending
                    "marks_possible": integer,
                    "feedback": "string", // or "Not evaluated yet"
                    "evaluated_at_utc": "string (ISO 8601 format, naive UTC)", // or null
                    "evaluated_by": "string", // or null
                    "status": "string ('Evaluated' or 'Pending Evaluation')"
                },
                // ... more questions for this exam
            ]
        },
        // ... more submitted exams
    ]
    ```
*   **Error Responses:** `401`, `403`, `500`.

---

Okay, based on the code provided, the intended way to create an **Admin** account is by using a **Flask Command Line Interface (CLI) command**.

You **cannot** typically create an Admin account through the regular `/auth/register` API endpoint used by Teachers and Students. This is a security measure to ensure only authorized personnel can create administrative users.

Here's how to create an Admin account:

1.  **Access the Backend Server:** You need terminal (command line) access to the environment where your Flask backend application code resides.

2.  **Activate Virtual Environment:** If you are using a Python virtual environment (which is highly recommended), make sure it's activated.
    *   On Linux/macOS: `source venv/bin/activate` (or your environment's activation command)
    *   On Windows: `.\venv\Scripts\activate`

3.  **Navigate to Project Directory:** Change your directory (`cd`) to the root of your Flask project (the directory containing the `wsgi.py` file or the main `app` package).

4.  **Ensure Database is Setup:** Before creating a user, the database must exist, and the necessary tables must be created. Make sure you have run the database migrations:
    ```bash
    flask db upgrade
    ```
    (If you haven't initialized migrations yet, you'd run `flask db init` and `flask db migrate` first).

5.  **Run the `create-admin` Command:** Execute the following command in your terminal:
    ```bash
    flask create-admin
    ```

6.  **Follow Prompts:** The command will interactively prompt you to enter the required information:
    ```
    --- Create Admin User ---
    Enter Admin Name: John Admin
    Enter Admin Email: admin@yourexamportal.com
    Enter Admin Password: your_strong_password_here
    ```
    *(Enter the desired name, email, and a strong password when prompted)*

7.  **Check Output:**
    *   If successful, you will see a message like:
        ```
        Admin user 'John Admin' (admin@yourexamportal.com) created successfully.
        ```
    *   If there's an error (e.g., the email already exists), you'll see an error message:
        ```
        Error: User with email 'admin@yourexamportal.com' already exists (Role: Admin).
        ```

**Summary:**

The process leverages the custom CLI command defined in your `app/__init__.py` file, which directly interacts with the `User` model to create an Admin user with `is_verified` set to `True` and the `role` set to `UserRole.ADMIN`.


---