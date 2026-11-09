"""Compilation of the LangGraph research orchestrator state graph."""
from langgraph.graph import END, START, StateGraph
from src.agent.nodes import (
    analyze_evidence_node,
    collect_data_node,
    create_job_node,
    deduplicate_and_verify_node,
    generate_report_node,
    handle_failure_node,
    persist_results_node,
    validate_inputs_node,
    verify_claims_node,
)
from src.agent.state import ResearchState


def route_after_validation(state: ResearchState) -> str:
    """Route after input validation check."""
    if state.get("status") in ("invalid_input", "failed"):
        return "handle_failure"
    return "create_job"


def route_after_job_creation(state: ResearchState) -> str:
    """Route after database job creation."""
    if state.get("status") == "failed":
        return "handle_failure"
    return "collect_data"


def route_after_data_collection(state: ResearchState) -> str:
    """Route after price and news collection."""
    if state.get("status") in ("failed", "rate_limited", "no_data"):
        return "handle_failure"
    return "deduplicate_and_verify"


def build_research_graph() -> StateGraph:
    """Construct the compiled LangGraph workflow for Stock Market News & Sentiment Research."""
    workflow = StateGraph(ResearchState)

    # Register all nodes
    workflow.add_node("validate_inputs", validate_inputs_node)
    workflow.add_node("create_job", create_job_node)
    workflow.add_node("collect_data", collect_data_node)
    workflow.add_node("deduplicate_and_verify", deduplicate_and_verify_node)
    workflow.add_node("analyze_evidence", analyze_evidence_node)
    workflow.add_node("verify_claims", verify_claims_node)
    workflow.add_node("generate_report", generate_report_node)
    workflow.add_node("persist_results", persist_results_node)
    workflow.add_node("handle_failure", handle_failure_node)

    # Define linear and conditional edges
    workflow.add_edge(START, "validate_inputs")
    workflow.add_conditional_edges(
        "validate_inputs",
        route_after_validation,
        {"handle_failure": "handle_failure", "create_job": "create_job"},
    )
    workflow.add_conditional_edges(
        "create_job",
        route_after_job_creation,
        {"handle_failure": "handle_failure", "collect_data": "collect_data"},
    )
    workflow.add_conditional_edges(
        "collect_data",
        route_after_data_collection,
        {"handle_failure": "handle_failure", "deduplicate_and_verify": "deduplicate_and_verify"},
    )
    workflow.add_edge("deduplicate_and_verify", "analyze_evidence")
    workflow.add_edge("analyze_evidence", "verify_claims")
    workflow.add_edge("verify_claims", "generate_report")
    workflow.add_edge("generate_report", "persist_results")
    workflow.add_edge("persist_results", END)
    workflow.add_edge("handle_failure", END)

    return workflow.compile()


# Compiled research orchestrator singleton
research_graph = build_research_graph()

