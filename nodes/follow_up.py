# nodes/follow_up.py

from datetime import datetime, timedelta
from state.workflow_state import WorkflowState, lead_reducer
from nodes.communication_agent import communication_agent
from nodes.db_update import db_update_node

def follow_up_node(state: WorkflowState) -> WorkflowState:
    """
    Handles follow-ups with retries and automatic closure:
    - Triggers communication agent
    - Updates DB
    - Retries up to max_retries if no response
    - Marks follow-up done if client responds or retries exhausted
    """
    print("🔹 FollowUp Node running")

    # Skip if already done
    if state.follow_up_done:
        print(f"⏹ Follow-up already done for lead {state.lead_id}")
        return state

    # Default channel
    channel = state.preferred_channel or "call"

    # Increment retry count
    retries = (state.retry_count or 0) + 1

    updates = {
        "pending_action": "communication_agent",
        "conversation_thread": state.conversation_thread + [
            f"[{datetime.now().isoformat()}] Follow-up attempt #{retries} via {channel}"
        ],
        "retry_count": retries,
        "next_action_time": (datetime.now() + timedelta(minutes=10)).isoformat()  # next follow-up in 10 mins
    }

    # Apply updates
    updated_state = lead_reducer(state, updates)

    # Execute communication agent
    updated_state = communication_agent(updated_state)

    # Log to DB
    updated_state = db_update_node(updated_state)

    # -----------------------------
    # Check for completion
    # -----------------------------
    client_responded = False
    # Example: check if last message in thread is from client
    if updated_state.conversation_thread and "client reply" in updated_state.conversation_thread[-1].lower():
        client_responded = True

    if client_responded:
        updated_state.follow_up_done = True
        updated_state.lead_status = "contacted"
        print(f"✅ Client responded. Follow-up completed for lead {updated_state.lead_id}")
    elif retries >= (state.max_retries or 3):
        updated_state.follow_up_done = True
        updated_state.lead_status = "no_response"
        print(f"⚠️ Max retries reached. Follow-up closed for lead {updated_state.lead_id}")
    else:
        # Schedule next retry automatically
        updated_state.pending_action = "follow_up_node"
        print(f"⏳ Will retry follow-up for lead {updated_state.lead_id} (attempt {retries})")

    return updated_state
