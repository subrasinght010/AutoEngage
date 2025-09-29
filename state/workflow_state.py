from typing import TypedDict, List, Optional

# -----------------------------
# 1. Shared Workflow State
# -----------------------------
class WorkflowState(TypedDict, total=False):
    lead_id: Optional[str]
    lead_data: dict                   # client info
    client_type: Optional[str]        # new / existing
    pending_action: Optional[str]     # next agent to run
    preferred_channel: Optional[str]  # call / email / whatsapp
    conversation_thread: List[str]    # previous messages
    thread_id: Optional[str]          # conversation thread id
    follow_up_time: Optional[str]     # scheduled follow-up
    last_contacted_at: Optional[str]  # timestamp of last interaction
    lead_status: str                  # new / verified / contacted / closed / no_response
    db_log: List[str]                 # log of all actions/events
    next_action_time: Optional[str]   # optional: next scheduled action
    channel_history: List[str]        # track channels used
    follow_up_done: bool              # True if follow-up completed
    retry_count: int                  # number of follow-up attempts

# -----------------------------
# 2. Default state factory
# -----------------------------
def create_default_workflow_state() -> WorkflowState:
    """Return a new WorkflowState with default values"""
    return WorkflowState(
        lead_id=None,
        lead_data={},
        client_type=None,
        pending_action=None,
        preferred_channel=None,
        conversation_thread=[],
        thread_id=None,
        follow_up_time=None,
        last_contacted_at=None,
        lead_status="new",
        db_log=[],
        next_action_time=None,
        channel_history=[],
        follow_up_done=False,
        retry_count=0
    )

# -----------------------------
# 3. Reducer function
# -----------------------------
def lead_reducer(state: WorkflowState, updates: dict) -> WorkflowState:
    """Apply updates to state and return updated WorkflowState"""
    for key, value in updates.items():
        if key in state:
            state[key] = value
    return state
