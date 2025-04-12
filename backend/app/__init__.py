import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS

from .config import config_by_name

# Initialize extensions without app context
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
cors = CORS()

def create_app(config_name=None):
    """Application Factory Function"""
    if config_name is None:
        config_name = os.getenv('FLASK_CONFIG', 'dev') # Default to 'dev' if not set

    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    # Initialize extensions with app context
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}}) # Allow all origins for /api/* routes

    # Import models here to ensure they are known to Flask-Migrate
    from . import models

    # Register Blueprints
    from .routers.auth import auth_bp
    from .routers.teacher import teacher_bp
    from .routers.student import student_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(teacher_bp, url_prefix='/api/teacher')
    app.register_blueprint(student_bp, url_prefix='/api/student')

    @app.route('/')
    def index():
        return "Exam Evaluation API Backend is running!"

    return app