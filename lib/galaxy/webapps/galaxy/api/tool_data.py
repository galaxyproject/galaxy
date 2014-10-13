
from galaxy import exceptions
from galaxy import web, util
from galaxy.web import _future_expose_api_anonymous
from galaxy.web import _future_expose_api
from galaxy.web.base.controller import BaseAPIController
from galaxy.web.base.controller import UsesVisualizationMixin
from galaxy.web.base.controller import UsesHistoryMixin
from galaxy.visualization.genomes import GenomeRegion
from galaxy.util.json import dumps
from galaxy.visualization.data_providers.genome import *

from galaxy.managers.collections_util import dictify_dataset_collection_instance


class ToolData( BaseAPIController ):
    """
    RESTful controller for interactions with tools.
    """

    @web.expose_api
    def index( self, trans, **kwds ):
        """
        GET /api/tool_data: returns a list tool_data tables::

        """
        return trans.app.tool_data_tables.data_tables.keys()

    @web.expose_api
    def show( self, trans, id, **kwds ):
        return trans.app.tool_data_tables.data_tables[id].to_dict()
