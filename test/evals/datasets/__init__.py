"""Eval datasets defined as pydantic-evals Cases."""

from .bioinformatics_workflows import bioinformatics_workflows_dataset
from .error_analysis import error_analysis_dataset
from .orchestrator_planning import orchestrator_planning_dataset
from .router_tool_use import router_tool_use_dataset
from .routing import routing_dataset
from .staining_quantification import staining_quantification_dataset
from .tool_recommendation import tool_recommendation_dataset

__all__ = [
    "bioinformatics_workflows_dataset",
    "error_analysis_dataset",
    "orchestrator_planning_dataset",
    "router_tool_use_dataset",
    "routing_dataset",
    "staining_quantification_dataset",
    "tool_recommendation_dataset",
]
