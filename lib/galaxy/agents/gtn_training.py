"""GTN Training Agent - searches Galaxy Training Network tutorials and FAQs."""

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
    extract_result_content,
    extract_structured_output,
    extract_usage_info,
    GalaxyAgentDependencies,
    normalize_llm_text,
)
from .gtn import GTNSearchDB

log = logging.getLogger(__name__)


class GTNSearchResponse(BaseModel):
    """Structured response from GTN training agent."""

    tutorials: list[dict[str, Any]] = Field(default_factory=list, description="List of matching tutorials")
    faqs: list[dict[str, Any]] = Field(default_factory=list, description="List of matching FAQs")
    summary: str = Field(..., description="Natural language summary of findings")
    learning_path: Optional[str] = Field(None, description="Suggested learning progression")
    prerequisites: list[str] = Field(default_factory=list, description="Recommended prerequisites")
    total_time: Optional[str] = Field(None, description="Estimated total time for suggested tutorials")


class GTNTrainingAgent(BaseGalaxyAgent):
    """Searches GTN tutorials to help users find training materials and learning paths."""

    agent_type = AgentType.GTN_TRAINING
    capability_blurb = (
        "Find Galaxy Training Network tutorials and step-by-step guidance for an analysis you want to learn."
    )

    # The model tends to keep re-searching long after it has enough material,
    # and every extra round re-sends the whole growing transcript -- a single
    # query was costing ~18 search rounds / ~90k tokens. Cap the number of
    # data-gathering tool calls and, once spent, return a terminal instruction
    # so the model synthesizes from what it already has instead of looping.
    MAX_TOOL_CALLS = 3
    # Note: name the search tools explicitly rather than saying "don't call any
    # tools" -- the structured response is itself delivered via an output tool
    # call, so a blanket "no tools" instruction makes the model emit prose that
    # fails structured-output validation.
    _TOOL_BUDGET_MESSAGE = (
        "SEARCH BUDGET REACHED. You already have enough material to answer. "
        "Do NOT call search_gtn_tutorials, search_gtn_faqs, "
        "search_tutorials_by_tools, or get_tutorial_content again. Produce your "
        "final structured answer now from the results and tutorial content "
        "already returned above. If none is a strong match, say so and point to "
        "the relevant GTN topic page."
    )

    def __init__(self, deps: GalaxyAgentDependencies):
        super().__init__(deps)

        self._tool_calls = 0

        db_path = getattr(deps.config, "gtn_database_path", None)
        download_url = getattr(deps.config, "gtn_database_url", None)

        self.gtn_db: GTNSearchDB | None = None
        try:
            self.gtn_db = GTNSearchDB(db_path=db_path, download_url=download_url)
            log.info("GTN database initialized successfully")
        except (OSError, RuntimeError) as e:
            log.warning(f"GTN database not available: {e}")
            self.gtn_db = None

    def _charge_tool_budget(self) -> Optional[str]:
        """Count a data-gathering tool call; once over budget return a stop
        message instead of more data so the model answers from what it has."""
        self._tool_calls += 1
        if self._tool_calls > self.MAX_TOOL_CALLS:
            return self._TOOL_BUDGET_MESSAGE
        return None

    def _create_agent(self) -> Agent[GalaxyAgentDependencies, Any]:
        if not self._supports_structured_output():
            return Agent(
                self._get_model(),
                deps_type=GalaxyAgentDependencies,
                system_prompt=self._get_simple_system_prompt(),
                retries=self._get_retries(),
            )

        agent = Agent(
            self._get_model(),
            deps_type=GalaxyAgentDependencies,
            output_type=GTNSearchResponse,
            system_prompt=self.get_system_prompt(),
            # gpt-oss occasionally emits prose instead of a valid GTNSearchResponse;
            # the pydantic-ai default of 1 output retry turns that into a hard error.
            # Configurable via inference_services, defaulting to 3 so an occasional
            # malformed output recovers.
            retries=self._get_retries(),
        )

        @agent.tool
        async def search_gtn_tutorials(
            ctx: RunContext[GalaxyAgentDependencies],
            query: str,
            topic: Optional[str] = None,
            difficulty: Optional[str] = None,
            hands_on_only: bool = False,
            limit: int = 5,
        ) -> str:
            """Search GTN tutorials using full-text search over titles, descriptions, and content."""
            over_budget = self._charge_tool_budget()
            if over_budget:
                return over_budget
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
            except Exception as e:
                log.warning(f"GTN search failed: {e}")
                return json.dumps({"error": str(e)})

        @agent.tool
        async def get_tutorial_content(
            ctx: RunContext[GalaxyAgentDependencies],
            topic: str,
            tutorial: str,
            max_length: int = 1500,
        ) -> str:
            """Get the full content of a specific tutorial by topic and name."""
            over_budget = self._charge_tool_budget()
            if over_budget:
                return over_budget
            if not self.gtn_db:
                return "GTN database not available"
            try:
                content = self.gtn_db.get_tutorial_content(topic, tutorial, max_length)
                return content or f"Tutorial {topic}/{tutorial} not found"
            except Exception as e:
                log.warning(f"Failed to get tutorial content: {e}")
                return f"Error: {e}"

        @agent.tool
        async def list_gtn_topics(ctx: RunContext[GalaxyAgentDependencies]) -> str:
            """List all available GTN tutorial topics."""
            if not self.gtn_db:
                return json.dumps({"error": "GTN database not available"})
            try:
                topics = self.gtn_db.get_topics()
                return json.dumps({"topics": topics, "count": len(topics)})
            except Exception as e:
                log.warning(f"Failed to get topics: {e}")
                return json.dumps({"error": str(e)})

        @agent.tool
        async def search_gtn_faqs(
            ctx: RunContext[GalaxyAgentDependencies],
            query: str,
            category: Optional[str] = None,
            limit: int = 5,
        ) -> str:
            """Search Galaxy / GTN FAQs for short, definitional or how-do-I questions.

            FAQs are curated short answers covering Galaxy interface basics
            ("what is a history", "how do I share a workflow"). Prefer this
            over ``search_gtn_tutorials`` for queries shorter than about
            eight words or phrased as ``what is X`` / ``how do I X``.
            """
            over_budget = self._charge_tool_budget()
            if over_budget:
                return over_budget
            if not self.gtn_db:
                return json.dumps({"error": "GTN database not available"})
            try:
                results = self.gtn_db.search_faqs(query=query, category=category, limit=limit)
                return json.dumps(
                    {
                        "results": [r.to_dict() for r in results],
                        "count": len(results),
                    }
                )
            except Exception as e:
                log.warning(f"GTN FAQ search failed: {e}")
                return json.dumps({"error": str(e)})

        @agent.tool
        async def search_tutorials_by_tools(
            ctx: RunContext[GalaxyAgentDependencies],
            tool_names: list[str],
            limit: int = 5,
        ) -> str:
            """Find tutorials that use specific Galaxy tools."""
            over_budget = self._charge_tool_budget()
            if over_budget:
                return over_budget
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
            except Exception as e:
                log.warning(f"Tool search failed: {e}")
                return json.dumps({"error": str(e)})

        return agent

    def get_system_prompt(self) -> str:
        prompt_path = Path(__file__).parent / "prompts" / "gtn_training.md"
        return prompt_path.read_text()

    async def process(self, query: str, context: Optional[dict[str, Any]] = None) -> AgentResponse:
        validation_error = self._validate_query(query)
        if validation_error:
            return self._validation_error_response(validation_error)

        self._tool_calls = 0

        if not self.gtn_db:
            return self._build_response(
                content="GTN database is not available. Please ensure it's properly initialized.",
                confidence=ConfidenceLevel.LOW,
                method="error",
                query=query,
                error="gtn_database_unavailable",
            )

        try:
            message_history = self._extract_message_history(context)
            result = await self._run_with_retry(query, message_history=message_history)

            usage = extract_usage_info(result)
            if usage:
                log.info(
                    "GTN agent token usage: input=%s output=%s total=%s (query_len=%d)",
                    usage.get("input_tokens", 0),
                    usage.get("output_tokens", 0),
                    usage.get("total_tokens", 0),
                    len(query),
                )

            if self._supports_structured_output():
                response_data = extract_structured_output(result, GTNSearchResponse, log)
                if response_data is None:
                    return self._build_response(
                        content=extract_result_content(result),
                        confidence=ConfidenceLevel.LOW,
                        method="text_fallback",
                        result=result,
                        query=query,
                        error="invalid_structured_output",
                    )

                used_fallback = False
                if not response_data.tutorials and not response_data.faqs:
                    log.info("No tutorials or FAQs in response, falling back to direct search")
                    fallback_results = self.gtn_db.search(query, limit=5)
                    if fallback_results:
                        used_fallback = True
                        response_data = GTNSearchResponse(
                            tutorials=[r.to_dict() for r in fallback_results],
                            summary=f"Found {len(fallback_results)} tutorials related to your query",
                        )

                return self._build_response(
                    content=self._format_gtn_response(response_data),
                    confidence=(
                        ConfidenceLevel.HIGH
                        if response_data.tutorials or response_data.faqs
                        else ConfidenceLevel.MEDIUM
                    ),
                    method="structured_with_fallback" if used_fallback else "structured",
                    result=result,
                    query=query,
                    suggestions=self._create_suggestions(response_data),
                    agent_data={
                        "tutorial_count": len(response_data.tutorials),
                        "faq_count": len(response_data.faqs),
                        "has_learning_path": bool(response_data.learning_path),
                        "total_time": response_data.total_time,
                    },
                )

            # Simple-text path for backends that don't support structured output.
            response_text = extract_result_content(result)
            parsed_result = self._parse_simple_response(response_text)
            return self._build_response(
                content=parsed_result.get("content", response_text),
                confidence=parsed_result.get("confidence", ConfidenceLevel.MEDIUM),
                method="simple_text",
                result=result,
                query=query,
                suggestions=parsed_result.get("suggestions", []),
                agent_data={"tutorial_count": parsed_result.get("tutorial_count", 0)},
            )

        except (OSError, ValueError) as e:
            log.error(f"GTN training agent error: {e}")
            return self._get_error_response(str(e))

    def _format_gtn_response(self, response_data: GTNSearchResponse) -> str:
        parts: list[str] = []
        if response_data.summary:
            parts.append(response_data.summary)

        if response_data.tutorials:
            parts.append("\n**Relevant Tutorials:**")
            for i, tutorial in enumerate(response_data.tutorials, 1):
                title = tutorial.get("title", "Untitled Tutorial")
                topic = tutorial.get("topic", "Unknown")
                difficulty = tutorial.get("difficulty", "Unknown")
                time_estimation = tutorial.get("time_estimation", "Unknown")
                url = tutorial.get("url", "#")
                snippet = tutorial.get("snippet", "")

                parts.append(f"\n{i}. **{title}**")
                if snippet:
                    parts.append(f"   {snippet}")
                if topic and topic != "Unknown":
                    parts.append(f"   - Topic: {topic}")
                if difficulty and difficulty != "Unknown":
                    parts.append(f"   - Difficulty: {difficulty}")
                if time_estimation and time_estimation != "Unknown":
                    parts.append(f"   - Time: {time_estimation}")
                parts.append(f"   - Link: {url}")

        if response_data.faqs:
            parts.append("\n**Relevant FAQs:**")
            for i, faq in enumerate(response_data.faqs, 1):
                title = faq.get("title", "Untitled FAQ")
                category = faq.get("category", "Unknown")
                area = faq.get("area", "")
                url = faq.get("url", "#")
                snippet = faq.get("snippet", "")

                parts.append(f"\n{i}. **{title}**")
                if snippet:
                    parts.append(f"   {snippet}")
                if category and category != "Unknown":
                    parts.append(f"   - Category: {category}")
                if area:
                    parts.append(f"   - Area: {area}")
                parts.append(f"   - Link: {url}")

        if response_data.learning_path:
            parts.append(f"\n**Suggested Learning Path:**\n{response_data.learning_path}")

        if response_data.prerequisites:
            parts.append("\n**Prerequisites:**")
            for prereq in response_data.prerequisites:
                parts.append(f"- {prereq}")

        if response_data.total_time:
            parts.append(f"\n**Total Time Investment:** {response_data.total_time}")

        return "\n".join(parts)

    def _create_suggestions(self, response_data: GTNSearchResponse) -> list[ActionSuggestion]:
        suggestions: list[ActionSuggestion] = []

        for tutorial in response_data.tutorials[:3]:
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

        for faq in response_data.faqs[:3]:
            title = faq.get("title", "Untitled FAQ")
            url = faq.get("url", "#")
            suggestions.append(
                ActionSuggestion(
                    action_type=ActionType.VIEW_EXTERNAL,
                    description=f"Open FAQ: {title}",
                    parameters={"url": url},
                    confidence=ConfidenceLevel.HIGH,
                    priority=1 if not response_data.tutorials else 2,
                )
            )

        topics: set[str] = set()
        for t in response_data.tutorials:
            topic = t.get("topic")
            if topic and topic != "Unknown":
                topics.add(topic)
        for topic in list(topics)[:2]:
            suggestions.append(
                ActionSuggestion(
                    action_type=ActionType.VIEW_EXTERNAL,
                    description=f"Explore more {topic} tutorials",
                    parameters={"url": f"https://training.galaxyproject.org/training-material/topics/{topic.lower()}/"},
                    confidence=ConfidenceLevel.MEDIUM,
                    priority=2,
                )
            )

        return suggestions

    def _get_simple_system_prompt(self) -> str:
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
        # normalize_llm_text handles literal \n that some backends emit instead of real newlines
        normalized_text = normalize_llm_text(response_text)

        tutorials = re.search(r"TUTORIALS:\s*([^\n]+)", normalized_text, re.IGNORECASE)
        topics = re.search(r"TOPICS:\s*([^\n]+)", normalized_text, re.IGNORECASE)
        summary = re.search(r"SUMMARY:\s*([^\n]+)", normalized_text, re.IGNORECASE)
        confidence_match = re.search(r"CONFIDENCE:\s*(\w+)", normalized_text, re.IGNORECASE)

        confidence_level = ConfidenceLevel.MEDIUM
        if confidence_match:
            conf_str = confidence_match.group(1).lower()
            if conf_str == "high":
                confidence_level = ConfidenceLevel.HIGH
            elif conf_str == "low":
                confidence_level = ConfidenceLevel.LOW

        content_parts: list[str] = []
        if summary and summary.group(1).strip():
            content_parts.append(summary.group(1).strip())
        if tutorials and tutorials.group(1).strip():
            content_parts.append(f"\n**Recommended Tutorials:**\n{tutorials.group(1).strip()}")
        if topics and topics.group(1).strip():
            content_parts.append(f"\n**Related Topics:** {topics.group(1).strip()}")
        content_parts.append(
            "\n**Note:** Visit https://training.galaxyproject.org/training-material/ to access all tutorials."
        )
        if not content_parts:
            content_parts = [response_text]

        suggestions: list[ActionSuggestion] = []
        if tutorials and tutorials.group(1).strip() and self.gtn_db:
            for tutorial_name in [t.strip() for t in tutorials.group(1).split(",")][:3]:
                results = self.gtn_db.search(tutorial_name, limit=1)
                if results:
                    result = results[0]
                    suggestions.append(
                        ActionSuggestion(
                            action_type=ActionType.VIEW_EXTERNAL,
                            description=f"Open tutorial: {result.title}",
                            parameters={"url": result.url},
                            confidence=confidence_level,
                            priority=1,
                        )
                    )

        if not suggestions:
            suggestions.append(
                ActionSuggestion(
                    action_type=ActionType.VIEW_EXTERNAL,
                    description="Visit Galaxy Training Network",
                    parameters={"url": "https://training.galaxyproject.org/training-material/"},
                    confidence=confidence_level,
                    priority=1,
                )
            )

        return {
            "content": "\n".join(content_parts),
            "confidence": confidence_level,
            "tutorial_count": len(tutorials.group(1).split(",")) if tutorials and tutorials.group(1).strip() else 0,
            "suggestions": suggestions,
        }

    def _get_fallback_content(self) -> str:
        return (
            "I couldn't search the training materials at this moment. "
            "You can browse tutorials directly at: "
            "https://training.galaxyproject.org/training-material/"
        )

    def _get_error_response(self, error_message: str) -> AgentResponse:
        return self._build_response(
            content=f"I encountered an error while searching training materials: {error_message}\n\n"
            f"You can browse tutorials directly at: https://training.galaxyproject.org/training-material/",
            confidence=ConfidenceLevel.LOW,
            method="error_fallback",
            suggestions=[
                ActionSuggestion(
                    action_type=ActionType.VIEW_EXTERNAL,
                    description="Visit Galaxy Training Network",
                    parameters={"url": "https://training.galaxyproject.org/training-material/"},
                    confidence=ConfidenceLevel.HIGH,
                    priority=1,
                )
            ],
            error=error_message,
        )
