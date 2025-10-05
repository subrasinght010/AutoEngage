"""
Intent Detector with RAG integration
"""

from state.workflow_state import WorkflowState, lead_reducer
from tools.language_model import LanguageModel
from tools.vector_store import query_knowledge_base
import json

llm = LanguageModel()


def intent_detector_llm(state: WorkflowState) -> WorkflowState:
    """
    Detect intent and generate response with RAG context
    """
    last_message = state.conversation_thread[-1] if state.conversation_thread else ""
    
    if not last_message:
        return state
    
    # Extract user message
    user_message = last_message.split(": ", 1)[-1] if ": " in last_message else last_message
    
    # Query RAG for relevant knowledge
    print(f"🔍 Querying RAG for: {user_message}")
    relevant_docs = query_knowledge_base(user_message, top_k=3)
    
    # Format RAG context
    rag_context = ""
    if relevant_docs:
        rag_context = "\n\n**Company Knowledge Context:**\n"
        for doc in relevant_docs:
            rag_context += f"- {doc['content'][:200]}...\n"
    else:
        rag_context = "\n\n**Company Knowledge Context:** No relevant information found in knowledge base.\n"
    
    # Build conversation history
    recent_history = state.conversation_thread[-5:] if len(state.conversation_thread) > 5 else state.conversation_thread
    conversation_history = "\n".join(recent_history)
    
    # LLM Prompt with RAG
    prompt = f"""You are an AI support agent for TechCorp.

**CRITICAL: Answer using ONLY the Company Knowledge Context below. If info is not there, say you'll connect with a specialist.**

{rag_context}

**Your Task:**
1. Analyze the user message
2. Detect intent (callback_request, send_details_email, product_query, etc.)
3. Generate natural response using company knowledge
4. Return structured JSON

**Conversation History:**
{conversation_history}

**Current User Message:** {user_message}

**Respond in JSON format:**
{{
  "immediate_response": "Natural conversational response",
  "intent": "callback_request|send_details_email|send_details_sms|send_details_whatsapp|product_query|policy_query|complaint|general_inquiry",
  "entities": {{
    "callback_time": null,
    "channel": null,
    "email": null,
    "phone": null,
    "whatsapp_number": null,
    "details_type": null,
    "missing_info": []
  }},
  "needs_clarification": false,
  "clarification_question": null,
  "actions": [],
  "used_knowledge": true,
  "escalate_to_human": false
}}

JSON Response:"""
    
    # Call LLM
    llm_response_text = llm.generate(prompt)
    
    # Parse JSON
    try:
        llm_response = json.loads(llm_response_text)
    except json.JSONDecodeError:
        # Fallback if JSON parsing fails
        llm_response = {
            "immediate_response": "I'm having trouble processing that. Could you please rephrase?",
            "intent": "general_inquiry",
            "entities": {},
            "needs_clarification": True,
            "actions": []
        }
    
    # Update state
    updates = {
        "preferred_channel": llm_response.get("entities", {}).get("channel"),
        "pending_action": "communication_agent" if not llm_response.get("needs_clarification") else "wait_for_clarification",
        "conversation_thread": state.conversation_thread + [f"Agent: {llm_response['immediate_response']}"],
        "intent_detected": llm_response.get("intent"),
        "entities_extracted": llm_response.get("entities", {}),
        "needs_clarification": llm_response.get("needs_clarification", False),
        "actions_to_execute": llm_response.get("actions", [])
    }
    
    updated_state = lead_reducer(state, updates)
    print(f"🔹 Intent Detector: intent={llm_response.get('intent')}, used_knowledge={llm_response.get('used_knowledge', False)}")
    
    return updated_state