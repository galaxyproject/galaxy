"""Factory for building the appropriate AgentRegistry from config."""

import logging
from typing import TYPE_CHECKING

from .registry import (
    AgentRegistry,
    build_default_registry,
)
from .static_backend import StaticAgentRegistry

if TYPE_CHECKING:
    from galaxy.config import GalaxyAppConfiguration

log = logging.getLogger(__name__)


def build_registry(config: "GalaxyAppConfiguration") -> AgentRegistry:
    """Build an AgentRegistry based on config.

    Uses StaticAgentRegistry when inference_services.static_responses is set,
    otherwise builds the default registry with real agents.
    """
    inference_config = getattr(config, "inference_services", None) or {}
    static_responses = inference_config.get("static_responses") if isinstance(inference_config, dict) else None
    if static_responses:
        log.info(f"Static agent backend loaded: {static_responses}")
        return StaticAgentRegistry(static_responses)
    return build_default_registry(config)
