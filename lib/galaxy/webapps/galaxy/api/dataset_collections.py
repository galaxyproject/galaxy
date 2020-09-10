from logging import getLogger

import routes

from galaxy import managers
from galaxy.exceptions import ObjectNotFound
from galaxy.managers.base import decode_id
from galaxy.managers.collections_util import (
    api_payload_to_create_params,
    dictify_dataset_collection_instance,
    dictify_element_reference
)
from galaxy.web import expose_api
from galaxy.webapps.base.controller import (
    BaseAPIController,
    UsesLibraryMixinItems
)

log = getLogger(__name__)


class DatasetCollectionsController(
    BaseAPIController,
    UsesLibraryMixinItems,
):

    def __init__(self, app):
        super().__init__(app)
        self.history_manager = managers.histories.HistoryManager(app)

    @expose_api
    def index(self, trans, **kwd):
        trans.response.status = 501
        return 'not implemented'

    @expose_api
    def create(self, trans, payload, **kwd):
        """
        * POST /api/dataset_collections:
            create a new dataset collection instance.

        :type   payload: dict
        :param  payload: (optional) dictionary structure containing:
            * collection_type: dataset colltion type to create.
            * instance_type:   Instance type - 'history' or 'library'.
            * name:            the new dataset collections's name
            * datasets:        object describing datasets for collection
        :rtype:     dict
        :returns:   element view of new dataset collection
        """
        # TODO: Error handling...
        create_params = api_payload_to_create_params(payload)
        instance_type = payload.pop("instance_type", "history")
        if instance_type == "history":
            history_id = payload.get('history_id')
            history_id = decode_id(self.app, history_id)
            history = self.history_manager.get_owned(history_id, trans.user, current_history=trans.history)
            create_params["parent"] = history
        elif instance_type == "library":
            folder_id = payload.get('folder_id')
            library_folder = self.get_library_folder(trans, folder_id, check_accessible=True)
            self.check_user_can_add_to_library_item(trans, library_folder, check_accessible=False)
            create_params["parent"] = library_folder
        else:
            trans.status = 501
            return
        dataset_collection_instance = self.__service(trans).create(trans=trans, **create_params)
        return dictify_dataset_collection_instance(dataset_collection_instance,
                                                   security=trans.security, parent=create_params["parent"])

    @expose_api
    def show(self, trans, instance_type, id, **kwds):
        dataset_collection_instance = self.__service(trans).get_dataset_collection_instance(
            trans,
            id=id,
            instance_type=instance_type,
        )
        if instance_type == 'history':
            parent = dataset_collection_instance.history
        elif instance_type == 'library':
            parent = dataset_collection_instance.folder
        else:
            trans.status = 501
            return
        return dictify_dataset_collection_instance(
            dataset_collection_instance,
            security=trans.security,
            parent=parent,
            view='element'
        )

    @expose_api
    def contents(self, trans, hdca_id, parent_id, instance_type='history', limit=None, offset=None, **kwds):
        """
        * GET /api/dataset_collection/{hdca_id}/contents/{parent_id}?limit=100&offset=0
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
        svc = self.__service(trans)
        encode_id = trans.app.security.encode_id

        # validate HDCA for current user, will throw error if not permitted
        # TODO: refactor get_dataset_collection_instance
        hdca = svc.get_dataset_collection_instance(trans,
            id=hdca_id, check_ownership=True,
            instance_type=instance_type)

        # check to make sure the dsc is part of the validated hdca
        decoded_parent_id = decode_id(self.app, parent_id)
        if not hdca.contains_collection(decoded_parent_id):
            errmsg = 'Requested dataset collection is not contained within indicated history content'
            raise ObjectNotFound(errmsg)

        # retrieve contents
        contents_qry = svc.get_collection_contents_qry(decoded_parent_id, limit=limit, offset=offset)

        # dictify and tack on a collection_url for drilling down into nested collections
        def process_element(dsc_element):
            result = dictify_element_reference(dsc_element, recursive=False, security=trans.security)
            if result["element_type"] == "dataset_collection":
                result["object"]["contents_url"] = routes.url_for('contents_dataset_collection',
                    hdca_id=encode_id(hdca.id),
                    parent_id=encode_id(result["object"]["id"]))
            trans.security.encode_all_ids(result, recursive=True)
            return result

        results = contents_qry.with_session(trans.sa_session()).all()
        return [process_element(el) for el in results]

    def __service(self, trans):
        service = trans.app.dataset_collections_service
        return service
