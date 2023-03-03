"""
API operations on Galaxy's object store.
"""
import logging
from typing import (
    Any,
    Dict,
    List,
)

from fastapi import (
    Path,
    Query,
)

from galaxy.exceptions import (
    ObjectNotFound,
    RequestParameterInvalidException,
)
from galaxy.managers.context import ProvidesUserContext
from galaxy.objectstore import BaseObjectStore
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
    default=False, title="Selectable", description="Restrict index query to user selectable object stores."
)


@router.cbv
class FastAPIObjectStore:
    object_store: BaseObjectStore = depends(BaseObjectStore)

    @router.get(
        "/api/object_store",
        summary="",
        response_description="",
    )
    def index(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        selectable: bool = SelectableQueryParam,
    ) -> List[Dict[str, Any]]:
        if not selectable:
            raise RequestParameterInvalidException(
                "The object store index query currently needs to be called with selectable=true"
            )
        selectable_ids = self.object_store.object_store_ids_allowing_selection()
        return [self._dict_for(selectable_id) for selectable_id in selectable_ids]

    @router.get(
        "/api/object_store/{object_store_id}",
        summary="Return boolean to indicate if Galaxy's default object store allows selection.",
        response_description="A list with details about the remote files available to the user.",
    )
    def show_info(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        object_store_id: str = ConcreteObjectStoreIdPathParam,
    ) -> Dict[str, Any]:
        return self._dict_for(object_store_id)

    def _dict_for(self, object_store_id: str) -> Dict[str, Any]:
        concrete_object_store = self.object_store.get_concrete_store_by_object_store_id(object_store_id)
        if concrete_object_store is None:
            raise ObjectNotFound()
        as_dict = concrete_object_store.to_dict()
        as_dict["object_store_id"] = object_store_id
        return as_dict
