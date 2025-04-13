from flask import Flask
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from config import Config
from app.models import User, UserRole
from werkzeug.security import generate_password_hash
from app.extensions import db, migrate
from app.extensions import db, migrate
import click

jwt = JWTManager()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    CORS(app) # Enable CORS for all routes - configure properly for production
    
     # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    # Register Blueprints
    from app.routes.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.routes.admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    from app.routes.teacher import bp as teacher_bp
    app.register_blueprint(teacher_bp, url_prefix='/teacher')

    from app.routes.student import bp as student_bp
    app.register_blueprint(student_bp, url_prefix='/student')

    # Optional: Add a simple root route for testing
    @app.route('/')
    def index():
        return "Online Exam Portal API is running!"

    # Add a command to create an admin user
    @app.cli.command('create-admin')
    def create_admin():
        """Creates an admin user."""
        email = input('Email: ')
        password = input('Password: ')

        if not email or not password:
            print("Error: Email and password are required.")
            return

        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            print(f"Error: User with email '{email}' already exists.")
            return

        admin_user = User(email=email, role=UserRole.ADMIN, is_verified=True, name="admin")
        admin_user.set_password(password)
       
        db.session.add(admin_user)
        db.session.commit()

        print(f"Admin user '{email}' created successfully.")


    return app

# Import models here to avoid circular imports with blueprints
from app import models