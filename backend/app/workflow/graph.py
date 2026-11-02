"""
AAMC MCAT Multi-Agent LangGraph Workflow.

Assembles and compiles the StateGraph connecting the Fused Generator, Reviewer,
Regenerator, Diagram Generator, Quality Gate Reject, and Finalize nodes.
"""

from langgraph.graph import END, StateGraph

from app.workflow.engine import (
    WorkflowRunResult,
    run_workflow,
    run_workflow_stream,
)
from app.workflow.nodes import (
    blind_solver_node,
    finalize_node,
    fused_generator_node,
    generator_node,
    image_node,
    regenerator_node,
    reject_node,
    reviewer_node,
)
from app.workflow.routes import (
    route_after_fused_generation,
    route_after_review,
)
from app.workflow.state import AgentWorkflowState


def create_mcat_graph() -> StateGraph:
    """
    Builds and compiles the multi-agent LangGraph workflow for official AAMC MCAT.

    Workflow Topology:
    1. Entry Point -> fused_generator (combined drafting and self-critique)
    2. route_after_fused_generation:
       - Score > 90: image_generator (if diagram required) or finalize
       - Score <= 90 or unverified: reviewer (for independent audit)
    3. route_after_review:
       - Score <= 90 and attempts < max: regenerator -> reviewer (remediation loop)
       - Score <= 90 and attempts >= max: reject -> END (Strict Quality Gate)
       - Score > 90: image_generator (if diagram required) or finalize -> END
    4. Modular Pipeline Nodes:
       - generator: Single-pass generator node for modular invocation.
       - blind_solver: Blind-solver student dual-validation node (invoked in engine review loop).
    """
    workflow = StateGraph(AgentWorkflowState)

    # Agent Nodes
    workflow.add_node("fused_generator", fused_generator_node)
    workflow.add_node("generator", generator_node)
    workflow.add_node("reviewer", reviewer_node)
    workflow.add_node("blind_solver", blind_solver_node)
    workflow.add_node("regenerator", regenerator_node)
    workflow.add_node("image_generator", image_node)
    workflow.add_node("finalize", finalize_node)
    workflow.add_node("reject", reject_node)

    # Edges & Conditional Routing
    workflow.set_entry_point("fused_generator")
    workflow.add_conditional_edges(
        "fused_generator",
        route_after_fused_generation,
        {
            "reviewer": "reviewer",
            "image_generator": "image_generator",
            "finalize": "finalize",
        },
    )
    workflow.add_edge("generator", "reviewer")

    workflow.add_conditional_edges(
        "reviewer",
        route_after_review,
        {
            "regenerator": "regenerator",
            "image_generator": "image_generator",
            "finalize": "finalize",
            "reject": "reject",
        },
    )

    workflow.add_edge("regenerator", "reviewer")
    workflow.add_edge("image_generator", "finalize")
    workflow.add_edge("finalize", END)
    workflow.add_edge("reject", END)

    return workflow.compile()


# Global compiled graph singleton
mcat_graph = create_mcat_graph()

__all__ = [
    "AgentWorkflowState",
    "WorkflowRunResult",
    "blind_solver_node",
    "create_mcat_graph",
    "finalize_node",
    "fused_generator_node",
    "generator_node",
    "image_node",
    "mcat_graph",
    "regenerator_node",
    "reject_node",
    "reviewer_node",
    "route_after_fused_generation",
    "route_after_review",
    "run_workflow",
    "run_workflow_stream",
]
