"""
API operations on the contents of a history dataset.
"""
import logging
import os

from six import string_types

from galaxy import (
    exceptions as galaxy_exceptions,
    managers,
    model,
    util,
    web
)
from galaxy.datatypes import dataproviders
from galaxy.util.path import (
    safe_walk
)
from galaxy.visualization.data_providers.genome import (
    BamDataProvider,
    FeatureLocationIndexDataProvider,
    SamDataProvider
)
from galaxy.web.base.controller import (
    BaseAPIController,
    UsesVisualizationMixin
)
from galaxy.web.framework.helpers import is_true

log = logging.getLogger(__name__)


class DatasetsController(BaseAPIController, UsesVisualizationMixin):

    def __init__(self, app):
        super(DatasetsController, self).__init__(app)
        self.hda_manager = managers.hdas.HDAManager(app)
        self.hda_serializer = managers.hdas.HDASerializer(self.app)
        self.ldda_manager = managers.lddas.LDDAManager(app)

    def _parse_serialization_params(self, kwd, default_view):
        view = kwd.get('view', None)
        keys = kwd.get('keys')
        if isinstance(keys, string_types):
            keys = keys.split(',')
        return dict(view=view, keys=keys, default_view=default_view)

    @web.expose_api
    def index(self, trans, **kwd):
        """
        GET /api/datasets
        Lists datasets.
        """
        trans.response.status = 501
        return 'not implemented'

    @web.expose_api_anonymous
    def show(self, trans, id, hda_ldda='hda', data_type=None, provider=None, **kwd):
        """
        GET /api/datasets/{encoded_dataset_id}
        Displays information about and/or content of a dataset.
        """
        # Get dataset.
        try:
            dataset = self.get_hda_or_ldda(trans, hda_ldda=hda_ldda, dataset_id=id)
        except Exception as e:
            return str(e)

        # Use data type to return particular type of data.
        try:
            if data_type == 'state':
                rval = self._dataset_state(trans, dataset)
            elif data_type == 'converted_datasets_state':
                rval = self._converted_datasets_state(trans, dataset, kwd.get('chrom', None),
                                                      is_true(kwd.get('retry', False)))
            elif data_type == 'data':
                rval = self._data(trans, dataset, **kwd)
            elif data_type == 'features':
                rval = self._search_features(trans, dataset, kwd.get('query'))
            elif data_type == 'raw_data':
                rval = self._raw_data(trans, dataset, provider, **kwd)
            elif data_type == 'track_config':
                rval = self.get_new_track_config(trans, dataset)
            elif data_type == 'genome_data':
                rval = self._get_genome_data(trans, dataset, kwd.get('dbkey', None))
            else:
                # Default: return dataset as dict.
                if hda_ldda == 'hda':
                    return self.hda_serializer.serialize_to_view(dataset,
                                                                 view=kwd.get('view', 'detailed'), user=trans.user, trans=trans)
                else:
                    rval = dataset.to_dict()

        except Exception as e:
            rval = "Error in dataset API at listing contents: " + str(e)
            log.error(rval + ": %s" % str(e), exc_info=True)
            trans.response.status = 500
        return rval

    @web._future_expose_api
    def update_permissions(self, trans, dataset_id, payload, **kwd):
        """
        PUT /api/datasets/{encoded_dataset_id}/permissions
        Updates permissions of a dataset.

        :rtype:     dict
        :returns:   dictionary containing new permissions
        """
        if payload:
            kwd.update(payload)
        hda_ldda = kwd.get('hda_ldda', 'hda')
        dataset_assoc = self.get_hda_or_ldda(trans, hda_ldda=hda_ldda, dataset_id=dataset_id)
        if hda_ldda == "hda":
            self.hda_manager.update_permissions(trans, dataset_assoc, **kwd)
            return self.hda_manager.serialize_dataset_association_roles(trans, dataset_assoc)
        else:
            self.ldda_manager.update_permissions(trans, dataset_assoc, **kwd)
            return self.ldda_manager.serialize_dataset_association_roles(trans, dataset_assoc)

    def _dataset_state(self, trans, dataset, **kwargs):
        """
        Returns state of dataset.
        """
        msg = self.hda_manager.data_conversion_status(dataset)
        if not msg:
            msg = dataset.conversion_messages.DATA

        return msg

    def _converted_datasets_state(self, trans, dataset, chrom=None, retry=False):
        """
        Init-like method that returns state of dataset's converted datasets.
        Returns valid chroms for that dataset as well.
        """
        msg = self.hda_manager.data_conversion_status(dataset)
        if msg:
            return msg

        # Get datasources and check for messages (which indicate errors). Retry if flag is set.
        data_sources = dataset.get_datasources(trans)
        messages_list = [data_source_dict['message'] for data_source_dict in data_sources.values()]
        msg = self._get_highest_priority_msg(messages_list)
        if msg:
            if retry:
                # Clear datasources and then try again.
                dataset.clear_associated_files()
                return self._converted_datasets_state(trans, dataset, chrom)
            else:
                return msg

        # If there is a chrom, check for data on the chrom.
        if chrom:
            data_provider = trans.app.data_provider_registry.get_data_provider(trans,
                                                                               original_dataset=dataset, source='index')
            if not data_provider.has_data(chrom):
                return dataset.conversion_messages.NO_DATA

        # Have data if we get here
        return {"status": dataset.conversion_messages.DATA, "valid_chroms": None}

    def _search_features(self, trans, dataset, query):
        """
        Returns features, locations in dataset that match query. Format is a
        list of features; each feature is a list itself: [name, location]
        """
        if dataset.can_convert_to("fli"):
            converted_dataset = dataset.get_converted_dataset(trans, "fli")
            if converted_dataset:
                data_provider = FeatureLocationIndexDataProvider(converted_dataset=converted_dataset)
                if data_provider:
                    return data_provider.get_data(query)

        return []

    def _data(self, trans, dataset, chrom, low, high, start_val=0, max_vals=None, **kwargs):
        """
        Provides a block of data from a dataset.
        """
        # Parameter check.
        if not chrom:
            return dataset.conversion_messages.NO_DATA

        # Dataset check.
        msg = self.hda_manager.data_conversion_status(dataset)
        if msg:
            return msg

        # Get datasources and check for messages.
        data_sources = dataset.get_datasources(trans)
        messages_list = [data_source_dict['message'] for data_source_dict in data_sources.values()]
        return_message = self._get_highest_priority_msg(messages_list)
        if return_message:
            return return_message

        extra_info = None
        mode = kwargs.get("mode", "Auto")
        data_provider_registry = trans.app.data_provider_registry
        indexer = None

        # Coverage mode uses index data.
        if mode == "Coverage":
            # Get summary using minimal cutoffs.
            indexer = data_provider_registry.get_data_provider(trans, original_dataset=dataset, source='index')
            return indexer.get_data(chrom, low, high, **kwargs)

        # TODO:
        # (1) add logic back in for no_detail
        # (2) handle scenario where mode is Squish/Pack but data requested is large, so reduced data needed to be returned.

        # If mode is Auto, need to determine what type of data to return.
        if mode == "Auto":
            # Get stats from indexer.
            indexer = data_provider_registry.get_data_provider(trans, original_dataset=dataset, source='index')
            stats = indexer.get_data(chrom, low, high, stats=True)

            # If stats were requested, return them.
            if 'stats' in kwargs:
                if stats['data']['max'] == 0:
                    return {'dataset_type': indexer.dataset_type, 'data': None}
                else:
                    return stats

            # Stats provides features/base and resolution is bases/pixel, so
            # multiplying them yields features/pixel.
            features_per_pixel = stats['data']['max'] * float(kwargs['resolution'])

            # Use heuristic based on features/pixel and region size to determine whether to
            # return coverage data. When zoomed out and region is large, features/pixel
            # is determining factor. However, when sufficiently zoomed in and region is
            # small, coverage data is no longer provided.
            if int(high) - int(low) > 50000 and features_per_pixel > 1000:
                return indexer.get_data(chrom, low, high)

        #
        # Provide individual data points.
        #

        # Get data provider.
        data_provider = data_provider_registry.get_data_provider(trans, original_dataset=dataset, source='data')

        # Allow max_vals top be data provider set if not passed
        if max_vals is None:
            max_vals = data_provider.get_default_max_vals()

        # Get reference sequence and mean depth for region; these is used by providers for aligned reads.
        region = None
        mean_depth = None
        if isinstance(data_provider, (SamDataProvider, BamDataProvider)):
            # Get reference sequence.
            if dataset.dbkey:
                # FIXME: increase region 1M each way to provide sequence for
                # spliced/gapped reads. Probably should provide refseq object
                # directly to data provider.
                region = self.app.genomes.reference(trans, dbkey=dataset.dbkey, chrom=chrom,
                                                    low=(max(0, int(low) - 1000000)),
                                                    high=(int(high) + 1000000))

            # Get mean depth.
            if not indexer:
                indexer = data_provider_registry.get_data_provider(trans, original_dataset=dataset, source='index')
            stats = indexer.get_data(chrom, low, high, stats=True)
            mean_depth = stats['data']['mean']

        # Get and return data from data_provider.
        result = data_provider.get_data(chrom, int(low), int(high), int(start_val), int(max_vals),
                                        ref_seq=region, mean_depth=mean_depth, **kwargs)
        result.update({'dataset_type': data_provider.dataset_type, 'extra_info': extra_info})
        return result

    def _raw_data(self, trans, dataset, provider=None, **kwargs):
        """
        Uses original (raw) dataset to return data. This method is useful
        when the dataset is not yet indexed and hence using data would
        be slow because indexes need to be created.
        """
        # Dataset check.
        msg = self.hda_manager.data_conversion_status(dataset)
        if msg:
            return msg

        registry = trans.app.data_provider_registry

        # allow the caller to specify which provider is used
        #   pulling from the original providers if possible, then the new providers
        if provider:
            if provider in registry.dataset_type_name_to_data_provider:
                data_provider = registry.dataset_type_name_to_data_provider[provider](dataset)

            elif dataset.datatype.has_dataprovider(provider):
                kwargs = dataset.datatype.dataproviders[provider].parse_query_string_settings(kwargs)
                # use dictionary to allow more than the data itself to be returned (data totals, other meta, etc.)
                return {
                    'data': list(dataset.datatype.dataprovider(dataset, provider, **kwargs))
                }

            else:
                raise dataproviders.exceptions.NoProviderAvailable(dataset.datatype, provider)

        # no provider name: look up by datatype
        else:
            data_provider = registry.get_data_provider(trans, raw=True, original_dataset=dataset)

        # Return data.
        data = data_provider.get_data(**kwargs)

        return data

    @web.expose_api_anonymous
    def extra_files(self, trans, history_content_id, history_id, **kwd):
        """
        GET /api/histories/{encoded_history_id}/contents/{encoded_content_id}/extra_files
        Generate list of extra files.
        """
        decoded_content_id = self.decode_id(history_content_id)

        hda = self.hda_manager.get_accessible(decoded_content_id, trans.user)
        extra_files_path = hda.extra_files_path
        rval = []
        for root, directories, files in safe_walk(extra_files_path):
            for directory in directories:
                rval.append({"class": "Directory", "path": os.path.relpath(os.path.join(root, directory), extra_files_path)})
            for file in files:
                rval.append({"class": "File", "path": os.path.relpath(os.path.join(root, file), extra_files_path)})

        return rval

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
        decoded_content_id = self.decode_id(history_content_id)
        raw = util.string_as_bool_or_none(raw)

        rval = ''
        try:
            hda = self.hda_manager.get_accessible(decoded_content_id, trans.user)

            if raw:
                if filename and filename != 'index':
                    object_store = trans.app.object_store
                    store_by = getattr(object_store, "store_by", "id")
                    dir_name = 'dataset_%s_files' % getattr(hda.dataset, store_by)
                    file_path = object_store.get_filename(hda.dataset,
                                                          extra_dir=dir_name,
                                                          alt_name=filename)
                else:
                    file_path = hda.file_name
                rval = open(file_path, 'rb')
            else:
                display_kwd = kwd.copy()
                if 'key' in display_kwd:
                    del display_kwd["key"]
                rval = hda.datatype.display_data(trans, hda, preview, filename, to_ext, **display_kwd)
        except Exception as e:
            log.exception("Error getting display data for dataset (%s) from history (%s)",
                          history_content_id, history_id)
            trans.response.status = 500
            rval = "Could not get display data for dataset: %s" % e
        return rval

    @web.expose_api_raw_anonymous
    def get_metadata_file(self, trans, history_content_id, history_id, metadata_file=None, **kwd):
        """
        GET /api/histories/{history_id}/contents/{history_content_id}/metadata_file
        """
        decoded_content_id = self.decode_id(history_content_id)
        rval = ''
        try:
            hda = self.hda_manager.get_accessible(decoded_content_id, trans.user)
            file_ext = hda.metadata.spec.get(metadata_file).get("file_ext", metadata_file)
            fname = ''.join(c in util.FILENAME_VALID_CHARS and c or '_' for c in hda.name)[0:150]
            trans.response.headers["Content-Type"] = "application/octet-stream"
            trans.response.headers["Content-Disposition"] = 'attachment; filename="Galaxy%s-[%s].%s"' % (hda.hid, fname, file_ext)
            return open(hda.metadata.get(metadata_file).file_name, 'rb')
        except Exception as e:
            log.exception("Error getting metadata_file (%s) for dataset (%s) from history (%s)",
                          metadata_file, history_content_id, history_id)
            trans.response.status = 500
            rval = "Could not get metadata for dataset: %s" % e
        return rval

    @web._future_expose_api_anonymous
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
        decoded_id = self.decode_id(dataset_id)
        hda = self.hda_manager.get_accessible(decoded_id, trans.user)
        if ext:
            converted = self._get_or_create_converted(trans, hda, ext, **kwargs)
            return self.hda_serializer.serialize_to_view(converted,
                user=trans.user, trans=trans, **self._parse_serialization_params(kwargs, 'detailed'))

        return self.hda_serializer.serialize_converted_datasets(hda, 'converted')

    def _get_or_create_converted(self, trans, original, target_ext, **kwargs):
        try:
            original.get_converted_dataset(trans, target_ext)
            converted = original.get_converted_files_by_type(target_ext)
            return converted

        except model.NoConverterException:
            exc_data = dict(source=original.ext, target=target_ext, available=list(original.get_converter_types().keys()))
            raise galaxy_exceptions.RequestParameterInvalidException('Conversion not possible', **exc_data)
