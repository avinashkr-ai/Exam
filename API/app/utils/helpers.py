# app/utils/helpers.py
from flask_jwt_extended import get_jwt_identity
from flask import jsonify # Added for potential error handling

def get_current_user_id():
    """Extracts the user ID from the JWT identity dictionary."""
    identity = get_jwt_identity()
    # Ensure identity is a dictionary and has the 'id' key
    if isinstance(identity, dict) and 'id' in identity:
        return identity['id']
    else:
        # This case should ideally not happen if login sets identity correctly
        # Log this error if it occurs
        print(f"Error: Invalid JWT identity format: {identity}")
        # Consider raising an exception or returning an error response
        # For now, returning None, but routes using this should handle it.
        # A better approach might be to force re-authentication
        # return jsonify({"msg": "Invalid authentication token"}), 401
        return None # Or raise an error