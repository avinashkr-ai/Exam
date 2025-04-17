```
├── API
    ├── README.md
    ├── app
    │   ├── __init__.py
    │   ├── __pycache__
    │   │   ├── __init__.cpython-311.pyc
    │   │   ├── extensions.cpython-311.pyc
    │   │   └── models.cpython-311.pyc
    │   ├── extensions.py
    │   ├── models.py
    │   ├── routes
    │   │   ├── __init__.py
    │   │   ├── __pycache__
    │   │   │   ├── __init__.cpython-311.pyc
    │   │   │   ├── admin.cpython-311.pyc
    │   │   │   ├── auth.cpython-311.pyc
    │   │   │   ├── student.cpython-311.pyc
    │   │   │   └── teacher.cpython-311.pyc
    │   │   ├── admin.py
    │   │   ├── auth.py
    │   │   ├── student.py
    │   │   ├── t.py
    │   │   └── teacher.py
    │   ├── services
    │   │   ├── __init__.py
    │   │   └── ai_evaluation.py
    │   └── utils
    │   │   ├── __pycache__
    │   │       ├── decorators.cpython-311.pyc
    │   │       └── helpers.cpython-311.pyc
    │   │   ├── decorators.py
    │   │   └── helpers.py
    ├── config.py
    ├── instance
    │   └── app.db
    ├── migrations
    │   ├── README
    │   ├── alembic.ini
    │   ├── env.py
    │   ├── script.py.mako
    │   └── versions
    │   │   └── 81a19105d58b_initial_database_schema_setup.py
    ├── requirements.txt
    ├── run.sh
    ├── setup.sh
    └── wsgi.py
├── Project-Structure.md
├── admin.md
├── new.md
├── online-exam-portal
    ├── .editorconfig
    ├── .gitignore
    ├── .vscode
    │   ├── extensions.json
    │   ├── launch.json
    │   └── tasks.json
    ├── angular.json
    ├── docs
    │   ├── favicon.ico
    │   ├── index.html
    │   ├── main-GW67GNQ5.js
    │   ├── polyfills-FFHMD2TL.js
    │   ├── scripts-EEEIPNC3.js
    │   └── styles-NEB3GHJL.css
    ├── package-lock.json
    ├── package.json
    ├── public
    │   └── favicon.ico
    ├── src
    │   ├── app
    │   │   ├── admin
    │   │   │   └── components
    │   │   │   │   ├── dashboard
    │   │   │   │       ├── dashboard.component.html
    │   │   │   │       └── dashboard.component.ts
    │   │   │   │   ├── evaluate-response
    │   │   │   │       ├── evaluate-response.component.html
    │   │   │   │       └── evaluate-response.component.ts
    │   │   │   │   ├── results-overview
    │   │   │   │       ├── results-overview.component.html
    │   │   │   │       └── results-overview.component.ts
    │   │   │   │   └── user-management
    │   │   │   │       ├── user-management.component.html
    │   │   │   │       └── user-management.component.ts
    │   │   ├── app.component.html
    │   │   ├── app.component.scss
    │   │   ├── app.component.ts
    │   │   ├── app.config.ts
    │   │   ├── app.routes.ts
    │   │   ├── auth
    │   │   │   └── components
    │   │   │   │   ├── login
    │   │   │   │       ├── login.component.html
    │   │   │   │       └── login.component.ts
    │   │   │   │   └── register
    │   │   │   │       ├── register.component.html
    │   │   │   │       └── register.component.ts
    │   │   ├── core
    │   │   │   ├── guards
    │   │   │   │   └── auth.guard.ts
    │   │   │   ├── interceptors
    │   │   │   │   └── auth.interceptor.ts
    │   │   │   ├── models
    │   │   │   │   ├── evaluation.ts
    │   │   │   │   ├── exam.ts
    │   │   │   │   ├── question.ts
    │   │   │   │   ├── response.ts
    │   │   │   │   └── user.ts
    │   │   │   └── services
    │   │   │   │   ├── api.service.ts
    │   │   │   │   ├── auth.service.ts
    │   │   │   │   └── error-handler.service.ts
    │   │   ├── shared
    │   │   │   └── components
    │   │   │   │   ├── error-alert
    │   │   │   │       ├── error-alert.component.html
    │   │   │   │       └── error-alert.component.ts
    │   │   │   │   ├── footer
    │   │   │   │       ├── footer.component.html
    │   │   │   │       └── footer.component.ts
    │   │   │   │   ├── header
    │   │   │   │       ├── header.component.html
    │   │   │   │       └── header.component.ts
    │   │   │   │   └── loading-spinner
    │   │   │   │       ├── loading-spinner.component.html
    │   │   │   │       └── loading-spinner.component.ts
    │   │   ├── student
    │   │   │   └── components
    │   │   │   │   ├── dashboard
    │   │   │   │       ├── dashboard.component.html
    │   │   │   │       └── dashboard.component.ts
    │   │   │   │   ├── exam-list
    │   │   │   │       ├── exam-list.component.html
    │   │   │   │       └── exam-list.component.ts
    │   │   │   │   ├── exam-take
    │   │   │   │       ├── exam-take.component.html
    │   │   │   │       └── exam-take.component.ts
    │   │   │   │   └── results
    │   │   │   │       ├── results.component.html
    │   │   │   │       └── results.component.ts
    │   │   └── teacher
    │   │   │   └── components
    │   │   │       ├── dashboard
    │   │   │           ├── dashboard.component.html
    │   │   │           └── dashboard.component.ts
    │   │   │       ├── exam-management
    │   │   │           ├── exam-management.component.html
    │   │   │           └── exam-management.component.ts
    │   │   │       ├── exam-results
    │   │   │           ├── exam-results.component.html
    │   │   │           └── exam-results.component.ts
    │   │   │       └── question-management
    │   │   │           ├── question-management.component.html
    │   │   │           └── question-management.component.ts
    │   ├── environments
    │   │   ├── environment.prod.ts
    │   │   └── environment.ts
    │   ├── index.html
    │   ├── main.ts
    │   └── styles.scss
    ├── tsconfig.app.json
    ├── tsconfig.json
    └── tsconfig.spec.json
├── report.md
├── student.md
├── synopsis.md
└── teacher.md
```