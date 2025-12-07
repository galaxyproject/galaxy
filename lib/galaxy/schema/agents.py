"""
Pydantic schemas for AI agent responses and requests.
"""

from enum import Enum
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from pydantic import (
    BaseModel,
    Field,
)


class ConfidenceLevel(str, Enum):
    """Confidence levels for agent responses."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ActionType(str, Enum):
    """Types of actions agents can suggest."""

    TOOL_RUN = "tool_run"
    PARAMETER_CHANGE = "parameter_change"
    WORKFLOW_STEP = "workflow_step"
    DOCUMENTATION = "documentation"
    CONTACT_SUPPORT = "contact_support"
    VIEW_EXTERNAL = "view_external"  # Open external URL in new tab
    SAVE_TOOL = "save_tool"
    TEST_TOOL = "test_tool"
    REFINE_QUERY = "refine_query"


class ActionSuggestion(BaseModel):
    """Structured suggestion for user action."""

    action_type: ActionType = Field(description="Type of action to take")
    description: str = Field(description="Human-readable description of the action")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters for the action")
    confidence: ConfidenceLevel = Field(description="Confidence in this suggestion")
    priority: int = Field(default=1, description="Priority level (1=high, 2=medium, 3=low)")


class AgentResponse(BaseModel):
    """Structured response from an AI agent."""

    content: str = Field(description="Main response content")
    confidence: ConfidenceLevel = Field(description="Confidence in the response")
    agent_type: str = Field(description="Type of agent that generated this response")
    suggestions: List[ActionSuggestion] = Field(default_factory=list, description="Actionable suggestions")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    reasoning: Optional[str] = Field(default=None, description="Explanation of the agent's reasoning")


class AgentQueryRequest(BaseModel):
    """Request to query an AI agent."""

    query: str = Field(description="The user's question or request")
    agent_type: str = Field(default="auto", description="Preferred agent type ('auto' for routing)")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context for the query")
    stream: bool = Field(default=False, description="Whether to stream the response")


class AgentQueryResponse(BaseModel):
    """Response from an AI agent query."""

    response: AgentResponse = Field(description="The agent's response")
    routing_info: Optional[Dict[str, Any]] = Field(
        default=None, description="Information about how the query was routed"
    )
    processing_time: Optional[float] = Field(default=None, description="Time taken to process the query in seconds")


class AvailableAgent(BaseModel):
    """Information about an available agent."""

    agent_type: str = Field(description="Unique identifier for the agent")
    name: str = Field(description="Human-readable name")
    description: str = Field(description="Description of the agent's capabilities")
    enabled: bool = Field(description="Whether the agent is currently enabled")
    model: Optional[str] = Field(default=None, description="LLM model used by the agent")
    specialties: List[str] = Field(default_factory=list, description="Areas of specialization")


class AgentListResponse(BaseModel):
    """Response listing available agents."""

    agents: List[AvailableAgent] = Field(description="List of available agents")
    total_count: int = Field(description="Total number of agents")


class RoutingDecision(BaseModel):
    """Decision made by the router agent."""

    primary_agent: str = Field(description="Primary agent to handle the query")
    secondary_agents: List[str] = Field(default_factory=list, description="Additional agents that might help")
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
    solution_steps: List[str] = Field(description="Step-by-step solution")
    alternative_approaches: List[str] = Field(default_factory=list, description="Alternative solutions")
    confidence: ConfidenceLevel = Field(description="Confidence in the analysis")
    related_documentation: List[str] = Field(default_factory=list, description="Relevant documentation links")
    requires_admin: bool = Field(default=False, description="Whether admin intervention is needed")


class ToolRecommendationRequest(BaseModel):
    """Request for tool recommendations."""

    task_description: str = Field(description="Description of the task to accomplish")
    input_format: Optional[str] = Field(default=None, description="Format of input data")
    output_format: Optional[str] = Field(default=None, description="Desired output format")
    preferences: Dict[str, Any] = Field(default_factory=dict, description="User preferences or constraints")


class ToolSuggestion(BaseModel):
    """Suggestion for a specific tool."""

    tool_id: str = Field(description="Galaxy tool identifier")
    tool_name: str = Field(description="Human-readable tool name")
    relevance_score: float = Field(description="Relevance score (0.0 to 1.0)")
    rationale: str = Field(description="Explanation for why this tool is recommended")
    suggested_parameters: Dict[str, Any] = Field(default_factory=dict, description="Recommended parameter values")


class ToolRecommendationResponse(BaseModel):
    """Response with tool recommendations."""

    recommended_tools: List[ToolSuggestion] = Field(description="List of recommended tools")
    workflow_suggestions: List[str] = Field(default_factory=list, description="Suggestions for workflow structure")
    parameter_recommendations: Dict[str, Any] = Field(default_factory=dict, description="General parameter guidance")
    confidence: ConfidenceLevel = Field(description="Confidence in the recommendations")


class DatasetAnalysisRequest(BaseModel):
    """Request for dataset quality analysis."""

    dataset_id: str = Field(description="Galaxy dataset identifier")
    analysis_type: str = Field(default="comprehensive", description="Type of analysis to perform")
    focus_areas: List[str] = Field(default_factory=list, description="Specific areas to focus on")


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
    issues_found: List[QualityIssue] = Field(description="List of quality issues detected")
    recommendations: List[str] = Field(description="General recommendations for improvement")
    preprocessing_steps: List[str] = Field(description="Suggested preprocessing steps")
    confidence: ConfidenceLevel = Field(description="Confidence in the analysis")


class WorkflowOptimizationRequest(BaseModel):
    """Request for workflow optimization."""

    workflow_id: Optional[str] = Field(default=None, description="Galaxy workflow identifier")
    workflow_structure: Optional[Dict[str, Any]] = Field(default=None, description="Workflow structure data")
    performance_goals: List[str] = Field(default_factory=list, description="Optimization goals")


class OptimizationSuggestion(BaseModel):
    """Suggestion for workflow optimization."""

    suggestion_type: str = Field(description="Type of optimization")
    description: str = Field(description="Detailed description of the suggestion")
    expected_benefit: str = Field(description="Expected improvement")
    implementation_difficulty: str = Field(description="Difficulty level to implement")
    priority: int = Field(description="Priority level")


class WorkflowOptimizationResponse(BaseModel):
    """Response from workflow optimization analysis."""

    optimization_suggestions: List[OptimizationSuggestion] = Field(description="List of optimization suggestions")
    performance_improvements: List[str] = Field(description="Expected performance improvements")
    bottlenecks_identified: List[str] = Field(description="Identified bottlenecks")
    estimated_time_savings: Optional[str] = Field(default=None, description="Estimated time savings")
    confidence: ConfidenceLevel = Field(description="Confidence in the analysis")


class AgentMetrics(BaseModel):
    """Metrics for agent performance monitoring."""

    agent_type: str = Field(description="Type of agent")
    total_queries: int = Field(description="Total number of queries processed")
    success_rate: float = Field(description="Success rate (0.0 to 1.0)")
    average_response_time: float = Field(description="Average response time in seconds")
    confidence_distribution: Dict[str, int] = Field(description="Distribution of confidence levels")
    last_update: str = Field(description="Last update timestamp")


class AgentStatus(BaseModel):
    """Current status of an agent."""

    agent_type: str = Field(description="Type of agent")
    enabled: bool = Field(description="Whether the agent is enabled")
    health_status: str = Field(description="Health status (healthy, degraded, unavailable)")
    last_response_time: Optional[float] = Field(default=None, description="Last response time in seconds")
    error_rate: float = Field(description="Recent error rate")
    model_info: Dict[str, Any] = Field(default_factory=dict, description="Information about the underlying model")


class SystemStatus(BaseModel):
    """Overall system status for all agents."""

    total_agents: int = Field(description="Total number of registered agents")
    healthy_agents: int = Field(description="Number of healthy agents")
    agent_statuses: List[AgentStatus] = Field(description="Status of each agent")
    system_health: str = Field(description="Overall system health")
    last_check: str = Field(description="Last health check timestamp")
