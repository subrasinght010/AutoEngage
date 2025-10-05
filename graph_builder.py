"""
LangGraph Workflow Builder
Complete flow with RAG integration
"""

from langgraph.graph import Graph, StateGraph, END
from state.workflow_state import WorkflowState
from nodes.incoming_listener import incoming_listener
from nodes.intent_detector import intent_detector_llm
from nodes.knowledge_agent import knowledge_agent
from nodes.communication_agent import communication_agent
from nodes.schedule_call import schedule_call_node, execute_call_node
from nodes.db_update import db_update_node
from nodes.verify_data import verify_data_node
from nodes.follow_up import follow_up_node


def create_workflow_graph():
    """
    Create the complete workflow graph
    """
    
    # Initialize graph
    workflow = StateGraph(WorkflowState)
    
    # Add all nodes
    workflow.add_node("incoming_listener", incoming_listener)
    workflow.add_node("intent_detector", intent_detector_llm)
    workflow.add_node("knowledge_agent", knowledge_agent)
    workflow.add_node("communication_agent", communication_agent)
    workflow.add_node("schedule_callback", schedule_call_node)
    workflow.add_node("execute_call", execute_call_node)
    workflow.add_node("db_update", db_update_node)
    workflow.add_node("verify_data", verify_data_node)
    workflow.add_node("follow_up", follow_up_node)
    
    # Define edges (workflow flow)
    
    # Incoming call/message flow
    workflow.add_edge("incoming_listener", "intent_detector")
    
    # Intent detection routing
    def route_after_intent(state: WorkflowState):
        """Route based on detected intent"""
        intent = state.get("intent_detected")
        needs_clarification = state.get("needs_clarification", False)
        
        if needs_clarification:
            return "communication_agent"  # Ask clarification
        
        if intent in ["product_query", "policy_query"]:
            return "knowledge_agent"  # Use RAG
        elif intent == "callback_request":
            return "schedule_callback"
        else:
            return "communication_agent"  # Handle other intents
    
    workflow.add_conditional_edges(
        "intent_detector",
        route_after_intent,
        {
            "knowledge_agent": "knowledge_agent",
            "schedule_callback": "schedule_callback",
            "communication_agent": "communication_agent"
        }
    )
    
    # Knowledge agent → communication
    workflow.add_edge("knowledge_agent", "communication_agent")
    
    # Schedule callback → communication (send confirmation)
    workflow.add_edge("schedule_callback", "communication_agent")
    
    # Communication → DB update
    workflow.add_edge("communication_agent", "db_update")
    
    # DB update → END
    workflow.add_edge("db_update", END)
    
    # Follow-up flow
    workflow.add_edge("follow_up", "execute_call")
    workflow.add_edge("execute_call", "intent_detector")
    
    # Set entry point
    workflow.set_entry_point("incoming_listener")
    
    return workflow.compile()


# Create compiled graph
compiled_workflow = create_workflow_graph()


# Test function
def test_workflow():
    """Test the workflow with sample data"""
    
    print("=== Testing Voice Call Flow ===\n")
    
    # Simulate incoming call
    initial_state = WorkflowState(
        lead_id="test_123",
        lead_data={"name": "John", "phone": "+919876543210", "email": "john@example.com"},
        client_type="new",
        conversation_thread=[],
        lead_status="new"
    )
    
    # Simulate user saying: "What's your refund policy?"
    message_data = {
        "lead_id": "test_123",
        "message": "What's your refund policy?",
        "channel": "call"
    }
    
    # Run workflow
    result = compiled_workflow.invoke(initial_state)
    
    print("\n=== Workflow Result ===")
    print(f"Final State: {result}")
    print(f"Conversation Thread: {result.get('conversation_thread')}")
    print(f"Actions Executed: {result.get('actions_to_execute')}")


if __name__ == "__main__":
    test_workflow()