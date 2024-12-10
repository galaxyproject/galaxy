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
    TestModifyInstancePayload,
    UserFileSourceModel,
)
from galaxy.model import User
from galaxy.util.config_templates import (
    OAuth2Info,
    PluginStatus,
)
from galaxy.work.context import SessionRequestContext
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

TemplateIdPathParam: str = Path(
    ..., title="Template ID", description="The template ID of the target file source template."
)

TemplateVersionPathParam = Path(
    ..., title="Template Version", description="The template version of the target file source template."
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

    @router.get(
        "/api/file_source_templates/{template_id}/{template_version}/oauth2",
        response_description="OAuth2 authorization url to redirect user to prior to creation.",
        operation_id="file_sources__template_oauth2",
    )
    def template_oauth2(
        self,
        trans: SessionRequestContext = DependsOnTrans,
        template_id: str = TemplateIdPathParam,
        template_version: int = TemplateVersionPathParam,
    ) -> OAuth2Info:
        return self.file_source_instances_manager.template_oauth2(trans, template_id, template_version)

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
    async def test_instance_configuration(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        payload: CreateInstancePayload = Body(...),
    ) -> PluginStatus:
        return await self.file_source_instances_manager.plugin_status(trans, payload)

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
        "/api/file_source_instances/{uuid}",
        summary="Get a persisted user file source instance.",
        operation_id="file_sources__instances_get",
    )
    def instances_show(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        uuid: UUID4 = UserFileSourceIdPathParam,
    ) -> UserFileSourceModel:
        return self.file_source_instances_manager.show(trans, uuid)

    @router.get(
        "/api/file_source_instances/{uuid}/test",
        summary="Test a file source instance and return status.",
        operation_id="file_sources__instances_test_instance",
    )
    async def instance_test(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        uuid: UUID4 = UserFileSourceIdPathParam,
    ) -> PluginStatus:
        return await self.file_source_instances_manager.plugin_status_for_instance(trans, uuid)

    @router.put(
        "/api/file_source_instances/{uuid}",
        summary="Update or upgrade user file source instance.",
        operation_id="file_sources__instances_update",
    )
    def update_instance(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        uuid: UUID4 = UserFileSourceIdPathParam,
        payload: ModifyInstancePayload = Body(...),
    ) -> UserFileSourceModel:
        return self.file_source_instances_manager.modify_instance(trans, uuid, payload)

    @router.post(
        "/api/file_source_instances/{uuid}/test",
        summary="Test updating or upgrading user file source instance.",
        operation_id="file_sources__test_instances_update",
    )
    async def test_update_instance(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        uuid: UUID4 = UserFileSourceIdPathParam,
        payload: TestModifyInstancePayload = Body(...),
    ) -> PluginStatus:
        return await self.file_source_instances_manager.test_modify_instance(trans, uuid, payload)

    @router.delete(
        "/api/file_source_instances/{uuid}",
        summary="Purge user file source instance.",
        operation_id="file_sources__instances_purge",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def purge_instance(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        uuid: UUID4 = UserFileSourceIdPathParam,
    ):
        self.file_source_instances_manager.purge_instance(trans, uuid)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
