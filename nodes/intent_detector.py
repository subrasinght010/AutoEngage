# nodes/intent_detector_llm.py

from state.workflow_state import WorkflowState, lead_reducer
# from tools.language_model import query_llm  # LLM wrapper function

def intent_detector_llm(state: WorkflowState) -> WorkflowState:
    """
    Detects client intent using an LLM.
    Determines preferred channel and action based on natural language.
    """

    last_message = state.conversation_thread[-1] if state.conversation_thread else ""

    # Skip if no message
    if not last_message:
        return state

    # -----------------------------
    # 1. Query LLM
    # -----------------------------
    prompt = f"""
    Analyze this client message and return:
    1. preferred_channel (call / email / whatsapp)
    2. action (reply / schedule_call / send_document / follow_up)
    Respond in JSON format.
    Message: "{last_message}"
    """

    llm_response = {}#query_llm(prompt)  # Example: returns {"preferred_channel": "whatsapp", "action": "reply"}

    preferred_channel = llm_response.get("preferred_channel", state.preferred_channel or "email")
    pending_action = llm_response.get("action", "communication_agent")

    # -----------------------------
    # 2. Update state
    # -----------------------------
    updates = {
        "preferred_channel": preferred_channel,
        "pending_action": pending_action
    }

    updated_state = lead_reducer(state, updates)
    print(f"🔹 LLM Intent Detector: channel={preferred_channel}, action={pending_action}")
    return updated_state
