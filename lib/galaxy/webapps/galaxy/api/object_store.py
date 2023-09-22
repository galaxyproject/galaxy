"""
API operations on Galaxy's object store.
"""
import logging
from typing import List

from fastapi import (
    Path,
    Query,
)

from galaxy.exceptions import (
    ObjectNotFound,
    RequestParameterInvalidException,
)
from galaxy.managers.context import ProvidesUserContext
from galaxy.objectstore import (
    BaseObjectStore,
    ConcreteObjectStoreModel,
)
from . import (
    depends,
    DependsOnTrans,
    Router,
)

log = logging.getLogger(__name__)

router = Router(tags=["object sstore"])

ConcreteObjectStoreIdPathParam: str = Path(
    ..., title="Concrete Object Store ID", description="The concrete object store ID."
)

SelectableQueryParam: bool = Query(
    default=False,
    title="Selectable",
    description="Restrict index query to user selectable object stores, the current implementation requires this to be true.",
)


@router.cbv
class FastAPIObjectStore:
    object_store: BaseObjectStore = depends(BaseObjectStore)

    @router.get(
        "/api/object_stores",
        summary="Get a list of (currently only concrete) object stores configured with this Galaxy instance.",
        response_description="A list of the configured object stores.",
    )
    def index(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        selectable: bool = SelectableQueryParam,
    ) -> List[ConcreteObjectStoreModel]:
        if not selectable:
            raise RequestParameterInvalidException(
                "The object store index query currently needs to be called with selectable=true"
            )
        selectable_ids = self.object_store.object_store_ids_allowing_selection()
        return [self._model_for(selectable_id) for selectable_id in selectable_ids]

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

    def _model_for(self, object_store_id: str) -> ConcreteObjectStoreModel:
        concrete_object_store = self.object_store.get_concrete_store_by_object_store_id(object_store_id)
        if concrete_object_store is None:
            raise ObjectNotFound()
        return concrete_object_store.to_model(object_store_id)
