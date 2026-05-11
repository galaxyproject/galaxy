"""HTTP API for user-self-registered Pulsar compute resources (BYOC).

Three flows live here:

1. ``POST /api/pulsar_byoc/registration`` — logged-in user asks Galaxy for a
   one-shot bootstrap token. Returns a copy-pasteable command the user runs
   on the Pulsar host.
2. ``POST /api/pulsar_byoc/bootstrap`` — host-side callback. The
   bootstrap_token authenticates the call; the body carries the relay
   refresh token + manager_name (= relay user ``sub``) from the device-flow
   login. We round-trip the refresh token against the relay to validate it
   and pull the rotated value into the vault.
3. ``GET/DELETE /api/pulsar_byoc[/{id}]`` — list/inspect/disable the
   resources owned by the requesting user.

Controller stays thin: request parsing, response shaping, dependency
injection of :class:`PulsarByocService`. Business logic + exception
translation lives in the service.
"""

import logging

from fastapi import (
    Body,
    Depends,
    HTTPException,
    Path,
    Response,
    status,
)

from galaxy.managers.context import ProvidesUserContext
from galaxy.schema.pulsar_byoc import (
    BootstrapPayload,
    PulsarByocResourceSummary,
    RegistrationTicket,
)
from galaxy.webapps.galaxy.api import (
    depends,
    DependsOnTrans,
    Router,
)
from galaxy.webapps.galaxy.services.pulsar_byoc import PulsarByocService

log = logging.getLogger(__name__)

router = Router(tags=["pulsar_byoc"])

ResourceIdPathParam: int = Path(..., title="Resource ID", description="Numeric ID of a BYOC resource.")


def _require_enabled(trans: ProvidesUserContext = DependsOnTrans) -> None:
    """FastAPI dependency that 404s every BYOC route when the feature flag
    is off. Use via ``Depends(_require_enabled)`` in the route decorator's
    ``dependencies`` list — keeps individual handlers free of the gate."""
    if not trans.app.config.enable_pulsar_byoc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pulsar BYOC is disabled on this Galaxy instance.",
        )


# Class-level dependency applied via route decorators below; consolidated
# here so the six route declarations stay grep-able.
_GATE = [Depends(_require_enabled)]


@router.cbv
class FastAPIPulsarByoc:
    service: PulsarByocService = depends(PulsarByocService)

    @router.post(
        "/api/pulsar_byoc/registration",
        summary="Start a BYOC Pulsar registration",
        response_model=RegistrationTicket,
        dependencies=_GATE,
    )
    def start_registration(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> RegistrationTicket:
        return self.service.start_registration(trans)

    @router.post(
        "/api/pulsar_byoc/bootstrap",
        summary="Complete a BYOC Pulsar registration (host-side callback)",
        response_model=PulsarByocResourceSummary,
        dependencies=_GATE,
    )
    def complete_registration(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        payload: BootstrapPayload = Body(...),
    ) -> PulsarByocResourceSummary:
        # The bootstrap_token in ``payload`` is the auth here — this endpoint
        # must work even when Galaxy is called from a host the user is not
        # browser-authenticated against.
        return self.service.complete_registration(trans, payload)

    @router.get(
        "/api/pulsar_byoc",
        summary="List the requesting user's BYOC Pulsar resources",
        response_model=list[PulsarByocResourceSummary],
        dependencies=_GATE,
    )
    def index(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> list[PulsarByocResourceSummary]:
        return self.service.list_for(trans)

    @router.get(
        "/api/pulsar_byoc/{resource_id}",
        summary="Get one of the requesting user's BYOC Pulsar resources",
        response_model=PulsarByocResourceSummary,
        dependencies=_GATE,
    )
    def show(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        resource_id: int = ResourceIdPathParam,
    ) -> PulsarByocResourceSummary:
        return self.service.show(trans, resource_id)

    @router.delete(
        "/api/pulsar_byoc/{resource_id}",
        summary="Disable one of the requesting user's BYOC Pulsar resources",
        status_code=status.HTTP_204_NO_CONTENT,
        dependencies=_GATE,
    )
    def delete(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        resource_id: int = ResourceIdPathParam,
    ) -> Response:
        self.service.delete(trans, resource_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.post(
        "/api/pulsar_byoc/{resource_id}/purge",
        summary="Fully delete a disabled BYOC resource (vault secret + DB row)",
        status_code=status.HTTP_204_NO_CONTENT,
        dependencies=_GATE,
    )
    def purge(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        resource_id: int = ResourceIdPathParam,
    ) -> Response:
        self.service.purge(trans, resource_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
