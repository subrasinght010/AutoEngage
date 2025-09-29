# nodes/schedule.py

from datetime import datetime, timedelta
from state.workflow_state import WorkflowState, lead_reducer
from nodes.intent_detector import intent_detector_llm
from nodes.db_update import db_update_node
from nodes.communication_agent import communication_agent

# -----------------------------
# Schedule Call Node
# -----------------------------
def schedule_call_node(state: WorkflowState) -> WorkflowState:
    """
    Schedule a call for a lead.
    Sets next_action_time dynamically and pending_action to execute_call_node.
    """
    print("🔹 Scheduling call for lead:", state.lead_id)

    # Example: schedule call 10 minutes from now if not specified
    next_time = state.next_action_time or (datetime.now() + timedelta(minutes=10)).isoformat()

    updates = {
        "pending_action": "execute_call_node",
        "next_action_time": next_time
    }
    return lead_reducer(state, updates)

# -----------------------------
# Execute Call Node
# -----------------------------
def execute_call_node(state: WorkflowState) -> WorkflowState:
    """
    Executes the call and triggers next steps:
    - Communication via preferred channel
    - DB logging
    - LLM intent detection for next actions (follow-up, documents, etc.)
    """
    print("🔹 Executing call for lead:", state.lead_id)

    # Update state: mark call as executed
    updates = {
        "pending_action": None,
        "last_contacted_at": datetime.now().isoformat()
    }
    updated_state = lead_reducer(state, updates)

    # Execute communication (call/email/WhatsApp)
    updated_state = communication_agent(updated_state)

    # Log the action in DB
    updated_state = db_update_node(updated_state)

    # Detect next steps using LLM (intent, follow-up, document requests)
    updated_state = intent_detector_llm(updated_state)

    return updated_state
