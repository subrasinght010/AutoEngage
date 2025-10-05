"""
Knowledge Agent - Uses RAG to answer queries
"""

from state.workflow_state import WorkflowState, lead_reducer
from tools.vector_store import query_knowledge_base
from tools.language_model import LanguageModel

llm = LanguageModel()


def knowledge_agent(state: WorkflowState) -> WorkflowState:
    """
    Query knowledge base and generate response using RAG
    """
    last_message = state.conversation_thread[-1] if state.conversation_thread else ""
    
    # Extract user query (remove timestamp/prefix)
    user_query = last_message.split(": ", 1)[-1] if ": " in last_message else last_message
    
    # Query RAG system
    print(f"🔍 Querying knowledge base for: {user_query}")
    relevant_docs = query_knowledge_base(user_query, top_k=3, relevance_threshold=0.7)
    
    if not relevant_docs:
        # No relevant knowledge found
        response = (
            "I don't have specific information about that in my knowledge base. "
            "Would you like me to connect you with a specialist who can help?"
        )
        
        updates = {
            "pending_action": "escalate_to_human",
            "conversation_thread": state.conversation_thread + [f"Agent: {response}"]
        }
        return lead_reducer(state, updates)
    
    # Format context from retrieved documents
    rag_context = "\n\n".join([
        f"[Source: {doc['metadata'].get('source', 'Unknown')}]\n{doc['content']}"
        for doc in relevant_docs
    ])
    
    # Generate response using LLM with RAG context
    prompt = f"""Based ONLY on the following company knowledge, answer the user's question.
        If the answer is not in the provided knowledge, say you don't have that information.

        Company Knowledge:
        {rag_context}

        User Question: {user_query}

        Provide a helpful, concise answer in 2-3 sentences:"""
            
    response = llm.generate(prompt)
    
    # Update state
    updates = {
        "pending_action": "communication_agent",
        "conversation_thread": state.conversation_thread + [f"Agent (with knowledge): {response}"],
        "knowledge_used": True
    }
    
    return lead_reducer(state, updates)