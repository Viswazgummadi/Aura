# src/agent/memory/manager.py

import chromadb
import uuid
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain.schema import BaseMessage, messages_from_dict, messages_to_dict
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import json
from src.core.model_manager import llm_manager
from src.database import crud, database

# --- Configuration ---
# This sets up a persistent, file-based vector store in our project directory.
CHROMA_PERSIST_DIRECTORY = "./chroma_db"

class MemoryManager:
    def __init__(self):
        """
        Initializes the MemoryManager without loading heavy components.
        Components will be lazy-loaded on their first use.
        """
        self._embedding_model_cache: dict[int, GoogleGenerativeAIEmbeddings] = {}
        self._chroma_client = None

    def _initialize_user_components(self, user_id: int):
        """
        A private method to initialize components for a specific user on first use.
        It now fetches the user's specific API key.
        """
        # Check if we've already created an embedding model for this user.
        if user_id not in self._embedding_model_cache:
            db = database.SessionLocal()
            try:
                # Get THIS user's API key for Google.
                api_key_obj = crud.get_user_api_key_for_provider(db, user_id=user_id, provider_name="google")
                if not api_key_obj:
                    raise Exception(f"Cannot initialize memory for user {user_id}: No active Google API key found.")
                
                embedding_model = GoogleGenerativeAIEmbeddings(
                    model="models/embedding-001",
                    google_api_key=api_key_obj.key
                )
                # Cache the model instance for this user.
                self._embedding_model_cache[user_id] = embedding_model
                print(f"INFO: [User {user_id}] Initialized embedding model using their API key ID {api_key_obj.id}")
            finally:
                db.close()
        
        # Chroma client is global and can be initialized once.
        if self._chroma_client is None:
            self._chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIRECTORY)

    def _get_vector_store(self, user_id: int) -> Chroma:
        """
        Retrieves or creates a user-specific collection in ChromaDB.
        """
        # Ensure components for this user are initialized.
        self._initialize_user_components(user_id)
        
        collection_name = f"user_{user_id}_semantic_memory"
        return Chroma(
            client=self._chroma_client,
            collection_name=collection_name,
            # Use the cached embedding model for this specific user.
            embedding_function=self._embedding_model_cache[user_id],
        )

    # --- Public Methods for the Agent ---

    def get_chat_history(self, user_id: int, session_id: str) -> ChatMessageHistory:
        """
        Retrieves short-term episodic memory (chat history) from the SQL database.
        """
        db = database.SessionLocal()
        try:
            db_messages = crud.get_chat_history(db, session_id=session_id, user_id=user_id)
            
            # --- IMPROVED VERSION ---
            # This is a more direct and readable way to achieve the same result.
            langchain_messages = []
            for msg in db_messages:
                # The 'message' field in the DB is a JSON string of a single-item list.
                # 1. Load the string into a Python list of dicts.
                # 2. Get the first (and only) item from that list.
                message_dict = json.loads(msg.message)
                # 3. Convert that single dictionary into a LangChain message object.
                langchain_messages.extend(messages_from_dict([message_dict]))
                
            return ChatMessageHistory(messages=langchain_messages)
        finally:
            db.close()

    def add_chat_message(self, user_id: int, session_id: str, message: BaseMessage):
        """
        Adds a new message to the short-term episodic memory (SQL database).
        """
        db = database.SessionLocal()
        try:
            dict_message = messages_to_dict([message])
            # Pass the dictionary to the crud function
            crud.add_chat_message(db, session_id=session_id, message_json_dict=dict_message[0], user_id=user_id)
        finally:
            db.close()

    def add_to_long_term_memory(self, user_id: int, content: str):
        """
        Adds a piece of information to the user's long-term semantic memory (Vector Store).
        This is how the agent "learns" a new fact about the user.
        """
        vector_store = self._get_vector_store(user_id)
        vector_store.add_texts(texts=[content])
        print(f"INFO: Added to long-term memory for user {user_id}: '{content}'")

    def search_long_term_memory(self, user_id: int, query: str, k: int = 5) -> list[str]:
        """
        Performs a semantic search on the user's long-term memory.
        Returns the `k` most relevant pieces of information.
        """
        vector_store = self._get_vector_store(user_id)
        results = vector_store.similarity_search(query=query, k=k)
        return [doc.page_content for doc in results]

# Create a single, global instance for the application to use
memory_manager = MemoryManager()