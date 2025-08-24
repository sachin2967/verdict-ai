# app/services.py
import os
from pathlib import Path
from typing import List

# LangChain and related imports
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from pypdf import PdfReader
from langchain.chains.summarize import load_summarize_chain

# --- IMPORTS FOR THE NEW LCEL APPROACH ---
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
# --- END NEW IMPORTS ---


class RAGService:
    """
    Encapsulates the entire RAG pipeline logic.
    """

    def __init__(self,
                 data_dir: str = os.getenv("DATA_DIR", "./data"),
                 index_path: str = os.getenv(
                     "FAISS_INDEX_PATH", "./nyaysaathi_faiss_index"),
                 chunk_size: int = 1000,
                 chunk_overlap: int = 200):

        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        if not self.google_api_key:
            raise ValueError(
                "GOOGLE_API_KEY not found in environment variables.")

        self.data_dir = data_dir
        self.index_path = index_path
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # Initialize components
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001", google_api_key=self.google_api_key)
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", google_api_key=self.google_api_key, temperature=0.4)
        self.vector_store = self._load_or_build_vector_store()
        self.qa_chain = self._setup_conversational_chain()

    def _load_pdfs(self) -> List[Document]:
        """Reads all PDFs from the data directory."""
        docs = []
        data_path = Path(self.data_dir)
        pdf_files = list(data_path.glob("*.pdf"))

        if not pdf_files:
            raise FileNotFoundError(
                f"No PDF files found in the directory: {self.data_dir}")

        for pdf_path in pdf_files:
            reader = PdfReader(pdf_path)
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text and text.strip():
                    docs.append(Document(
                        page_content=text.strip(),
                        metadata={"source": pdf_path.name, "page": i + 1}
                    ))
        return docs

    def _load_or_build_vector_store(self, rebuild: bool = False):
        """Loads a FAISS index from disk or builds it if it doesn't exist."""
        index_dir = Path(self.index_path)
        required_files = [index_dir / "index.faiss", index_dir / "index.pkl"]
        index_is_valid = all(f.exists() for f in required_files)

        if index_is_valid and not rebuild:
            print(
                f"[RAGService] Loading existing FAISS index from {self.index_path}")
            return FAISS.load_local(str(index_dir), self.embeddings, allow_dangerous_deserialization=True)

        print(
            f"[RAGService] No valid index found. Building new index from PDFs in {self.data_dir}")
        raw_docs = self._load_pdfs()

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap)
        split_docs = splitter.split_documents(raw_docs)

        print(
            f"[RAGService] Creating FAISS index from {len(split_docs)} document chunks...")
        db = FAISS.from_documents(split_docs, self.embeddings)
        index_dir.mkdir(parents=True, exist_ok=True)
        db.save_local(str(index_dir))
        print(f"[RAGService] FAISS index saved to {self.index_path}")
        return db

    def _setup_conversational_chain(self):
        """Sets up the conversational retrieval chain using the modern LCEL approach."""

       
        retriever = self.vector_store.as_retriever(
            search_type="similarity", search_kwargs={"k": 7})

        # 1. Contextualize Question Prompt
        # This prompt rephrases the user's question to be a standalone question
        # based on the chat history.
        contextualize_q_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "Given a chat history and the latest user question which might reference context in the chat history, formulate a standalone question which can be understood without the chat history. Do NOT answer the question, just reformulate it if needed and otherwise return it as is."),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )

        # 2. Create the History-Aware Retriever
        # This chain takes the user's input and chat history, uses the LLM to create a better search query, and retrieves documents.
        history_aware_retriever = create_history_aware_retriever(
            self.llm, retriever, contextualize_q_prompt
        )

        
        # ALTERNATIVE Answering Prompt
        qa_system_prompt = """You are Verdict, a specialized AI legal assistant for Indian law. Your behavior changes based on the user's input.

        **Greeting Mode:**
        If the user provides a simple greeting like "hello" or "hi", respond with a professional greeting. For example: "Hello, I am Verdict, your AI legal assistant. How can I help you with your query today?" Do not use the context or citations for greetings.

        **Question-Answering Mode:**
        For any other input, you must act as a legal analyst. Follow these rules strictly:
        1.  Analyze the CONTEXT below to answer the user's question.
        2.  Your answer must be derived ONLY from the legal documents provided in the CONTEXT section.
        3.  Provide a clear and concise response formatted using Markdown. Use bullet points (`*`) for lists.
        4.  After each piece of information, you MUST provide an inline citation in the format `[Source: filename.pdf, Page X]`.
        5.  If the context does not contain the information to answer, respond with: "I do not have sufficient information in the provided legal documents to answer that question."
        6.  Do not use any external knowledge.

        CONTEXT:
        {context}

        Question: {input}
        Answer (in Markdown):"""

        qa_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", qa_system_prompt),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )

        # 4. Create the main document processing chain
        question_answer_chain = create_stuff_documents_chain(self.llm, qa_prompt)

        # 5. Combine the retriever and the answering chain
        rag_chain = create_retrieval_chain(
            history_aware_retriever, question_answer_chain)

        return rag_chain

    def ask_question(self, question: str, chat_history: list):
        """Processes a question using the RAG chain with the modern .invoke() method."""
        if not self.qa_chain:
            raise RuntimeError("QA Chain is not initialized.")

        # Format chat history for the new chain
        formatted_history = []
        for q, a in chat_history:
            formatted_history.append(HumanMessage(content=q))
            formatted_history.append(AIMessage(content=a))

        # Use .invoke() instead of the old __call__ method
        response = self.qa_chain.invoke({
            "input": question,
            "chat_history": formatted_history
        })

        # The new chain returns source documents in a different key
        response['source_documents'] = response.get('context', [])
        return response
    
    def summarize_document(self, file_path: str) -> str:
        """
        Loads a PDF from a given path and returns a summary.
        """
        if not self.qa_chain:  # Using qa_chain's llm
            raise RuntimeError("Chain is not initialized.")

        print(f"[RAGService] Loading document for summarization: {file_path}")
        try:
            loader = PdfReader(file_path)
            docs_to_summarize = []
            for i, page in enumerate(loader.pages):
                text = page.extract_text()
                if text and text.strip():
                    docs_to_summarize.append(Document(
                        page_content=text.strip(),
                        metadata={"source": os.path.basename(
                            file_path), "page": i + 1}
                    ))
        except Exception as e:
            return f"Error loading or reading the PDF file: {e}"

        if not docs_to_summarize:
            return "Could not extract any text from the document."

        # # Get the LLM from your existing chain
        # # This is a way to access the LLM without re-initializing it.
        # # The 'question_answer_chain' is the last part of your rag_chain.
        # llm = self.qa_chain.steps[-1].llm

        # Use the 'map_reduce' chain type for long documents
        summary_chain = load_summarize_chain(llm=self.llm, chain_type="map_reduce")

        print("[RAGService] Generating summary...")
        summary_result = summary_chain.invoke(docs_to_summarize)

        return summary_result.get('output_text', "Sorry, I was unable to generate a summary.")
