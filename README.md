# NyaySaathi AI — Local Flask RAG Demo

This project is a local demonstration of a Retrieval-Augmented Generation (RAG) pipeline using Flask, LangChain, Google Gemini, and FAISS for answering questions about Indian law based on provided PDF documents.

## Prerequisites
 - Python 3.9+
 - `pip` and `venv`

## Setup & Running the Application

1.  **Clone the Repository**
    ```bash
    git clone <your-repo-url>
    cd nyaysaathi-ai
    ```

2.  **Create a Virtual Environment**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables**
    Copy the `.env.example` to `.env` and fill in your API key.
    ```bash
    cp .env.example .env
    # Now, edit the .env file with your GOOGLE_API_KEY
    ```

5.  **Add Legal Documents**
    Place your legal statute PDFs (e.g., `Constitution_of_India.pdf`, `IPC.pdf`) into the `data/` folder.

6.  **Run the Application**
    ```bash
    python run.py
    ```
    The application will be available at `http://127.0.0.1:5000`.

## How It Works

-   **First Run:** When you run the app for the first time, the `RAGService` will read all PDFs from the `/data` directory, split them into chunks, generate embeddings using the Gemini API, and save a searchable FAISS vector index to the `/nyaysaathi_faiss_index` directory. This may take a few moments.
-   **Subsequent Runs:** The application will load the pre-built FAISS index from the disk, which is much faster.
-   **To Re-build the Index:** Simply delete the `/nyaysaathi_faiss_index` directory and restart the application.

## Project Structure

This project uses a standard Flask application factory pattern for better organization and scalability.

-   `run.py`: The entry point to start the server.
-   `app/`: The main Flask application package.
    -   `__init__.py`: The application factory (`create_app`) which initializes Flask and the RAG service.
    -   `routes.py`: Contains the web endpoints (e.g., `/` and `/ask`).
    -   `services.py`: Encapsulates all the core RAG logic in the `RAGService` class.
    -   `static/` & `templates/`: Standard Flask folders for frontend assets.
-   `data/`: Directory for source PDF documents.
-   `nyaysaathi_faiss_index/`: Where the generated vector store is saved.