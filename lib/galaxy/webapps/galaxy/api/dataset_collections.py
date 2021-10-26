from logging import getLogger

from fastapi import Body

from galaxy import exceptions
from galaxy.managers.context import ProvidesHistoryContext
from galaxy.schema.schema import (
    CreateNewCollectionPayload,
    HDCADetailed,
)
from galaxy.web import expose_api
from galaxy.webapps.galaxy.services.dataset_collections import (
    DatasetCollectionsService,
    UpdateCollectionAttributePayload,
)
from . import (
    BaseGalaxyAPIController,
    depends,
    DependsOnTrans,
    Router
)

log = getLogger(__name__)

router = Router(tags=['dataset collections'])


@router.cbv
class FastAPIDatasetCollections:
    service: DatasetCollectionsService = depends(DatasetCollectionsService)

    @router.post(
        '/api/dataset_collections',
        summary="Create a new dataset collection instance.",
    )
    def create(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
        payload: CreateNewCollectionPayload = Body(...),
    ) -> HDCADetailed:
        return self.service.create(trans, payload)


class DatasetCollectionsController(BaseGalaxyAPIController):
    service: DatasetCollectionsService = depends(DatasetCollectionsService)

    @expose_api
    def index(self, trans, **kwd):
        raise exceptions.NotImplemented

    @expose_api
    def create(self, trans: ProvidesHistoryContext, payload: dict, **kwd):
        """
        * POST /api/dataset_collections:
            create a new dataset collection instance.

        :type   payload: dict
        :param  payload: (optional) dictionary structure containing:
            * collection_type: dataset collection type to create.
            * instance_type:   Instance type - 'history' or 'library'.
            * name:            the new dataset collections's name
            * datasets:        object describing datasets for collection
        :rtype:     dict
        :returns:   element view of new dataset collection
        """
        create_payload = CreateNewCollectionPayload(**payload)
        return self.service.create(trans, create_payload)

    @expose_api
    def update(self, trans: ProvidesHistoryContext, payload: dict, id):
        """
        Iterate over all datasets of a collection and copy datasets with new attributes to a new collection.
        e.g attributes = {'dbkey': 'dm3'}

        * POST /api/dataset_collections/{hdca_id}/copy:
            create a new dataset collection instance.
        """
        update_payload = UpdateCollectionAttributePayload(**payload)
        return self.service.update(trans, id, update_payload)

    @expose_api
    def attributes(self, trans: ProvidesHistoryContext, id, instance_type='history'):
        """
        GET /api/dataset_collections/{hdca_id}/attributes

        Returns dbkey/extension for collection elements
        """
        return self.service.attributes(trans, id, instance_type)

    @expose_api
    def suitable_converters(self, trans: ProvidesHistoryContext, id, instance_type='history', **kwds):
        """
        GET /api/dataset_collections/{hdca_id}/suitable_converters

        Returns suitable converters for all datatypes in collection
        """
        return self.service.suitable_converters(trans, id, instance_type)

    @expose_api
    def show(self, trans: ProvidesHistoryContext, id, instance_type='history', **kwds):
        """
        GET /api/dataset_collections/{hdca_id}
        GET /api/dataset_collections/{ldca_id}?instance_type=library
        """
        return self.service.show(trans, id, instance_type)

    @expose_api
    def contents(self, trans: ProvidesHistoryContext, hdca_id, parent_id, instance_type='history', limit=None, offset=None, **kwds):
        """
        GET /api/dataset_collection/{hdca_id}/contents/{parent_id}?limit=100&offset=0

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
        return self.service.contents(trans, hdca_id, parent_id, instance_type, limit, offset)
