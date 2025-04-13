import os
from app import create_app

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

app = create_app()

if __name__ == '__main__':
    # Use a production WSGI server like Gunicorn or Waitress instead of app.run() for deployment
    # Example: gunicorn -w 4 run:app
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))