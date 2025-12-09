"""
Query router agent for intelligent request routing.
"""

import logging
import re
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
)

from pydantic import BaseModel
from pydantic_ai import Agent

from galaxy.schema.agents import ConfidenceLevel
from .base import (
    ActionSuggestion,
    ActionType,
    AgentResponse,
    AgentType,
    BaseGalaxyAgent,
    GalaxyAgentDependencies,
)

log = logging.getLogger(__name__)


class RoutingDecision(BaseModel):
    """Structured decision from the router agent."""

    primary_agent: str
    secondary_agents: List[str] = []
    complexity: str  # "simple" or "complex"
    confidence: str = "medium"  # "low", "medium", or "high" - plain string to avoid $defs in JSON schema
    reasoning: str
    direct_response: str = ""  # If router can answer directly

    def get_confidence_level(self) -> ConfidenceLevel:
        """Convert string confidence to ConfidenceLevel enum."""
        conf_str = (self.confidence or "medium").lower()
        if conf_str == "high":
            return ConfidenceLevel.HIGH
        elif conf_str == "low":
            return ConfidenceLevel.LOW
        return ConfidenceLevel.MEDIUM


class QueryRouterAgent(BaseGalaxyAgent):
    """
    Router agent that analyzes queries and routes them to appropriate specialists.

    This agent serves as the central coordinator, determining which specialized
    agent(s) should handle a user's query based on the content and context.
    """

    def _create_agent(self) -> Agent:
        """Create the router agent with structured output."""
        model_name = self._get_agent_config("model", "")

        # DeepSeek models don't support structured output, use fallback
        if "deepseek" in model_name.lower():
            return Agent(
                self._get_model(),
                deps_type=GalaxyAgentDependencies,
                system_prompt=self._get_simple_system_prompt(),
            )
        else:
            return Agent(
                self._get_model(),
                deps_type=GalaxyAgentDependencies,
                output_type=RoutingDecision,
                system_prompt=self.get_system_prompt(),
            )

    def get_system_prompt(self) -> str:
        """Get the system prompt for the router agent."""
        prompt_path = Path(__file__).parent / "prompts" / "router.md"
        return prompt_path.read_text()

    async def route_query(self, query: str, context: Dict[str, Any] = None) -> RoutingDecision:
        """
        Route a query to appropriate agent(s).

        Args:
            query: The user's query
            context: Optional context (job info, etc.)

        Returns:
            RoutingDecision with agent selection and reasoning
        """
        try:
            # Build the full query with context if we have conversation history
            full_query = query
            if context and "conversation_history" in context:
                history = context["conversation_history"]
                if history and len(history) > 0:
                    # Format conversation history for the model
                    history_text = "Previous conversation:\n"
                    for msg in history[-6:]:
                        role = msg.get("role", "unknown")
                        content = msg.get("content", "")
                        history_text += f"{role}: {content}\n"
                    history_text += f"\nCurrent query: {query}"
                    full_query = history_text

            # Use pydantic-ai for all endpoints with retry logic
            result = await self._run_with_retry(full_query)

            model_name = self._get_agent_config("model", "")

            # Handle DeepSeek simple text response
            if "deepseek" in model_name.lower():
                response_text = str(result.data) if hasattr(result, "data") else str(result)
                return self._parse_simple_response(response_text, query)

            # Handle structured output for other models
            if hasattr(result, "data"):
                return result.data
            elif hasattr(result, "output"):
                return result.output
            elif hasattr(result, "primary_agent"):
                # It's already a RoutingDecision
                return result
            else:
                # For pydantic-ai, the result might be wrapped
                return result
        except (ConnectionError, TimeoutError, OSError) as e:
            log.warning(f"Router agent network error, using fallback: {e}")
            return self._fallback_routing(query, context)
        except ValueError as e:
            log.warning(f"Router agent value error, using fallback: {e}")
            return self._fallback_routing(query, context)

    def _fallback_routing(self, query: str, context: Dict[str, Any] = None) -> RoutingDecision:
        """Fallback routing when AI router fails - uses intent-based heuristics."""
        query_lower = query.lower()

        # Define keyword sets for different intents
        intent_keywords = {
            AgentType.ERROR_ANALYSIS: (
                ["error", "fail", "crash", "not work", "broken", "stderr", "exit code", "died", "killed"],
                1.0,  # Base score
            ),
            AgentType.CUSTOM_TOOL: (
                ["create", "build", "make", "wrap", "custom tool", "new tool", "yaml", "xml definition"],
                1.0,
            ),
            AgentType.TOOL_RECOMMENDATION: (
                [
                    "which tool",
                    "what tool",
                    "how to",
                    "how do i",
                    "find tool",
                    "need to",
                    "want to",
                    "select",
                    "filter",
                    "process",
                    "convert",
                    "align",
                    "map",
                    "call variants",
                ],
                0.5,  # Lower base score as it's a common fallback
            ),
        }

        # Score each intent
        scores = dict.fromkeys(intent_keywords, 0.0)
        for intent, (keywords, base_score) in intent_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                scores[intent] += base_score

        # Determine the winning agent
        if not any(scores.values()):
            # If no keywords matched, default to tool_recommendation
            best_agent = AgentType.TOOL_RECOMMENDATION
            reasoning = "No clear intent keywords found, defaulting to tool recommendation."
            confidence = "low"
        else:
            best_agent = max(scores, key=scores.get)
            reasoning = f"Query contains keywords related to {best_agent.replace('_', ' ')}."
            # Determine confidence based on score
            if scores[best_agent] > 1.5:
                confidence = "high"
            elif scores[best_agent] > 0.5:
                confidence = "medium"
            else:
                confidence = "low"

        # Simple direct responses for greetings or citations
        if any(phrase in query_lower for phrase in ["cite galaxy", "citation", "reference"]):
            return RoutingDecision(
                primary_agent="router",
                confidence="high",
                reasoning="User is asking for citation information.",
                direct_response="""To cite Galaxy, please use: Nekrutenko, A., et al. (2024). The Galaxy platform for accessible, reproducible, and collaborative data analyses: 2024 update. Nucleic Acids Research. https://doi.org/10.1093/nar/gkae410

For specific tools, please also cite the individual tool publications.""",
            )

        return RoutingDecision(
            primary_agent=best_agent,
            secondary_agents=[],
            complexity="simple",  # Fallback is always simple
            confidence=confidence,
            reasoning=reasoning,
            direct_response="",
        )

    async def process(self, query: str, context: Dict[str, Any] = None) -> AgentResponse:
        """
        Process a routing request and return guidance.

        For the router agent, processing means making routing decisions
        and potentially providing direct responses for simple queries.
        """
        routing_decision = await self.route_query(query, context)

        # If we have a direct response, return it
        if routing_decision.direct_response:
            return AgentResponse(
                content=routing_decision.direct_response,
                confidence=routing_decision.get_confidence_level(),
                agent_type=self.agent_type,
                suggestions=[],
                metadata={"routing_decision": routing_decision.model_dump(), "handled_directly": True},
            )

        # Otherwise, provide routing guidance
        content = self._format_routing_response(routing_decision)

        suggestions = [
            ActionSuggestion(
                action_type=ActionType.TOOL_RUN,
                description=f"Route to {routing_decision.primary_agent} agent",
                parameters={"agent": routing_decision.primary_agent},
                confidence=routing_decision.get_confidence_level(),
                priority=1,
            )
        ]

        # Add secondary agent suggestions
        for secondary_agent in routing_decision.secondary_agents:
            suggestions.append(
                ActionSuggestion(
                    action_type=ActionType.TOOL_RUN,
                    description=f"Also consult {secondary_agent} agent",
                    parameters={"agent": secondary_agent},
                    confidence=ConfidenceLevel.MEDIUM,
                    priority=2,
                )
            )

        return AgentResponse(
            content=content,
            confidence=routing_decision.get_confidence_level(),
            agent_type=self.agent_type,
            suggestions=suggestions,
            metadata={"routing_decision": routing_decision.model_dump(), "handled_directly": False},
            reasoning=routing_decision.reasoning,
        )

    def _format_routing_response(self, decision: RoutingDecision) -> str:
        """Format the routing decision into a user-friendly response."""
        content_parts = [f"I'll route your query to the {decision.primary_agent.replace('_', ' ')} specialist."]

        if decision.reasoning:
            content_parts.append(f"Reasoning: {decision.reasoning}")

        if decision.secondary_agents:
            secondary_list = ", ".join(agent.replace("_", " ") for agent in decision.secondary_agents)
            content_parts.append(f"I may also consult: {secondary_list}")

        if decision.complexity == "complex":
            content_parts.append("This appears to be a complex query that may require multiple steps to resolve.")

        return " ".join(content_parts)

    def _get_simple_system_prompt(self) -> str:
        """Simple system prompt for models that don't support structured output."""
        return """
        You are a Galaxy platform routing assistant. Analyze the user's query and respond with a simple routing decision.
        
        Available agents:
        - error_analysis: For debugging, troubleshooting, job failures
        - custom_tool: For creating new tools, tool development
        - tool_recommendation: For finding tools, "how to" questions, analysis guidance
        
        Respond in this exact format:
        ROUTE_TO: [agent_name]
        REASONING: [brief explanation]
        
        Example:
        ROUTE_TO: tool_recommendation
        REASONING: User asking how to perform analysis task
        """

    def _parse_simple_response(self, response_text: str, query: str) -> RoutingDecision:
        """Parse simple text response from DeepSeek into RoutingDecision."""
        # Extract ROUTE_TO and REASONING from response
        route_match = re.search(r"ROUTE_TO:\s*(\w+)", response_text, re.IGNORECASE)
        reasoning_match = re.search(r"REASONING:\s*(.+?)(?:\n|$)", response_text, re.IGNORECASE | re.DOTALL)

        if route_match:
            agent = route_match.group(1).lower()
            reasoning = reasoning_match.group(1).strip() if reasoning_match else "DeepSeek routing"

            # Validate agent is routable (excludes router, orchestrator, experimental agents)
            routable_agents = [
                AgentType.ERROR_ANALYSIS,
                AgentType.CUSTOM_TOOL,
                AgentType.TOOL_RECOMMENDATION,
            ]
            if agent not in routable_agents:
                agent = AgentType.TOOL_RECOMMENDATION
                reasoning = f"Fallback to {AgentType.TOOL_RECOMMENDATION}. Original: {reasoning}"

            return RoutingDecision(
                primary_agent=agent,
                secondary_agents=[],
                complexity="simple",
                confidence="medium",
                reasoning=reasoning,
            )
        else:
            # Couldn't parse, use fallback
            return self._fallback_routing(query)

    def _get_fallback_content(self) -> str:
        """Get fallback content for router failures."""
        return "Unable to determine the best routing for your query."
