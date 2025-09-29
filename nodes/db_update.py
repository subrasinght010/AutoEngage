# nodes/db_update.py

from datetime import datetime
from state.workflow_state import WorkflowState, lead_reducer
from tools.db_client import save_lead

def db_update_node(state: WorkflowState) -> WorkflowState:
    """
    1. Append a log entry to state.db_log
    2. Save/Update the lead record in the DB
    3. Return the updated state
    """
    # ✅ Step 1: Add log entry
    log_entry = {
        "time": datetime.now().isoformat(),
        "action": state.pending_action,
        "lead_id": state.lead_id
    }
    updated_state = lead_reducer(state, {
        "db_log": state.db_log + [log_entry]
    })

    # ✅ Step 2: Build the record to save
    lead_record = {
        "id": updated_state.lead_id,
        "lead_data": updated_state.lead_data,
        "conversation_thread": updated_state.conversation_thread,
        "preferred_channel": updated_state.preferred_channel,
        "pending_action": updated_state.pending_action,
        "next_action_time": updated_state.next_action_time,
        "db_log": updated_state.db_log,
    }

    # ✅ Step 3: Save to DB
    save_lead(lead_record)
    print(f"✅ DB updated for lead {updated_state.lead_id}")

    return updated_state
