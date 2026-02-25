"""
Workflow report agent for generating markdown reports from Galaxy workflows.
"""

import logging
from pathlib import Path

from .base import (
    GalaxyAgentDependencies,
    SimpleGalaxyAgent,
)

log = logging.getLogger(__name__)


class WorkflowReportAgent(SimpleGalaxyAgent):
    """
    Agent that generates a markdown report for a Galaxy workflow.
    """

    agent_type = "workflow_report"

    def get_system_prompt(self) -> str:
        prompt_path = Path(__file__).parent / "prompts" / "workflow_report.md"
        return prompt_path.read_text()
