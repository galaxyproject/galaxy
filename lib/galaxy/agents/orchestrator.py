"""
Workflow orchestration agent for coordinating multiple agents on complex tasks.
"""

import asyncio
import logging
import re
from pathlib import Path
from typing import (
    Any,
    Optional,
)

from pydantic import BaseModel
from pydantic_ai import Agent

from galaxy.schema.agents import ConfidenceLevel
from .base import (
    AgentResponse,
    AgentType,
    BaseGalaxyAgent,
    GalaxyAgentDependencies,
)

log = logging.getLogger(__name__)


def _create_error_response(agent_name: str, error_msg: str, is_timeout: bool = False) -> AgentResponse:
    """Create a standardized error response for agent failures."""
    return AgentResponse(
        content=error_msg,
        confidence=ConfidenceLevel.LOW,
        agent_type=agent_name,
        suggestions=[],
        metadata={"error": True, "timeout": is_timeout},
    )


class AgentPlan(BaseModel):
    """Simple plan for which agents to call."""

    agents: list[str]  # List of agent names to call
    sequential: bool = False  # True if agents should run in sequence
    reasoning: str


class WorkflowOrchestratorAgent(BaseGalaxyAgent):
    """
    Agent that orchestrates multiple specialist agents for complex tasks.

    This agent analyzes complex queries and coordinates multiple agents
    to provide comprehensive solutions.
    """

    agent_type = AgentType.ORCHESTRATOR

    def __init__(self, deps: GalaxyAgentDependencies):
        super().__init__(deps)

    def _create_agent(self) -> Agent[GalaxyAgentDependencies, Any]:
        """Create the orchestrator agent with conditional structured output."""
        if self._supports_structured_output():
            agent = Agent(
                self._get_model(),
                deps_type=GalaxyAgentDependencies,
                output_type=AgentPlan,
                system_prompt=self.get_system_prompt(),
            )
        else:
            # DeepSeek and other models without structured output
            agent = Agent(
                self._get_model(),
                deps_type=GalaxyAgentDependencies,
                system_prompt=self._get_simple_system_prompt(),
            )

        return agent

    def get_system_prompt(self) -> str:
        """Get the system prompt for agent selection."""
        prompt_path = Path(__file__).parent / "prompts" / "orchestrator.md"
        return prompt_path.read_text()

    async def process(self, query: str, context: Optional[dict[str, Any]] = None) -> AgentResponse:
        """
        Process an orchestration request and coordinate multiple agents.

        Args:
            query: Complex user query requiring multiple agents
            context: Additional context for orchestration

        Returns:
            Comprehensive response from multiple coordinated agents
        """
        try:
            # Get agent plan from LLM
            plan = await self._get_agent_plan(query)

            # Execute agents
            if plan.sequential:
                responses = await self._execute_sequential(plan.agents, query, context)
            else:
                responses = await self._execute_parallel(plan.agents, query, context)

            # Combine responses
            combined_content = self._combine_responses(responses, plan.reasoning)

            return AgentResponse(
                content=combined_content,
                confidence=ConfidenceLevel.HIGH,
                agent_type=self.agent_type,
                suggestions=[],
                metadata={
                    "agents_used": plan.agents,
                    "execution_type": "sequential" if plan.sequential else "parallel",
                    "reasoning": plan.reasoning,
                },
            )

        except OSError as e:
            log.error(f"Orchestration network error: {e}")
            return self._get_fallback_response(query, str(e))
        except ValueError as e:
            log.error(f"Orchestration value error: {e}")
            return self._get_fallback_response(query, str(e))
        except Exception as e:
            log.error(f"Unexpected error during orchestration: {e}")
            return self._get_fallback_response(query, str(e))

    async def _get_agent_plan(self, query: str) -> AgentPlan:
        """Get plan for which agents to call."""
        try:
            result = await self._run_with_retry(query)

            if self._supports_structured_output():
                if hasattr(result, "data"):
                    return result.data
                elif hasattr(result, "output"):
                    return result.output
                else:
                    return result
            else:
                # Parse simple text response for models without structured output
                response_text = str(result.data) if hasattr(result, "data") else str(result)
                return self._parse_simple_plan(response_text)

        except OSError as e:
            log.warning(f"Agent plan generation network error, using fallback: {e}")
            return AgentPlan(
                agents=["error_analysis"],
                sequential=False,
                reasoning="Fallback to single agent due to network error",
            )
        except ValueError as e:
            log.warning(f"Agent plan generation value error, using fallback: {e}")
            return AgentPlan(
                agents=["error_analysis"],
                sequential=False,
                reasoning="Fallback to single agent due to planning error",
            )

    def _parse_simple_plan(self, response_text: str) -> AgentPlan:
        """Parse text response into AgentPlan for models without structured output."""
        # Extract agents list
        agents_match = re.search(r"agents.*?\[(.*?)\]", response_text, re.IGNORECASE | re.DOTALL)
        if agents_match:
            agents_str = agents_match.group(1)
            agents = [a.strip().strip("\"'") for a in agents_str.split(",")]
        else:
            agents = ["error_analysis"]  # fallback

        # Extract sequential flag
        sequential = "sequential=true" in response_text.lower()

        # Extract reasoning
        reasoning_match = re.search(
            r"reasoning[=:]?\s*[\"']?(.*?)[\"']?$",
            response_text,
            re.IGNORECASE | re.MULTILINE,
        )
        reasoning = reasoning_match.group(1) if reasoning_match else "Multi-agent coordination"

        return AgentPlan(agents=agents, sequential=sequential, reasoning=reasoning)

    def _get_agent_timeout(self) -> float:
        """Get timeout in seconds for individual agent execution."""
        return self._get_agent_config("agent_timeout", 60.0)

    async def _execute_sequential(
        self, agents: list[str], query: str, context: Optional[dict[str, Any]] = None
    ) -> dict[str, AgentResponse]:
        """Execute agents sequentially with timeout protection."""
        from galaxy.agents import agent_registry

        responses = {}
        current_query = query
        timeout = self._get_agent_timeout()

        for agent_name in agents:
            try:
                agent = agent_registry.get_agent(agent_name, self.deps)
                # Execute with timeout protection
                response = await asyncio.wait_for(agent.process(current_query, context or {}), timeout=timeout)
                responses[agent_name] = response

                # For sequential execution, next agent can see previous results
                if len(responses) > 1:
                    current_query = f"{query}\n\nPrevious analysis: {response.content}"

            except asyncio.TimeoutError:
                log.error(f"Agent {agent_name} timed out after {timeout}s")
                responses[agent_name] = _create_error_response(
                    agent_name,
                    f"Agent {agent_name} timed out after {timeout} seconds",
                    is_timeout=True,
                )
            except (ValueError, ConnectionError, TimeoutError) as e:
                log.error(f"Error executing agent {agent_name}: {e}")
                responses[agent_name] = _create_error_response(agent_name, f"Agent {agent_name} encountered an error")

        return responses

    async def _execute_parallel(
        self, agents: list[str], query: str, context: Optional[dict[str, Any]] = None
    ) -> dict[str, AgentResponse]:
        """Execute agents in parallel with timeout protection."""
        from galaxy.agents import agent_registry

        timeout = self._get_agent_timeout()

        async def call_agent(agent_name: str):
            try:
                agent = agent_registry.get_agent(agent_name, self.deps)
                # Execute with timeout protection
                response = await asyncio.wait_for(agent.process(query, context or {}), timeout=timeout)
                return agent_name, response
            except asyncio.TimeoutError:
                log.error(f"Agent {agent_name} timed out after {timeout}s")
                return agent_name, _create_error_response(
                    agent_name,
                    f"Agent {agent_name} timed out after {timeout} seconds",
                    is_timeout=True,
                )
            except (ValueError, ConnectionError, TimeoutError) as e:
                log.error(f"Error executing agent {agent_name}: {e}")
                return agent_name, _create_error_response(agent_name, f"Agent {agent_name} encountered an error")

        # Run all agents in parallel
        tasks = [call_agent(agent_name) for agent_name in agents]
        results = await asyncio.gather(*tasks)

        return dict(results)

    def _combine_responses(self, responses: dict[str, AgentResponse], reasoning: str) -> str:
        """Combine multiple agent responses into a single coherent response."""
        if not responses:
            return "No agent responses received."

        if len(responses) == 1:
            return list(responses.values())[0].content

        # Build combined response
        sections = [f"## Multi-Agent Analysis\n{reasoning}\n"]

        for agent_name, response in responses.items():
            agent_title = agent_name.replace("_", " ").title()
            sections.append(f"### {agent_title}")
            sections.append(response.content)
            sections.append("")  # blank line

        return "\n".join(sections)

    def _get_simple_system_prompt(self) -> str:
        """Simple system prompt for models without structured output."""
        return """
        You coordinate multiple Galaxy agents. Determine which agents to call and in what order.

        Available agents: error_analysis, custom_tool

        Respond in this format:
        AGENTS: [agent1, agent2]
        SEQUENTIAL: true/false
        REASONING: explanation

        Example:
        AGENTS: [error_analysis, custom_tool]
        SEQUENTIAL: true
        REASONING: Analyze error first, then suggest creating a tool
        """
