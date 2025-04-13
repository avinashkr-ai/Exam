Great! Glad to hear the application is running.

Here is the updated API documentation based on the corrected code and the requirements discussed. This should help you test all the endpoints effectively using a tool like Postman or Insomnia.

Online Exam Portal - API Documentation (Updated)

Base URL: (Your running server, e.g., http://127.0.0.1:5000)

Authentication:

Most endpoints require a JSON Web Token (JWT).

Obtain the token via POST /auth/login.

Include the token in the Authorization header for subsequent requests:
Authorization: Bearer <YOUR_JWT_TOKEN>

Many endpoints also require specific roles (Admin, Teacher, Student) and for the user account to be verified. These requirements are noted for each endpoint.

🛡️ Common APIs (Authentication & User Info)
Method	Endpoint	Description	Auth Required	Request Body (JSON)	Success Response (200/201)	Error Responses
POST	/auth/register	Register a new user (default: Student).	None	{"name": "Test User", "email": "test@example.com", "password": "password123", "role": "Student"} (Role optional, defaults to Student)	{"msg": "User registered successfully. Awaiting verification if applicable.", "user": {"id": 1, "name": "Test User", "email": "test@example.com", "role": "Student"}}	400 Bad Request (Missing fields), 409 Conflict (Email exists), 400 Bad Request (Invalid role)
POST	/auth/login	Login to get JWT access token.	None	{"email": "verified.student@example.com", "password": "password123"}	{"access_token": "eyJhbGciOiJI..."}	400 Bad Request (Missing fields), 401 Unauthorized (Bad email/password), 403 Forbidden (Account not verified)
POST	/auth/refresh	Optional: Get a new access token using refresh token.	Refresh JWT	(Requires Flask-JWT-Extended refresh token setup)	{"access_token": "eyJhbGciOi..."}	401 Unauthorized (Invalid/Expired refresh token)
GET	/auth/me	Get current authenticated user's details.	Access JWT	None	{"id": 1, "name": "Test User", "email": "test@example.com", "role": "Student", "is_verified": true}	401 Unauthorized (Invalid/Expired token), 404 Not Found (User deleted after token issued)
POST	/auth/logout	Logs out the user (Basic: confirms action).	Access JWT	None	{"msg": "Logout successful. Please discard your token."}	401 Unauthorized (Invalid/Expired token)
🧑‍💼 Admin APIs

(Requires: Access JWT + Admin Role + Verified Account)

Method	Endpoint	Description	Request Body (JSON)	Path/Query Params	Success Response (200/201)	Error Responses
GET	/admin/dashboard	Get admin dashboard statistics.	None	None	{"message": "Admin Dashboard", "active_teachers": 5, "active_students": 50, "pending_verifications": 3, "total_exams": 15, "total_responses_submitted": 250, "responses_evaluated": 200, "responses_pending_evaluation": 50}	401 Unauthorized, 403 Forbidden
GET	/admin/users/pending	Get list of users awaiting verification.	None	None	[{"id": 2, "name": "Pending Teacher", "email": "pending.t@example.com", "role": "Teacher", "registered_at": "2024-01-10T10:00:00"}, ...]	401 Unauthorized, 403 Forbidden
POST	/admin/users/verify/<user_id>	Verify a registered Teacher or Student.	None	user_id (int)	{"msg": "User pending.t@example.com verified successfully"}	401 Unauthorized, 403 Forbidden, 404 Not Found (User ID), 400 Bad Request (User already verified or trying to verify Admin)
GET	/admin/teachers	Get list of all registered teachers.	None	None	[{"id": 3, "name": "Teacher One", "email": "teacher1@example.com", "is_verified": true}, ...]	401 Unauthorized, 403 Forbidden
GET	/admin/students	Get list of all registered students.	None	None	[{"id": 4, "name": "Student One", "email": "student1@example.com", "is_verified": true}, ...]	401 Unauthorized, 403 Forbidden
DELETE	/admin/users/<user_id>	Delete a Teacher or Student user.	None	user_id (int)	{"msg": "User student1@example.com deleted successfully"}	401 Unauthorized, 403 Forbidden (e.g., trying to delete self or another Admin), 404 Not Found (User ID)
GET	/admin/results/all	Get all evaluated results (paginated).	None	?page=1&per_page=20 (Optional)	{"results": [{"evaluation_id": 1, "student_name": "S Name", ..., "marks_awarded": 4.5, ...}], "total": 150, "pages": 8, "current_page": 1}	401 Unauthorized, 403 Forbidden
POST	/admin/evaluate/response/<response_id>	Trigger AI evaluation for a specific response.	None	response_id (int)	{"msg": "AI evaluation successful", "evaluation_id": 12, "marks_awarded": 4.0, "feedback": "Good explanation, but missed point X."} OR {"msg": "AI evaluation skipped: Student response was empty. Marked as 0.", ...}	401 Unauthorized, 403 Forbidden, 404 Not Found (Response ID or related Question), 400 Bad Request (Already evaluated), 500 Internal Server Error (AI API call failure, parsing error, other exception)
👩‍🏫 Teacher APIs

(Requires: Access JWT + Teacher Role + Verified Account)

Method	Endpoint	Description	Request Body (JSON)	Path/Query Params	Success Response (200/201)	Error Responses
GET	/teacher/dashboard	Get teacher dashboard statistics.	None	None	{"message": "Teacher Dashboard", "my_exams_count": 10}	401 Unauthorized, 403 Forbidden
POST	/teacher/exams	Create a new exam.	{"title": "Midterm Exam", "description": "Covers chapters 1-5.", "scheduled_time": "2024-10-20T09:00:00Z", "duration": 90} (Use ISO 8601 UTC)	None	{"msg": "Exam created successfully", "exam_id": 25, "title": "Midterm Exam"}	401 Unauthorized, 403 Forbidden, 400 Bad Request (Missing fields, invalid format)
GET	/teacher/exams	Get exams created by this teacher.	None	None	[{"id": 25, "title": "Midterm Exam", ..., "created_at": "..."}]	401 Unauthorized, 403 Forbidden
GET	/teacher/exams/<exam_id>	Get details of a specific exam.	None	exam_id (int)	{"id": 25, "title": "Midterm Exam", "description": "...", "scheduled_time": "...", "duration": 90}	401 Unauthorized, 403 Forbidden, 404 Not Found (Exam ID not found or not owned by teacher)
PUT	/teacher/exams/<exam_id>	Update an exam's details.	{ "description": "Updated description", "duration": 100 } (Send only fields to update)	exam_id (int)	{"msg": "Exam updated successfully"}	401 Unauthorized, 403 Forbidden, 404 Not Found, 400 Bad Request (Invalid data format, no changes provided)
DELETE	/teacher/exams/<exam_id>	Delete an exam and all related data.	None	exam_id (int)	{"msg": "Exam and associated data deleted successfully"}	401 Unauthorized, 403 Forbidden, 404 Not Found
POST	/teacher/exams/<exam_id>/questions	Add a question to an exam.	MCQ: {"question_text": "...", "question_type": "MCQ", "marks": 1, "options": {"A": "Opt1", "B": "Opt2"}, "correct_answer": "A"}<br/>SA/LA: {"question_text": "...", "question_type": "Short Answer", "marks": 5, "word_limit": 50}	exam_id (int)	{"msg": "Question added successfully", "question_id": 101}	401 Unauthorized, 403 Forbidden, 404 Not Found (Exam), 400 Bad Request (Missing fields, invalid type, validation fail)
GET	/teacher/exams/<exam_id>/questions	Get all questions for a specific exam.	None	exam_id (int)	[{"id": 101, "question_text": "...", "question_type": "MCQ", ...}, {"id": 102, ...}]	401 Unauthorized, 403 Forbidden, 404 Not Found (Exam)
PUT	/teacher/exams/<exam_id>/questions/<question_id>	Update a specific question.	{ "marks": 6, "question_text": "Updated text..." } (Send only fields to update)	exam_id (int), question_id (int)	{"msg": "Question updated successfully"}	401 Unauthorized, 403 Forbidden, 404 Not Found (Exam/Question), 400 Bad Request (Invalid data, validation fail, no changes)
DELETE	/teacher/exams/<exam_id>/questions/<question_id>	Delete a specific question.	None	exam_id (int), question_id (int)	{"msg": "Question deleted successfully"}	401 Unauthorized, 403 Forbidden, 404 Not Found (Exam/Question)
GET	/teacher/exams/results/<exam_id>	Get results for a specific exam (by student).	None	exam_id (int)	[{"student_id": 4, "student_name": "S Name", "total_marks_awarded": 8.5, "total_marks_possible": 10, "details": [{ "question_id": 101, ... }, ...]}, ...]	401 Unauthorized, 403 Forbidden, 404 Not Found (Exam)
🎓 Student APIs

(Requires: Access JWT + Student Role + Verified Account)

Method	Endpoint	Description	Request Body (JSON)	Path/Query Params	Success Response (200/201)	Error Responses
GET	/student/dashboard	Get student dashboard statistics.	None	None	{"message": "Student Dashboard", "completed_exams_count": 3, "upcoming_exams": [{"id": 26, "title": "Final Exam", "scheduled_time": "..."}]}	401 Unauthorized, 403 Forbidden
GET	/student/exams/available	Get list of exams available to take (not submitted).	None	None	[{"id": 26, "title": "Final Exam", ..., "status": "Active"}, {"id": 27, "title": "Quiz 3", ..., "status": "Upcoming"}]	401 Unauthorized, 403 Forbidden
GET	/student/exams/<exam_id>/take	Get questions for starting/taking an exam.	None	exam_id (int)	{"exam_id": 26, "exam_title": "Final Exam", "questions": [{"id": 105, "question_text": "...", "options": {...}, ...}], "time_remaining_seconds": 3590}	401 Unauthorized, 403 Forbidden (Not active, already submitted), 404 Not Found (Exam)
POST	/student/exams/<exam_id>/submit	Submit answers for an exam.	{"answers": [{"question_id": 105, "response_text": "My answer for Q105"}, {"question_id": 106, "response_text": "B"}]}	exam_id (int)	{"msg": "Exam submitted successfully."}	401 Unauthorized, 403 Forbidden (Deadline passed, already submitted), 404 Not Found (Exam), 400 Bad Request (Invalid format, no valid answers)
GET	/student/results/my	Get results for all submitted/evaluated exams.	None	None	[{"exam_id": 25, "exam_title": "Midterm Exam", ..., "total_marks_awarded": 8.5, "total_marks_possible": 10, "questions": [{"question_id": 101, "your_response": "...", "marks_awarded": 4.5, ...}, ...]}, ...]	401 Unauthorized, 403 Forbidden

Remember to replace placeholders like <user_id>, <exam_id>, <question_id>, <response_id>, and <YOUR_JWT_TOKEN> with actual values during testing. Good luck!