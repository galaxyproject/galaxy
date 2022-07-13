from logging import getLogger
from typing import (
    List,
    Optional,
    Set,
)

from pydantic import (
    BaseModel,
    Extra,
    Field,
    ValidationError,
)

from galaxy import exceptions
from galaxy.datatypes.registry import Registry
from galaxy.managers.collections import DatasetCollectionManager
from galaxy.managers.collections_util import (
    api_payload_to_create_params,
    dictify_dataset_collection_instance,
    dictify_element_reference,
)
from galaxy.managers.context import ProvidesHistoryContext
from galaxy.managers.hdcas import HDCAManager
from galaxy.managers.histories import HistoryManager
from galaxy.schema.fields import (
    EncodedDatabaseIdField,
    ModelClassField,
)
from galaxy.schema.schema import (
    AnyHDCA,
    CreateNewCollectionPayload,
    DatasetCollectionInstanceType,
    DCESummary,
    DCEType,
    HDCADetailed,
    TagCollection,
)
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.webapps.base.controller import UsesLibraryMixinItems
from galaxy.webapps.galaxy.services.base import ServiceBase

log = getLogger(__name__)


class UpdateCollectionAttributePayload(BaseModel):
    """Contains attributes that can be updated for all elements in a dataset collection."""

    dbkey: str = Field(..., description="TODO")

    class Config:
        extra = Extra.forbid  # will cause validation to fail if extra attributes are included,


class DatasetCollectionAttributesResult(BaseModel):
    dbkey: str = Field(..., description="TODO")
    # Are the following fields really used/needed?
    extension: str = Field(..., description="The dataset file extension.", example="txt")
    model_class: str = ModelClassField("HistoryDatasetCollectionAssociation")
    dbkeys: Optional[Set[str]]
    extensions: Optional[Set[str]]
    tags: TagCollection


class SuitableConverter(BaseModel):
    tool_id: str = Field(..., description="The ID of the tool that can perform the type conversion.")
    name: str = Field(..., description="The name of the converter.")
    target_type: str = Field(..., description="The type to convert to.")
    original_type: str = Field(..., description="The type to convert from.")


class SuitableConverters(BaseModel):
    """Collection of converters that can be used on a particular dataset collection."""

    __root__: List[SuitableConverter]


class DatasetCollectionContentElements(BaseModel):
    """Represents a collection of elements contained in the dataset collection."""

    __root__: List[DCESummary]


class DatasetCollectionsService(ServiceBase, UsesLibraryMixinItems):
    def __init__(
        self,
        security: IdEncodingHelper,
        history_manager: HistoryManager,
        hdca_manager: HDCAManager,
        collection_manager: DatasetCollectionManager,
        datatypes_registry: Registry,
    ):
        super().__init__(security)
        self.history_manager = history_manager
        self.hdca_manager = hdca_manager
        self.collection_manager = collection_manager
        self.datatypes_registry = datatypes_registry

    def create(self, trans: ProvidesHistoryContext, payload: CreateNewCollectionPayload) -> HDCADetailed:
        """
        Create a new dataset collection instance.

        :type   payload: dict
        :param  payload: (optional) dictionary structure containing:
            * collection_type: dataset collection type to create.
            * instance_type:   Instance type - 'history' or 'library'.
            * name:            the new dataset collections's name
            * datasets:        object describing datasets for collection
        :rtype:     dict
        :returns:   element view of new dataset collection
        """
        # TODO: Error handling...
        create_params = api_payload_to_create_params(payload.dict(exclude_unset=True))
        if payload.instance_type == DatasetCollectionInstanceType.history:
            if payload.history_id is None:
                raise exceptions.RequestParameterInvalidException("Parameter history_id is required.")
            history_id = self.decode_id(payload.history_id)
            history = self.history_manager.get_owned(history_id, trans.user, current_history=trans.history)
            create_params["parent"] = history
            create_params["history"] = history
        elif payload.instance_type == DatasetCollectionInstanceType.library:
            library_folder = self.get_library_folder(trans, payload.folder_id, check_accessible=True)
            self.check_user_can_add_to_library_item(trans, library_folder, check_accessible=False)
            create_params["parent"] = library_folder
        else:
            raise exceptions.RequestParameterInvalidException()

        dataset_collection_instance = self.collection_manager.create(trans=trans, **create_params)
        rval = dictify_dataset_collection_instance(
            dataset_collection_instance,
            security=trans.security,
            url_builder=trans.url_builder,
            parent=create_params["parent"],
        )
        return rval

    def copy(
        self, trans: ProvidesHistoryContext, id: EncodedDatabaseIdField, payload: UpdateCollectionAttributePayload
    ):
        """
        Iterate over all datasets of a collection and copy datasets with new attributes to a new collection.
        e.g attributes = {'dbkey': 'dm3'}
        """
        self.collection_manager.copy(
            trans, trans.history, "hdca", id, copy_elements=True, dataset_instance_attributes=payload.dict()
        )

    def attributes(
        self,
        trans: ProvidesHistoryContext,
        id: EncodedDatabaseIdField,
        instance_type: DatasetCollectionInstanceType = DatasetCollectionInstanceType.history,
    ) -> DatasetCollectionAttributesResult:
        """
        Returns dbkey/extension for collection elements
        """
        dataset_collection_instance = self.collection_manager.get_dataset_collection_instance(
            trans, id=id, instance_type=instance_type, check_ownership=True
        )
        rval = dataset_collection_instance.to_dict(view="dbkeysandextensions")
        return rval

    def suitable_converters(
        self,
        trans: ProvidesHistoryContext,
        id: EncodedDatabaseIdField,
        instance_type: DatasetCollectionInstanceType = DatasetCollectionInstanceType.history,
    ) -> SuitableConverters:
        """
        Returns suitable converters for all datatypes in collection
        """
        rval = self.collection_manager.get_converters_for_collection(trans, id, self.datatypes_registry, instance_type)
        return rval

    def show(
        self,
        trans: ProvidesHistoryContext,
        id: EncodedDatabaseIdField,
        instance_type: DatasetCollectionInstanceType = DatasetCollectionInstanceType.history,
    ) -> AnyHDCA:
        """
        Returns information about a particular dataset collection.
        """
        dataset_collection_instance = self.collection_manager.get_dataset_collection_instance(
            trans,
            id=id,
            instance_type=instance_type,
        )
        if instance_type == DatasetCollectionInstanceType.history:
            parent = dataset_collection_instance.history
        elif instance_type == DatasetCollectionInstanceType.library:
            parent = dataset_collection_instance.folder
        else:
            raise exceptions.RequestParameterInvalidException()

        rval = dictify_dataset_collection_instance(
            dataset_collection_instance,
            security=trans.security,
            url_builder=trans.url_builder,
            parent=parent,
            view="element",
        )
        return rval

    def contents(
        self,
        trans: ProvidesHistoryContext,
        hdca_id: EncodedDatabaseIdField,
        parent_id: EncodedDatabaseIdField,
        instance_type: DatasetCollectionInstanceType = DatasetCollectionInstanceType.history,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> DatasetCollectionContentElements:
        """
        Shows direct child contents of indicated dataset collection parent id

        :type   string:     encoded string id
        :param  id:         HDCA.id
        :type   string:     encoded string id
        :param  parent_id:  parent dataset_collection.id for the dataset contents to be viewed
        :type   integer:    int
        :param  limit:      pagination limit for returned dataset collection elements
        :type   integer:    int
        :param  offset:     pagination offset for returned dataset collection elements
        :rtype:     list
        :returns:   list of dataset collection elements and contents
        """
        # validate HDCA for current user, will throw error if not permitted
        # TODO: refactor get_dataset_collection_instance
        hdca = self.collection_manager.get_dataset_collection_instance(
            trans, id=hdca_id, check_ownership=True, instance_type=instance_type
        )

        # check to make sure the dsc is part of the validated hdca
        decoded_parent_id = self.decode_id(parent_id)
        if not hdca.contains_collection(decoded_parent_id):
            raise exceptions.ObjectNotFound(
                "Requested dataset collection is not contained within indicated history content"
            )

        # retrieve contents
        contents = self.collection_manager.get_collection_contents(trans, decoded_parent_id, limit=limit, offset=offset)

        # dictify and tack on a collection_url for drilling down into nested collections
        def serialize_element(dsc_element) -> DCESummary:
            result = dictify_element_reference(dsc_element, recursive=False, security=trans.security)
            if result["element_type"] == DCEType.dataset_collection:
                assert trans.url_builder
                result["object"]["contents_url"] = trans.url_builder(
                    "contents_dataset_collection",
                    hdca_id=self.encode_id(hdca.id),
                    parent_id=self.encode_id(result["object"]["id"]),
                )
            trans.security.encode_all_ids(result, recursive=True)
            return result

        rval = [serialize_element(el) for el in contents]
        try:
            return DatasetCollectionContentElements.parse_obj(rval)
        except ValidationError:
            log.exception(
                f"Serializing DatasetCollectionContentsElements failed. Collection is populated: {hdca.collection.populated}"
            )
            raise
