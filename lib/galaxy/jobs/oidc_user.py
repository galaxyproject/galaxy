"""Resolve a container username from a user's stored OIDC token claims.

Destination configuration is parsed and validated up front - when Galaxy loads its job
configuration for statically defined destinations, and when a job is dispatched for
destinations produced by dynamic rules - so that administrator mistakes surface as
configuration errors rather than as failed user jobs.
"""

import logging
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import (
    Any,
    Protocol,
    TYPE_CHECKING,
)

import jwt

from galaxy.authnz.util import provider_name_to_backend
from galaxy.exceptions import ConfigurationError
from galaxy.jobs.job_destination import JobDestination
from galaxy.tool_util.deps import docker_util
from galaxy.util import (
    asbool,
    unicodify,
)

if TYPE_CHECKING:
    from galaxy.model import (
        Job,
        User,
    )

log = logging.getLogger(__name__)

PARAM = docker_util.USERNAME_FROM_OIDC_TOKEN_CLAIM_PARAM
RESOLVED_PARAM = f"docker_{docker_util.USERNAME_FROM_TOKEN_PROP}"
DEFAULT_TEMPLATE = ".*"
# Order matters - a provider's access token is preferred, but its ID token is tried when the
# access token is opaque or carries no usable claim.
TOKEN_KINDS = ("access", "id")


class OidcUsernameError(Exception):
    """No configured provider could supply a container username for this user."""


@dataclass(frozen=True)
class OidcUsernameProvider:
    name: str
    backend: str
    claim: str
    template: "re.Pattern[str]"

    def username_from(self, tokens: Mapping[str, Any]) -> str | None:
        for token_kind in TOKEN_KINDS:
            token = tokens.get(token_kind)
            if not token:
                continue
            try:
                claimed = jwt.decode(token, options={"verify_signature": False})[self.claim]
                match = self.template.match(claimed) if isinstance(claimed, str) else None
                if match:
                    # Preserve the complete matched username: capture groups can express
                    # regex structure without requesting a different account mapping.
                    username = match.group(0)
                    if username:
                        return username
            except Exception:
                log.debug(
                    "Failed to extract Docker user from OIDC provider [%s] %s token",
                    self.name,
                    token_kind,
                    exc_info=True,
                )
        return None


@dataclass(frozen=True)
class OidcUsernameConfig:
    """Validated ``docker_username_from_oidc_token_claim`` destination configuration."""

    providers: tuple[OidcUsernameProvider, ...]

    def username_for(self, user: "User") -> str:
        for provider in self.providers:
            try:
                tokens = user.get_oidc_tokens(provider.backend)
            except Exception:
                log.debug("Failed to obtain Docker user tokens from OIDC provider [%s]", provider.name, exc_info=True)
                continue
            username = provider.username_from(tokens)
            if username:
                return username
        raise OidcUsernameError("Failed to get a username for container from OIDC token, contact Galaxy admin.")


def parse_config(destination_params: Mapping[str, Any]) -> OidcUsernameConfig | None:
    """Validate the destination parameters, returning ``None`` when the feature is off.

    :raises galaxy.exceptions.ConfigurationError: if the configuration cannot be honored.
    """
    options = docker_util.parse_username_from_token_options(destination_params.get(PARAM))
    if not options.enabled:
        return None

    if options.set_user and destination_params.get("docker_set_user"):
        raise ConfigurationError(f"docker_set_user cannot be used together with {PARAM} set_user")
    if not asbool(destination_params.get("docker_enabled", False)):
        raise ConfigurationError(f"{PARAM} requires docker_enabled on the same destination")

    config = destination_params[PARAM]
    providers = config.get("providers")
    if not isinstance(providers, Mapping) or not providers:
        raise ConfigurationError(f"{PARAM} requires a non-empty providers mapping")

    parsed_providers = []
    for name, settings in providers.items():
        backend = provider_name_to_backend(name)
        if backend is None:
            raise ConfigurationError(f"Unknown OIDC provider [{name}] for Docker username")
        if not isinstance(settings, Mapping) or not isinstance(settings.get("claim"), str) or not settings["claim"]:
            raise ConfigurationError(f"OIDC provider [{name}] requires a non-empty username claim")
        try:
            template = re.compile(settings.get("template", DEFAULT_TEMPLATE))
        except (re.error, TypeError) as exc:
            raise ConfigurationError(f"Invalid Docker username template for OIDC provider [{name}]") from exc
        parsed_providers.append(
            OidcUsernameProvider(name=name, backend=backend, claim=settings["claim"], template=template)
        )

    return OidcUsernameConfig(providers=tuple(parsed_providers))


def validate_destination(destination_id: str | None, destination_params: Mapping[str, Any]) -> None:
    """Fail Galaxy startup rather than individual jobs when a destination is misconfigured."""
    try:
        parse_config(destination_params)
    except ConfigurationError as exc:
        raise ConfigurationError(f"Invalid destination [{destination_id}]: {unicodify(exc)}") from exc


class DescribesJobIdentity(Protocol):
    """The part of a job wrapper this needs, so the resolver can be exercised without one."""

    @property
    def job_destination(self) -> JobDestination: ...

    def get_job(self) -> "Job": ...


def configure_destination(job_wrapper: DescribesJobIdentity) -> None:
    """Record the identity this job's container should use on its destination parameters."""
    destination_params = job_wrapper.job_destination.params
    config = parse_config(destination_params)
    if config is None:
        return
    user = job_wrapper.get_job().user
    if user is None:
        raise OidcUsernameError("Failed to get a username for container from OIDC token, job has no user.")
    destination_params[RESOLVED_PARAM] = config.username_for(user)
