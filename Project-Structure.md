```backend/
    |-- app/
    |   |-- __init__.py         # Application factory, blueprint registration
    |   |-- config.py           # Configuration settings
    |   |-- models.py           # SQLAlchemy database models
    |   |-- schemas.py          # Marshmallow schemas for serialization/validation
    |   |-- extensions.py       # Flask extensions initialization (db, migrate, jwt, ma, cors, bcrypt)
    |   |-- utils.py            # Decorators, password hashing etc.
    |   |-- auth/               # Authentication Blueprint
    |   |   |-- __init__.py     # Defines the auth blueprint
    |   |   `-- routes.py       # Login, register, refresh endpoints
    |   |-- users/              # User Management Blueprint (Admin focused)
    |   |   |-- __init__.py     # Defines the users blueprint
    |   |   `-- routes.py       # Verify, list, manage users
    |   |-- exams/              # Exam Management Blueprint
    |   |   |-- __init__.py     # Defines the exams blueprint
    |   |   `-- routes.py       # CRUD exams, publish, list available
    |   |-- questions/          # Question Management Blueprint
    |   |   |-- __init__.py     # Defines the questions blueprint
    |   |   `-- routes.py       # CRUD questions within exams
    |   |-- attempts/           # Exam Attempt & Submission Blueprint
    |   |   |-- __init__.py     # Defines the attempts blueprint
    |   |   `-- routes.py       # Get exam for attempt, submit responses
    |   |-- evaluations/        # Evaluation Blueprint
    |   |   |-- __init__.py     # Defines the evaluations blueprint
    |   |   `-- routes.py       # Trigger AI evaluation
    |   |-- results/            # Results Viewing Blueprint
    |   |   |-- __init__.py     # Defines the results blueprint
    |   |   `-- routes.py       # View results (student/teacher/admin)
    |   `-- services/           # Business logic / External services
    |       |-- __init__.py
    |       `-- ai_evaluator.py # AI evaluation logic
    |-- migrations/             # Flask-Migrate migration files
    |-- .env                    # Environment variables (DATABASE_URL, SECRET_KEY, JWT_SECRET_KEY, GEMINI_API_KEY)
    |-- .flaskenv               # Flask environment variables (FLASK_APP, FLASK_DEBUG)
    |-- requirements.txt        # Python dependencies
    `-- run.py                  # Script to run the Flask application```

````frontend/
    |-- src/
    |   |-- app/
    |   |   |-- core/                # Singleton services, guards, interceptors, core layout
    |   |   |   |-- components/
    |   |   |   |   |-- navbar/
    |   |   |   |-- guards/
    |   |   |   |   |-- auth.guard.ts
    |   |   |   |   |-- role.guard.ts
    |   |   |   |-- interceptors/
    |   |   |   |   |-- token.interceptor.ts
    |   |   |   |-- services/         # Often put services directly here or subfolder like auth/
    |   |   |   |   |-- auth.service.ts
    |   |   |   |   |-- api.service.ts  # Optional generic wrapper
    |   |   |   |-- core.module.ts
    |   |   |-- shared/              # Reusable components, pipes, directives
    |   |   |   |-- components/      # e.g., exam-list, question-display
    |   |   |   |-- pipes/
    |   |   |   |-- directives/
    |   |   |   |-- shared.module.ts
    |   |   |-- auth/                # Auth feature module (Login, Register, Profile)
    |   |   |   |-- components/
    |   |   |   |   |-- login/
    |   |   |   |   |-- register/
    |   |   |   |   |-- profile/      # Optional profile view
    |   |   |   |-- auth-routing.module.ts
    |   |   |   |-- auth.module.ts
    |   |   |-- teacher/             # Teacher feature module
    |   |   |   |-- components/
    |   |   |   |   |-- dashboard/
    |   |   |   |   |-- exam-create/
    |   |   |   |   |-- exam-detail/  # View/Edit exam, manage questions, schedule
    |   |   |   |   |-- submission-list/ # View submissions for an exam
    |   |   |   |   |-- grade-submission/ # Detail/Grade view for a submission
    |   |   |   |-- teacher-routing.module.ts
    |   |   |   |-- teacher.module.ts
    |   |   |-- student/             # Student feature module
    |   |   |   |-- components/
    |   |   |   |   |-- dashboard/    # View available exams
    |   |   |   |   |-- exam-taking/ # Component to take the exam
    |   |   |   |   |-- submission-history/ # View own past submissions
    |   |   |   |-- student-routing.module.ts
    |   |   |   |-- student.module.ts
    |   |   |-- models/              # Data structure interfaces
    |   |   |   |-- user.model.ts
    |   |   |   |-- exam.model.ts
    |   |   |   |-- question.model.ts
    |   |   |   |-- submission.model.ts
    |   |   |   |-- ...
    |   |   |-- app-routing.module.ts
    |   |   |-- app.component.ts
    |   |   |-- app.component.html
    |   |   |-- app.module.ts
    |   |-- assets/
    |   |-- environments/
    |   |   |-- environment.ts       # Development settings (e.g., API URL)
    |   |   |-- environment.prod.ts  # Production settings
    |   |-- ...
    |-- angular.json
    |-- package.json
    |-- tsconfig.json
```