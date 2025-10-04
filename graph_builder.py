# graph_builder.py
from langgraph import Graph
from state.workflow_state import WorkflowState
from nodes.communication_agent import communication_agent
from nodes.db_update import db_update_node
from nodes.follow_up import follow_up_node
from nodes.incoming_listener import incoming_listener
from nodes.intent_detector import intent_detector_llm as intent_detector_node
from nodes.schedule_call import schedule_call_node, execute_call_node
from nodes.verify_data import verify_data_node

# Build a reusable graph instance (for CLI testing / visualization)
state = WorkflowState()
graph = Graph(state=state)

# Nodes registration
graph.add_node("verify_data_node", verify_data_node)
graph.add_node("schedule_call_node", schedule_call_node)
graph.add_node("execute_call_node", execute_call_node)
graph.add_node("intent_detector_node", intent_detector_node)
graph.add_node("communication_agent", communication_agent)
graph.add_node("follow_up_node", follow_up_node)
graph.add_node("db_update_node", db_update_node)
graph.add_node("incoming_listener", incoming_listener)

# Edges - normal lead flow
graph.add_edge("verify_data_node", "schedule_call_node")
graph.add_edge("schedule_call_node", "execute_call_node")
graph.add_edge("execute_call_node", "intent_detector_node")
graph.add_edge("intent_detector_node", "communication_agent")

# DB logging from all key steps
for node in [
    "verify_data_node", "schedule_call_node", "execute_call_node",
    "intent_detector_node", "communication_agent", "follow_up_node", "incoming_listener"
]:
    graph.add_edge(node, "db_update_node")

# Incoming message flow
graph.add_edge("incoming_listener", "intent_detector_node")
graph.add_edge("intent_detector_node", "communication_agent")  # branch for new client

#while communicating on whatapp or email may need to schedule call
graph.add_edge("communication_agent", "intent_detector_node")
graph.add_edge("intent_detector_node", "schedule_call_node")


# Follow-up flow
graph.add_edge("follow_up_node", "execute_call_node")
graph.add_edge("follow_up_node", "communication_agent")

# CLI runner for testing the graph manually
if __name__ == "__main__":
    print("=== NEW LEAD FLOW ===")
    graph.run(start_node="verify_data_node")

    print("\n=== INCOMING MESSAGE FLOW ===")
    graph.run(start_node="incoming_listener")

    print("\n=== FOLLOW-UP FLOW ===")
    graph.run(start_node="follow_up_node")

    print("\n=== Final WorkflowState ===")
    print(state)
