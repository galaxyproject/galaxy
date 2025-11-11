import logging
from typing import Optional
from urllib.parse import unquote_plus

from pydantic import BaseModel

from galaxy.datatypes.display_applications.util import (
    decode_dataset_user,
    encode_dataset_user,
)
from galaxy.datatypes.registry import Registry
from galaxy.exceptions import MessageException
from galaxy.structured_app import StructuredApp

log = logging.getLogger(__name__)


class CreateLinkStep(BaseModel):
    name: str
    state: Optional[str] = None
    ready: Optional[bool] = False


class CreateLinkFeedback(BaseModel):
    messages: Optional[list[tuple[str, str]]] = None
    refresh: Optional[bool] = False
    resource: Optional[str] = None
    preparable_steps: Optional[list[CreateLinkStep]] = None


class CreateLinkIncoming(BaseModel):
    app_name: str
    dataset_id: str
    link_name: str
    kwd: Optional[dict[str, str]] = None


class Link(BaseModel):
    name: str


class DisplayApplication(BaseModel):
    id: str
    name: str
    version: str
    filename_: str
    links: list[Link]


class ReloadFeedback(BaseModel):
    message: str
    reloaded: list[Optional[str]]
    failed: list[Optional[str]]


class DisplayApplicationsManager:
    """Interface/service object for sharing logic between controllers."""

    def __init__(self, app: StructuredApp):
        self._app = app

    @property
    def datatypes_registry(self) -> Registry:
        return self._app.datatypes_registry

    def index(self) -> list[DisplayApplication]:
        """
        Returns the list of display applications.

        :returns:   list of available display applications
        :rtype:     list
        """
        rval = []
        for display_app in self.datatypes_registry.display_applications.values():
            rval.append(
                DisplayApplication(
                    id=display_app.id,
                    name=display_app.name,
                    version=display_app.version,
                    filename_=display_app._filename,
                    links=[Link(name=link.name) for link in display_app.links.values()],
                )
            )
        return rval

    def reload(self, ids: list[str]) -> ReloadFeedback:
        """
        Reloads the list of display applications.

        :param  ids:  list containing ids of display to be reloaded
        :type   ids:  list
        """
        self._app.queue_worker.send_control_task(
            "reload_display_application", noop_self=True, kwargs={"display_application_ids": ids}
        )
        reloaded, failed = self.datatypes_registry.reload_display_applications(ids)
        if not reloaded and failed:
            message = 'Unable to reload any of the {} requested display applications ("{}").'.format(
                len(failed),
                '", "'.join(failed),
            )
        elif failed:
            message = (
                'Reloaded {} display applications ("{}"), but failed to reload {} display applications ("{}").'.format(
                    len(reloaded), '", "'.join(reloaded), len(failed), '", "'.join(failed)
                )
            )
        elif not reloaded:
            message = "You need to request at least one display application to reload."
        else:
            message = 'Reloaded {} requested display applications ("{}").'.format(len(reloaded), '", "'.join(reloaded))
        return ReloadFeedback(message=message, reloaded=reloaded, failed=failed)

    def create_link(
        self,
        trans,
        dataset_id=None,
        user_id=None,
        app_name=None,
        link_name=None,
        **kwds,
    ) -> CreateLinkFeedback:
        """Access to external display applications"""
        if None in [app_name, link_name]:
            raise MessageException("A display application name and link name must be provided.")
        app_name = unquote_plus(app_name)
        link_name = unquote_plus(link_name)
        # Build list of parameters to pass in to display application logic (app_kwds)
        app_kwds = {}
        for name, value in dict(kwds).items():  # clone kwds because we remove stuff as we go.
            if name.startswith("app_"):
                app_kwds[name[len("app_") :]] = value
                del kwds[name]
        if kwds:
            log.debug(f"Unexpected Keywords passed to display_application: {kwds}")  # route memory?
        # decode ids
        data, user = decode_dataset_user(trans, dataset_id, user_id)
        if not data:
            raise MessageException(f"Invalid reference dataset id: {str(dataset_id)}.")
        if user is None:
            user = trans.user
        if user:
            user_roles = user.all_roles()
        else:
            user_roles = []
        # Decode application name and link name
        if self._can_access_dataset(trans, data, additional_roles=user_roles):
            messages = []
            preparable_steps = []
            refresh = False
            display_app = self.datatypes_registry.display_applications.get(app_name)
            if not display_app:
                log.debug("Unknown display application has been requested: %s", app_name)
                raise MessageException(f"The requested display application ({app_name}) is not available.")
            dataset_hash, user_hash = encode_dataset_user(trans, data, user)
            try:
                display_link = display_app.get_link(link_name, data, dataset_hash, user_hash, trans, app_kwds)
            except Exception as e:
                log.debug("Error generating display_link: %s", e)
                # User can sometimes recover from, e.g. conversion errors by fixing input metadata, so use conflict
                raise MessageException(f"Error generating display_link: {e}")
            if not display_link:
                log.debug("Unknown display link has been requested: %s", link_name)
                raise MessageException(f"Unknown display link has been requested: {link_name}")
            if data.state == data.states.ERROR:
                messages.append(
                    (
                        "This dataset is in an error state, you cannot view it at an external display application.",
                        "error",
                    )
                )
            elif data.deleted:
                messages.append(
                    ("This dataset has been deleted, you cannot view it at an external display application.", "error")
                )
            elif data.state != data.states.OK:
                messages.append(
                    (
                        "You must wait for this dataset to be created before you can view it at an external display application.",
                        "info",
                    )
                )
                refresh = True
            else:
                # We have permissions, dataset is not deleted and is in OK state, allow access
                if display_link.display_ready():
                    # redirect user to url generated by display link
                    return CreateLinkFeedback(resource=display_link.display_url())
                else:
                    refresh = True
                    messages.append(
                        (
                            "Launching this display application required additional datasets to be generated, you can view the status of these jobs below.",
                            "info",
                        )
                    )
                    if not display_link.preparing_display():
                        display_link.prepare_display()
                    preparable_steps = display_link.get_prepare_steps()
            return CreateLinkFeedback(
                messages=messages,
                refresh=refresh,
                preparable_steps=preparable_steps,
            )
        raise MessageException("You do not have permission to view this dataset at an external display application.")

    def _can_access_dataset(self, trans, dataset_association, allow_admin=True, additional_roles=None):
        roles = trans.get_current_user_roles()
        if additional_roles:
            roles = roles + additional_roles
        return (allow_admin and trans.user_is_admin) or trans.app.security_agent.can_access_dataset(
            roles, dataset_association.dataset
        )
