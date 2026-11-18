"""
nodes.py - Unified workflow graph nodes module.

Decomposed into:
- `node_generator.py`: Fused generator and agent usage tracking.
- `node_reviewer.py`: Reviewer, blind solver, and regenerator nodes.
- `node_finalize.py`: Reject, image generation, and question finalization nodes.

Consolidates all node operations and provides dynamic test monkeypatch synchronization
across specialized workflow modules.
"""

from __future__ import annotations

import sys
from types import ModuleType
from typing import Any

import app.workflow.node_finalize as _node_finalize
import app.workflow.node_generator as _node_generator
import app.workflow.node_reviewer as _node_reviewer
from app.agents.blind_solver import BlindSolverResult, blind_solve_question
from app.agents.generator import (
    generate_question,
    generate_question_with_self_critique,
)
from app.agents.image_generator import generate_image_stimulus
from app.agents.option_balancer import (
    balance_and_shuffle_options,
    calculate_option_symmetry,
)
from app.agents.regenerator import regenerate_question
from app.agents.reviewer import review_question
from app.workflow.node_finalize import (
    finalize_node,
    image_node,
    reject_node,
)
from app.workflow.node_generator import (
    _record_agent_usage,
    agent_usage_entry,
    fused_generator_node,
)
from app.workflow.node_reviewer import (
    ReviewAndSolveOutcome,
    blind_solver_node,
    build_review_update,
    build_solver_update,
    build_usage_only_update,
    regenerator_node,
    reviewer_node,
    run_review_and_solve,
)

__all__ = [
    "BlindSolverResult",
    "ReviewAndSolveOutcome",
    "_record_agent_usage",
    "agent_usage_entry",
    "balance_and_shuffle_options",
    "blind_solve_question",
    "blind_solver_node",
    "build_review_update",
    "build_solver_update",
    "build_usage_only_update",
    "calculate_option_symmetry",
    "finalize_node",
    "fused_generator_node",
    "generate_image_stimulus",
    "generate_question",
    "generate_question_with_self_critique",
    "image_node",
    "regenerate_question",
    "regenerator_node",
    "reject_node",
    "review_question",
    "reviewer_node",
    "run_review_and_solve",
]

_ROUTING_TARGETS: dict[str, list[ModuleType]] = {
    # Generator module targets
    "generate_question": [_node_generator],
    "generate_question_with_self_critique": [_node_generator],
    "fused_generator_node": [_node_generator],
    # Reviewer module targets
    "review_question": [_node_reviewer],
    "blind_solve_question": [_node_reviewer],
    "regenerate_question": [_node_reviewer],
    "reviewer_node": [_node_reviewer],
    "blind_solver_node": [_node_reviewer],
    "regenerator_node": [_node_reviewer],
    "run_review_and_solve": [_node_reviewer],
    "build_review_update": [_node_reviewer],
    "build_solver_update": [_node_reviewer],
    "build_usage_only_update": [_node_reviewer],
    # Finalize module targets
    "generate_image_stimulus": [_node_finalize],
    "reject_node": [_node_finalize],
    "image_node": [_node_finalize],
    "finalize_node": [_node_finalize],
}


class _WorkflowNodesFacade(ModuleType):
    """Facade module ensuring test monkeypatches on app.workflow.nodes propagate to child modules."""

    def __setattr__(self, name: str, value: Any) -> None:
        super().__setattr__(name, value)
        for target_module in _ROUTING_TARGETS.get(name, []):
            setattr(target_module, name, value)


_facade = _WorkflowNodesFacade(__name__, __doc__)
_facade.__dict__.update(sys.modules[__name__].__dict__)
sys.modules[__name__] = _facade
