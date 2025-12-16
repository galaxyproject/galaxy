"""
DSPy-based agent for Galaxy - demonstrates integration of DSPy with Galaxy agent framework.

This agent shows how to use DSPy's declarative programming approach within Galaxy's
agent system, combining DSPy's optimization capabilities with Galaxy's tool integration.
"""

import logging
from typing import (
    Any,
    Dict,
    List,
    Literal,
    Optional,
)

from pydantic import (
    BaseModel,
    Field,
)

from .base import (
    ActionSuggestion,
    ActionType,
    AgentResponse,
    BaseGalaxyAgent,
    GalaxyAgentDependencies,
)

# DSPy imports - wrapped in try/except for graceful degradation
try:
    import dspy
    from dspy import (
        InputField,
        OutputField,
        Predict,
        Signature,
    )

    HAS_DSPY = True
except ImportError:
    HAS_DSPY = False
    dspy = None
    Signature = object
    InputField = OutputField = lambda: None
    Predict = object

log = logging.getLogger(__name__)


class ToolRecommendationSignature(Signature):
    """Given a user query and available tools, recommend the best Galaxy tool with reasoning."""

    user_query = InputField()
    available_tools = InputField()

    recommended_tool = OutputField()
    reasoning = OutputField()
    confidence = OutputField()
    alternatives = OutputField()


class DSPyToolRecommendation(BaseModel):
    """Structured output for DSPy tool recommendations."""

    recommended_tool: str = Field(description="Primary tool recommendation")
    reasoning: str = Field(description="Reasoning behind the recommendation")
    confidence: Literal["low", "medium", "high"] = Field(description="Confidence level")
    alternatives: List[str] = Field(default_factory=list, description="Alternative tools")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Suggested parameters")


class DSPyGalaxyAgent(BaseGalaxyAgent):
    """
    Galaxy agent that uses DSPy for self-improving tool recommendations.

    This agent demonstrates how to integrate DSPy's declarative programming
    and optimization capabilities with Galaxy's agent framework.
    """

    def __init__(self, deps: GalaxyAgentDependencies):
        """Initialize DSPy agent."""
        if not HAS_DSPY:
            raise ImportError("DSPy is required for DSPyGalaxyAgent. Please install with: pip install dspy-ai")

        super().__init__(deps)

        # Configure DSPy language model
        self._configure_dspy()

        # Initialize DSPy modules
        self.tool_recommender = Predict(ToolRecommendationSignature)

    def _configure_dspy(self):
        """Configure DSPy with the appropriate language model."""
        # Use the same model configuration as other Galaxy agents
        model_name = self._get_model_name()
        api_key = self._get_agent_config("api_key")
        base_url = self._get_agent_config("api_base_url")

        if not api_key:
            raise ValueError("API key is required for DSPy agent")

        # Create LM instance for OpenAI-compatible endpoint
        lm = dspy.LM(
            model=model_name,
            api_key=api_key,
            api_base=base_url.rstrip("/") if base_url else None,
        )

        # Set the language model for DSPy
        dspy.settings.configure(lm=lm)

    def _create_agent(self):
        """DSPy agents don't use pydantic-ai Agent - they use DSPy modules directly."""

        # For compatibility with BaseGalaxyAgent, return a mock agent
        class MockAgent:
            async def run(self, *args, **kwargs):
                # This won't be called since we override process()
                pass

        return MockAgent()

    def get_system_prompt(self) -> str:
        """Get system prompt for DSPy agent."""
        return """
        You are a Galaxy tool recommendation expert using advanced reasoning.
        Analyze user requests and recommend the most appropriate Galaxy tools.
        Provide detailed reasoning and consider alternative approaches.
        """

    async def process(self, query: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """
        Process query using DSPy modules.

        This method bypasses the standard pydantic-ai approach and uses
        DSPy's declarative programming paradigm instead.
        """
        try:
            # Prepare context for DSPy
            available_tools = self._get_available_tools_context()

            # Use DSPy to generate recommendation
            result = self.tool_recommender(user_query=query, available_tools=available_tools)

            # Parse alternatives
            alternatives = []
            if result.alternatives:
                alternatives = [alt.strip() for alt in result.alternatives.split(",") if alt.strip()]

            # Create structured response
            dspy_result = DSPyToolRecommendation(
                recommended_tool=result.recommended_tool,
                reasoning=result.reasoning,
                confidence=result.confidence.lower(),
                alternatives=alternatives,
            )

            # Format response content
            content = self._format_dspy_response(dspy_result)

            # Create suggestions
            suggestions = self._create_dspy_suggestions(dspy_result)

            return AgentResponse(
                content=content,
                confidence=dspy_result.confidence,
                agent_type=self.agent_type,
                suggestions=suggestions,
                metadata={
                    "method": "dspy",
                    "recommended_tool": dspy_result.recommended_tool,
                    "has_alternatives": bool(alternatives),
                    "dspy_version": dspy.__version__ if HAS_DSPY else "not_available",
                },
                reasoning=dspy_result.reasoning,
            )

        except Exception as e:
            log.error(f"DSPy agent failed: {e}")
            return self._get_fallback_response(query, str(e))

    def _get_available_tools_context(self) -> str:
        """Get context about available Galaxy tools for DSPy."""
        # This would ideally query the Galaxy tool registry
        return """
        Available Galaxy tools include:
        - BWA-MEM: For mapping sequencing reads to reference genomes
        - HISAT2: For RNA-seq read alignment
        - StringTie: For transcript assembly and quantification  
        - DESeq2: For differential gene expression analysis
        - FastQC: For quality control of sequencing data
        - Trimmomatic: For read trimming and filtering
        - BLAST: For sequence similarity searching
        - SAMtools: For manipulating SAM/BAM files
        - Bowtie2: For fast read alignment
        - Cufflinks: For transcript discovery and abundance estimation
        """

    def _format_dspy_response(self, result: DSPyToolRecommendation) -> str:
        """Format DSPy result into user-friendly content."""
        parts = []

        parts.append(f"**Recommended Tool:** {result.recommended_tool}")
        parts.append(f"**Reasoning:** {result.reasoning}")

        if result.alternatives:
            parts.append("**Alternative Options:**")
            for alt in result.alternatives:
                parts.append(f"- {alt}")

        parts.append(f"**Confidence:** {result.confidence.title()}")

        return "\n\n".join(parts)

    def _create_dspy_suggestions(self, result: DSPyToolRecommendation) -> List[ActionSuggestion]:
        """Create action suggestions from DSPy result."""
        suggestions = []

        # Suggest running the recommended tool
        suggestions.append(
            ActionSuggestion(
                action_type=ActionType.TOOL_RUN,
                description=f"Run {result.recommended_tool}",
                parameters={"tool_name": result.recommended_tool},
                confidence=result.confidence,
                priority=1,
            )
        )

        # Suggest alternatives
        for alt in result.alternatives[:2]:  # Limit to top 2
            suggestions.append(
                ActionSuggestion(
                    action_type=ActionType.TOOL_RUN,
                    description=f"Try alternative: {alt}",
                    parameters={"tool_name": alt},
                    confidence="medium",
                    priority=2,
                )
            )

        return suggestions

    def _get_fallback_content(self) -> str:
        """Get fallback content for DSPy failures."""
        return "Unable to generate tool recommendations using advanced reasoning at this time."

    # DSPy-specific methods for optimization and improvement

    def optimize_with_examples(self, examples: List[Dict[str, str]]):
        """
        Optimize the DSPy agent using example queries and expected outputs.

        Args:
            examples: List of {"query": str, "expected_tool": str, "reasoning": str}
        """
        if not HAS_DSPY:
            log.warning("DSPy not available for optimization")
            return

        try:
            # Convert examples to DSPy format
            trainset = []
            for example in examples:
                trainset.append(
                    dspy.Example(
                        user_query=example["query"],
                        available_tools=self._get_available_tools_context(),
                        recommended_tool=example["expected_tool"],
                        reasoning=example.get("reasoning", ""),
                    ).with_inputs("user_query", "available_tools")
                )

            # Use DSPy's optimizer to improve the agent
            optimizer = dspy.BootstrapFewShot(metric=self._evaluation_metric)
            optimized_recommender = optimizer.compile(
                self.tool_recommender,
                trainset=trainset,
            )

            # Replace the current recommender with optimized version
            self.tool_recommender = optimized_recommender

            log.info(f"DSPy agent optimized with {len(examples)} examples")

        except Exception as e:
            log.error(f"DSPy optimization failed: {e}")

    def _evaluation_metric(self, example, prediction, trace=None):
        """
        Evaluation metric for DSPy optimization.

        Returns a score between 0 and 1 based on how well the prediction
        matches the expected output.
        """
        if prediction.recommended_tool.lower() == example.recommended_tool.lower():
            return 1.0
        return 0.0
