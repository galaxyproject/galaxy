import logging

from fastapi import Body

from galaxy.managers.context import ProvidesUserContext
from galaxy.webapps.galaxy.services.tool_request_form import (
    ToolRequestFormData,
    ToolRequestFormService,
)
from . import (
    depends,
    DependsOnTrans,
    Router,
)

log = logging.getLogger(__name__)

router = Router(tags=["tool request form"])


@router.cbv
class ToolRequestFormAPI:
    service: ToolRequestFormService = depends(ToolRequestFormService)

    @router.post(
        "/api/tool_request_form",
        summary="Submit a tool installation request to the instance admins.",
        status_code=204,
    )
    def submit_tool_request(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        payload: ToolRequestFormData = Body(),
    ) -> None:
        """Submit a request for a new tool to be installed on this Galaxy instance.

        Sends a notification to all admin users with the submitted request details.
        Requires the notification system and tool request form to be enabled in the configuration.
        """
        self.service.submit_tool_request(trans, payload)
