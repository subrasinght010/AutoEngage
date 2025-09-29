# nodes/communication_agent.py

from state.workflow_state import WorkflowState, lead_reducer
# from tools.call_api import make_call
# from tools.email_service import send_email
# from tools.whatsapp_api import send_whatsapp
from datetime import datetime

def communication_agent(state: WorkflowState) -> WorkflowState:
    """
    Sends outgoing communication or replies to incoming messages based on
    preferred_channel and conversation context.
    """

    lead_data = state.lead_data
    channel = state.preferred_channel
    lead_id = state.lead_id

    # Get last message from conversation for context
    last_message = state.conversation_thread[-1] if state.conversation_thread else ""

    # -----------------------------
    # 1. Decide action based on channel
    # -----------------------------
    if channel == "call":
        phone = lead_data.get("phone")
        if phone:
            # make_call(phone, message="Automated call regarding your inquiry")
            action_summary = f"Outgoing call to {phone}"
        else:
            action_summary = "No phone number available for call"

    elif channel == "email":
        email = lead_data.get("email")
        if email:
            # send_email(email, subject="Automated Follow-Up", body="Hello, following up on your request.")
            action_summary = f"Outgoing email to {email}"
        else:
            action_summary = "No email available"

    elif channel == "whatsapp":
        phone = lead_data.get("phone")
        if phone:
            # send_whatsapp(phone, message="Hello! This is an automated follow-up message.")
            action_summary = f"Outgoing WhatsApp to {phone}"
        else:
            action_summary = "No phone number available for WhatsApp"

    else:
        action_summary = "No valid channel specified"

    # -----------------------------
    # 2. Update state
    # -----------------------------
    updates = {
        "last_contacted_at": datetime.now().isoformat(),
        "conversation_thread": state.conversation_thread + [f"[{datetime.now().isoformat()}] {action_summary}"],
        "channel_history": state.channel_history + [channel],
        "pending_action": None  # Next action can be set by follow-up node
    }

    updated_state = lead_reducer(state, updates)
    print(f"✅ Communication executed: {action_summary}")

    return updated_state
