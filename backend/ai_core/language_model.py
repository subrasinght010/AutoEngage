import os
import logging
from dotenv import load_dotenv
from langchain.chat_models import ChatOpenAI
from ai_core.memory_manager import MemoryManager
from ai_core.vector_db import search_vector_db

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("Missing OPENAI_API_KEY in environment variables")

llm = ChatOpenAI(model_name="gpt-4-turbo", openai_api_key=api_key)

memory = MemoryManager()
MAX_MEMORY = 10  

def generate_response(query: str) -> str:
    try:
        retrieved_docs = search_vector_db(query, top_k=3)
        past_messages = memory.get_conversation_context().get("history", [])[-MAX_MEMORY:]

        context = "\n".join([doc['text'] for doc in retrieved_docs]) if retrieved_docs else "No relevant documents found."

        full_prompt = f"Context:\n{context}\n\n" + (f"Past Messages:\n{past_messages}\n\n" if past_messages else "") + f"Query: {query}"

        response = llm.predict(full_prompt).strip()

        memory.add_message("user", query)
        memory.add_message("assistant", response)

        logger.info(f"Query: {query} | Response: {response}")

        return response

    except Exception as e:
        logger.error(f"Error in AI response generation: {e}")
        return "I'm sorry, but I encountered an error while processing your request."
