"""
API operations on the contents of a history dataset.
"""
import logging

from galaxy import (
    util,
    web
)
from galaxy.schema import (
    FilterQueryParams,
)
from galaxy.schema.schema import (
    DatasetSourceType,
)
from galaxy.webapps.galaxy.api.common import (
    get_update_permission_payload,
    parse_serialization_params,
)
from galaxy.webapps.galaxy.services.datasets import (
    DatasetShowParams,
    DatasetsService,
)
from . import BaseGalaxyAPIController, depends

log = logging.getLogger(__name__)


class DatasetsController(BaseGalaxyAPIController, UsesVisualizationMixin):
    service: DatasetsService = depends(DatasetsService)

    @web.expose_api
    def index(self, trans, limit=500, offset=0, history_id=None, **kwd):
        """
        GET /api/datasets/

        Search datasets or collections using a query system

        :rtype:     list
        :returns:   dictionaries containing summary of dataset or dataset_collection information

        The list returned can be filtered by using two optional parameters:

            :q:
                string, generally a property name to filter by followed
                by an (often optional) hyphen and operator string.

            :qv:

                string, the value to filter by

        ..example::

            To filter the list to only those created after 2015-01-29,
            the query string would look like:
                '?q=create_time-gt&qv=2015-01-29'

            Multiple filters can be sent in using multiple q/qv pairs:
                '?q=create_time-gt&qv=2015-01-29&q=name-contains&qv=experiment-1'

        The list returned can be paginated using two optional parameters:
            limit:  integer, defaults to no value and no limit (return all)
                    how many items to return
            offset: integer, defaults to 0 and starts at the beginning
                    skip the first ( offset - 1 ) items and begin returning
                    at the Nth item

        ..example:
            limit and offset can be combined. Skip the first two and return five:
                '?limit=5&offset=3'

        The list returned can be ordered using the optional parameter:
            order:  string containing one of the valid ordering attributes followed
                    (optionally) by '-asc' or '-dsc' (default) for ascending and descending
                    order respectively. Orders can be stacked as a comma-
                    separated list of values.
                    Allowed ordering attributes are: 'create_time', 'extension',
                    'hid', 'history_id', 'name', 'update_time'.
                    'order' defaults to 'create_time'.

        ..example:
            To sort by name descending then create time descending:
                '?order=name-dsc,create_time'

        """
        serialization_params = parse_serialization_params(**kwd)
        filter_parameters = FilterQueryParams(**kwd)
        filter_parameters.limit = filter_parameters.limit or limit
        filter_parameters.offset = filter_parameters.offset or offset
        return self.service.index(
            trans, history_id, serialization_params, filter_parameters
        )

    @web.expose_api_anonymous_and_sessionless
    def show(self, trans, id, hda_ldda='hda', data_type=None, provider=None, **kwd):
        """
        GET /api/datasets/{encoded_dataset_id}
        Displays information about and/or content of a dataset.
        """
        serialization_params = parse_serialization_params(**kwd)
        kwd.update({
            "hda_ldda": hda_ldda,
            "data_type": data_type,
            "provider": provider,
        })
        params = DatasetShowParams(**kwd)
        rval = self.service.show(trans, id, params, serialization_params)
        return rval

    @web.expose_api_anonymous
    def show_storage(self, trans, dataset_id, hda_ldda='hda', **kwd):
        """
        GET /api/datasets/{encoded_dataset_id}/storage

        Display user-facing storage details related to the objectstore a
        dataset resides in.
        """
        return self.service.show_storage(trans, dataset_id, hda_ldda)

    @web.expose_api_anonymous
    def show_inheritance_chain(self, trans, dataset_id, hda_ldda='hda', **kwd):
        """
        GET /api/datasets/{dataset_id}/inheritance_chain

        Display inheritance chain for the given dataset

        For internal use, this endpoint may change without warning.
        """
        return self.service.show_inheritance_chain(trans, dataset_id, hda_ldda)

    @web.expose_api
    def update_permissions(self, trans, dataset_id, payload, **kwd):
        """
        PUT /api/datasets/{encoded_dataset_id}/permissions
        Updates permissions of a dataset.

        :rtype:     dict
        :returns:   dictionary containing new permissions
        """
        hda_ldda = kwd.pop('hda_ldda', DatasetSourceType.hda)
        if payload:
            kwd.update(payload)
        update_payload = get_update_permission_payload(kwd)
        return self.service.update_permissions(trans, dataset_id, update_payload, hda_ldda)

    @web.expose_api_anonymous_and_sessionless
    def extra_files(self, trans, history_content_id, history_id, **kwd):
        """
        GET /api/histories/{encoded_history_id}/contents/{encoded_content_id}/extra_files
        Generate list of extra files.
        """
        return self.service.extra_files(trans, history_content_id)

    @web.expose_api_raw_anonymous
    def display(self, trans, history_content_id, history_id,
                preview=False, filename=None, to_ext=None, raw=False, **kwd):
        """
        GET /api/histories/{encoded_history_id}/contents/{encoded_content_id}/display
        Displays history content (dataset).

        The query parameter 'raw' should be considered experimental and may be dropped at
        some point in the future without warning. Generally, data should be processed by its
        datatype prior to display (the defult if raw is unspecified or explicitly false.
        """
        raw = util.string_as_bool(raw)
        display_data, headers = self.service.display(
            trans, history_content_id, history_id, preview, filename, to_ext, raw, **kwd
        )
        trans.response.headers.update(headers)
        return display_data

    @web.expose_api
    def get_content_as_text(self, trans, dataset_id):
        """ Returns item content as Text. """
        return self.service.get_content_as_text(trans, dataset_id)

    @web.expose_api_raw_anonymous_and_sessionless
    def get_metadata_file(self, trans, history_content_id, history_id, metadata_file=None, **kwd):
        """
        GET /api/histories/{history_id}/contents/{history_content_id}/metadata_file
        """
        # TODO: remove open_file parameter when deleting this legacy endpoint
        metadata_file, headers = self.service.get_metadata_file(
            trans, history_content_id, metadata_file, open_file=True
        )
        trans.response.headers.update(headers)
        return metadata_file

    @web.expose_api_anonymous
    def converted(self, trans, dataset_id, ext, **kwargs):
        """
        converted( self, trans, dataset_id, ext, **kwargs )
        * GET /api/datasets/{dataset_id}/converted/{ext}
            return information about datasets made by converting this dataset
            to a new format

        :type   dataset_id: str
        :param  dataset_id: the encoded id of the original HDA to check
        :type   ext:        str
        :param  ext:        file extension of the target format or None.

        If there is no existing converted dataset for the format in `ext`,
        one will be created.

        If `ext` is None, a dictionary will be returned of the form
        { <converted extension> : <converted id>, ... } containing all the
        *existing* converted datasets.

        ..note: `view` and `keys` are also available to control the serialization
            of individual datasets. They have no effect when `ext` is None.

        :rtype:     dict
        :returns:   dictionary containing detailed HDA information
                    or (if `ext` is None) an extension->dataset_id map
        """
        serialization_params = parse_serialization_params(**kwargs)
        return self.service.converted(trans, dataset_id, ext, serialization_params)
