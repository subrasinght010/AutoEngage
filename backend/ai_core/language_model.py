import os
import logging
from dotenv import load_dotenv
from llama_cpp import Llama
from ai_core.memory_manager import MemoryManager
from ai_core.vector_db import search_vector_db

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Load local OpenChat 3.5 model
llm = Llama(
    model_path=os.path.join(os.path.dirname(__file__), "models", "openchat-3.5-1210.Q5_K_M.gguf"),
    n_ctx=2048,
    n_threads=4,
    n_gpu_layers=20,  # tweak this for faster M2 performance
    verbose=False
)

memory = MemoryManager()
MAX_MEMORY = 10  

def generate_response(query: str) -> str:
    try:
        # Retrieve relevant documents from vector database
        retrieved_docs = search_vector_db(query, top_k=3)
        past_messages = memory.get_conversation_context().get("history", [])[-MAX_MEMORY:]

        # Prepare context from retrieved documents and past conversation history
        context = "\n".join([doc['text'] for doc in retrieved_docs]) if retrieved_docs else "No relevant documents found."

        full_prompt = f"Context:\n{context}\n\n" + (f"Past Messages:\n{past_messages}\n\n" if past_messages else "") + f"Query: {query}"

        # Use local OpenChat 3.5 model for generating the response
        response = llm(full_prompt, max_tokens=256, temperature=0.7, stop=["User:", "Agent:"])['choices'][0]['text'].strip()

        # Update conversation history
        memory.add_message("user", query)
        memory.add_message("assistant", response)

        logger.info(f"Query: {query} | Response: {response}")

        return response

    except Exception as e:
        logger.error(f"Error in AI response generation: {e}")
        return "I'm sorry, but I encountered an error while processing your request."
