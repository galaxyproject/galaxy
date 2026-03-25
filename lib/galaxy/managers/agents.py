"""Agent service layer for AI agent management."""

import logging
import mimetypes
from typing import (
    Any,
    Optional,
)
from urllib.parse import urlencode

try:
    from itsdangerous import (
        BadSignature,
        SignatureExpired,
        URLSafeTimedSerializer,
    )

    HAS_ITSDANGEROUS = True
except ImportError:  # pragma: no cover - optional dependency guard
    HAS_ITSDANGEROUS = False
    URLSafeTimedSerializer = None

from galaxy.agents import GalaxyAgentDependencies
from galaxy.agents.registry import AgentRegistry
from galaxy.agents.router import QueryRouterAgent
from galaxy.config import GalaxyAppConfiguration
from galaxy.exceptions import ConfigurationError
from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.jobs import JobManager
from galaxy.model import User
from galaxy.schema.agents import AgentResponse

log = logging.getLogger(__name__)


class AgentService:
    """Service layer for AI agent execution and routing."""

    def __init__(
        self,
        config: GalaxyAppConfiguration,
        job_manager: JobManager,
        registry: AgentRegistry,
    ):
        self.config = config
        self.job_manager = job_manager
        self.registry = registry

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
            get_agent=self.registry.get_agent,
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
            agent = self.registry.get_agent(agent_type, deps)
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
            return AgentResponse(
                content=response.content,
                agent_type=response.agent_type,
                confidence=response.confidence,
                suggestions=response.suggestions,
                metadata=response.metadata.model_copy(update={"fallback": True}),
                reasoning=response.reasoning,
            )
        except OSError as e:
            log.error(f"Network error executing agent {agent_type}: {e}")
            raise
        except RuntimeError as e:
            log.exception(f"Runtime error executing agent {agent_type}: {e}")
            raise

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
    ) -> dict[str, Any]:
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

    def list_agents(self) -> list[str]:
        return self.registry.list_agents()

    def get_agent_info(self, agent_type: str) -> dict:
        return self.registry.get_agent_info(agent_type)
