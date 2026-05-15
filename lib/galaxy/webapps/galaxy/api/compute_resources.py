"""HTTP API for user-self-registered compute resources.

Three flows live here:

1. ``POST /api/compute_resources/registrations`` — logged-in user asks Galaxy
   for a one-shot registration token. Returns a copy-pasteable command the user
   runs on the Pulsar host.
2. ``POST /api/compute_resources/registrations/complete`` — host-side callback.
   The bootstrap_token authenticates the call; the body carries the relay
   refresh token + manager_name (= relay user ``sub``) from the device-flow
   login. We round-trip the refresh token against the relay to validate it
   and pull the rotated value into the vault.
3. ``GET/DELETE /api/compute_resources[/{id}]`` — list/inspect/disable the
   resources owned by the requesting user.

Controller stays thin: request parsing, response shaping, dependency
injection of :class:`ComputeResourceService`. Business logic + exception
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
from galaxy.schema.compute_resources import (
    ComputeResourceSummary,
    RegistrationCompletionPayload,
    RegistrationTicket,
)
from galaxy.webapps.galaxy.api import (
    depends,
    DependsOnTrans,
    Router,
)
from galaxy.webapps.galaxy.services.compute_resources import ComputeResourceService

log = logging.getLogger(__name__)

router = Router(tags=["compute_resources"])

ResourceIdPathParam: int = Path(..., title="Resource ID", description="Numeric ID of a compute resource.")


def _require_enabled(trans: ProvidesUserContext = DependsOnTrans) -> None:
    """FastAPI dependency that 404s every compute-resource route when the
    feature flag is off. Use via ``Depends(_require_enabled)`` in the route
    decorator's ``dependencies`` list — keeps individual handlers free of
    the gate."""
    if not trans.app.config.enable_compute_resources:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Compute resources are disabled on this Galaxy instance.",
        )


# Class-level dependency applied via route decorators below; consolidated
# here so the six route declarations stay grep-able.
_GATE = [Depends(_require_enabled)]


@router.cbv
class FastAPIComputeResources:
    service: ComputeResourceService = depends(ComputeResourceService)

    @router.post(
        "/api/compute_resources/registrations",
        summary="Start a compute-resource registration",
        response_model=RegistrationTicket,
        dependencies=_GATE,
    )
    def start_registration(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> RegistrationTicket:
        return self.service.start_registration(trans)

    @router.post(
        "/api/compute_resources/registrations/complete",
        summary="Complete a compute-resource registration (host-side callback)",
        response_model=ComputeResourceSummary,
        dependencies=_GATE,
    )
    def complete_registration(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        payload: RegistrationCompletionPayload = Body(...),
    ) -> ComputeResourceSummary:
        # The bootstrap_token in ``payload`` is the auth here — this endpoint
        # must work even when Galaxy is called from a host the user is not
        # browser-authenticated against.
        return self.service.complete_registration(trans, payload)

    @router.get(
        "/api/compute_resources",
        summary="List the requesting user's compute resources",
        response_model=list[ComputeResourceSummary],
        dependencies=_GATE,
    )
    def index(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> list[ComputeResourceSummary]:
        return self.service.list_for(trans)

    @router.get(
        "/api/compute_resources/{resource_id}",
        summary="Get one of the requesting user's compute resources",
        response_model=ComputeResourceSummary,
        dependencies=_GATE,
    )
    def show(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        resource_id: int = ResourceIdPathParam,
    ) -> ComputeResourceSummary:
        return self.service.show(trans, resource_id)

    @router.delete(
        "/api/compute_resources/{resource_id}",
        summary="Disable one of the requesting user's compute resources",
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
        "/api/compute_resources/{resource_id}/purge",
        summary="Fully delete a disabled compute resource (vault secret + DB row)",
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
