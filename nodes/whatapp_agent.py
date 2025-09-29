# # langgraph_workflow_annotated.py

# from langgraph import Graph, Node, State
# from dataclasses import dataclass, field
# from typing import Dict, List, Optional, Annotated
# from datetime import datetime

# # -----------------------------
# # 1. Annotated Workflow State
# # -----------------------------
# @dataclass
# class WorkflowState(State):
#     lead_id: Optional[str] = None  # Unique ID for the lead
#     lead_data: Annotated[Dict, "Stores lead contact info like email, phone"] = field(default_factory=dict)
#     client_type: Optional[str] = None  # "new" or "existing"
#     pending_action: Optional[str] = None  # Next node/agent to run in workflow
#     preferred_channel: Optional[str] = None  # "call", "email", or "whatsapp"
#     conversation_thread: Annotated[List[str], "List of messages exchanged with the client"] = field(default_factory=list)
#     thread_id: Optional[str] = None  # ID for threaded conversation
#     follow_up_time: Optional[str] = None  # Scheduled follow-up time (ISO format)
#     last_contacted_at: Optional[str] = None  # Timestamp of last interaction
#     lead_status: str = "new"  # "new", "verified", "contacted", or "closed"
#     db_log: Annotated[List[Dict], "Logs all actions/events in workflow"] = field(default_factory=list)
#     next_action_time: Optional[str] = None  # Optional scheduled action time
#     channel_history: Annotated[List[str], "Tracks which channels were used for communication"] = field(default_factory=list)

# # -----------------------------
# # 2. Reducer function
# # -----------------------------
# def lead_reducer(state: WorkflowState, updates: dict) -> WorkflowState:
#     """
#     Apply updates to WorkflowState safely and return updated state.
#     """
#     for key, value in updates.items():
#         if hasattr(state, key):
#             setattr(state, key, value)
#         else:
#             print(f"Warning: {key} not in WorkflowState")
#     return state

# # -----------------------------
# # 3. Node functions
# # -----------------------------
# def verify_data_node(state: WorkflowState) -> WorkflowState:
#     print("🔹 Verifying lead")
#     updates = {
#         "pending_action": "schedule_call_node",
#         "lead_status": "verified"
#     }
#     return lead_reducer(state, updates)

# def schedule_call_node(state: WorkflowState) -> WorkflowState:
#     print("🔹 Scheduling call")
#     updates = {
#         "pending_action": "execute_call_node",
#         "next_action_time": "2025-09-30T16:00:00"
#     }
#     return lead_reducer(state, updates)

# def execute_call_node(state: WorkflowState) -> WorkflowState:
#     print("🔹 Executing call")
#     updates = {
#         "pending_action": "intent_detector_node",
#         "last_contacted_at": datetime.now().isoformat()
#     }
#     return lead_reducer(state, updates)

# def intent_detector_node(state: WorkflowState) -> WorkflowState:
#     print("🔹 IntentDetector running")
#     last_message = state.conversation_thread[-1] if state.conversation_thread else ""

#     # Detect preferred communication channel
#     if any(k in last_message.lower() for k in ["whatsapp", "message", "chat"]):
#         channel = "whatsapp"
#     elif any(k in last_message.lower() for k in ["email", "send pdf", "attach"]):
#         channel = "email"
#     elif any(k in last_message.lower() for k in ["call", "phone"]):
#         channel = "call"
#     else:
#         channel = "email"

#     updates = {
#         "preferred_channel": channel,
#         "pending_action": "communication_agent"
#     }

#     # Ensure thread_id exists for threaded conversation
#     if not state.thread_id:
#         updates["thread_id"] = "thread_" + (state.lead_id or "new")

#     return lead_reducer(state, updates)

# def communication_agent(state: WorkflowState) -> WorkflowState:
#     print(f"🔹 Communicating via {state.preferred_channel}")
#     thread_info = f"(thread: {state.thread_id})" if state.thread_id else ""

#     # Placeholder sending logic
#     if state.preferred_channel == "email":
#         print(f"Sending EMAIL to {state.lead_data.get('email')} {thread_info}")
#     elif state.preferred_channel == "whatsapp":
#         print(f"Sending WHATSAPP to {state.lead_data.get('phone')} {thread_info}")
#     elif state.preferred_channel == "call":
#         print(f"Making CALL to {state.lead_data.get('phone')} {thread_info}")

#     updates = {
#         "pending_action": None,
#         "last_contacted_at": datetime.now().isoformat(),
#         "channel_history": state.channel_history + [state.preferred_channel],
#         "conversation_thread": state.conversation_thread + [f"Sent via {state.preferred_channel}"]
#     }

#     return lead_reducer(s_
