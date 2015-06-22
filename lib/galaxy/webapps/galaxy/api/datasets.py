"""
API operations on the contents of a history dataset.
"""
from galaxy import web
from galaxy.web.framework.helpers import is_true
from galaxy import util

from galaxy.visualization.data_providers.genome import FeatureLocationIndexDataProvider
from galaxy.visualization.data_providers.genome import SamDataProvider
from galaxy.visualization.data_providers.genome import BamDataProvider
from galaxy.datatypes import dataproviders

from galaxy.web.base.controller import BaseAPIController
from galaxy.web.base.controller import UsesVisualizationMixin
from galaxy import managers

import logging
log = logging.getLogger( __name__ )


class DatasetsController( BaseAPIController, UsesVisualizationMixin ):

    def __init__( self, app ):
        super( DatasetsController, self ).__init__( app )
        self.hda_manager = managers.hdas.HDAManager( app )
        self.hda_serializer = managers.hdas.HDASerializer( self.app )

    @web.expose_api
    def index( self, trans, **kwd ):
        """
        GET /api/datasets
        Lists datasets.
        """
        trans.response.status = 501
        return 'not implemented'

    @web.expose_api_anonymous
    def show( self, trans, id, hda_ldda='hda', data_type=None, provider=None, **kwd ):
        """
        GET /api/datasets/{encoded_dataset_id}
        Displays information about and/or content of a dataset.
        """
        # Get dataset.
        try:
            dataset = self.get_hda_or_ldda( trans, hda_ldda=hda_ldda, dataset_id=id )
        except Exception as e:
            return str( e )

        # Use data type to return particular type of data.
        try:
            if data_type == 'state':
                rval = self._dataset_state( trans, dataset )
            elif data_type == 'converted_datasets_state':
                rval = self._converted_datasets_state( trans, dataset, kwd.get( 'chrom', None ),
                                                       is_true( kwd.get( 'retry', False ) ) )
            elif data_type == 'data':
                rval = self._data( trans, dataset, **kwd )
            elif data_type == 'features':
                rval = self._search_features( trans, dataset, kwd.get( 'query' ) )
            elif data_type == 'raw_data':
                rval = self._raw_data( trans, dataset, provider, **kwd )
            elif data_type == 'track_config':
                rval = self.get_new_track_config( trans, dataset )
            elif data_type == 'genome_data':
                rval = self._get_genome_data( trans, dataset, kwd.get('dbkey', None) )
            else:
                # Default: return dataset as dict.
                if hda_ldda == 'hda':
                    return self.hda_serializer.serialize_to_view( dataset,
                        view=kwd.get( 'view', 'detailed' ), user=trans.user, trans=trans )
                else:
                    rval = dataset.to_dict()

        except Exception as e:
            rval = "Error in dataset API at listing contents: " + str( e )
            log.error( rval + ": %s" % str(e), exc_info=True )
            trans.response.status = 500
        return rval

    def _dataset_state( self, trans, dataset, **kwargs ):
        """
        Returns state of dataset.
        """
        msg = self.hda_manager.data_conversion_status( dataset )
        if not msg:
            msg = dataset.conversion_messages.DATA

        return msg

    def _converted_datasets_state( self, trans, dataset, chrom=None, retry=False ):
        """
        Init-like method that returns state of dataset's converted datasets.
        Returns valid chroms for that dataset as well.
        """
        msg = self.hda_manager.data_conversion_status( dataset )
        if msg:
            return msg

        # Get datasources and check for messages (which indicate errors). Retry if flag is set.
        data_sources = dataset.get_datasources( trans )
        messages_list = [ data_source_dict[ 'message' ] for data_source_dict in data_sources.values() ]
        msg = self._get_highest_priority_msg( messages_list )
        if msg:
            if retry:
                # Clear datasources and then try again.
                dataset.clear_associated_files()
                return self._converted_datasets_state( trans, dataset, chrom )
            else:
                return msg

        # If there is a chrom, check for data on the chrom.
        if chrom:
            data_provider = trans.app.data_provider_registry.get_data_provider( trans,
                original_dataset=dataset, source='index' )
            if not data_provider.has_data( chrom ):
                return dataset.conversion_messages.NO_DATA

        # Have data if we get here
        return { "status": dataset.conversion_messages.DATA, "valid_chroms": None }

    def _search_features( self, trans, dataset, query ):
        """
        Returns features, locations in dataset that match query. Format is a
        list of features; each feature is a list itself: [name, location]
        """
        if dataset.can_convert_to( "fli" ):
            converted_dataset = dataset.get_converted_dataset( trans, "fli" )
            if converted_dataset:
                data_provider = FeatureLocationIndexDataProvider( converted_dataset=converted_dataset )
                if data_provider:
                    return data_provider.get_data( query )

        return []

    def _data( self, trans, dataset, chrom, low, high, start_val=0, max_vals=None, **kwargs ):
        """
        Provides a block of data from a dataset.
        """
        # Parameter check.
        if not chrom:
            return dataset.conversion_messages.NO_DATA

        # Dataset check.
        msg = self.hda_manager.data_conversion_status( dataset )
        if msg:
            return msg

        # Get datasources and check for essages.
        data_sources = dataset.get_datasources( trans )
        messages_list = [ data_source_dict[ 'message' ] for data_source_dict in data_sources.values() ]
        return_message = self._get_highest_priority_msg( messages_list )
        if return_message:
            return return_message

        extra_info = None
        mode = kwargs.get( "mode", "Auto" )
        data_provider_registry = trans.app.data_provider_registry
        indexer = None

        # Coverage mode uses index data.
        if mode == "Coverage":
            # Get summary using minimal cutoffs.
            indexer = data_provider_registry.get_data_provider( trans, original_dataset=dataset, source='index' )
            return indexer.get_data( chrom, low, high, **kwargs )

        # TODO:
        # (1) add logic back in for no_detail
        # (2) handle scenario where mode is Squish/Pack but data requested is large, so reduced data needed to be returned.

        # If mode is Auto, need to determine what type of data to return.
        if mode == "Auto":
            # Get stats from indexer.
            indexer = data_provider_registry.get_data_provider( trans, original_dataset=dataset, source='index' )
            stats = indexer.get_data( chrom, low, high, stats=True )

            # If stats were requested, return them.
            if 'stats' in kwargs:
                if stats[ 'data' ][ 'max' ] == 0:
                    return { 'dataset_type': indexer.dataset_type, 'data': None }
                else:
                    return stats

            # Stats provides features/base and resolution is bases/pixel, so
            # multiplying them yields features/pixel.
            features_per_pixel = stats[ 'data' ][ 'max' ] * float( kwargs[ 'resolution' ] )

            # Use heuristic based on features/pixel and region size to determine whether to
            # return coverage data. When zoomed out and region is large, features/pixel
            # is determining factor. However, when sufficiently zoomed in and region is
            # small, coverage data is no longer provided.
            if int( high ) - int( low ) > 50000 and features_per_pixel > 1000:
                return indexer.get_data( chrom, low, high )

        #
        # Provide individual data points.
        #

        # Get data provider.
        data_provider = data_provider_registry.get_data_provider( trans, original_dataset=dataset, source='data' )

        # Allow max_vals top be data provider set if not passed
        if max_vals is None:
            max_vals = data_provider.get_default_max_vals()

        # Get reference sequence and mean depth for region; these is used by providers for aligned reads.
        region = None
        mean_depth = None
        if isinstance( data_provider, (SamDataProvider, BamDataProvider ) ):
            # Get reference sequence.
            if dataset.dbkey:
                # FIXME: increase region 1M each way to provide sequence for
                # spliced/gapped reads. Probably should provide refseq object
                # directly to data provider.
                region = self.app.genomes.reference( trans, dbkey=dataset.dbkey, chrom=chrom,
                                                     low=( max( 0, int( low  ) - 1000000 ) ),
                                                     high=( int( high ) + 1000000 ) )

            # Get mean depth.
            if not indexer:
                indexer = data_provider_registry.get_data_provider( trans, original_dataset=dataset, source='index' )
            stats = indexer.get_data( chrom, low, high, stats=True )
            mean_depth = stats[ 'data' ][ 'mean' ]

        # Get and return data from data_provider.
        result = data_provider.get_data( chrom, int( low ), int( high ), int( start_val ), int( max_vals ),
                                         ref_seq=region, mean_depth=mean_depth, **kwargs )
        result.update( { 'dataset_type': data_provider.dataset_type, 'extra_info': extra_info } )
        return result

    def _raw_data( self, trans, dataset, provider=None, **kwargs ):
        """
        Uses original (raw) dataset to return data. This method is useful
        when the dataset is not yet indexed and hence using data would
        be slow because indexes need to be created.
        """
        # Dataset check.
        msg = self.hda_manager.data_conversion_status( dataset )
        if msg:
            return msg

        registry = trans.app.data_provider_registry

        # allow the caller to specifiy which provider is used
        #   pulling from the original providers if possible, then the new providers
        if provider:
            if provider in registry.dataset_type_name_to_data_provider:
                data_provider = registry.dataset_type_name_to_data_provider[ provider ]( dataset )

            elif dataset.datatype.has_dataprovider( provider ):
                kwargs = dataset.datatype.dataproviders[ provider ].parse_query_string_settings( kwargs )
                # use dictionary to allow more than the data itself to be returned (data totals, other meta, etc.)
                return {
                    'data': list( dataset.datatype.dataprovider( dataset, provider, **kwargs ) )
                }

            else:
                raise dataproviders.exceptions.NoProviderAvailable( dataset.datatype, provider )

        # no provider name: look up by datatype
        else:
            data_provider = registry.get_data_provider( trans, raw=True, original_dataset=dataset )

        # Return data.
        data = data_provider.get_data( **kwargs )

        return data

    @web.expose_api_raw_anonymous
    def display( self, trans, history_content_id, history_id,
                 preview=False, filename=None, to_ext=None, chunk=None, raw=False, **kwd ):
        """
        GET /api/histories/{encoded_history_id}/contents/{encoded_content_id}/display
        Displays history content (dataset).

        The query parameter 'raw' should be considered experimental and may be dropped at
        some point in the future without warning. Generally, data should be processed by its
        datatype prior to display (the defult if raw is unspecified or explicitly false.
        """
        decoded_content_id = self.decode_id( history_content_id )
        raw = util.string_as_bool_or_none( raw )

        rval = ''
        try:
            hda = self.hda_manager.get_accessible( decoded_content_id, trans.user )

            if raw:
                if filename and filename != 'index':
                    file_path = trans.app.object_store.get_filename( hda.dataset,
                        extra_dir=( 'dataset_%s_files' % hda.dataset.id ), alt_name=filename)
                else:
                    file_path = hda.file_name
                rval = open( file_path )

            else:
                display_kwd = kwd.copy()
                if 'key' in display_kwd:
                    del display_kwd["key"]
                rval = hda.datatype.display_data( trans, hda, preview, filename, to_ext, chunk, **display_kwd )

        except Exception as exception:
            log.error( "Error getting display data for dataset (%s) from history (%s): %s",
                       history_content_id, history_id, str( exception ), exc_info=True )
            trans.response.status = 500
            rval = ( "Could not get display data for dataset: " + str( exception ) )

        return rval

     @web.expose_api
    def show_params(self, trans, payload, **kwd):
        """
            show_params( trans, payload )
            * POST /api/datasets/show_params
            Show the parameters used for the job associated with an HDA

            :type   payload: dict
            :param  payload: dictionary structure containing:
                * dataset_id:       the id of dataset

            :rtype:     dict
            :returns:   parameters used for the job associated with an HDA

        """
        dataset_id = payload['dataset_id']
        try:
            hda = trans.sa_session.query(trans.app.model.HistoryDatasetAssociation).get(self.decode_id(dataset_id))
        except ValueError:
            hda = None
        if not hda:
            raise paste.httpexceptions.HTTPRequestRangeNotSatisfiable(
                "Invalid reference dataset id: %s." % escape(str(dataset_id)))

        # Get the associated job, if any. If this hda was copied from another,
        # we need to find the job that created the origial dataset association.
        params_objects = None
        job = None
        tool = None
        upgrade_messages = {}
        has_parameter_errors = False
        inherit_chain = hda.source_dataset_chain
        if inherit_chain:
            job_dataset_association = inherit_chain[-1][0]
        else:
            job_dataset_association = hda
        if job_dataset_association.creating_job_associations:
            job = job_dataset_association.creating_job_associations[0].job
            if job:
                # Get the tool object
                try:
                    # Load the tool
                    toolbox = self.get_toolbox()
                    tool = toolbox.get_tool(job.tool_id)
                    assert tool is not None, 'Requested tool has not been loaded.'
                    # Load parameter objects, if a parameter type has changed, it's possible for the value to no longer be valid
                    try:
                        params_objects = job.get_param_values(trans.app, ignore_errors=False)
                    except:
                        params_objects = job.get_param_values(trans.app, ignore_errors=True)
                        # use different param_objects in the following line, since we want to display original values as much as possible
                        upgrade_messages = tool.check_and_update_param_values(
                            job.get_param_values(trans.app, ignore_errors=True),
                            trans,
                            update_values=False)
                        has_parameter_errors = True
                except:
                    pass

        if job is None:
            return None
        # return trans.show_error_message( "Job information is not available for this dataset." )
        # TODO: we should provide the basic values along with the objects, in order to better handle reporting of old values during upgrade

        encoded_hda_id = trans.security.encode_id( hda.id )
        encoded_history_id = trans.security.encode_id( hda.history_id )

        params = {'tool': tool.name, 'name': hda.file_name,
                  'created': hda.create_time.strftime(trans.app.config.pretty_datetime_format),
                  'filesize': util.nice_size(hda.dataset.file_size), 'dbkey': hda.dbkey, 'format': hda.ext,
                  'tool_version': hda.tool_version,
                  #'tool_standard_output': h.url_for(controller='dataset', action='stdout', dataset_id=encoded_hda_id),
                  #'tool_Standard_errror': h.url_for(controller='dataset', action='stderr', dataset_id=encoded_hda_id),
                  'api_id': encoded_hda_id, 'history_id': encoded_history_id,
                  'job': None}

        if hda.dataset.uuid:
            params['uuid'] =str(hda.dataset.uuid)


        if trans.user_is_admin() or trans.app.config.expose_dataset_path:
            params['full_path'] = hda.file_name

        if job:
            params['job'] = {
                'galaxy_tool_id': job.tool_id,
                'galaxy_tool_version': job.tool_version,
                'tool_exit_code': job.exit_code,
            }

            if job.command_line and trans.user_is_admin():
                params['job']['job_commandline'] = job.command_line

            if job and trans.user_is_admin():

                job_metrics = trans.app.job_metrics
                for metric in job.metrics:
                    metric_title, metric_value = job_metrics.format(metric.plugin, metric.metric_name, metric.metric_value)
                    params['job'][metric.metric_name] = metric_value
        return params
