from chromadb import Client
from chromadb.config import Settings

# Initialize Chroma client
chroma_client = Client(
    Settings(
        chroma_api_impl="rest",
        chroma_server_host="http://localhost:8000"  # Docker container Chroma API
    )
)

# Create or get a collection for conversation embeddings
conversation_collection = chroma_client.get_or_create_collection(name="conversation_embeddings")

def add_embedding(conversation_id: str, lead_id: int, text: str, embedding: list):
    conversation_collection.add(
        ids=[conversation_id],
        embeddings=[embedding],
        metadatas=[{"lead_id": lead_id}],
        documents=[text]
    )


def query_embeddings(query_vector: list, n_results: int = 5):
    return conversation_collection.query(
        query_embeddings=[query_vector],
        n_results=n_results
    )

