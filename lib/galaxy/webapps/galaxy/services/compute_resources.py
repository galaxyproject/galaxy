"""Thin service layer between Galaxy's compute-resource API controller and the manager.

Owns the API-shaped glue:

* Model -> Pydantic-schema mapping (``_to_summary``).
* Domain-exception → ``HTTPException`` translation, so the controller stays
  free of try/except chains and the manager stays free of FastAPI types.

Registration-command artefacts (relay URL, one-liner) are composed by the
manager — this service just maps the manager's result onto the response
schema.

Matches the pattern used by ``galaxy.webapps.galaxy.services.credentials``
and other recently-introduced services.
"""

from __future__ import annotations

from fastapi import (
    HTTPException,
    status,
)

from galaxy import exceptions
from galaxy.managers.compute_resources import (
    ComputeResourceError,
    ComputeResourceManager,
    RegistrationRateLimited,
    RegistrationTokenExpired,
    RegistrationTokenInvalid,
    RelayVerificationFailed,
    ResourceHasRunningJobs,
)
from galaxy.managers.context import ProvidesUserContext
from galaxy.model import (
    ComputeResource,
    User,
)
from galaxy.schema.compute_resources import (
    ComputeResourceSummary,
    RegistrationCompletionPayload,
    RegistrationTicket,
)


def _to_summary(resource: ComputeResource) -> ComputeResourceSummary:
    return ComputeResourceSummary(
        id=resource.id,
        manager_name=resource.manager_name,
        relay_url=resource.relay_url,
        relay_topic_prefix=resource.relay_topic_prefix,
        status=resource.status,
        create_time=resource.create_time,
        update_time=resource.update_time,
        last_seen_time=resource.last_seen_time,
    )


def _require_authenticated(trans: ProvidesUserContext) -> User:
    if trans.user is None:
        raise exceptions.AuthenticationRequired("Compute resources API requires an authenticated user.")
    return trans.user


class ComputeResourceService:
    """Bridges :class:`ComputeResourceManager` to the FastAPI controller."""

    compute_resource_manager: ComputeResourceManager

    def __init__(self, compute_resource_manager: ComputeResourceManager) -> None:
        self.compute_resource_manager = compute_resource_manager

    # ---- registration ----------------------------------------------------

    def start_registration(self, trans: ProvidesUserContext) -> RegistrationTicket:
        user = _require_authenticated(trans)
        try:
            ticket = self.compute_resource_manager.start_registration(user)
        except RegistrationRateLimited as exc:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc

        return RegistrationTicket(
            bootstrap_token=ticket.bootstrap_token,
            expires_at=ticket.expires_at,
            relay_url=ticket.relay_url,
            one_liner=ticket.one_liner,
        )

    def complete_registration(
        self, trans: ProvidesUserContext, payload: RegistrationCompletionPayload
    ) -> ComputeResourceSummary:
        try:
            resource = self.compute_resource_manager.complete_registration(
                bootstrap_token=payload.bootstrap_token,
                refresh_token=payload.refresh_token,
                relay_url=payload.relay_url,
                manager_name=payload.manager_name,
                relay_topic_prefix=payload.relay_topic_prefix,
            )
        except RegistrationTokenInvalid as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
        except RegistrationTokenExpired as exc:
            raise HTTPException(status_code=status.HTTP_410_GONE, detail=str(exc)) from exc
        except RelayVerificationFailed as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except ComputeResourceError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        return _to_summary(resource)

    # ---- queries ---------------------------------------------------------

    def list_for(self, trans: ProvidesUserContext) -> list[ComputeResourceSummary]:
        user = _require_authenticated(trans)
        return [_to_summary(r) for r in self.compute_resource_manager.list_for(user)]

    def show(self, trans: ProvidesUserContext, resource_id: int) -> ComputeResourceSummary:
        user = _require_authenticated(trans)
        resource = self.compute_resource_manager.get_for_user(user, resource_id)
        if resource is None:
            # Don't leak existence to a cross-user probe.
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        return _to_summary(resource)

    # ---- lifecycle -------------------------------------------------------

    def delete(self, trans: ProvidesUserContext, resource_id: int) -> None:
        user = _require_authenticated(trans)
        resource = self.compute_resource_manager.delete(user, resource_id)
        if resource is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    def purge(self, trans: ProvidesUserContext, resource_id: int) -> None:
        user = _require_authenticated(trans)
        try:
            resource = self.compute_resource_manager.purge(user, resource_id)
        except ResourceHasRunningJobs as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        if resource is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
