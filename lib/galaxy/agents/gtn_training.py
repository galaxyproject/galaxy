"""
GTN Training Agent for Galaxy.

This agent provides access to Galaxy Training Network tutorials and learning resources,
helping users find relevant training materials, understand tool usage, and learn
Galaxy workflows through hands-on tutorials.
"""

import json
import logging
import re
from pathlib import Path
from typing import (
    Any,
    Optional,
)

from pydantic import (
    BaseModel,
    Field,
)
from pydantic_ai import (
    Agent,
    RunContext,
)

from galaxy.schema.agents import ConfidenceLevel
from .base import (
    ActionSuggestion,
    ActionType,
    AgentResponse,
    AgentType,
    BaseGalaxyAgent,
    GalaxyAgentDependencies,
)
from .gtn import GTNSearchDB

log = logging.getLogger(__name__)


class GTNSearchRequest(BaseModel):
    """Model for GTN search requests."""

    query: str = Field(..., description="Search query for tutorials")
    topic: Optional[str] = Field(None, description="Filter by specific topic")
    difficulty: Optional[str] = Field(None, description="Filter by difficulty level")
    hands_on_only: bool = Field(False, description="Only return hands-on tutorials")
    limit: int = Field(5, description="Maximum number of results")


class GTNSearchResponse(BaseModel):
    """Structured response from GTN training agent."""

    tutorials: list[dict[str, Any]] = Field(
        default_factory=list, description="List of matching tutorials"
    )
    summary: str = Field(..., description="Natural language summary of findings")
    learning_path: Optional[str] = Field(
        None, description="Suggested learning progression"
    )
    prerequisites: list[str] = Field(
        default_factory=list, description="Recommended prerequisites"
    )
    total_time: Optional[str] = Field(
        None, description="Estimated total time for suggested tutorials"
    )


class GTNTrainingAgent(BaseGalaxyAgent):
    """
    Agent specialized in finding and recommending Galaxy training materials.

    This agent searches the GTN database to help users find relevant tutorials,
    create learning paths, and understand Galaxy tools through hands-on training.
    """

    agent_type = AgentType.GTN_TRAINING

    def __init__(self, deps: GalaxyAgentDependencies):
        """Initialize the GTN training agent."""
        super().__init__(deps)

        # Initialize GTN database (lazy - only when DB file exists)
        self.gtn_db: GTNSearchDB | None = None
        try:
            self.gtn_db = GTNSearchDB()
            log.info("GTN database initialized successfully")
        except FileNotFoundError as e:
            log.warning(f"GTN database file not found: {e}")
            self.gtn_db = None
        except OSError as e:
            log.error(f"Failed to initialize GTN database: {e}")
            self.gtn_db = None

    def _create_agent(self) -> Agent[GalaxyAgentDependencies, Any]:
        """Create the pydantic-ai agent with GTN search capabilities."""
        if self._supports_structured_output():
            agent = Agent(
                self._get_model(),
                deps_type=GalaxyAgentDependencies,
                output_type=GTNSearchResponse,
                system_prompt=self.get_system_prompt(),
            )
        else:
            # DeepSeek and other models without structured output
            agent = Agent(
                self._get_model(),
                deps_type=GalaxyAgentDependencies,
                system_prompt=self._get_simple_system_prompt(),
            )

        # Add GTN search tools only for models that support them
        if self._supports_structured_output():

            @agent.tool
            async def search_gtn_tutorials(
                ctx: RunContext[GalaxyAgentDependencies],
                query: str,
                topic: Optional[str] = None,
                difficulty: Optional[str] = None,
                hands_on_only: bool = False,
                limit: int = 10,
            ) -> str:
                """
                IMPORTANT: Always call this tool for tutorial searches! Search GTN tutorials for relevant content.

                Args:
                    query: Natural language search query (REQUIRED)
                    topic: Optional topic filter
                    difficulty: Optional difficulty filter (introductory/intermediate/advanced)
                    hands_on_only: Only return hands-on tutorials
                    limit: Maximum number of results

                Returns:
                    JSON string with search results
                """
                if not self.gtn_db:
                    return json.dumps({"error": "GTN database not available"})

                try:
                    results = self.gtn_db.search(
                        query=query,
                        topic=topic,
                        difficulty=difficulty,
                        hands_on_only=hands_on_only,
                        limit=limit,
                    )

                    return json.dumps(
                        {
                            "results": [r.to_dict() for r in results],
                            "count": len(results),
                        }
                    )
                except (AttributeError, KeyError, TypeError) as e:
                    log.warning(f"GTN search failed: {e}")
                    return json.dumps({"error": str(e)})

            @agent.tool
            async def get_tutorial_content(
                ctx: RunContext[GalaxyAgentDependencies],
                topic: str,
                tutorial: str,
                max_length: int = 2000,
            ) -> str:
                """
                Get content of a specific tutorial.

                Args:
                    topic: Tutorial topic
                    tutorial: Tutorial name
                    max_length: Maximum content length to return

                Returns:
                    Tutorial content or error message
                """
                if not self.gtn_db:
                    return "GTN database not available"

                try:
                    content = self.gtn_db.get_tutorial_content(
                        topic, tutorial, max_length
                    )
                    return content or f"Tutorial {topic}/{tutorial} not found"
                except (AttributeError, KeyError, TypeError) as e:
                    log.warning(f"Failed to get tutorial content: {e}")
                    return f"Error: {e}"

            @agent.tool
            async def list_gtn_topics(ctx: RunContext[GalaxyAgentDependencies]) -> str:
                """
                List all available GTN topics.

                Returns:
                    JSON string with list of topics
                """
                if not self.gtn_db:
                    return json.dumps({"error": "GTN database not available"})

                try:
                    topics = self.gtn_db.get_topics()
                    return json.dumps({"topics": topics, "count": len(topics)})
                except (AttributeError, KeyError, TypeError) as e:
                    log.warning(f"Failed to get topics: {e}")
                    return json.dumps({"error": str(e)})

            @agent.tool
            async def search_tutorials_by_tools(
                ctx: RunContext[GalaxyAgentDependencies],
                tool_names: list[str],
                limit: int = 5,
            ) -> str:
                """
                Find tutorials that use specific Galaxy tools.

                Args:
                    tool_names: List of tool names to search for
                    limit: Maximum number of results

                Returns:
                    JSON string with matching tutorials
                """
                if not self.gtn_db:
                    return json.dumps({"error": "GTN database not available"})

                try:
                    results = self.gtn_db.search_by_tools(tool_names, limit)
                    return json.dumps(
                        {
                            "results": [r.to_dict() for r in results],
                            "count": len(results),
                            "tools_searched": tool_names,
                        }
                    )
                except (AttributeError, KeyError, TypeError) as e:
                    log.warning(f"Tool search failed: {e}")
                    return json.dumps({"error": str(e)})

        return agent

    def _prepare_prompt(self, query: str, context: dict[str, Any]) -> str:
        """
        Prepare the prompt for GTN agent.

        We skip including conversation_history in the prompt as it can interfere
        with the model's ability to generate comprehensive tutorial responses.
        """
        if not context:
            return query

        # Filter out conversation_history which can cause response truncation
        filtered_context = {
            k: v for k, v in context.items() if k != "conversation_history" and v
        }

        if not filtered_context:
            return query

        # Add only relevant context
        context_str = "\n".join([f"{k}: {v}" for k, v in filtered_context.items()])
        return f"Context:\n{context_str}\n\n{query}"

    def get_system_prompt(self) -> str:
        """Get the system prompt for the GTN training agent."""
        prompt_path = Path(__file__).parent / "prompts" / "gtn_training.md"
        return prompt_path.read_text()

    async def process(
        self, query: str, context: Optional[dict[str, Any]] = None
    ) -> AgentResponse:
        """
        Process a training-related query.

        Args:
            query: The user's training question or request
            context: Optional context about the user's situation

        Returns:
            AgentResponse with tutorial recommendations
        """
        try:
            # Check if GTN database is available
            if not self.gtn_db:
                return AgentResponse(
                    content="GTN database is not available. Please ensure it's properly initialized.",
                    confidence=ConfidenceLevel.LOW,
                    agent_type=self.agent_type,
                    suggestions=[],
                )

            # Run the agent to process the query with retry logic
            result = await self._run_with_retry(query)

            # Extract token usage if available
            usage_info = {}
            if hasattr(result, "usage"):
                try:
                    usage = result.usage()
                    usage_info = {
                        "input_tokens": getattr(usage, "input_tokens", 0),
                        "output_tokens": getattr(usage, "output_tokens", 0),
                        "total_tokens": getattr(usage, "total_tokens", 0),
                    }
                except Exception:
                    pass  # Usage not available

            # Handle different response formats based on model capabilities
            if self._supports_structured_output():
                # Handle structured output
                if hasattr(result, "output"):
                    response_data = result.output
                elif hasattr(result, "data"):
                    response_data = result.data
                else:
                    response_data = result

                # Fallback: If no tutorials found, try direct database search
                if not response_data.tutorials or len(response_data.tutorials) == 0:
                    log.info("No tutorials in response, falling back to direct search")
                    if self.gtn_db:  # Additional safety check
                        fallback_results = self.gtn_db.search(query, limit=5)
                    else:
                        fallback_results = []
                    if fallback_results:
                        # Create a new response with the fallback results
                        response_data = GTNSearchResponse(
                            tutorials=[r.to_dict() for r in fallback_results],
                            summary=f"Found {len(fallback_results)} tutorials related to your query",
                            learning_path=None,
                            prerequisites=[],
                            total_time=None,
                        )

                # Format the response
                content = self._format_gtn_response(response_data)
                suggestions = self._create_suggestions(response_data)
                confidence = (
                    ConfidenceLevel.HIGH
                    if response_data.tutorials
                    else ConfidenceLevel.MEDIUM
                )

                return AgentResponse(
                    content=content,
                    confidence=confidence,
                    agent_type=self.agent_type,
                    suggestions=suggestions,
                    metadata={
                        "tutorial_count": len(response_data.tutorials),
                        "has_learning_path": bool(response_data.learning_path),
                        "total_time": response_data.total_time,
                        "model": self._get_model_name(),
                        "method": (
                            "structured_with_fallback"
                            if not hasattr(result, "output")
                            or not result.output.tutorials
                            else "structured"
                        ),
                        **usage_info,
                    },
                )
            else:
                # Handle simple text output from DeepSeek
                response_text = (
                    str(result.data) if hasattr(result, "data") else str(result)
                )
                parsed_result = self._parse_simple_response(response_text)

                return AgentResponse(
                    content=parsed_result.get("content", response_text),
                    confidence=parsed_result.get("confidence", ConfidenceLevel.MEDIUM),
                    agent_type=self.agent_type,
                    suggestions=parsed_result.get("suggestions", []),
                    metadata={
                        "method": "simple_text",
                        "model": self._get_model_name(),
                        "tutorial_count": parsed_result.get("tutorial_count", 0),
                        **usage_info,
                    },
                )

        except OSError as e:
            log.error(f"GTN training agent network error: {e}")
            return self._get_error_response(str(e))
        except ValueError as e:
            log.error(f"GTN training agent value error: {e}")
            return self._get_error_response(str(e))

    def _format_gtn_response(self, response_data: GTNSearchResponse) -> str:
        """Format the GTN search response into user-friendly text."""
        parts = []

        # Add summary
        if response_data.summary:
            parts.append(response_data.summary)

        # Add tutorial details
        if response_data.tutorials:
            parts.append("\n**Relevant Tutorials:**")
            for i, tutorial in enumerate(response_data.tutorials, 1):
                title = tutorial.get("title", "Untitled Tutorial")
                topic = tutorial.get("topic", "Unknown")
                difficulty = tutorial.get("difficulty", "Unknown")
                time_estimation = tutorial.get("time_estimation", "Unknown")
                url = tutorial.get("url", "#")
                description = tutorial.get("description", "")

                parts.append(f"\n{i}. **{title}**")
                if description:
                    parts.append(f"   {description}")

                # Only show topic if it's meaningful
                if topic and topic != "Unknown":
                    parts.append(f"   - Topic: {topic}")

                # Only show difficulty if it's meaningful
                if difficulty and difficulty != "Unknown":
                    parts.append(f"   - Difficulty: {difficulty}")

                # Only show time if it's meaningful
                if time_estimation and time_estimation != "Unknown":
                    parts.append(f"   - Time: {time_estimation}")

                parts.append(f"   - Link: {url}")

        # Add learning path if suggested
        if response_data.learning_path:
            parts.append(
                f"\n**Suggested Learning Path:**\n{response_data.learning_path}"
            )

        # Add prerequisites
        if response_data.prerequisites:
            parts.append("\n**Prerequisites:**")
            for prereq in response_data.prerequisites:
                parts.append(f"- {prereq}")

        # Add total time estimate
        if response_data.total_time:
            parts.append(f"\n**Total Time Investment:** {response_data.total_time}")

        return "\n".join(parts)

    def _create_suggestions(
        self, response_data: GTNSearchResponse
    ) -> list[ActionSuggestion]:
        """Create action suggestions based on found tutorials."""
        suggestions = []

        # Suggest opening tutorials
        for tutorial in response_data.tutorials[:3]:  # Top 3 tutorials
            title = tutorial.get("title", "Untitled Tutorial")
            url = tutorial.get("url", "#")

            suggestions.append(
                ActionSuggestion(
                    action_type=ActionType.VIEW_EXTERNAL,
                    description=f"Open tutorial: {title}",
                    parameters={"url": url},
                    confidence=ConfidenceLevel.HIGH,
                    priority=1,
                )
            )

        # Suggest searching for related topics
        if response_data.tutorials:
            topics = []
            for t in response_data.tutorials:
                topic = t.get("topic", "Unknown")
                if topic != "Unknown":
                    topics.append(topic)

            topics = list(set(topics))
            for topic in topics[:2]:  # Top 2 topics
                suggestions.append(
                    ActionSuggestion(
                        action_type=ActionType.VIEW_EXTERNAL,
                        description=f"Explore more {topic} tutorials",
                        parameters={
                            "url": f"https://training.galaxyproject.org/training-material/topics/{topic.lower()}/"
                        },
                        confidence=ConfidenceLevel.MEDIUM,
                        priority=2,
                    )
                )

        return suggestions

    def _get_simple_system_prompt(self) -> str:
        """Simple system prompt for models without structured output."""
        return """
        You are a Galaxy training specialist. Help users find relevant Galaxy Training Network tutorials.

        Respond in this exact format:
        TUTORIALS: [tutorial name 1, tutorial name 2]
        TOPICS: [topic 1, topic 2]
        SUMMARY: [brief summary of recommendations]
        CONFIDENCE: [high/medium/low]

        Example:
        TUTORIALS: Galaxy 101, RNA-seq analysis with Salmon
        TOPICS: Introduction, Transcriptomics
        SUMMARY: For beginners, start with Galaxy 101 to learn the basics, then move to RNA-seq analysis
        CONFIDENCE: high

        Always recommend actual GTN tutorials and provide helpful guidance.
        """

    def _parse_simple_response(self, response_text: str) -> dict[str, Any]:
        """Parse simple text response into structured format."""

        # Extract structured information from text
        tutorials = re.search(r"TUTORIALS:\s*([^\n]+)", response_text, re.IGNORECASE)
        topics = re.search(r"TOPICS:\s*([^\n]+)", response_text, re.IGNORECASE)
        summary = re.search(r"SUMMARY:\s*([^\n]+)", response_text, re.IGNORECASE)
        confidence_match = re.search(
            r"CONFIDENCE:\s*(\w+)", response_text, re.IGNORECASE
        )

        # Parse confidence level
        confidence_level = ConfidenceLevel.MEDIUM
        if confidence_match:
            conf_str = confidence_match.group(1).lower()
            if conf_str == "high":
                confidence_level = ConfidenceLevel.HIGH
            elif conf_str == "low":
                confidence_level = ConfidenceLevel.LOW

        # Build content
        content_parts = []

        if summary and summary.group(1).strip():
            content_parts.append(summary.group(1).strip())

        if tutorials and tutorials.group(1).strip():
            tutorial_list = tutorials.group(1).strip()
            content_parts.append(f"\n**Recommended Tutorials:**\n{tutorial_list}")

        if topics and topics.group(1).strip():
            topic_list = topics.group(1).strip()
            content_parts.append(f"\n**Related Topics:** {topic_list}")

        content_parts.append(
            "\n**Note:** Visit https://training.galaxyproject.org/training-material/ to access all tutorials."
        )

        if not content_parts:
            content_parts = [response_text]  # Fallback to full response

        # Create suggestions
        suggestions = []
        if tutorials and tutorials.group(1).strip():
            suggestions.append(
                ActionSuggestion(
                    action_type=ActionType.VIEW_EXTERNAL,
                    description="Visit Galaxy Training Network",
                    parameters={
                        "url": "https://training.galaxyproject.org/training-material/"
                    },
                    confidence=confidence_level,
                    priority=1,
                )
            )

        return {
            "content": "\n".join(content_parts),
            "confidence": confidence_level,
            "tutorial_count": len(tutorials.group(1).split(","))
            if tutorials and tutorials.group(1).strip()
            else 0,
            "suggestions": suggestions,
        }

    def _get_fallback_content(self) -> str:
        """Get fallback content for GTN failures."""
        return (
            "I couldn't search the training materials at this moment. "
            "You can browse tutorials directly at: "
            "https://training.galaxyproject.org/training-material/"
        )

    def _get_error_response(self, error_message: str) -> AgentResponse:
        """Get error response for GTN agent failures."""
        return AgentResponse(
            content=f"I encountered an error while searching training materials: {error_message}\n\n"
            f"You can browse tutorials directly at: https://training.galaxyproject.org/training-material/",
            confidence=ConfidenceLevel.LOW,
            agent_type=self.agent_type,
            suggestions=[
                ActionSuggestion(
                    action_type=ActionType.VIEW_EXTERNAL,
                    description="Visit Galaxy Training Network",
                    parameters={
                        "url": "https://training.galaxyproject.org/training-material/"
                    },
                    confidence=ConfidenceLevel.HIGH,
                    priority=1,
                )
            ],
            metadata={"error": error_message, "method": "error_fallback"},
        )
