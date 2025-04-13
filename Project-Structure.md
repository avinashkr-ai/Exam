exam-backend/
|-- app/
|   |-- __init__.py         # Application factory
|   |-- config.py           # Configuration settings
|   |-- models.py           # SQLAlchemy database models
|   |-- schemas.py          # Marshmallow schemas for serialization/validation
|   |-- resources/          # API Endpoints (Blueprints or Flask-RESTful Resources)
|   |   |-- __init__.py
|   |   |-- auth.py         # Authentication endpoints
|   |   |-- exams.py        # Exam CRUD and scheduling endpoints
|   |   |-- questions.py    # Question management endpoints
|   |   |-- submissions.py  # Student submission endpoints
|   |-- extensions.py       # Flask extensions initialization (db, migrate, jwt, ma, cors)
|   |-- utils.py            # Utility functions (e.g., decorators)
|   |-- services/           # Optional: Business logic layer
|-- migrations/             # Flask-Migrate migration files
|-- .env                    # Environment variables (DATABASE_URL, SECRET_KEY, JWT_SECRET_KEY)
|-- .flaskenv               # Flask environment variables (FLASK_APP, FLASK_DEBUG)
|-- requirements.txt        # Python dependencies
|-- run.py                  # Script to run the Flask development server



exam-frontend/
|-- angular.json            # Angular CLI configuration
|-- package.json            # Node dependencies
|-- tsconfig.json           # TypeScript configuration
|-- src/
|   |-- main.ts             # App entry point
|   |-- index.html          # Main HTML page
|   |-- styles.scss         # Global styles
|   |-- environments/       # Environment configurations (dev, prod)
|   |-- app/
|   |   |-- app.config.ts       # Main application configuration (providers, etc.)
|   |   |-- app.component.ts    # Root component
|   |   |-- app.component.html  # Root component template
|   |   |-- app.component.scss  # Root component styles
|   |   |-- app.routes.ts       # Main application routes
|   |   |
|   |   |-- core/                 # Core features (guards, interceptors, base services)
|   |   |   |-- guards/
|   |   |   |   |-- auth.guard.ts
|   |   |   |   |-- teacher.guard.ts
|   |   |   |   |-- student.guard.ts
|   |   |   |-- interceptors/
|   |   |   |   |-- auth.interceptor.ts # Adds JWT token to requests
|   |   |   |-- services/
|   |   |   |   |-- auth.service.ts
|   |   |   |   |-- storage.service.ts # Local/Session storage helper
|   |   |   |   |-- api.service.ts     # Base API interaction service
|   |   |   |-- models/             # TypeScript interfaces for API data
|   |   |       |-- user.model.ts
|   |   |       |-- exam.model.ts
|   |   |       |-- question.model.ts
|   |   |       |-- submission.model.ts
|   |   |
|   |   |-- features/             # Feature modules/components (routed)
|   |   |   |-- auth/
|   |   |   |   |-- login/
|   |   |   |   |-- register/
|   |   |   |-- teacher/
|   |   |   |   |-- dashboard/
|   |   |   |   |-- exam-create/
|   |   |   |   |-- exam-edit/
|   |   |   |   |-- view-submissions/
|   |   |   |-- student/
|   |   |   |   |-- dashboard/
|   |   |   |   |-- take-exam/
|   |   |   |   |-- view-results/
|   |   |
|   |   |-- shared/               # Shared components, pipes, directives
|   |       |-- components/
|   |       |   |-- navbar/
|   |       |   |-- question-form/ # Reusable form for different question types
|   |       |   |-- loading-spinner/
|   |       |-- pipes/
|   |       |-- directives/
|-- assets/                 # Static assets (images, etc.)