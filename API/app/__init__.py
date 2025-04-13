# app/__init__.py
from flask import Flask
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from config import Config
from app.models import User, UserRole # Import if needed for create-admin
from werkzeug.security import generate_password_hash
from app.extensions import db, migrate
import click

# Initialize JWTManager here
jwt = JWTManager()

# --- REMOVE THIS SECTION ---
# @jwt.user_identity_loader
# def user_identity_lookup(user_identity_dict):
#    # ... function body ...
#    pass # Remove the whole function and decorator
# --- END REMOVAL ---

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    CORS(app)

    db.init_app(app)
    migrate.init_app(app, db)
    # Initialize JWT *without* the loader callback
    jwt.init_app(app)

    # Register Blueprints (no changes here)
    from app.routes.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    from app.routes.admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')
    from app.routes.teacher import bp as teacher_bp
    app.register_blueprint(teacher_bp, url_prefix='/teacher')
    from app.routes.student import bp as student_bp
    app.register_blueprint(student_bp, url_prefix='/student')

    @app.route('/')
    def index():
        return "Online Exam Portal API is running!"

    # create-admin command (no changes needed here)
    @app.cli.command('create-admin')
    def create_admin():
        """Creates an admin user."""
        name = input('Admin Name: ')
        email = input('Email: ')
        password = input('Password: ')

        if not name or not email or not password:
            print("Error: Name, email, and password are required.")
            return

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            print(f"Error: User with email '{email}' already exists.")
            return

        admin_user = User(name=name, email=email, role=UserRole.ADMIN, is_verified=True)
        admin_user.set_password(password)

        try:
            db.session.add(admin_user)
            db.session.commit()
            print(f"Admin user '{name}' ({email}) created successfully.")
        except Exception as e:
             db.session.rollback()
             print(f"Error creating admin user: {e}")

    return app