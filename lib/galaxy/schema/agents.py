"""
Pydantic schemas for AI agent responses and requests.
"""

from enum import Enum
from typing import (
    Any,
    Optional,
)

from pydantic import (
    BaseModel,
    Field,
    model_validator,
)


class TokenUsage(BaseModel):
    """Token usage information from LLM calls."""

    input_tokens: int = Field(default=0, description="Number of input tokens")
    output_tokens: int = Field(default=0, description="Number of output tokens")
    total_tokens: int = Field(default=0, description="Total tokens used")


class ConfidenceLevel(str, Enum):
    """Confidence levels for agent responses."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ActionType(str, Enum):
    """Types of actions agents can suggest."""

    TOOL_RUN = "tool_run"
    SAVE_TOOL = "save_tool"
    CONTACT_SUPPORT = "contact_support"
    VIEW_EXTERNAL = "view_external"
    DOCUMENTATION = "documentation"


class ActionSuggestion(BaseModel):
    """Structured suggestion for user action."""

    action_type: ActionType = Field(description="Type of action to take")
    description: str = Field(description="Human-readable description of the action")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Parameters for the action")
    confidence: ConfidenceLevel = Field(description="Confidence in this suggestion")
    priority: int = Field(default=1, description="Priority level (1=high, 2=medium, 3=low)")

    @model_validator(mode="after")
    def validate_parameters(self) -> "ActionSuggestion":
        """Ensure required parameters exist for each action type."""
        if self.action_type == ActionType.TOOL_RUN:
            if not self.parameters.get("tool_id"):
                raise ValueError("TOOL_RUN requires 'tool_id' parameter")
        elif self.action_type == ActionType.SAVE_TOOL:
            if not self.parameters.get("tool_yaml"):
                raise ValueError("SAVE_TOOL requires 'tool_yaml' parameter")
        elif self.action_type == ActionType.VIEW_EXTERNAL:
            if not self.parameters.get("url"):
                raise ValueError("VIEW_EXTERNAL requires 'url' parameter")
        return self


class AgentResponse(BaseModel):
    """Structured response from an AI agent."""

    content: str = Field(description="Main response content")
    confidence: ConfidenceLevel = Field(description="Confidence in the response")
    agent_type: str = Field(description="Type of agent that generated this response")
    suggestions: list[ActionSuggestion] = Field(default_factory=list, description="Actionable suggestions")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    reasoning: Optional[str] = Field(default=None, description="Explanation of the agent's reasoning")


class AgentQueryRequest(BaseModel):
    """Request to query an AI agent.

    DEPRECATED: Use /api/chat instead for new integrations.
    """

    query: str = Field(description="The user's question or request")
    agent_type: str = Field(default="auto", description="Preferred agent type ('auto' for routing)")
    context: dict[str, Any] = Field(default_factory=dict, description="Additional context for the query")


class AgentQueryResponse(BaseModel):
    """Response from an AI agent query.

    DEPRECATED: Use /api/chat instead for new integrations.
    """

    response: AgentResponse = Field(description="The agent's response")
    processing_time: Optional[float] = Field(default=None, description="Time taken to process the query in seconds")


class AvailableAgent(BaseModel):
    """Information about an available agent."""

    agent_type: str = Field(description="Unique identifier for the agent")
    name: str = Field(description="Human-readable name")
    description: str = Field(description="Description of the agent's capabilities")
    enabled: bool = Field(description="Whether the agent is currently enabled")
    model: Optional[str] = Field(default=None, description="LLM model used by the agent")
    specialties: list[str] = Field(default_factory=list, description="Areas of specialization")


class AgentListResponse(BaseModel):
    """Response listing available agents."""

    agents: list[AvailableAgent] = Field(description="List of available agents")
    total_count: int = Field(description="Total number of agents")


class RoutingDecision(BaseModel):
    """Decision made by the router agent."""

    primary_agent: str = Field(description="Primary agent to handle the query")
    secondary_agents: list[str] = Field(default_factory=list, description="Additional agents that might help")
    complexity: str = Field(description="Query complexity assessment")
    confidence: ConfidenceLevel = Field(description="Confidence in the routing decision")
    reasoning: str = Field(description="Explanation for the routing choice")
    direct_response: str = Field(default="", description="Direct response if routing is not needed")


class ErrorAnalysisRequest(BaseModel):
    """Request for error analysis."""

    query: str = Field(description="Description of the error or problem")
    job_id: Optional[int] = Field(default=None, description="Galaxy job ID associated with the error")
    error_text: Optional[str] = Field(default=None, description="Specific error message text")
    tool_id: Optional[str] = Field(default=None, description="Tool that caused the error")


class ErrorCategory(BaseModel):
    """Classification of error types."""

    category: str = Field(description="Main error category")
    subcategory: Optional[str] = Field(default=None, description="More specific error subcategory")
    severity: str = Field(description="Error severity level")


class ErrorAnalysisResponse(BaseModel):
    """Response from error analysis."""

    error_category: ErrorCategory = Field(description="Classification of the error")
    likely_cause: str = Field(description="Most probable cause of the error")
    solution_steps: list[str] = Field(description="Step-by-step solution")
    alternative_approaches: list[str] = Field(default_factory=list, description="Alternative solutions")
    confidence: ConfidenceLevel = Field(description="Confidence in the analysis")
    related_documentation: list[str] = Field(default_factory=list, description="Relevant documentation links")
    requires_admin: bool = Field(default=False, description="Whether admin intervention is needed")


class DatasetAnalysisRequest(BaseModel):
    """Request for dataset quality analysis."""

    dataset_id: str = Field(description="Galaxy dataset identifier")
    analysis_type: str = Field(default="comprehensive", description="Type of analysis to perform")
    focus_areas: list[str] = Field(default_factory=list, description="Specific areas to focus on")


class QualityIssue(BaseModel):
    """Description of a data quality issue."""

    issue_type: str = Field(description="Type of quality issue")
    severity: str = Field(description="Severity level")
    description: str = Field(description="Detailed description of the issue")
    suggested_fix: str = Field(description="Recommended solution")
    affected_records: Optional[int] = Field(default=None, description="Number of affected records")


class DatasetAnalysisResponse(BaseModel):
    """Response from dataset quality analysis."""

    quality_score: float = Field(description="Overall quality score (0.0 to 1.0)")
    issues_found: list[QualityIssue] = Field(description="List of quality issues detected")
    recommendations: list[str] = Field(description="General recommendations for improvement")
    preprocessing_steps: list[str] = Field(description="Suggested preprocessing steps")
    confidence: ConfidenceLevel = Field(description="Confidence in the analysis")


class WorkflowOptimizationRequest(BaseModel):
    """Request for workflow optimization."""

    workflow_id: Optional[str] = Field(default=None, description="Galaxy workflow identifier")
    workflow_structure: Optional[dict[str, Any]] = Field(default=None, description="Workflow structure data")
    performance_goals: list[str] = Field(default_factory=list, description="Optimization goals")


class OptimizationSuggestion(BaseModel):
    """Suggestion for workflow optimization."""

    suggestion_type: str = Field(description="Type of optimization")
    description: str = Field(description="Detailed description of the suggestion")
    expected_benefit: str = Field(description="Expected improvement")
    implementation_difficulty: str = Field(description="Difficulty level to implement")
    priority: int = Field(description="Priority level")


class WorkflowOptimizationResponse(BaseModel):
    """Response from workflow optimization analysis."""

    optimization_suggestions: list[OptimizationSuggestion] = Field(description="List of optimization suggestions")
    performance_improvements: list[str] = Field(description="Expected performance improvements")
    bottlenecks_identified: list[str] = Field(description="Identified bottlenecks")
    estimated_time_savings: Optional[str] = Field(default=None, description="Estimated time savings")
    confidence: ConfidenceLevel = Field(description="Confidence in the analysis")


class AgentMetrics(BaseModel):
    """Metrics for agent performance monitoring."""

    agent_type: str = Field(description="Type of agent")
    total_queries: int = Field(description="Total number of queries processed")
    success_rate: float = Field(description="Success rate (0.0 to 1.0)")
    average_response_time: float = Field(description="Average response time in seconds")
    confidence_distribution: dict[str, int] = Field(description="Distribution of confidence levels")
    last_update: str = Field(description="Last update timestamp")


class AgentStatus(BaseModel):
    """Current status of an agent."""

    agent_type: str = Field(description="Type of agent")
    enabled: bool = Field(description="Whether the agent is enabled")
    health_status: str = Field(description="Health status (healthy, degraded, unavailable)")
    last_response_time: Optional[float] = Field(default=None, description="Last response time in seconds")
    error_rate: float = Field(description="Recent error rate")
    model_info: dict[str, Any] = Field(default_factory=dict, description="Information about the underlying model")


class SystemStatus(BaseModel):
    """Overall system status for all agents."""

    total_agents: int = Field(description="Total number of registered agents")
    healthy_agents: int = Field(description="Number of healthy agents")
    agent_statuses: list[AgentStatus] = Field(description="Status of each agent")
    system_health: str = Field(description="Overall system health")
    last_check: str = Field(description="Last health check timestamp")
