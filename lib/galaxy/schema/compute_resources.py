"""Pydantic models for the /api/compute_resources endpoints."""

from datetime import datetime
from typing import (
    Annotated,
    Optional,
)

from pydantic import Field

from galaxy.schema.fields import EncodedDatabaseIdField
from galaxy.schema.schema import Model


class ComputeResourceSummary(Model):
    """User-visible view of a registered compute resource.

    The relay refresh token is intentionally absent — it lives in the
    Galaxy vault and is never exposed through the API.
    """

    id: Annotated[
        EncodedDatabaseIdField,
        Field(description="Encoded ID of the compute resource."),
    ]
    manager_name: Annotated[
        str,
        Field(
            description=(
                "Globally unique relay user identifier; equals the JWT ``sub`` "
                "claim from the device-flow login and is used as the Pulsar "
                "manager name (relay topics are ``job_setup_<manager_name>`` etc.)."
            ),
        ),
    ]
    relay_url: Annotated[
        str,
        Field(description="Base URL of the pulsar-relay this resource is wired to."),
    ]
    relay_topic_prefix: Annotated[
        Optional[str],
        Field(
            None,
            description="Optional relay topic prefix, when the operator namespaces topics.",
        ),
    ]
    status: Annotated[
        str,
        Field(description="Lifecycle state: pending|active|disabled|deleted."),
    ]
    create_time: datetime
    update_time: datetime
    last_seen_time: Annotated[
        Optional[datetime],
        Field(None, description="Last time the relay observed this resource."),
    ]


class RegistrationTicket(Model):
    """Returned by ``POST /api/compute_resources/registrations``.

    Carries the one-shot bootstrap token the user passes to
    ``pulsar-config register-with-galaxy`` so the host-side flow can call
    back into Galaxy with the freshly-minted secondary refresh token.
    """

    bootstrap_token: Annotated[
        str,
        Field(
            description=(
                "Single-use, short-TTL opaque token. Authenticates the "
                "subsequent ``POST /api/compute_resources/registrations/complete`` callback."
            ),
        ),
    ]
    expires_at: datetime
    relay_url: Annotated[
        str,
        Field(description="Operator-configured relay URL the user's Pulsar should bind to."),
    ]
    one_liner: Annotated[
        str,
        Field(
            description=("Convenience command — the user pastes this onto their Pulsar host to complete bootstrap."),
        ),
    ]


class RegistrationCompletionPayload(Model):
    """Body of ``POST /api/compute_resources/registrations/complete``, sent by
    the user's host after the device-flow login. Authenticates via the
    bootstrap_token.
    """

    bootstrap_token: Annotated[str, Field(description="The token from RegistrationTicket.")]
    refresh_token: Annotated[
        str,
        Field(
            description=(
                "Relay refresh token earmarked for Galaxy (the secondary "
                "token from the device-flow pair). Stored in the user's "
                "vault and rotated by the compute-resource runner."
            ),
        ),
    ]
    relay_url: Annotated[str, Field(description="Relay URL the user's Pulsar bound to.")]
    manager_name: Annotated[
        str,
        Field(
            description=(
                "Relay user identifier (``sub`` claim); becomes the compute "
                "resource's manager name. Validated against the access token decoded "
                "from a refresh of ``refresh_token``."
            ),
        ),
    ]
    relay_topic_prefix: Annotated[
        Optional[str],
        Field(None, description="Optional relay topic prefix."),
    ]
