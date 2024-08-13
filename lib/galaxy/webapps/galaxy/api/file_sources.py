import logging
from typing import List

from fastapi import (
    Body,
    Path,
    Response,
    status,
)
from pydantic import UUID4

from galaxy.files.templates import FileSourceTemplateSummaries
from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.file_source_instances import (
    CreateInstancePayload,
    FileSourceInstancesManager,
    ModifyInstancePayload,
    UserFileSourceModel,
)
from galaxy.model import User
from galaxy.util.config_templates import PluginStatus
from . import (
    depends,
    DependsOnTrans,
    DependsOnUser,
    Router,
)

log = logging.getLogger(__name__)

router = Router(tags=["file_sources"])


UserFileSourceIdPathParam: UUID4 = Path(
    ..., title="User File Source UUID", description="The UUID index for a persisted UserFileSourceStore object."
)


@router.cbv
class FastAPIFileSources:
    file_source_instances_manager: FileSourceInstancesManager = depends(FileSourceInstancesManager)
    user: User = DependsOnUser

    @router.get(
        "/api/file_source_templates",
        summary="Get a list of file source templates available to build user defined file sources from",
        response_description="A list of the configured file source templates.",
        operation_id="file_sources__templates_index",
    )
    def index_templates(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> FileSourceTemplateSummaries:
        return self.file_source_instances_manager.summaries

    @router.post(
        "/api/file_source_instances",
        summary="Create a user-bound file source.",
        operation_id="file_sources__create_instance",
    )
    def create(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        payload: CreateInstancePayload = Body(...),
    ) -> UserFileSourceModel:
        return self.file_source_instances_manager.create_instance(trans, payload)

    @router.post(
        "/api/file_source_instances/test",
        summary="Test payload for creating user-bound file source.",
        operation_id="file_sources__test_new_instance_configuration",
    )
    def test_instance_configuration(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        payload: CreateInstancePayload = Body(...),
    ) -> PluginStatus:
        return self.file_source_instances_manager.plugin_status(trans, payload)

    @router.get(
        "/api/file_source_instances",
        summary="Get a list of persisted file source instances defined by the requesting user.",
        operation_id="file_sources__instances_index",
    )
    def instance_index(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> List[UserFileSourceModel]:
        return self.file_source_instances_manager.index(trans)

    @router.get(
        "/api/file_source_instances/{user_file_source_id}",
        summary="Get a persisted user file source instance.",
        operation_id="file_sources__instances_get",
    )
    def instances_show(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        user_file_source_id: UUID4 = UserFileSourceIdPathParam,
    ) -> UserFileSourceModel:
        return self.file_source_instances_manager.show(trans, user_file_source_id)

    @router.put(
        "/api/file_source_instances/{user_file_source_id}",
        summary="Update or upgrade user file source instance.",
        operation_id="file_sources__instances_update",
    )
    def update_instance(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        user_file_source_id: UUID4 = UserFileSourceIdPathParam,
        payload: ModifyInstancePayload = Body(...),
    ) -> UserFileSourceModel:
        return self.file_source_instances_manager.modify_instance(trans, user_file_source_id, payload)

    @router.delete(
        "/api/file_source_instances/{user_file_source_id}",
        summary="Purge user file source instance.",
        operation_id="file_sources__instances_purge",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def purge_instance(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        user_file_source_id: UUID4 = UserFileSourceIdPathParam,
    ):
        self.file_source_instances_manager.purge_instance(trans, user_file_source_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
