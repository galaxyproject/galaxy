"""Agent service layer for AI agent management."""

import logging
import mimetypes
import uuid
from typing import (
    Any,
    Dict,
    List,
    Optional,
    TYPE_CHECKING,
)
from urllib.parse import urlencode

try:
    from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

    HAS_ITSDANGEROUS = True
except ImportError:  # pragma: no cover - optional dependency guard
    HAS_ITSDANGEROUS = False
    URLSafeTimedSerializer = None  # type: ignore[assignment]

from galaxy.config import GalaxyAppConfiguration
from galaxy.exceptions import ConfigurationError
from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.jobs import JobManager
from galaxy.model import User
from galaxy.schema.agents import AgentResponse

# Import agent system (agents are optional; optional dependencies must not break import)
try:
    # Note: DSPy data analysis agent temporarily disabled; keep import commented.
    from galaxy.agents import (
        agent_registry,
        GalaxyAgentDependencies,
        # DataAnalysisDSPyAgent,
    )
    # from galaxy.agents.dspy_adapter import DSPyPlanResult
    from galaxy.agents.error_analysis import ErrorAnalysisAgent
    from galaxy.agents.router import QueryRouterAgent

    HAS_AGENTS = True
except ImportError:
    HAS_AGENTS = False
    agent_registry = None  # type: ignore[assignment,misc,unused-ignore]
    GalaxyAgentDependencies = None  # type: ignore[assignment,misc,unused-ignore]
    # DataAnalysisDSPyAgent = None  # type: ignore[assignment,misc,unused-ignore]
    # DSPyPlanResult = None  # type: ignore[assignment,misc,unused-ignore]
    QueryRouterAgent = None  # type: ignore[assignment,misc,unused-ignore]
    ErrorAnalysisAgent = None  # type: ignore[assignment,misc,unused-ignore]

if TYPE_CHECKING:
    from galaxy.agents.dspy_adapter import DSPyPlanResult  # pragma: no cover
    from galaxy.agents.data_analysis import DataAnalysisAgent  # pragma: no cover
else:  # pragma: no cover - provide dummies when DSPy agent disabled
    DataAnalysisDSPyAgent = Any  # type: ignore[assignment]
    DSPyPlanResult = Any  # type: ignore[assignment]

log = logging.getLogger(__name__)


class AgentService:
    """Service layer for AI agent execution and routing."""

    def __init__(
        self,
        config: GalaxyAppConfiguration,
        job_manager: JobManager,
    ):
        if not HAS_AGENTS:
            raise ConfigurationError("Agent system is not available")

        self.config = config
        self.job_manager = job_manager

        token_salt = "galaxy.agents.pyodide.dataset"
        self._dataset_token_signer = None
        if HAS_ITSDANGEROUS and URLSafeTimedSerializer is not None and getattr(self.config, "id_secret", None):
            # Used for signed dataset download tokens for browser-side execution.
            self._dataset_token_signer = URLSafeTimedSerializer(self.config.id_secret, salt=token_salt)
        else:
            log.warning(
                "itsdangerous is not available or id_secret is not configured; Pyodide dataset download tokens are "
                "disabled. Install via 'pip install itsdangerous' and set id_secret to enable data analysis execution "
                "with datasets."
            )
        ttl_default = getattr(self.config, "pyodide_dataset_token_ttl", 600)
        try:
            ttl_value = int(ttl_default)
        except (TypeError, ValueError):  # pragma: no cover - defensive fallback
            ttl_value = 600
        self._dataset_token_ttl = max(60, ttl_value)

    def create_dependencies(self, trans: ProvidesUserContext, user: User) -> GalaxyAgentDependencies:
        """Create agent dependencies for dependency injection."""
        toolbox = trans.app.toolbox if hasattr(trans, "app") and hasattr(trans.app, "toolbox") else None
        return GalaxyAgentDependencies(
            trans=trans,
            user=user,
            config=self.config,
            job_manager=self.job_manager,
            toolbox=toolbox,
            get_agent=agent_registry.get_agent,
        )

    async def execute_agent(
        self,
        agent_type: str,
        query: str,
        trans: ProvidesUserContext,
        user: User,
        context: Optional[dict[str, Any]] = None,
    ) -> AgentResponse:
        """Execute a specific agent and return response."""
        deps = self.create_dependencies(trans, user)

        if context is None:
            context = {}

        try:
            log.info(f"Executing {agent_type} agent for query: '{query[:100]}...'")
            agent = agent_registry.get_agent(agent_type, deps)
            # Temporarily disable DSPy agent execution path until the agent is fixed.
            # if isinstance(agent, DataAnalysisDSPyAgent):
            #     return await self._execute_data_analysis_dspy(agent, query, context or {})

            response = await agent.process(query, context)

            return AgentResponse(
                content=response.content,
                agent_type=response.agent_type,
                confidence=response.confidence,
                suggestions=response.suggestions,
                metadata=response.metadata,
                reasoning=response.reasoning,
            )
        except ValueError as e:
            log.warning(f"Unknown agent type {agent_type}, falling back to router: {e}")
            # Fallback to router for unknown agents - it handles general queries
            router = QueryRouterAgent(deps)
            response = await router.process(query, context)
            metadata = response.metadata.copy()
            metadata["fallback"] = True
            metadata["original_agent_type"] = agent_type
            return AgentResponse(
                content=response.content,
                agent_type=response.agent_type,
                confidence=response.confidence,
                suggestions=response.suggestions,
                metadata=metadata,
                reasoning=response.reasoning,
            )
        except OSError as e:
            log.error(f"Network error executing agent {agent_type}: {e}")
            raise
        except RuntimeError as e:
            log.exception(f"Runtime error executing agent {agent_type}: {e}")
            raise


    async def _execute_data_analysis_dspy(
        self,
        agent: DataAnalysisDSPyAgent,
        question: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        datasets: List[str] = context.get("dataset_ids", []) or []
        conversation_history = [dict(entry) for entry in context.get("conversation_history", [])]
        data_agent = DataAnalysisAgent(agent.deps)

        step_context = dict(context)
        step_context["conversation_history"] = conversation_history

        step_payload = agent.plan_step(question, step_context)
        plan = agent.last_plan()

        if plan is None:
            descriptors, _ = self._dataset_descriptors(data_agent, datasets)
            return self._build_dspy_response(agent, None, descriptors)

        if "final_answer" in step_payload:
            descriptors, _ = self._dataset_descriptors(data_agent, datasets)
            return self._build_dspy_response(
                agent,
                plan,
                descriptors,
                summary_override=step_payload.get("final_answer"),
            )

        action_payload = step_payload.get("action_payload") or {}
        action_name = step_payload.get("action") or action_payload.get("action")
        timeout_ms = action_payload.get("timeout_ms", DataAnalysisDSPyAgent.DEFAULT_TIMEOUT_MS)

        if plan.python_code and action_name == "ExecutePythonInBrowser":
            requested_dataset_ids = self._extract_dataset_ids(step_payload, datasets)
            descriptors, alias_index = self._dataset_descriptors(data_agent, requested_dataset_ids)
            pyodide_task = self._build_pyodide_task(agent.deps.trans, plan, descriptors, alias_index, timeout_ms)
            return self._build_dspy_response(
                agent,
                plan,
                descriptors,
                pyodide_task=pyodide_task,
            )

        descriptors, _ = self._dataset_descriptors(data_agent, datasets)
        return self._build_dspy_response(agent, plan, descriptors)

    def _build_dspy_response(
        self,
        agent: DataAnalysisDSPyAgent,
        plan: Optional[DSPyPlanResult],
        dataset_descriptors: List[Dict[str, Any]],
        *,
        summary_override: Optional[str] = None,
        pyodide_task: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        summary = (summary_override or (plan.summary if plan else "")).strip() if plan or summary_override else ""
        if not summary and plan and plan.raw_answer:
            summary = (plan.raw_answer.get("explanation") or "").strip()
        if not summary and pyodide_task:
            summary = "Generated analysis plan with executable Python."
        if not summary:
            summary = "Analysis complete."

        follow_up = plan.follow_up if plan else []
        analysis_steps: List[Dict[str, Any]] = []
        if plan and plan.analysis_steps:
            for step in plan.analysis_steps:
                analysis_steps.append(dict(step))

        if pyodide_task:
            for step in reversed(analysis_steps):
                if step.get("type") == "action":
                    step["status"] = "pending"
                    break
        else:
            for step in analysis_steps:
                if step.get("type") == "action" and "status" not in step:
                    step["status"] = "completed"

        metadata: Dict[str, Any] = {
            "planner": "dspy",
            "summary": summary,
            "analysis_steps": analysis_steps,
            "plots": plan.plots if plan else [],
            "files": plan.files if plan else [],
            "follow_up": follow_up,
            "datasets_used": dataset_descriptors,
            "dataset_ids": [descriptor.get("id") for descriptor in dataset_descriptors if descriptor.get("id")],
        }
        if plan and plan.raw_answer:
            metadata["raw_answer"] = plan.raw_answer
        if pyodide_task:
            metadata["pyodide_task"] = pyodide_task
            metadata["pyodide_status"] = "pending"
        else:
            metadata["pyodide_status"] = "completed"

        suggestions: List[Dict[str, Any]] = []
        if not pyodide_task and follow_up:
            suggestions = [
                {
                    "action_type": "refine_query",
                    "description": item,
                    "parameters": {},
                    "confidence": "medium",
                    "priority": index + 1,
                }
                for index, item in enumerate(follow_up)
            ]

        if pyodide_task:
            content = f"{summary}\n\nExecuting generated Python in the browser..." if summary else "Executing generated Python in the browser..."
            confidence = "medium"
        else:
            content = summary
            confidence = "high" if plan and plan.is_complete else "medium"

        return {
            "content": content,
            "agent_type": agent.agent_type,
            "confidence": confidence,
            "suggestions": suggestions,
            "metadata": metadata,
            "reasoning": None,
        }

    def _extract_dataset_ids(self, step_payload: Dict[str, Any], fallback_ids: List[str]) -> List[str]:
        dataset_ids: List[str] = []
        action_payload = step_payload.get("action_payload")
        if isinstance(action_payload, dict):
            for ref in action_payload.get("files") or []:
                dataset_id = ref.get("id") if isinstance(ref, dict) else ref
                if dataset_id and dataset_id not in dataset_ids:
                    dataset_ids.append(str(dataset_id))
            for ref in action_payload.get("datasets") or []:
                dataset_id = ref.get("id") if isinstance(ref, dict) else ref
                if dataset_id and dataset_id not in dataset_ids:
                    dataset_ids.append(str(dataset_id))
        for ref in step_payload.get("datasets") or []:
            dataset_id = ref.get("id") if isinstance(ref, dict) else ref
            if dataset_id and dataset_id not in dataset_ids:
                dataset_ids.append(str(dataset_id))
        if not dataset_ids:
            dataset_ids = list(dict.fromkeys(str(item) for item in fallback_ids))
        return dataset_ids

    def _dataset_descriptors(
        self,
        data_agent: "DataAnalysisAgent",
        dataset_ids: List[str],
    ) -> tuple[List[Dict[str, Any]], Dict[str, str]]:
        if not dataset_ids:
            return [], {}
        try:
            _, metadata = data_agent._prepare_dataset_aliases(dataset_ids)
        except Exception as exc:  # pragma: no cover - defensive fallback
            log.debug("Failed to prepare dataset aliases: %s", exc)
            metadata = []
        descriptors: List[Dict[str, Any]] = []
        alias_index: Dict[str, str] = {}
        for entry in metadata:
            dataset_id = entry.get("id")
            aliases = entry.get("aliases") or []
            info = {
                "id": dataset_id,
                "name": entry.get("name"),
                "size": entry.get("size"),
                "aliases": aliases,
            }
            descriptors.append(info)
            for alias in aliases:
                if dataset_id is not None:
                    alias_index.setdefault(alias, dataset_id)
            if dataset_id is not None:
                alias_index.setdefault(dataset_id, dataset_id)
        if not descriptors:
            for dataset_id in dataset_ids:
                dataset_id = str(dataset_id)
                descriptors.append(
                    {
                        "id": dataset_id,
                        "name": dataset_id,
                        "size": None,
                        "aliases": [dataset_id],
                    }
                )
                alias_index.setdefault(dataset_id, dataset_id)
        return descriptors, alias_index

    def _build_pyodide_task(
        self,
        trans: ProvidesUserContext,
        plan: DSPyPlanResult,
        dataset_descriptors: List[Dict[str, Any]],
        alias_index: Dict[str, str],
        timeout_ms: int,
    ) -> Dict[str, Any]:
        code = (plan.python_code or "").strip()
        packages = sorted({pkg for pkg in (plan.requirements or []) if pkg})
        files = []
        for descriptor in dataset_descriptors:
            dataset_id = descriptor.get("id")
            if not dataset_id:
                continue
            files.append(
                {
                    "id": dataset_id,
                    "name": descriptor.get("name") or dataset_id,
                    "size": descriptor.get("size"),
                    "aliases": descriptor.get("aliases") or [],
                    "url": self._dataset_download_url(trans, dataset_id),
                    "mime_type": self._guess_mime_type(descriptor.get("name")),
                }
            )
        config: Dict[str, Any] = {}
        index_url = getattr(self.config, "pyodide_index_url", None)
        if index_url:
            config["index_url"] = index_url
        task: Dict[str, Any] = {
            "task_id": str(uuid.uuid4()),
            "action": "ExecutePythonInBrowser",
            "code": code,
            "packages": packages,
            "files": files,
            "timeout_ms": timeout_ms or DataAnalysisDSPyAgent.DEFAULT_TIMEOUT_MS,
            "alias_map": alias_index,
        }
        if config:
            task["config"] = config
        return task

    def _dataset_download_url(self, trans: ProvidesUserContext, dataset_id: str) -> str:
        token = self._sign_dataset_download_token(trans, dataset_id)
        path = f"/api/chat/datasets/{dataset_id}/download"
        base_url = path
        url_builder = getattr(trans, "url_builder", None)
        if callable(url_builder):  # pragma: no branch - lightweight guard
            try:
                base_url = url_builder(path, qualified=True)
            except Exception:  # pragma: no cover - defensive
                base_url = path
        separator = "&" if "?" in base_url else "?"
        return f"{base_url}{separator}{urlencode({'token': token})}"

    def _sign_dataset_download_token(self, trans: ProvidesUserContext, dataset_id: str) -> str:
        if self._dataset_token_signer is None:
            raise ConfigurationError(
                "Pyodide dataset download tokens are not configured. Install 'itsdangerous' and configure id_secret."
            )
        session = getattr(trans, "galaxy_session", None)
        session_id = getattr(session, "id", None)
        encoded_user_id = None
        if trans.user:
            try:
                encoded_user_id = trans.security.encode_id(trans.user.id)
            except Exception:  # pragma: no cover - defensive guard
                encoded_user_id = None
        payload = {
            "dataset_id": dataset_id,
            "user_id": encoded_user_id,
            "session_id": session_id,
        }
        return self._dataset_token_signer.dumps(payload)

    def verify_dataset_download_token(
        self,
        trans: ProvidesUserContext,
        dataset_id: str,
        token: str,
    ) -> Dict[str, Any]:
        if self._dataset_token_signer is None:
            raise ConfigurationError(
                "Pyodide dataset download tokens are not configured. Install 'itsdangerous' and configure id_secret."
            )
        try:
            payload = self._dataset_token_signer.loads(token, max_age=self._dataset_token_ttl)
        except SignatureExpired as exc:  # pragma: no cover - time-based expiry
            raise ValueError("Dataset download token expired") from exc
        except BadSignature as exc:
            raise ValueError("Invalid dataset download token") from exc

        if payload.get("dataset_id") != dataset_id:
            raise ValueError("Token does not match requested dataset")

        expected_user = payload.get("user_id")
        actual_user = None
        if trans.user:
            try:
                actual_user = trans.security.encode_id(trans.user.id)
            except Exception:  # pragma: no cover - defensive guard
                actual_user = None

        if expected_user and expected_user != actual_user:
            raise ValueError("Token is not valid for the current user")

        expected_session = payload.get("session_id")
        session = getattr(trans, "galaxy_session", None)
        actual_session = getattr(session, "id", None)
        if expected_session and actual_session is not None and expected_session != actual_session:
            raise ValueError("Token is not valid for this session")

        return payload

    def _guess_mime_type(self, name: Optional[str]) -> str:
        if not name:
            return "application/octet-stream"
        mime, _ = mimetypes.guess_type(name)
        return mime or "application/octet-stream"

    async def route_and_execute(
        self,
        query: str,
        trans: ProvidesUserContext,
        user: User,
        context: Optional[dict[str, Any]] = None,
        agent_type: str = "auto",
    ) -> AgentResponse:
        """
        Execute query with automatic routing or specific agent.

        When agent_type is 'auto', the router agent handles the query directly,
        either answering it or using output functions to hand off to specialists.
        """
        if agent_type == "auto":
            # Router handles everything via output functions:
            # - Answers general questions directly
            # - Hands off to error_analysis for debugging
            # - Hands off to custom_tool for tool creation
            log.info(f"Processing query via router: '{query[:100]}...'")
            return await self.execute_agent("router", query, trans, user, context)
        else:
            # Explicit agent request - execute directly
            log.info(f"User explicitly requested agent: {agent_type}")
            return await self.execute_agent(agent_type, query, trans, user, context)
