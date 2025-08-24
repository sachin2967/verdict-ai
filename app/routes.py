# app/routes.py
import os
from flask import Blueprint, request, jsonify, render_template, session, current_app
from langchain_core.messages import HumanMessage, AIMessage
from werkzeug.utils import secure_filename

main_bp = Blueprint('main', __name__)


def allowed_file(filename):
    """Check if the file has an allowed extension."""
    allowed_extensions = current_app.config['ALLOWED_EXTENSIONS']  # Use app config to get allowed extensions
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions


@main_bp.route("/")
def home():
    """Renders the landing page."""
    return render_template("home.html")


@main_bp.route("/chat")
def chat():
    """Renders the main chat interface."""
    # Clear session history when starting a new chat session for a clean slate
    session.pop('chat_history', None)
    return render_template("chat.html")


@main_bp.route("/ask", methods=["POST"])
def ask():
    """Handles the user's question and returns the AI's answer."""
    data = request.get_json()
    if not data or "question" not in data:
        return jsonify({"error": "Missing 'question' in request body."}), 400
    
    question = data.get("question", "").strip()
    if not question:
        return jsonify({"error": "Question cannot be empty."}), 400

    rag_service = current_app.rag_service
    if not rag_service:
        return jsonify({"error": "The RAG service is not available. Please check server logs."}), 503

    chat_history = session.get("chat_history", [])

    try:
        # The LCEL chain expects a specific input format
        response = rag_service.ask_question(question, chat_history)
        answer = response.get("answer", "No answer found.")

        sources = []
        if 'source_documents' in response:
            # Use a set to avoid duplicate sources in the UI
            unique_sources = {(doc.metadata['source'], doc.metadata['page'])
                              for doc in response['source_documents']}
            for source, page in sorted(list(unique_sources)):
                sources.append({"source": source, "page": page})

        # Update session chat history
        chat_history.append((question, answer))
        session["chat_history"] = chat_history[-5:]  # Keep last 5 interactions

        return jsonify({"answer": answer, "sources": sources})

    except Exception as e:
        print(f"Error during question asking: {e}")
        return jsonify({"error": f"An internal error occurred: {e}"}), 500

# This API endpoint remains the same


# In app/routes.py

# 1. Allow both GET and POST
@main_bp.route('/summarize', methods=['GET', 'POST'])
def summarize_endpoint():
    # 2. Check if the request is a POST request (form submission)
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({"error": "No file part in the request"}), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(
                current_app.config['UPLOAD_FOLDER'], filename)

            try:
                file.save(filepath)
                summary = current_app.rag_service.summarize_document(filepath)
                return jsonify({"summary": summary})

            except Exception as e:
                # Add this print statement for better debugging!
                print(f"Error during summarization: {e}")
                return jsonify({"error": f"An error occurred: {str(e)}"}), 500

            finally:
                if os.path.exists(filepath):
                    os.remove(filepath)
        else:
            return jsonify({"error": "Invalid file type. Please upload a PDF."}), 400

    # 3. If it's a GET request, just show the page
    # Or whatever your HTML file is called
    return render_template("summarize.html")
