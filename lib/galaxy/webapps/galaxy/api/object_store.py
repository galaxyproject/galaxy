"""
API operations on Galaxy's object store.
"""

import logging
from typing import (
    List,
    Union,
)

from fastapi import (
    Body,
    Path,
    Query,
    Response,
    status,
)
from pydantic import UUID4

from galaxy.exceptions import (
    ObjectNotFound,
    RequestParameterInvalidException,
)
from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.object_store_instances import (
    CreateInstancePayload,
    ModifyInstancePayload,
    ObjectStoreInstancesManager,
    TestModifyInstancePayload,
    UserConcreteObjectStoreModel,
)
from galaxy.model import User
from galaxy.objectstore import (
    BaseObjectStore,
    ConcreteObjectStoreModel,
)
from galaxy.objectstore.templates import ObjectStoreTemplateSummaries
from galaxy.util.config_templates import PluginStatus
from . import (
    depends,
    DependsOnTrans,
    DependsOnUser,
    Router,
)

log = logging.getLogger(__name__)

router = Router(tags=["object_stores"])

ConcreteObjectStoreIdPathParam: str = Path(
    ..., title="Concrete Object Store ID", description="The concrete object store ID."
)

UserObjectStoreIdPathParam: UUID4 = Path(
    ...,
    title="User Object Store UUID",
    description="The UUID used to identify a persisted UserObjectStore object.",
)

SelectableQueryParam: bool = Query(
    default=False,
    title="Selectable",
    description="Restrict index query to user selectable object stores, the current implementation requires this to be true.",
)


@router.cbv
class FastAPIObjectStore:
    object_store: BaseObjectStore = depends(BaseObjectStore)
    object_store_instance_manager: ObjectStoreInstancesManager = depends(ObjectStoreInstancesManager)

    @router.get(
        "/api/object_stores",
        summary="Get a list of (currently only concrete) object stores configured with this Galaxy instance.",
        response_description="A list of the configured object stores.",
    )
    def index(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        selectable: bool = SelectableQueryParam,
    ) -> List[Union[ConcreteObjectStoreModel, UserConcreteObjectStoreModel]]:
        if not selectable:
            raise RequestParameterInvalidException(
                "The object store index query currently needs to be called with selectable=true"
            )
        selectable_ids = self.object_store.object_store_ids_allowing_selection()
        instances = [self._model_for(selectable_id) for selectable_id in selectable_ids]
        if trans.user:
            user_object_stores = trans.user.object_stores
            for user_object_store in user_object_stores:
                instances.append(self.object_store_instance_manager._to_model(trans, user_object_store))
        return instances

    @router.post(
        "/api/object_store_instances",
        summary="Create a user-bound object store.",
        operation_id="object_stores__create_instance",
    )
    def create(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        user: User = DependsOnUser,
        payload: CreateInstancePayload = Body(...),
    ) -> UserConcreteObjectStoreModel:
        return self.object_store_instance_manager.create_instance(trans, payload)

    @router.post(
        "/api/object_store_instances/test",
        summary="Test payload for creating user-bound object store.",
        operation_id="object_stores__test_new_instance_configuration",
    )
    def test_instance_configuration(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        user: User = DependsOnUser,
        payload: CreateInstancePayload = Body(...),
    ) -> PluginStatus:
        return self.object_store_instance_manager.plugin_status(trans, payload)

    @router.get(
        "/api/object_store_instances",
        summary="Get a list of persisted object store instances defined by the requesting user.",
        operation_id="object_stores__instances_index",
    )
    def instance_index(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        user: User = DependsOnUser,
    ) -> List[UserConcreteObjectStoreModel]:
        return self.object_store_instance_manager.index(trans)

    @router.get(
        "/api/object_store_instances/{uuid}",
        summary="Get a persisted user object store instance.",
        operation_id="object_stores__instances_get",
    )
    def instances_show(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        user: User = DependsOnUser,
        uuid: UUID4 = UserObjectStoreIdPathParam,
    ) -> UserConcreteObjectStoreModel:
        return self.object_store_instance_manager.show(trans, uuid)

    @router.get(
        "/api/object_store_instances/{uuid}/test",
        summary="Get a persisted user object store instance.",
        operation_id="object_stores__instances_test_instance",
    )
    def instance_test(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        uuid: UUID4 = UserObjectStoreIdPathParam,
    ) -> PluginStatus:
        return self.object_store_instance_manager.plugin_status_for_instance(trans, uuid)

    @router.get(
        "/api/object_stores/{object_store_id}",
        summary="Get information about a concrete object store configured with Galaxy.",
    )
    def show_info(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        object_store_id: str = ConcreteObjectStoreIdPathParam,
    ) -> ConcreteObjectStoreModel:
        return self._model_for(object_store_id)

    @router.put(
        "/api/object_store_instances/{uuid}",
        summary="Update or upgrade user object store instance.",
        operation_id="object_stores__instances_update",
    )
    def update_instance(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        user: User = DependsOnUser,
        uuid: UUID4 = UserObjectStoreIdPathParam,
        payload: ModifyInstancePayload = Body(...),
    ) -> UserConcreteObjectStoreModel:
        return self.object_store_instance_manager.modify_instance(trans, uuid, payload)

    @router.post(
        "/api/object_store_instances/{uuid}/test",
        summary="Test updating or upgrading user object source instance.",
        operation_id="object_stores__test_instances_update",
    )
    def test_update_instance(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        user_file_source_id: UUID4 = UserObjectStoreIdPathParam,
        payload: TestModifyInstancePayload = Body(...),
    ) -> PluginStatus:
        return self.object_store_instance_manager.test_modify_instance(trans, user_file_source_id, payload)

    @router.delete(
        "/api/object_store_instances/{uuid}",
        summary="Purge user object store instance.",
        operation_id="object_stores__instances_purge",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def purge_instance(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        user: User = DependsOnUser,
        uuid: UUID4 = UserObjectStoreIdPathParam,
    ):
        self.object_store_instance_manager.purge_instance(trans, uuid)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.get(
        "/api/object_store_templates",
        summary="Get a list of object store templates available to build user defined object stores from",
        response_description="A list of the configured object store templates.",
        operation_id="object_stores__templates_index",
    )
    def index_templates(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        user: User = DependsOnUser,
    ) -> ObjectStoreTemplateSummaries:
        return self.object_store_instance_manager.summaries

    def _model_for(self, object_store_id: str) -> ConcreteObjectStoreModel:
        concrete_object_store = self.object_store.get_concrete_store_by_object_store_id(object_store_id)
        if concrete_object_store is None:
            raise ObjectNotFound()
        return concrete_object_store.to_model(object_store_id)
