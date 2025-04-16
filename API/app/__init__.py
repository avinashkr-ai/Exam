# app/__init__.py

from flask import Flask
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from config import Config # Import application configuration
from app.models import User, UserRole # Import models used by create-admin command
from werkzeug.security import generate_password_hash # For hashing admin password
from app.extensions import db, migrate # Import initialized extensions
import click # For Flask CLI commands
import os # Potentially needed for env vars, though Config handles it

# Initialize JWTManager globally but configure within create_app
jwt = JWTManager()

# Removed the @jwt.user_identity_loader as we use custom claims

def create_app(config_class=Config):
    """Factory function to create the Flask application instance."""
    app = Flask(__name__)
    # Load configuration from Config object
    app.config.from_object(config_class)

    # Enable Cross-Origin Resource Sharing (CORS)
    # Configure origins properly for production deployments
    CORS(app) # Allow all origins for development, restrict in production

    # Initialize database and migration engine with the app context
    db.init_app(app)
    migrate.init_app(app, db)

    # Initialize JWTManager with the app context
    # It will now use the JWT_SECRET_KEY from the app config
    jwt.init_app(app)

    # --- Register Blueprints ---
    # Import blueprint objects
    from app.routes.auth import bp as auth_bp
    from app.routes.admin import bp as admin_bp
    from app.routes.teacher import bp as teacher_bp
    from app.routes.student import bp as student_bp

    # Register blueprints with URL prefixes
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(teacher_bp, url_prefix='/teacher')
    app.register_blueprint(student_bp, url_prefix='/student')
    print("Blueprints registered.")

    # --- Simple Health Check Route ---
    @app.route('/')
    def index():
        """Basic route to check if the API is running."""
        return jsonify({"message": "Online Exam Portal API is running!"}), 200

    # --- CLI Command to Create Initial Admin User ---
    @app.cli.command('create-admin')
    def create_admin():
        """Creates the initial administrator user via CLI."""
        print("--- Create Admin User ---")
        name = input('Enter Admin Name: ')
        email = input('Enter Admin Email: ')
        password = input('Enter Admin Password: ')

        # Basic input validation
        if not name or not email or not password:
            click.echo("Error: Name, email, and password cannot be empty.", err=True)
            return

        # Check if admin or user with this email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            click.echo(f"Error: User with email '{email}' already exists (Role: {existing_user.role.name}).", err=True)
            return

        # Create the admin user instance
        # Admin is automatically verified
        admin_user = User(name=name, email=email, role=UserRole.ADMIN, is_verified=True)
        admin_user.set_password(password) # Hash the password

        try:
            # Add to session and commit to database
            db.session.add(admin_user)
            db.session.commit()
            click.echo(f"Admin user '{name}' ({email}) created successfully.")
        except Exception as e:
             # Rollback in case of database error
             db.session.rollback()
             click.echo(f"Error creating admin user: {e}", err=True)

    print("Flask app creation completed.")
    return app

# No changes were needed in this file for the UTC refactoring.