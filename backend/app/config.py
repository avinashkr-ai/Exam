import os
from dotenv import load_dotenv

# Load environment variables from .env file, especially for settings not managed by Flask's own loading
load_dotenv()

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'a-default-very-secret-key')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # JWT Configuration - More options available
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'a-default-jwt-secret-key')
    JWT_TOKEN_LOCATION = ["headers"]
    JWT_ACCESS_TOKEN_EXPIRES = False # Example: set to False for testing, use timedelta for prod
    # Consider using: from datetime import timedelta; JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)

    # CORS Configuration
    CORS_HEADERS = 'Content-Type'
    # Be more specific with origins in production:
    # CORS_ORIGINS = ["http://localhost:4200", "https://your-frontend-domain.com"]
    CORS_RESOURCES = {r"/api/*": {"origins": "*"}} # Allow all origins for /api/* routes for now

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///../instance/dev.db')
    SQLALCHEMY_ECHO = False # Set to True to log SQL queries

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL', 'sqlite:///../instance/test.db')
    # Use a separate database for tests
    BCRYPT_LOG_ROUNDS = 4 # Faster hashing for tests
    JWT_SECRET_KEY = 'test-jwt-secret-key'
    PRESERVE_CONTEXT_ON_EXCEPTION = False

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    # Ensure DATABASE_URL is set correctly in the production environment
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    if not SQLALCHEMY_DATABASE_URI:
        raise ValueError("No DATABASE_URL set for production environment")
    # Add other production-specific settings like logging, etc.

# Dictionary to easily select config based on environment variable
config_by_name = dict(
    development=DevelopmentConfig,
    testing=TestingConfig,
    production=ProductionConfig,
    default=DevelopmentConfig
)

def get_config():
    """Helper function to get config object based on FLASK_ENV"""
    env = os.getenv('FLASK_ENV', 'default')
    return config_by_name.get(env, DevelopmentConfig)