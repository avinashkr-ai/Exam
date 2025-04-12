import os
from app import create_app, db # Import db as well for migration commands context

# Create app instance using the factory
config_name = os.getenv('FLASK_CONFIG', 'dev')
app = create_app(config_name)

# This is needed for Flask-Migrate commands to find the app and db
@app.shell_context_processor
def make_shell_context():
    from app import models # Import models here for shell context
    return {'db': db, 'User': models.User, 'Exam': models.Exam, 'Question': models.Question,
            'Submission': models.Submission, 'SubmittedAnswer': models.SubmittedAnswer,
            'Result': models.Result, 'ExamQuestion': models.ExamQuestion}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) # Listen on all interfaces if needed