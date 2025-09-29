from state.workflow_state import WorkflowState, lead_reducer

def verify_data_node(state: WorkflowState) -> WorkflowState:
    print("🔹 Verifying lead")
    updates = {
        "pending_action": "schedule_call_node",
        "lead_status": "verified"
    }
    return lead_reducer(state, updates)










