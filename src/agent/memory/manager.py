# src/agent/memory/manager.py

import chromadb
import uuid
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain.schema import BaseMessage, messages_from_dict, messages_to_dict
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from src.core.model_manager import model_manager
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
        self._embedding_model = None
        self._chroma_client = None

    def _initialize_components(self):
        """
        A private method to initialize components on first use.
        This prevents database calls during application startup.
        """
        # This function will only be called the first time a memory operation is needed.
        if self._embedding_model is None:
            # The database tables WILL exist by the time this is called.
            llm = model_manager.get_active_model()
            if not llm:
                raise Exception("Cannot initialize memory: No active LLM found.")
            self._embedding_model = GoogleGenerativeAIEmbeddings(model=llm.model_name)
        
        if self._chroma_client is None:
            self._chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIRECTORY)

    def _get_vector_store(self, user_id: int) -> Chroma:
        """
        Retrieves or creates a user-specific collection in ChromaDB.
        """
        # Ensure components are initialized before trying to use them.
        self._initialize_components()
        
        collection_name = f"user_{user_id}_semantic_memory"
        return Chroma(
            client=self._chroma_client,
            collection_name=collection_name,
            embedding_function=self._embedding_model,
        )

    # --- Public Methods for the Agent ---

    def get_chat_history(self, user_id: int, session_id: str) -> ChatMessageHistory:
        """
        Retrieves short-term episodic memory (chat history) from the SQL database.
        """
        db = database.SessionLocal()
        try:
            db_messages = crud.get_chat_history(db, session_id=session_id, user_id=user_id)
            # LangChain's helper functions convert our stored JSON back into message objects
            # Note: `message.message` is accessing the 'message' column of the ChatMessage model
            dict_messages = [messages_from_dict([message.message]) for message in db_messages]
            # Flatten the list of lists into a single list
            flat_messages = [item for sublist in dict_messages for item in sublist]
            return ChatMessageHistory(messages=flat_messages)
        finally:
            db.close()

    def add_chat_message(self, user_id: int, session_id: str, message: BaseMessage):
        """
        Adds a new message to the short-term episodic memory (SQL database).
        """
        db = database.SessionLocal()
        try:
            # Convert the LangChain message object to a JSON-serializable dictionary
            dict_message = messages_to_dict([message])
            # The result is a list with one item, we take the first
            crud.add_chat_message(db, session_id=session_id, message_json=dict_message[0], user_id=user_id)
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