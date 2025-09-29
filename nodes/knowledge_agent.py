# nodes/knowledge_agent.py
from tools.language_model import llm_query
from tools.vector_store import search_docs
from state.workflow_state import WorkflowState, lead_reducer

def knowledge_agent(state: WorkflowState) -> WorkflowState:
    last_message = state.conversation_thread[-1] if state.conversation_thread else ""
    
    # Fetch relevant company docs
    relevant_docs = search_docs(last_message, top_k=3)
    
    prompt = f"""
    You are an AI company agent.
    Only answer using the following company-approved data:
    {relevant_docs}

    Client message: {last_message}

    If the info is missing, politely say:
    "I’ll connect you with a human agent."
    """

    reply = llm_query(prompt)

    updates = {
        "pending_action": "communication_agent",
        "conversation_thread": state.conversation_thread + [f"Agent: {reply}"]
    }
    return lead_reducer(state, updates)
