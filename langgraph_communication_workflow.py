
from typing import Dict, List, Optional, Literal, Annotated
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoints.sqlite import SqliteSaver
from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool
import sqlite3
import json
from datetime import datetime
from enum import Enum

# Define communication channels and intents
class CommunicationChannel(str, Enum):
    CALL = "call"
    EMAIL = "email"
    WHATSAPP = "whatsapp"

class ClientType(str, Enum):
    NEW = "new"
    EXISTING = "existing"

class Intent(str, Enum):
    QUERY = "query"
    COMPLAINT = "complaint"
    INFO_REQUEST = "info_request"
    SUPPORT = "support"
    FOLLOW_UP = "follow_up"

class WorkflowType(str, Enum):
    OUTBOUND = "outbound"
    INBOUND = "inbound"

# Define the main state structure
class CommunicationState(TypedDict):
    # Core identification
    client_id: Optional[str]
    session_id: str
    thread_id: str
    
    # Communication details
    channel: CommunicationChannel
    workflow_type: WorkflowType
    client_type: Optional[ClientType]
    
    # Message handling
    messages: Annotated[List[BaseMessage], add_messages]
    current_message: str
    
    # Client data
    client_data: Dict
    preferred_language: Optional[str]
    conversation_history: List[Dict]
    
    # Intent and routing
    detected_intent: Optional[Intent]
    routing_decision: Optional[str]
    
    # Process tracking
    verification_status: bool
    scheduled_call: Optional[Dict]
    follow_up_required: bool
    follow_up_actions: List[str]
    
    # Database operations
    db_updates: List[Dict]
    interaction_log: List[Dict]
    
    # Agent responses
    agent_response: Optional[str]
    next_agent: Optional[str]

# Database tools
@tool
def log_interaction(session_id: str, channel: str, message: str, response: str, intent: str = None) -> str:
    """Log all interactions to database for tracking and auditing"""
    try:
        # This would connect to your actual database
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "channel": channel,
            "message": message,
            "response": response,
            "intent": intent
        }
        # Database insertion logic here
        return f"Interaction logged successfully for session {session_id}"
    except Exception as e:
        return f"Failed to log interaction: {str(e)}"

@tool
def update_client_record(client_id: str, updates: Dict) -> str:
    """Update client record in database"""
    try:
        # Database update logic here
        return f"Client record {client_id} updated successfully"
    except Exception as e:
        return f"Failed to update client record: {str(e)}"

@tool
def get_client_history(client_id: str) -> Dict:
    """Retrieve client conversation history"""
    try:
        # Database query logic here
        history = {
            "client_id": client_id,
            "previous_interactions": [],
            "preferences": {},
            "last_contact": None
        }
        return history
    except Exception as e:
        return {"error": f"Failed to retrieve history: {str(e)}"}

# Agent nodes for the workflow

def communication_detector(state: CommunicationState) -> CommunicationState:
    """Detect incoming communication and determine channel"""
    # In practice, this would integrate with your communication infrastructure
    # For now, we'll use the provided channel
    
    state["interaction_log"].append({
        "timestamp": datetime.now().isoformat(),
        "action": "communication_detected",
        "channel": state["channel"],
        "message": state["current_message"]
    })
    
    return state

def client_type_detector(state: CommunicationState) -> CommunicationState:
    """Determine if client is new or existing"""
    
    # Check if client exists in database
    if state.get("client_id"):
        # Simulate database lookup
        client_exists = True  # This would be actual DB query
        state["client_type"] = ClientType.EXISTING if client_exists else ClientType.NEW
    else:
        state["client_type"] = ClientType.NEW
    
    state["interaction_log"].append({
        "timestamp": datetime.now().isoformat(),
        "action": "client_type_detected",
        "client_type": state["client_type"]
    })
    
    return state

def db_analyzer(state: CommunicationState) -> CommunicationState:
    """Analyze new database entries for outbound processing"""
    
    # Analyze client data for completeness and quality
    client_data = state.get("client_data", {})
    
    analysis_results = {
        "data_complete": bool(client_data.get("name") and client_data.get("contact")),
        "data_quality_score": 0.8,  # Simulated score
        "missing_fields": [],
        "recommendations": []
    }
    
    if not analysis_results["data_complete"]:
        analysis_results["missing_fields"] = ["email", "phone"]
        analysis_results["recommendations"] = ["Request missing contact information"]
    
    state["client_data"]["analysis"] = analysis_results
    state["db_updates"].append({
        "timestamp": datetime.now().isoformat(),
        "action": "db_analysis_completed",
        "results": analysis_results
    })
    
    return state

def data_verifier(state: CommunicationState) -> CommunicationState:
    """Verify lead data for required fields and correctness"""
    
    client_data = state.get("client_data", {})
    verification_results = {
        "email_valid": True,  # Would use actual email validation
        "phone_valid": True,  # Would use actual phone validation
        "required_fields_present": True,
        "verification_score": 0.9
    }
    
    state["verification_status"] = verification_results["verification_score"] > 0.7
    state["client_data"]["verification"] = verification_results
    
    state["db_updates"].append({
        "timestamp": datetime.now().isoformat(),
        "action": "data_verification_completed",
        "status": state["verification_status"]
    })
    
    return state

def language_detector(state: CommunicationState) -> CommunicationState:
    """Detect or confirm lead's preferred language"""
    
    # Simulate language detection from message content or client data
    message = state.get("current_message", "")
    
    # This would use actual language detection service
    detected_language = "en"  # Default to English
    
    # Check client preferences if existing client
    if state["client_type"] == ClientType.EXISTING:
        client_data = state.get("client_data", {})
        preferred_lang = client_data.get("preferred_language")
        if preferred_lang:
            detected_language = preferred_lang
    
    state["preferred_language"] = detected_language
    state["db_updates"].append({
        "timestamp": datetime.now().isoformat(),
        "action": "language_detected",
        "language": detected_language
    })
    
    return state

def intent_detector(state: CommunicationState) -> CommunicationState:
    """Classify the type of inbound request using intent detection"""
    
    message = state.get("current_message", "")
    
    # Simulate intent classification (would use actual NLP model)
    intent_keywords = {
        Intent.QUERY: ["question", "how", "what", "when", "where", "why"],
        Intent.COMPLAINT: ["problem", "issue", "wrong", "error", "complain"],
        Intent.INFO_REQUEST: ["information", "details", "tell me", "explain"],
        Intent.SUPPORT: ["help", "support", "assistance", "can you"],
        Intent.FOLLOW_UP: ["follow up", "previous", "earlier", "status"]
    }
    
    detected_intent = Intent.QUERY  # Default
    
    message_lower = message.lower()
    for intent, keywords in intent_keywords.items():
        if any(keyword in message_lower for keyword in keywords):
            detected_intent = intent
            break
    
    state["detected_intent"] = detected_intent
    state["interaction_log"].append({
        "timestamp": datetime.now().isoformat(),
        "action": "intent_detected",
        "intent": detected_intent,
        "message": message
    })
    
    return state

def scheduler_agent(state: CommunicationState) -> CommunicationState:
    """Schedule calls via scheduler agent"""
    
    # Simulate call scheduling logic
    scheduled_call = {
        "call_id": f"call_{state['session_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "scheduled_time": datetime.now().isoformat(),
        "client_id": state.get("client_id"),
        "status": "scheduled",
        "channel": CommunicationChannel.CALL
    }
    
    state["scheduled_call"] = scheduled_call
    state["db_updates"].append({
        "timestamp": datetime.now().isoformat(),
        "action": "call_scheduled",
        "call_details": scheduled_call
    })
    
    return state

def calling_agent(state: CommunicationState) -> CommunicationState:
    """Make outbound calls using calling agent"""
    
    # Simulate outbound call process
    call_result = {
        "call_id": state.get("scheduled_call", {}).get("call_id"),
        "status": "completed",  # or "failed", "no_answer", etc.
        "duration": "5:30",
        "notes": "Client responded positively to offer",
        "follow_up_required": True
    }
    
    state["follow_up_required"] = call_result["follow_up_required"]
    if call_result["follow_up_required"]:
        state["follow_up_actions"].append("Send follow-up email with offer details")
    
    state["agent_response"] = f"Call completed successfully. Duration: {call_result['duration']}"
    
    state["interaction_log"].append({
        "timestamp": datetime.now().isoformat(),
        "action": "outbound_call_completed",
        "result": call_result
    })
    
    return state

def email_agent(state: CommunicationState) -> CommunicationState:
    """Handle email communications"""
    
    if state["workflow_type"] == WorkflowType.OUTBOUND:
        # Send outbound email
        email_content = f"Hello, following up on our previous interaction..."
        action = "outbound_email_sent"
    else:
        # Process inbound email
        email_content = f"Thank you for your email. We have received your {state['detected_intent']} and will respond accordingly."
        action = "inbound_email_processed"
    
    state["agent_response"] = email_content
    
    state["interaction_log"].append({
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "content": email_content,
        "language": state.get("preferred_language", "en")
    })
    
    return state

def whatsapp_agent(state: CommunicationState) -> CommunicationState:
    """Handle WhatsApp communications"""
    
    if state["workflow_type"] == WorkflowType.OUTBOUND:
        # Send outbound WhatsApp message
        whatsapp_content = f"Hi! We have an exciting offer for you..."
        action = "outbound_whatsapp_sent"
    else:
        # Process inbound WhatsApp message
        intent = state.get("detected_intent", Intent.QUERY)
        whatsapp_content = f"Thanks for your WhatsApp message! I understand you have a {intent}. Let me help you with that."
        action = "inbound_whatsapp_processed"
    
    state["agent_response"] = whatsapp_content
    
    state["interaction_log"].append({
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "content": whatsapp_content,
        "language": state.get("preferred_language", "en")
    })
    
    return state

def follow_up_processor(state: CommunicationState) -> CommunicationState:
    """Determine and execute follow-up actions"""
    
    if state.get("follow_up_required", False):
        # Determine appropriate follow-up actions
        intent = state.get("detected_intent")
        channel = state["channel"]
        
        follow_up_actions = []
        
        if intent == Intent.COMPLAINT:
            follow_up_actions.append("Escalate to supervisor")
            follow_up_actions.append("Send resolution timeline")
        elif intent == Intent.INFO_REQUEST:
            follow_up_actions.append("Send detailed information packet")
        elif intent == Intent.SUPPORT:
            follow_up_actions.append("Schedule technical support call")
        
        state["follow_up_actions"].extend(follow_up_actions)
        
        state["interaction_log"].append({
            "timestamp": datetime.now().isoformat(),
            "action": "follow_up_actions_determined",
            "actions": follow_up_actions
        })
    
    return state

def database_logger(state: CommunicationState) -> CommunicationState:
    """Final database logging and state persistence"""
    
    # Consolidate all updates and logs
    final_log_entry = {
        "session_id": state["session_id"],
        "client_id": state.get("client_id"),
        "channel": state["channel"],
        "workflow_type": state["workflow_type"],
        "client_type": state.get("client_type"),
        "detected_intent": state.get("detected_intent"),
        "agent_response": state.get("agent_response"),
        "follow_up_required": state.get("follow_up_required", False),
        "follow_up_actions": state.get("follow_up_actions", []),
        "interaction_history": state["interaction_log"],
        "db_updates": state["db_updates"],
        "timestamp": datetime.now().isoformat()
    }
    
    # In practice, this would save to your database
    print(f"Final log entry saved for session: {state['session_id']}")
    
    return state

# Routing functions
def route_workflow_type(state: CommunicationState) -> Literal["outbound_flow", "inbound_flow"]:
    """Route to appropriate workflow based on type"""
    return "outbound_flow" if state["workflow_type"] == WorkflowType.OUTBOUND else "inbound_flow"

def route_client_type(state: CommunicationState) -> Literal["new_client_flow", "existing_client_flow"]:
    """Route based on client type for inbound communications"""
    return "new_client_flow" if state["client_type"] == ClientType.NEW else "existing_client_flow"

def route_channel(state: CommunicationState) -> Literal["call_agent", "email_agent", "whatsapp_agent"]:
    """Route to appropriate channel agent"""
    channel_routing = {
        CommunicationChannel.CALL: "call_agent",
        CommunicationChannel.EMAIL: "email_agent", 
        CommunicationChannel.WHATSAPP: "whatsapp_agent"
    }
    return channel_routing[state["channel"]]

def needs_follow_up(state: CommunicationState) -> Literal["follow_up_processor", "database_logger"]:
    """Determine if follow-up processing is needed"""
    return "follow_up_processor" if state.get("follow_up_required", False) else "database_logger"

# Build the complete workflow graph
def build_communication_workflow():
    """Build the complete multi-channel communication workflow"""
    
    # Initialize the state graph
    workflow = StateGraph(CommunicationState)
    
    # Add all nodes
    workflow.add_node("communication_detector", communication_detector)
    workflow.add_node("client_type_detector", client_type_detector)
    workflow.add_node("db_analyzer", db_analyzer)
    workflow.add_node("data_verifier", data_verifier)
    workflow.add_node("language_detector", language_detector)
    workflow.add_node("intent_detector", intent_detector)
    workflow.add_node("scheduler_agent", scheduler_agent)
    workflow.add_node("calling_agent", calling_agent)
    workflow.add_node("email_agent", email_agent)
    workflow.add_node("whatsapp_agent", whatsapp_agent)
    workflow.add_node("follow_up_processor", follow_up_processor)
    workflow.add_node("database_logger", database_logger)
    
    # Set entry point
    workflow.set_entry_point("communication_detector")
    
    # Add edges for the workflow
    workflow.add_edge("communication_detector", "client_type_detector")
    
    # Route based on workflow type (outbound vs inbound)
    workflow.add_conditional_edges(
        "client_type_detector",
        route_workflow_type,
        {
            "outbound_flow": "db_analyzer",
            "inbound_flow": "intent_detector"
        }
    )
    
    # Outbound workflow edges
    workflow.add_edge("db_analyzer", "data_verifier")
    workflow.add_edge("data_verifier", "language_detector")
    workflow.add_edge("language_detector", "scheduler_agent")
    workflow.add_edge("scheduler_agent", "calling_agent")
    
    # Route from calling_agent to appropriate channel agent
    workflow.add_conditional_edges(
        "calling_agent",
        route_channel,
        {
            "call_agent": "follow_up_processor",  # Already handled by calling_agent
            "email_agent": "email_agent",
            "whatsapp_agent": "whatsapp_agent"
        }
    )
    
    # Inbound workflow - route to appropriate channel agent after intent detection
    workflow.add_conditional_edges(
        "intent_detector",
        route_channel,
        {
            "call_agent": "calling_agent",
            "email_agent": "email_agent",
            "whatsapp_agent": "whatsapp_agent"
        }
    )
    
    # All channel agents route to follow-up processing
    workflow.add_conditional_edges(
        "email_agent",
        needs_follow_up,
        {
            "follow_up_processor": "follow_up_processor",
            "database_logger": "database_logger"
        }
    )
    
    workflow.add_conditional_edges(
        "whatsapp_agent", 
        needs_follow_up,
        {
            "follow_up_processor": "follow_up_processor",
            "database_logger": "database_logger"
        }
    )
    
    # Follow-up processor always goes to database logger
    workflow.add_edge("follow_up_processor", "database_logger")
    
    # End at database logger
    workflow.add_edge("database_logger", END)
    
    return workflow

# Example usage and testing
def create_sample_states():
    """Create sample states for testing different scenarios"""
    
    # Outbound fresh lead scenario
    outbound_state = CommunicationState(
        session_id="session_001",
        thread_id="thread_001", 
        channel=CommunicationChannel.EMAIL,
        workflow_type=WorkflowType.OUTBOUND,
        current_message="New lead from website form",
        client_data={
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "+1234567890",
            "source": "website_form"
        },
        messages=[],
        conversation_history=[],
        db_updates=[],
        interaction_log=[],
        follow_up_actions=[]
    )
    
    # Inbound existing client scenario
    inbound_state = CommunicationState(
        session_id="session_002", 
        thread_id="thread_002",
        client_id="client_123",
        channel=CommunicationChannel.WHATSAPP,
        workflow_type=WorkflowType.INBOUND,
        current_message="Hi, I have a question about my recent order",
        client_data={
            "name": "Jane Smith",
            "email": "jane@example.com", 
            "preferred_language": "en"
        },
        messages=[HumanMessage(content="Hi, I have a question about my recent order")],
        conversation_history=[
            {"date": "2024-01-15", "channel": "email", "summary": "Product inquiry"}
        ],
        db_updates=[],
        interaction_log=[],
        follow_up_actions=[]
    )
    
    return outbound_state, inbound_state

if __name__ == "__main__":
    # Build the workflow
    workflow_graph = build_communication_workflow()
    
    # Compile with checkpointer for persistence
    checkpointer = SqliteSaver.from_conn_string(":memory:")
    compiled_workflow = workflow_graph.compile(checkpointer=checkpointer)
    
    print("Multi-Channel Communication Workflow built successfully!")
    print("\nWorkflow includes:")
    print("- Outbound processing for fresh database entries")
    print("- Inbound processing for incoming communications") 
    print("- Multi-channel support (Call, Email, WhatsApp)")
    print("- Client type detection (New vs Existing)")
    print("- Intent detection and routing")
    print("- Comprehensive database logging")
    print("- Follow-up action processing")
    print("- State persistence across all interactions")
