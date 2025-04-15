## Project Report: AI-Enhanced Online Exam Portal

**Version:** 1.2
**Date:** April 14, 2025

**Project Team:** (Add names if applicable)

**Table of Contents:**

1.  Executive Summary
2.  Introduction & Project Goals
3.  Problem Statement
4.  Proposed Solution & Scope
5.  System Architecture
6.  Technology Stack
7.  Frontend Implementation (Angular)
    *   7.1. Project Setup & Structure
    *   7.2. Core Module (`CoreModule`)
    *   7.3. Shared Module (`SharedModule`)
    *   7.4. Feature Modules (Auth, Student, Teacher, Admin)
    *   7.5. Routing & Navigation
    *   7.6. State Management & API Interaction
    *   7.7. UI/UX Considerations
    *   7.8. Frontend Challenges & Solutions
8.  Backend Implementation (Flask)
    *   8.1. Project Setup & Structure
    *   8.2. Database Modeling (`models.py`)
    *   8.3. API Endpoints & Blueprints
    *   8.4. Authentication & Authorization (JWT Custom Claims)
    *   8.5. AI Evaluation Service (`ai_evaluation.py`)
    *   8.6. Database Interaction & Migrations
    *   8.7. Backend Challenges & Solutions
9.  Database Design Overview
10. Deployment Strategy (Potential)
11. Testing Strategy (Proposed)
12. Conclusion
13. Future Work

---

**1. Executive Summary:**

This report details the design, implementation, and features of the AI-Enhanced Online Exam Portal, a web application built for college environments. Developed using Angular 18 for the frontend and Flask (Python) for the backend API, the portal facilitates secure and efficient online examinations. It supports distinct Admin, Teacher, and Student roles with role-specific functionalities, including exam creation (MCQ, Short/Long Answer), timed exam-taking, and result viewing. A key feature is the integration of Google's Gemini 1.5 Flash AI for automated evaluation assistance of subjective answers, triggered by administrators. The system employs JWT with custom claims for robust authentication and authorization, ensuring data security and integrity. This report covers the architecture, technology stack, implementation details of both frontend and backend, challenges faced, and potential future enhancements.

**2. Introduction & Project Goals:**

The project aimed to create a modern, centralized platform to address the inefficiencies and limitations of traditional or basic online examination systems in educational institutions. The primary goals were:

*   Develop a secure, role-based web application for online exams.
*   Support multiple question types (MCQ, Short Answer, Long Answer).
*   Implement secure user authentication and authorization using JWT.
*   Integrate AI for evaluating subjective answers to improve efficiency and provide feedback.
*   Provide distinct, intuitive interfaces for Admins, Teachers, and Students.
*   Ensure a scalable and maintainable codebase using Angular and Flask best practices.

**3. Problem Statement:**

Educational institutions often struggle with the logistical overhead of exam creation, administration, and grading. Manual grading, especially for subjective answers, is time-consuming and can lead to delays in student feedback. Existing online platforms may lack security, flexibility in question types, or efficient evaluation mechanisms. This project addresses these issues by providing a secure, integrated platform with AI-assisted grading capabilities.

**4. Proposed Solution & Scope:**

The solution is a web portal with three user roles managed via a Flask REST API and consumed by an Angular frontend.

*   **Functionality:** User registration/verification, login/logout, exam/question CRUD (Teacher), exam taking/submission (Student), result viewing (All roles, filtered), AI evaluation trigger (Admin).
*   **Scope (In):** Core features listed above, basic role-specific dashboards, JWT auth with custom claims, Gemini 1.5 Flash integration for subjective evaluation, PostgreSQL database, Angular modular frontend structure.
*   **Scope (Out - Initial):** Real-time proctoring, advanced analytics, other question types, notifications, mobile app, automatic MCQ grading.

**5. System Architecture:**

A standard Client-Server architecture is employed:

*   **Client (Browser):** Runs the Angular Single Page Application (SPA).
*   **Web Server (Hosting Angular):** Serves the static Angular build files (e.g., Netlify, Vercel, Firebase Hosting).
*   **API Server (Flask):** Runs the Python Flask application, handling API requests, business logic, and database interactions (e.g., Heroku, AWS EC2/ECS, Google App Engine).
*   **Database Server:** Hosts the PostgreSQL database (e.g., AWS RDS, Google Cloud SQL, self-hosted).
*   **AI Service:** Google Cloud (Vertex AI or AI Studio) hosting the Gemini API endpoint.

```mermaid
graph LR
    A[User Browser (Angular App)] -- HTTPS API Calls --> B(Flask Backend API);
    B -- DB Queries (SQLAlchemy) --> C(PostgreSQL Database);
    B -- AI API Call --> D(Google Gemini Service);
    C -- Data --> B;
    D -- Evaluation --> B;
    B -- JSON Responses --> A;
```

**6. Technology Stack:**

*   **Frontend:** Angular 18, TypeScript, HTML, SCSS, RxJS, Angular Router, HttpClientModule, Bootstrap 5 (Assumed).
*   **Backend:** Python 3.9+, Flask, Flask-SQLAlchemy, Flask-Migrate, Flask-JWT-Extended, Flask-Cors, google-generativeai, Tenacity (for retries).
*   **Database:** PostgreSQL.
*   **Version Control:** Git.

**7. Frontend Implementation (Angular):**

*   **7.1. Project Setup & Structure:**
    *   Initialized using Angular CLI (`ng new online-exam-portal`).
    *   Modular structure adopted (`src/app/`):
        *   `app.module.ts`: Root module bootstrapping `AppComponent`. Imports `BrowserModule`, `HttpClientModule`, `AppRoutingModule`, `CoreModule`, `SharedModule`.
        *   `app-routing.module.ts`: Defines top-level routes, lazy-loading feature modules (`Auth`, `Student`, `Teacher`, `Admin`). Handles default and wildcard redirects (to `/auth/login`).
        *   `core/`: For singleton services and guards.
        *   `shared/`: For reusable UI components, pipes, directives.
        *   `auth/`, `student/`, `teacher/`, `admin/`: Lazy-loaded feature modules containing specific components and routing.
    *   Environment files (`environments/`) configure API base URLs.

*   **7.2. Core Module (`CoreModule`):**
    *   Imported *once* in `AppModule`.
    *   **Services:**
        *   `AuthService`: Manages JWT token storage (e.g., `localStorage`), user authentication state (`BehaviorSubject<User | null>`), login/logout methods, retrieval of user ID/role from token claims.
        *   `ApiService`: Centralizes `HttpClient` requests. Handles adding the `Authorization` header (potentially via an `HttpInterceptor`), prepending the base API URL. Provides typed methods for API calls (e.g., `getExams()`, `submitAnswers()`).
        *   *(Optional) `ErrorHandlerService`*: Catches HTTP errors, potentially formats them for display.
    *   **Guards:**
        *   `AuthGuard`: Implements `CanActivate`/`CanActivateChild`. Checks if the user is logged in (via `AuthService`) and optionally if they have the required role before allowing route activation. Used in `AppRoutingModule` and feature routing modules.
    *   **Models:** TypeScript interfaces (`User`, `Exam`, `Question`, `StudentResponse`, `Evaluation`) define the expected structure of data transferred between frontend and backend.

*   **7.3. Shared Module (`SharedModule`):**
    *   Declares and Exports common, reusable UI components. Imported by feature modules as needed.
    *   **Components:**
        *   `HeaderComponent`: Displays application title, navigation links (conditionally based on auth status and role via `AuthService`), login/register or user info/logout actions.
        *   `FooterComponent`: Simple static footer.
        *   `LoadingSpinnerComponent`: Displayed during pending API calls.
        *   `ErrorAlertComponent`: Displays error messages passed to it.

*   **7.4. Feature Modules (Auth, Student, Teacher, Admin):**
    *   **`AuthModule` (`auth/`):** Lazy-loaded for `/auth`.
        *   Routing: Defines `/login`, `/register`.
        *   Components: `LoginComponent` (uses `AuthService.login`), `RegisterComponent` (uses `AuthService.register` or `ApiService`). Uses Reactive Forms for validation.
    *   **`StudentModule` (`student/`):** Lazy-loaded for `/student`. Protected by `AuthGuard`.
        *   Routing: Defines `/dashboard`, `/exams/available`, `/exams/:id/take`, `/results/my`.
        *   Components: `DashboardComponent` (calls `ApiService` for stats), `AvailableExamsComponent` (calls `GET /student/exams/available`), `ExamTakeComponent` (calls `GET /student/exams/:id/take`, manages timer, collects answers via forms, calls `POST /student/exams/:id/submit`), `ResultsComponent` (calls `GET /student/results/my`).
    *   **`TeacherModule` (`teacher/`):** Lazy-loaded for `/teacher`. Protected by `AuthGuard`.
        *   Routing: Defines `/dashboard`, `/exams`, `/exams/create`, `/exams/:id/edit`, `/exams/:id/questions`, `/exams/:id/results`.
        *   Components: `DashboardComponent`, `ExamListComponent`, `ExamFormComponent` (Create/Edit, calls `POST/PUT /teacher/exams`), `QuestionListComponent`, `QuestionFormComponent` (Create/Edit questions for specific exam, calls `POST/PUT /teacher/exams/:id/questions/...`), `ExamResultsComponent` (calls `GET /teacher/exams/results/:id`).
    *   **`AdminModule` (`admin/`):** Lazy-loaded for `/admin`. Protected by `AuthGuard`.
        *   Routing: Defines `/dashboard`, `/users/pending`, `/users/teachers`, `/users/students`, `/results/all`.
        *   Components: `DashboardComponent`, `PendingUsersComponent` (calls `GET /pending`, `POST /verify`), `UserListComponent` (Teachers/Students, calls `GET/DELETE`), `AllResultsComponent` (calls `GET /results/all`, potentially with pagination), `EvaluateResponseComponent` (UI to select response and trigger `POST /evaluate/response/:id`).

*   **7.5. Routing & Navigation:**
    *   `AppRoutingModule` handles top-level, lazy-loaded routes and redirects.
    *   Feature routing modules handle routes internal to each feature.
    *   `AuthGuard` protects authenticated routes.
    *   `HeaderComponent` provides primary navigation links (`routerLink`).
    *   Programmatic navigation (`Router.navigate`) used after login, logout, form submissions etc.

*   **7.6. State Management & API Interaction:**
    *   User authentication state and basic user info (ID, role) managed within `AuthService` using RxJS `BehaviorSubject`. Components subscribe to this for reactive UI updates.
    *   `ApiService` centralizes interaction with the Flask backend API using Angular's `HttpClient`. Asynchronous operations handled with RxJS Observables (`subscribe`, `pipe`, `map`, `catchError`).
    *   Loading states managed within components (e.g., setting a `isLoading` flag before API call, clearing it in `subscribe`/`finalize`).

*   **7.7. UI/UX Considerations:**
    *   Leverages Bootstrap 5 for layout, components, and basic responsiveness.
    *   Clear separation of concerns using components.
    *   Use of loading indicators (`LoadingSpinnerComponent`) and error messages (`ErrorAlertComponent`) enhances user experience during API interactions.
    *   Forms utilize Angular's Reactive Forms for robust validation.

*   **7.8. Frontend Challenges & Solutions:**
    *   **Routing Errors (NG04002):** Resolved by ensuring correct lazy-loading paths in `AppRoutingModule` and defining component routes within feature routing modules.
    *   **State Management:** Keeping UI consistent with auth state addressed using `AuthService` and `BehaviorSubject`.
    *   **Asynchronous Operations:** Handled using RxJS patterns for API calls and managing component state during loading/error scenarios.
    *   **Token Handling:** Securely storing and retrieving the JWT (e.g., `localStorage`), and automatically adding it to requests (using `HttpInterceptor` within `ApiService` is a common pattern).

**8. Backend Implementation (Flask):**

*   **8.1. Project Setup & Structure:**
    *   Standard Flask project structure using blueprints for modularity.
    *   `wsgi.py` or `run.py` as entry point.
    *   `app/`: Main application package.
        *   `__init__.py`: App factory (`create_app`), registers blueprints, initializes extensions (`db`, `migrate`, `jwt`, `cors`).
        *   `models.py`: SQLAlchemy model definitions.
        *   `extensions.py`: Centralized extension object instantiations (e.g., `db = SQLAlchemy()`).
        *   `routes/`: Contains blueprints (`auth.py`, `admin.py`, `teacher.py`, `student.py`).
        *   `services/`: Contains business logic decoupled from routes, like `ai_evaluation.py`.
        *   `utils/`: Helper functions (`helpers.py`) and custom decorators (`decorators.py`).
    *   `config.py`: Configuration class loading from environment variables (`.env`).
    *   `migrations/`: Database migration scripts generated by Flask-Migrate.

*   **8.2. Database Modeling (`models.py`):**
    *   SQLAlchemy ORM used to define Python classes mapping to database tables (`User`, `Exam`, `Question`, `StudentResponse`, `Evaluation`).
    *   Relationships defined using `db.relationship` (e.g., User-Exam, Exam-Question, Question-Response, Response-Evaluation). Cascades (`all, delete-orphan`) configured where appropriate (e.g., deleting an Exam deletes its Questions).
    *   Enums (`UserRole`, `QuestionType`) used for predefined choices.
    *   Password hashing implemented using `werkzeug.security.generate_password_hash` and `check_password_hash`.
    *   Appropriate data types used (`db.DateTime`, `db.Integer`, `db.String`, `db.Text`, `db.Boolean`, `db.Float`, `db.JSON`).

*   **8.3. API Endpoints & Blueprints:**
    *   Functionality grouped into Blueprints (`auth`, `admin`, `teacher`, `student`) registered in `create_app`.
    *   Routes defined within each blueprint using `@bp.route(...)`.
    *   Endpoints return JSON responses using `jsonify`. Standard HTTP status codes used to indicate success/failure.

*   **8.4. Authentication & Authorization (JWT Custom Claims):**
    *   `Flask-JWT-Extended` configured in `create_app`.
    *   Login (`/auth/login`): Verifies credentials, creates a JWT using `create_access_token`.
        *   `identity`: Set to `str(user.id)`.
        *   `additional_claims`: A dictionary `{'user_info': {'id': user.id, 'role': user.role.name}}` is added.
    *   Decorators (`utils/decorators.py`):
        *   `@jwt_required()`: Built-in decorator, placed first to ensure a valid token exists.
        *   Custom Decorators (`@admin_required`, `@teacher_required`, `@student_required`, `@verified_required`):
            *   Use `verify_jwt_in_request()` internally (or rely on `@jwt_required` having run).
            *   Use helper functions (`utils/helpers.py`) `get_current_user_role()` and `get_current_user_id()` which extract data from the `user_info` custom claim via `get_jwt()`.
            *   Check the extracted role against the required role.
            *   Query the database using the extracted ID to check the `is_verified` status.
            *   Return `401` or `403` errors if checks fail.

*   **8.5. AI Evaluation Service (`services/ai_evaluation.py`):**
    *   Function `evaluate_response_with_gemini` encapsulates AI interaction.
    *   Takes question details and student answer as input.
    *   Constructs a detailed prompt for the Gemini 1.5 Flash model, explicitly requesting JSON output (`{"marks_awarded": float, "feedback": string}`) and outlining evaluation criteria.
    *   Uses the `google-generativeai` library to call the Gemini API.
    *   Includes retry logic (`@retry` from `tenacity`) for transient API errors.
    *   Parses the AI response: attempts to parse as JSON first; falls back to structured text parsing ("Marks: ...", "Feedback: ...") if JSON fails. Validates marks range.
    *   Returns `(marks, feedback)` tuple on success, or `(None, error_message)` on failure (API error, parsing error, safety block).
    *   Called by the `/admin/evaluate/response/<response_id>` endpoint.

*   **8.6. Database Interaction & Migrations:**
    *   Flask-SQLAlchemy provides the `db.session` for database operations (add, commit, rollback, query).
    *   Flask-Migrate used for managing schema evolution. Workflow: Modify `models.py` -> `flask db migrate` -> `flask db upgrade`. Direct `ALTER TABLE` commands are avoided.

*   **8.7. Backend Challenges & Solutions:**
    *   **JWT Identity Handling:** Initial "Subject must be string" error resolved by setting the primary `identity` to `str(user.id)` and storing the complex user information (ID, role) in `additional_claims`, accessed via `get_jwt()` in decorators. Removed `@jwt.user_identity_loader`.
    *   **AI Prompt Engineering:** Crafting a reliable prompt for Gemini that consistently returns the desired JSON format required iteration. Including explicit format instructions and validation criteria was key. Parsing logic handles both strict JSON and potential text variations.
    *   **Database Portability:** While development might use SQLite, care was taken to use SQLAlchemy features generally compatible with PostgreSQL (like `db.DateTime`, avoiding highly SQLite-specific functions in final query logic where possible). `make_interval` is PostgreSQL specific for date math.
    *   **Error Handling:** Standard `try...except` blocks used in routes to catch database errors or service failures, rollback sessions, log errors, and return appropriate JSON error responses.

**9. Database Design Overview:**

*(Simplified description, assumes relationships are set up correctly in models.py)*

*   `users`: Stores user credentials, role, verification status.
*   `exams`: Defines exam metadata, linked to the creating teacher (`users`).
*   `questions`: Defines individual questions, linked to an `exams`. Contains type-specific data (`options`, `correct_answer`, `word_limit`).
*   `student_responses`: Links a `users` (student) and a `questions` (within an `exams`), storing the submitted text/choice.
*   `evaluations`: Stores the grading result for a specific `student_responses`, including marks, AI feedback, and evaluator info.

**10. Deployment Strategy (Potential):**

*   **Backend (Flask):** Containerize using Docker. Deploy to platforms like Heroku (using Gunicorn), AWS ECS/EKS, Google Cloud Run/App Engine. Requires configuring environment variables (`DATABASE_URL`, `JWT_SECRET_KEY`, `GEMINI_API_KEY`, etc.).
*   **Frontend (Angular):** Build static assets (`ng build`). Host on static hosting providers like Netlify, Vercel, Firebase Hosting, AWS S3+CloudFront, or serve from the backend server (less common for SPAs). Configure environment files for production API URL.
*   **Database (PostgreSQL):** Use managed services like AWS RDS, Google Cloud SQL, or Heroku Postgres for scalability, backups, and maintenance.
*   **CORS:** Ensure Flask-Cors is configured correctly in production to allow requests only from the deployed frontend domain.

**11. Testing Strategy (Proposed):**

*   **Backend:**
    *   *Unit Tests (pytest):* Test individual functions (e.g., password hashing, AI prompt generation, response parsing), model logic.
    *   *Integration Tests (pytest with Flask test client):* Test API endpoints, database interactions, authentication logic, ensuring decorators work. Mock external AI service calls.
*   **Frontend:**
    *   *Unit Tests (Jasmine/Karma):* Test individual components, services (mocking dependencies like `AuthService`, `ApiService`).
    *   *Integration Tests:* Test component interactions within modules.
    *   *End-to-End Tests (Cypress/Protractor):* Simulate user flows (login, create exam, take exam, view results) in a real browser interacting with a test backend.
*   **Manual Testing:** Thoroughly test all user flows and edge cases using tools like Postman for the API and browsers for the frontend.

**12. Conclusion:**

The AI-Enhanced Online Exam Portal successfully meets the objectives of creating a modern, secure, and efficient platform for college assessments. The distinct roles, flexible question types, robust JWT authentication, and innovative AI-assisted evaluation provide significant advantages over traditional methods. The modular architecture in both the Angular frontend and Flask backend promotes maintainability and scalability. While challenges in JWT handling and AI integration were encountered, the implemented solutions provide a stable foundation. The portal significantly streamlines the examination process, reduces grading workload for subjective questions, and offers timely feedback, ultimately enhancing the educational experience.

**13. Future Work:**

*   Implement automatic MCQ grading.
*   Develop real-time proctoring features.
*   Build comprehensive analytics dashboards.
*   Add notifications (email/in-app).
*   Expand supported question types.
*   Allow Teachers to review/override AI evaluations.
*   Develop mobile applications.

---