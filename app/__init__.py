# app/__init__.py
import os
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

# Import your new RAG service
from .services import RAGService


def create_app():
    """Create and configure an instance of the Flask application."""
    load_dotenv()

    app = Flask(__name__)
    CORS(app)
    app.config['SECRET_KEY'] = os.getenv(
        "FLASK_SECRET_KEY", "a-default-secret-key")
    
    # Configuration
    app.config['UPLOAD_FOLDER'] = 'temp_uploads'
    app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'txt', 'docx'}

    # Ensure the upload folder exists
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    # Initialize and attach the RAG service to the app instance
    # This is better than a global variable. The service and its chain
    # are loaded once when the app starts.
    try:
        app.rag_service = RAGService()
        print("[Flask App] RAG Service initialized successfully.")
    except Exception as e:
        print(f"[Flask App] CRITICAL: Failed to initialize RAG Service: {e}")
        # Depending on the desired behavior, you might want to exit or handle this.
        # For now, we'll let it run but it will fail on /ask requests.
        app.rag_service = None

    # Register the blueprint
    from . import routes
    app.register_blueprint(routes.main_bp)

    return app
