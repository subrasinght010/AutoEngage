from langchain.memory import ConversationBufferMemory
from ai_core.vector_db import add_to_vector_store

class MemoryManager:
    def __init__(self):
        self.memory = ConversationBufferMemory(return_messages=True)

    def add_message(self, role, message):
        if role == "user":
            self.memory.chat_memory.add_user_message(message)
            try:
                add_to_vector_store(message)
            except Exception as e:
                pass  
        else:
            self.memory.chat_memory.add_ai_message(message)

    def get_conversation_context(self):
        return self.memory.load_memory_variables({})
