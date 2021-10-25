from logging import getLogger
from typing import Optional, Set

import routes
from pydantic import BaseModel, Field

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
from galaxy.schema.fields import EncodedDatabaseIdField, ModelClassField
from galaxy.schema.schema import (
    CreateNewCollectionPayload,
    DatasetCollectionInstanceType,
    HDCADetailed,
    TagCollection,
)
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.webapps.base.controller import UsesLibraryMixinItems
from galaxy.webapps.galaxy.services.base import ServiceBase


log = getLogger(__name__)


class UpdateCollectionAttributePayload(BaseModel):
    """Contains attributes that can be updated for all elements in a dataset collection."""
    dbkey: str = Field(
        ...,
        description="TODO"
    )


class DatasetCollectionAttributesResult(BaseModel):
    dbkey: str = Field(
        ...,
        description="TODO"
    )
    # Are the following fields really used/needed?
    extension: str = Field(
        ...,
        description="The dataset file extension.",
        example="txt"
    )
    model_class: str = ModelClassField("HistoryDatasetCollectionAssociation")
    dbkeys: Optional[Set[str]]
    extensions: Optional[Set[str]]
    tags: TagCollection


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
            dataset_collection_instance, security=trans.security, parent=create_params["parent"]
        )
        return HDCADetailed.construct(**rval)

    def update(self, trans: ProvidesHistoryContext, id: EncodedDatabaseIdField, payload: UpdateCollectionAttributePayload):
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
            trans,
            id=id,
            instance_type=instance_type,
            check_ownership=True
        )
        rval = dataset_collection_instance.to_dict(view="dbkeysandextensions")
        return DatasetCollectionAttributesResult.construct(**rval)

    def suitable_converters(self, trans: ProvidesHistoryContext, id, instance_type='history'):
        """
        Returns suitable converters for all datatypes in collection
        """
        return self.collection_manager.get_converters_for_collection(trans, id, self.datatypes_registry, instance_type)

    def show(self, trans: ProvidesHistoryContext, id, instance_type='history'):
        """
        Returns information about a particular dataset collection.
        """
        dataset_collection_instance = self.collection_manager.get_dataset_collection_instance(
            trans,
            id=id,
            instance_type=instance_type,
        )
        if instance_type == 'history':
            parent = dataset_collection_instance.history
        elif instance_type == 'library':
            parent = dataset_collection_instance.folder
        else:
            raise exceptions.RequestParameterInvalidException()

        return dictify_dataset_collection_instance(
            dataset_collection_instance,
            security=trans.security,
            parent=parent,
            view='element'
        )

    def contents(self, trans: ProvidesHistoryContext, hdca_id, parent_id, instance_type='history', limit=None, offset=None):
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
        hdca = self.collection_manager.get_dataset_collection_instance(trans,
            id=hdca_id, check_ownership=True,
            instance_type=instance_type)

        # check to make sure the dsc is part of the validated hdca
        decoded_parent_id = self.decode_id(parent_id)
        if parent_id != hdca_id and not hdca.contains_collection(decoded_parent_id):
            errmsg = 'Requested dataset collection is not contained within indicated history content'
            raise exceptions.ObjectNotFound(errmsg)

        # retrieve contents
        contents_qry = self.collection_manager.get_collection_contents_qry(decoded_parent_id, limit=limit, offset=offset)

        # dictify and tack on a collection_url for drilling down into nested collections
        def process_element(dsc_element):
            result = dictify_element_reference(dsc_element, recursive=False, security=trans.security)
            if result["element_type"] == "dataset_collection":
                result["object"]["contents_url"] = routes.url_for('contents_dataset_collection',
                    hdca_id=self.encode_id(hdca.id),
                    parent_id=self.encode_id(result["object"]["id"]))
            trans.security.encode_all_ids(result, recursive=True)
            return result

        results = contents_qry.with_session(trans.sa_session()).all()
        return [process_element(el) for el in results]
