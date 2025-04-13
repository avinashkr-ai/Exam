import os
from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException # Import HTTPException
from marshmallow import ValidationError # Import ValidationError

from .config import get_config
from .extensions import db, migrate, ma, jwt, cors, bcrypt
from . import models # Import models to register them with SQLAlchemy

def create_app():
    """Application Factory Function"""
    app = Flask(__name__, instance_relative_config=True)

    # --- Load Configuration ---
    config = get_config()
    app.config.from_object(config)

    # Ensure the instance folder exists (for SQLite)
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass # Already exists

    # --- Initialize Extensions ---
    db.init_app(app)
    migrate.init_app(app, db)
    ma.init_app(app)
    jwt.init_app(app)
    bcrypt.init_app(app)
    # Initialize CORS with config settings or defaults
    cors.init_app(app, resources=app.config.get('CORS_RESOURCES', {r"/api/*": {"origins": "*"}}))

    # --- Register Blueprints ---
    with app.app_context():
        from .resources import auth, exams, questions, submissions

        app.register_blueprint(auth.bp) # Prefix defined in auth.py
        app.register_blueprint(exams.bp) # Prefix defined in exams.py
        app.register_blueprint(questions.bp) # Prefix defined in questions.py (includes /exams/<id>)
        app.register_blueprint(submissions.bp) # Prefix defined in submissions.py

        # --- Database Creation (for development/testing convenience) ---
        # In production, rely solely on Flask-Migrate upgrade commands
        if app.config['DEBUG'] or app.config['TESTING']:
             # Check if tables exist before creating - avoids issues if run multiple times
             # inspector = db.inspect(db.engine)
             # if not inspector.has_table("user"): # Check for one table
             #     print("Creating database tables...")
             #     db.create_all()
             # Rely on migrations is generally better practice even in dev
             pass

    # --- Global Error Handlers ---
    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        """Return JSON instead of HTML for HTTP errors."""
        response = e.get_response()
        response.data = jsonify({
            "code": e.code,
            "name": e.name,
            "message": e.description, # Use description for message
        }).data
        response.content_type = "application/json"
        return response

    @app.errorhandler(ValidationError)
    def handle_marshmallow_validation(err):
        """Catch Marshmallow validation errors globally."""
        return jsonify(errors=err.messages), 400

    @app.errorhandler(Exception)
    def handle_generic_exception(e):
        """Handle unexpected errors."""
        # Log the error in production
        app.logger.error(f"Unhandled Exception: {str(e)}", exc_info=True)

        # Return a generic 500 error in production
        if not app.config['DEBUG'] and not app.config['TESTING']:
            return jsonify(message="An internal server error occurred"), 500

        # Return detailed error in debug/testing
        return jsonify(
            message="An unexpected error occurred",
            error=str(e)
        ), 500


    # --- Shell Context Processor (Optional) ---
    @app.shell_context_processor
    def make_shell_context():
        return {'db': db, 'User': models.User, 'Exam': models.Exam, 'Question': models.Question,
                'Option': models.Option, 'Submission': models.Submission, 'Answer': models.Answer}

    return app