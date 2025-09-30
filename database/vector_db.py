import os
from langchain.vectorstores import FAISS
from langchain.embeddings.openai import OpenAIEmbeddings

# Initialize Embeddings
openai_api_key = os.getenv("OPENAI_API_KEY")
embeddings = OpenAIEmbeddings(api_key=openai_api_key)

# FAISS Index Storage Path
db_path = "backend/database/vector_store"

def initialize_vector_store():
    """Loads or creates a FAISS vector store."""
    if os.path.exists(db_path):
        return FAISS.load_local(db_path, embeddings)
    return FAISS.from_texts([], embeddings)

vector_store = initialize_vector_store()

def add_to_vector_store(text):
    """Adds a new text embedding dynamically to FAISS."""
    vector_store.add_texts([text])
    vector_store.save_local(db_path)

def search_vector_db(query, top_k=5):
    """Retrieves similar conversations from FAISS."""
    return vector_store.similarity_search(query, k=top_k)
