# Online Exam System - Frontend Developer Guide

## Project Overview

The Online Exam System is a web application designed to facilitate the creation, management, and execution of online exams. It supports multiple user roles with varying permissions, providing a flexible platform for educational institutions or training programs. This document serves as a comprehensive guide for frontend developers, outlining how to interact with the backend API and integrate it into the frontend application.

## User Roles

The system defines three distinct user roles, each with specific functionalities:

1.  **Admin:**
    *   Manages the system, users (teachers and students), and system-wide settings.
    *   Can verify new users, delete users, and access all exam results.
    * Can trigger AI evaluation for questions.

2.  **Teacher:**
    *   Creates, updates, and deletes exams.
    *   Adds, updates, and deletes questions for exams.
    *   Reviews exam results for their exams.

3.  **Student:**
    *   Views available exams.
    *   Takes exams.
    *   Submits exam responses.
    *   Views their exam results.

## API Endpoints

The following table details all the API endpoints available in the Online Exam System, including their methods, parameters, request/response examples, and authentication requirements.

**Authentication Endpoints:**

| Endpoint            | Method | Description                       | Request Body                                                       | Response Example                                                                                                          | Authentication |
| :------------------ | :----- | :-------------------------------- | :----------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------ | :------------- |
| `/auth/register`   | POST   | Register a new user.              | `{"name": "User Name", "email": "user@email.com", "password": "password", "role": "student"}` | `{"msg": "User created successfully", "user_id": 1, "name": "User Name", "email": "user@email.com"}`                       | None           |
| `/auth/login`      | POST   | Login a user and get a JWT token. | `{"email": "user@email.com", "password": "password"}`           | `{"msg": "Login successful", "access_token": "JWT_TOKEN"}`                                                             | None           |
| `/auth/logout`     | POST   | Logout the current user.          | None                                                               | `{"msg": "Logout successful"}`                                                                                            | JWT            |

**Admin Endpoints (requires `admin` role, `jwt`, and `verification`):**

| Endpoint                         | Method | Description                                        | Request Body                                                | Response Example                                                                                                            | Authentication      |
| :------------------------------- | :----- | :------------------------------------------------- | :---------------------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------- | :------------------ |
| `/admin/dashboard`               | GET    | Get admin dashboard statistics.                    | None                                                        | `{"message": "Admin Dashboard", "teachers": 5, "students": 10, "exams": 20}`                                              | JWT, Admin, Verified |
| `/admin/users/pending`           | GET    | Get a list of pending users.                       | None                                                        | `[{"id": 2, "name": "Pending User", "email": "pending@email.com", "role": "teacher"}]`                                      | JWT, Admin, Verified |
| `/admin/users/verify/<user_id>` | POST   | Verify a user.                                     | None                                                        | `{"msg": "User pending@email.com verified successfully"}`                                                              | JWT, Admin, Verified |
| `/admin/teachers`                | GET    | Get a list of all teachers.                        | None                                                        | `[{"id": 3, "name": "Teacher One", "email": "teacher@email.com", "is_verified": true}]`                                   | JWT, Admin, Verified |
| `/admin/students`                | GET    | Get a list of all students.                        | None                                                        | `[{"id": 4, "name": "Student One", "email": "student@email.com", "is_verified": false}]`                                    | JWT, Admin, Verified |
| `/admin/users/<user_id>`        | DELETE | Delete a user.                                     | None                                                        | `{"msg": "User user@email.com deleted successfully"}`                                                                  | JWT, Admin, Verified |
| `/admin/results/all`             | GET    | Get all exam results.                              | None                                                        | `[{"evaluation_id": 1, "student_name": "Student One", "student_email": "student@email.com", "exam_title": "Exam 1", "question_text": "Question 1...", "marks_awarded": 5, "evaluated_by": "AI_Gemini (Admin Trigger: 1)", "evaluated_at": "2024-01-01T12:00:00"}]` | JWT, Admin, Verified |
| `/admin/evaluate/response/<response_id>` | POST   | Triggers AI Evaluation to evaluate a response | None                                                        | `{"msg": "AI evaluation successful","evaluation_id": 1,"marks_awarded": 5,"feedback": "Good Answer"}`                                                        | JWT, Admin, Verified |

**Teacher Endpoints (requires `teacher` role, `jwt`, and `verification`):**

| Endpoint                                   | Method | Description                                                | Request Body                                                                                                                                                                                              | Response Example                                                                                                                                                                                                           | Authentication         |
| :----------------------------------------- | :----- | :--------------------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :--------------------- |
| `/teacher/dashboard`                       | GET    | Get teacher dashboard statistics.                          | None                                                                                                                                                                                                      | `{"message": "Teacher Dashboard", "my_exams_count": 10}`                                                                                                                                                                        | JWT, Teacher, Verified |
| `/teacher/exams`                           | POST   | Create a new exam.                                        | `{"title": "New Exam", "description": "Exam Description", "scheduled_time": "2024-12-31T10:00:00", "duration": 60}`                                                                                             | `{"msg": "Exam created successfully", "exam_id": 1, "title": "New Exam"}`                                                                                                                                                           | JWT, Teacher, Verified |
| `/teacher/exams`                           | GET    | Get teacher's exams.                                      | None                                                                                                                                                                                                      | `[{"id": 1, "title": "Exam 1", "description": "Exam 1 Description", "scheduled_time": "2024-12-31T10:00:00", "duration": 60, "created_at": "2024-01-01T09:00:00"}]`                                                                | JWT, Teacher, Verified |
| `/teacher/exams/<exam_id>`                | GET    | Get details of an exam.                                   | None                                                                                                                                                                                                      | `{"id": 1, "title": "Exam 1", "description": "Exam 1 Description", "scheduled_time": "2024-12-31T10:00:00", "duration": 60}`                                                                                                       | JWT, Teacher, Verified |
| `/teacher/exams/<exam_id>`                | PUT    | Update an exam.                                           | `{"title": "Updated Exam", "description": "Updated Description", "scheduled_time": "2025-01-01T12:00:00", "duration": 90}` (fields can be partial)                                                               | `{"msg": "Exam updated successfully"}`                                                                                                                                                                                                | JWT, Teacher, Verified |
| `/teacher/exams/<exam_id>`                | DELETE | Delete an exam.                                           | None                                                                                                                                                                                                      | `{"msg": "Exam and associated data deleted successfully"}`                                                                                                                                                                          | JWT, Teacher, Verified |
| `/teacher/exams/<exam_id>/questions`      | POST   | Add a question to an exam.                               | `{"question_text": "Question 1?", "question_type": "MCQ", "marks": 5, "options": {"A": "Option A", "B": "Option B"}, "correct_answer": "A", "word_limit": 100}`                                                  | `{"msg": "Question added successfully", "question_id": 1}`                                                                                                                                                                             | JWT, Teacher, Verified |
| `/teacher/exams/<exam_id>/questions`      | GET    | Get all questions for an exam.                            | None                                                                                                                                                                                                      | `[{"id": 1, "question_text": "Question 1?", "question_type": "MCQ", "marks": 5, "options": {"A": "Option A", "B": "Option B"}, "correct_answer": "A", "word_limit": 100}]`                                                  | JWT, Teacher, Verified |
| `/teacher/exams/<exam_id>/questions/<question_id>` | PUT    | Update a question.                                        | `{"question_text": "Updated Question", "question_type": "SHORT_ANSWER", "marks": 10}` (fields can be partial)                                                                                                            | `{"msg": "Question updated successfully"}`                                                                                                                                                                                                | JWT, Teacher, Verified |
| `/teacher/exams/<exam_id>/questions/<question_id>` | DELETE | Delete a question.                                        | None                                                                                                                                                                                                      | `{"msg": "Question deleted successfully"}`                                                                                                                                                                                             | JWT, Teacher, Verified |
| `/teacher/exams/results/<exam_id>`         | GET    | Get the results for an exam.                              | None                                                                                                                                                                                                      | `[{"student_id": 4,"student_name": "Student One","question_id": 1, "question_text": "Question 1?", "response_text": "Student Answer","submitted_at": "2024-01-01T11:00:00","evaluations": [{"evaluation_id": 1, "marks_awarded": 5, "feedback": "Good Answer", "evaluated_by": "AI_Gemini", "evaluated_at": "2024-01-01T12:00:00"}]}]` | JWT, Teacher, Verified |

**Student Endpoints (requires `student` role, `jwt`, and `verification`):**

| Endpoint                      | Method | Description                                                | Request Body                                                                                                               | Response Example                                                                                                                                                                                                                                                          | Authentication          |
| :---------------------------- | :----- | :--------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | :---------------------- |
| `/student/dashboard`          | GET    | Get student dashboard statistics.                          | None                                                                                                                       | `{"message": "Student Dashboard", "completed_exams_count": 2, "upcoming_exams": [{"id": 2, "title": "Exam 2", "scheduled_time": "2025-01-01T10:00:00"}]}`                                                                                                                                       | JWT, Student, Verified  |
| `/student/exams/available`    | GET    | Get available exams for the student.                       | None                                                                                                                       | `[{"id": 2, "title": "Exam 2", "description": "Exam 2 Description", "scheduled_time": "2025-01-01T10:00:00", "duration": 90, "status": "Upcoming"}]`                                                                                                                                                   | JWT, Student, Verified  |
| `/student/exams/take/<exam_id>` | GET    | Get the exam questions to take.                         | None                                                                                                                        | `{"exam_id": 2, "title": "Exam 2", "questions": [{"id": 1, "question_text": "Question 1?", "question_type": "MCQ", "marks": 5, "options": {"A": "Option A", "B": "Option B"}, "word_limit": 100}]}`                                                                                           | JWT, Student, Verified |
| `/student/exams/submit/<exam_id>` | POST   | Submit an exam response.                               | `[{"1": "Answer to question 1"}, {"2": "Answer to question 2"}]` (question_id: response)                                   | `{"msg": "Exam submitted successfully"}`                                                                                                                                                                                                                                    | JWT, Student, Verified |
| `/student/exams/results`       | GET    | Get the student's results.                                | None                                                                                                                       | `[{"exam_title": "Exam 1", "question_text": "Question 1?", "response_text": "Student Answer","submitted_at": "2024-01-01T11:00:00", "evaluations": [{"evaluation_id": 1, "marks_awarded": 5, "feedback": "Good Answer", "evaluated_by": "AI_Gemini", "evaluated_at": "2024-01-01T12:00:00"}]}]` | JWT, Student, Verified |

## Authentication Flow

1.  **Registration:**
    *   A new user registers via `POST /auth/register`, providing their `name`, `email`, `password`, and `role`.
    *   The backend creates the user and returns a success message with the user details.
2.  **Login:**
    *   A registered user logs in via `POST /auth/login`, providing their `email` and `password`.
    *   The backend authenticates the user and returns a JWT token.
3.  **Protected Endpoints:**
    *   Subsequent requests to protected endpoints must include the JWT token in the `Authorization` header.
    *   Example: `Authorization: Bearer <JWT_TOKEN>`
4.  **Logout:**
    * User can logout by calling the endpoint `POST /auth/logout`.
5.  **Verification:**
    * New users are initially not verified.
    * Admins can verify users by using `POST /admin/users/verify/<user_id>`.
    * Only verified users can access the endpoints.

## User Flows

### Admin User Flow

1.  **Login:**
    *   Navigate to the login page.
    *   Enter admin credentials.
    *   Submit the login form.
    *   Receive a JWT token.
2.  **Access Admin Dashboard:**
    *   Navigate to `/admin/dashboard`.
    *   Include the JWT token in the `Authorization` header.
    *   View system statistics (number of teachers, students, exams).
3.  **Manage Pending Users:**
    *   Navigate to `/admin/users/pending`.
    *   Include the JWT token in the `Authorization` header.
    *   View a list of pending users.
    *   Click "Verify" next to a user.
    *   A `POST` request is sent to `/admin/users/verify/<user_id>`.
4.  **Manage Teachers/Students:**
    *   Navigate to `/admin/teachers` or `/admin/students`.
    *   Include the JWT token in the `Authorization` header.
    *   View a list of all teachers or students.
5. **Delete a user**
    * Go to the view of users.
    * Click on delete for the desired user.
    * A `DELETE` request is sent to `/admin/users/<user_id>`.
6.  **View All Results:**
    *   Navigate to `/admin/results/all`.
    *   Include the JWT token in the `Authorization` header.
    *   View all exam results.
7. **Trigger AI Evaluation**
    * Select the response to evaluate.
    * Click on the evaluate button.
    * A `POST` request is sent to `/admin/evaluate/response/<response_id>`.
8. **Logout**
    *   Navigate to `/auth/logout`.
    * Include the JWT token in the `Authorization` header.

### Teacher User Flow

1.  **Login:**
    *   Navigate to the login page.
    *   Enter teacher credentials.
    *   Submit the login form.
    *   Receive a JWT token.
2.  **Access Teacher Dashboard:**
    *   Navigate to `/teacher/dashboard`.
    *   Include the JWT token in the `Authorization` header.
    *   View teacher-specific statistics (number of exams created).
3.  **Create Exam:**
    *   Navigate to `/teacher/exams`.
    *   Include the JWT token in the `Authorization` header.
    *   Fill in exam details (title, description, scheduled time, duration).
    *   Submit the form.
    *   A `POST` request is sent to `/teacher/exams`.
4.  **Manage Exams:**
    *   Navigate to `/teacher/exams`.
    *   Include the JWT token in the `Authorization` header.
    *   View a list of created exams.
    *   Click on an exam to view details (sends a `GET` request to `/teacher/exams/<exam_id>`).
    *   Click "Edit" to update an exam (sends a `PUT` request to `/teacher/exams/<exam_id>`).
    *   Click "Delete" to delete an exam (sends a `DELETE` request to `/teacher/exams/<exam_id>`).
5.  **Add Questions:**
    *   Navigate to `/teacher/exams/<exam_id>/questions`.
    *   Include the JWT token in the `Authorization` header.
    *   Fill in question details (text, type, marks, options, correct answer).
    *   Submit the form.
    *   A `POST` request is sent to `/teacher/exams/<exam_id>/questions`.
6.  **Manage Questions:**
    *   Navigate to `/teacher/exams/<exam_id>/questions`.
    *   Include the JWT token in the `Authorization` header.
    *   View a list of exam questions (sends a `GET` request to `/teacher/exams/<exam_id>/questions`).
    *   Click "Edit" to update a question (sends a `PUT` request to `/teacher/exams/<exam_id>/questions/<question_id>`).
    *   Click "Delete" to delete a question (sends a `DELETE` request to `/teacher/exams/<exam_id>/questions/<question_id>`).
7.  **View Results:**
    *   Navigate to `/teacher/exams/results/<exam_id>`.
    *   Include the JWT token in the `Authorization` header.
    *   View the results for the selected exam.
8. **Logout**
    *   Navigate to `/auth/logout`.
    * Include the JWT token in the `Authorization` header.

### Student User Flow

1.  **Login:**
    *   Navigate to the login page.
    *   Enter student credentials.
    *   Submit the login form.
    *   Receive a JWT token.
2.  **Access Student Dashboard:**
    *   Navigate to `/student/dashboard`.
    *   Include the JWT token in the `Authorization` header.
    *   View student-specific statistics (number of completed exams, upcoming exams).
3.  **View Available Exams:**
    *   Navigate to `/student/exams/available`.
    *   Include the JWT token in the `Authorization` header.
    *   View a list of available exams.
4.  **Take Exam:**
    *   Click "Take Exam" next to an available exam.
    *   A `GET` request is sent to `/student/exams/take/<exam_id>`.
    *   View exam questions.
5.  **Submit Exam:**
    *   Answer all questions.
    *   Submit the exam.
    *   A `POST` request is sent to `/student/exams/submit/<exam_id>`, including the answers.
6.  **View Results:**
    *   Navigate to `/student/exams/results`.
    *   Include the JWT token in the `Authorization` header.
    *   View the results of submitted exams.
7. **Logout**
    *   Navigate to `/auth/logout`.
    * Include the JWT token in the `Authorization` header.