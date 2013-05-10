"""
API operations on the contents of a dataset.
"""
from galaxy import web
from galaxy.visualization.data_providers.genome import FeatureLocationIndexDataProvider
from galaxy.web.base.controller import BaseAPIController, UsesVisualizationMixin, UsesHistoryDatasetAssociationMixin
from galaxy.web.base.controller import UsesHistoryMixin
from galaxy.web.framework.helpers import is_true

import logging
log = logging.getLogger( __name__ )

class DatasetsController( BaseAPIController, UsesVisualizationMixin, UsesHistoryMixin,
                          UsesHistoryDatasetAssociationMixin ):

    @web.expose_api
    def index( self, trans, **kwd ):
        """
        GET /api/datasets
        Lists datasets.
        """
        trans.response.status = 501
        return 'not implemented'
        
    @web.expose_api
    def show( self, trans, id, hda_ldda='hda', data_type=None, **kwd ):
        """
        GET /api/datasets/{encoded_dataset_id}
        Displays information about and/or content of a dataset.
        """
        # Get dataset.
        try:
            dataset = self.get_hda_or_ldda( trans, hda_ldda=hda_ldda, dataset_id=id )
        except Exception, e:
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
                rval = self._raw_data( trans, dataset, **kwd )
            elif data_type == 'track_config':
                rval = self.get_new_track_config( trans, dataset )
            elif data_type == 'genome_data':
                rval = self._get_genome_data( trans, dataset, kwd.get('dbkey', None) )
            else:
                # Default: return dataset as dict.
                if hda_ldda == 'hda':
                    rval = self.get_hda_dict( trans, dataset )
                    # add these to match api/history_contents.py, show
                    rval[ 'display_types' ] = self.get_old_display_applications( trans, dataset )
                    rval[ 'display_apps' ] = self.get_display_apps( trans, dataset )
                else:
                    rval = dataset.get_api_value()
                
        except Exception, e:
            rval = "Error in dataset API at listing contents: " + str( e )
            log.error( rval + ": %s" % str(e), exc_info=True )
            trans.response.status = 500
        return rval

    def _dataset_state( self, trans, dataset, **kwargs ):
        """
        Returns state of dataset.
        """
        msg = self.check_dataset_state( trans, dataset )
        if not msg:
            msg = dataset.conversion_messages.DATA

        return msg
        
    def _converted_datasets_state( self, trans, dataset, chrom=None, retry=False ):
        """
        Init-like method that returns state of dataset's converted datasets. 
        Returns valid chroms for that dataset as well.
        """
        msg = self.check_dataset_state( trans, dataset )
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
            data_provider_registry = trans.app.data_provider_registry
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
        msg = self.check_dataset_state( trans, dataset )
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
        # Handle histogram mode uniquely for now:
        data_provider_registry = trans.app.data_provider_registry
        if mode == "Coverage":
            # Get summary using minimal cutoffs.
            indexer = data_provider_registry.get_data_provider( trans, original_dataset=dataset, source='index' )
            summary = indexer.get_data( chrom, low, high, detail_cutoff=0, draw_cutoff=0, **kwargs )
            if summary == "detail":
                # Use maximum level of detail--2--to get summary data no matter the resolution.
                summary = indexer.get_data( chrom, low, high, resolution=kwargs[ 'resolution' ],
                                            level=2, detail_cutoff=0, draw_cutoff=0 )
            return summary

        if 'index' in data_sources and data_sources['index']['name'] == "summary_tree" and mode == "Auto":
            # Only check for summary_tree if it's Auto mode (which is the default)
            # 
            # Have to choose between indexer and data provider
            indexer = data_provider_registry.get_data_provider( trans, original_dataset=dataset, source='index' )
            summary = indexer.get_data( chrom, low, high, resolution=kwargs[ 'resolution' ] )
            if summary is None:
                return { 'dataset_type': indexer.dataset_type, 'data': None }
                
            if summary == "draw":
                kwargs["no_detail"] = True # meh
                extra_info = "no_detail"
            elif summary != "detail":
                return summary
        
        # Get data provider.
        data_provider = data_provider_registry.get_data_provider( trans, original_dataset=dataset, source='data' )
        
        # Allow max_vals top be data provider set if not passed
        if max_vals is None:
            max_vals = data_provider.get_default_max_vals()

        # Get reference sequence for region; this is used by providers for aligned reads.
        ref_seq = None
        if dataset.dbkey:
            data_dict = self.app.genomes.reference( trans, dbkey=dataset.dbkey, chrom=chrom, low=low, high=high )
            if data_dict:
                ref_seq = data_dict[ 'data' ]

        # Get and return data from data_provider.
        result = data_provider.get_data( chrom, int( low ), int( high ), int( start_val ), int( max_vals ), 
                                         ref_seq=ref_seq, **kwargs )
        result.update( { 'dataset_type': data_provider.dataset_type, 'extra_info': extra_info } )
        return result

    def _raw_data( self, trans, dataset, **kwargs ):
        """
        Uses original (raw) dataset to return data. This method is useful 
        when the dataset is not yet indexed and hence using data would
        be slow because indexes need to be created.
        """
        # Dataset check.
        msg = self.check_dataset_state( trans, dataset )
        if msg:
            return msg
    
        # Return data.
        data_provider = trans.app.data_provider_registry.get_data_provider( trans, raw=True, original_dataset=dataset )
        data = data_provider.get_data( **kwargs )

        return data

    @web.expose_api_raw
    def display( self, trans, history_content_id, history_id,
                 preview=False, filename=None, to_ext=None, chunk=None, **kwd ):
        """
        GET /api/histories/{encoded_history_id}/contents/{encoded_content_id}/display
        Displays history content (dataset).
        """
        # Huge amount of code overlap with lib/galaxy/webapps/galaxy/api/history_content:show here.
        rval = ''
        try:
            # for anon users:
            #TODO: check login_required?
            #TODO: this isn't actually most_recently_used (as defined in histories)
            if( ( trans.user == None )
            and ( history_id == trans.security.encode_id( trans.history.id ) ) ):
                history = trans.history
                #TODO: dataset/hda by id (from history) OR check_ownership for anon user
                hda = self.get_history_dataset_association( trans, history, history_content_id,
                    check_ownership=False, check_accessible=True )

            else:
                history = self.get_history( trans, history_id,
                    check_ownership=True, check_accessible=True, deleted=False )
                hda = self.get_history_dataset_association( trans, history, history_content_id,
                    check_ownership=True, check_accessible=True )

            rval = hda.datatype.display_data( trans, hda, preview, filename, to_ext, chunk, **kwd )

        except Exception, exception:
            log.error( "Error getting display data for dataset (%s) from history (%s): %s",
                       history_content_id, history_id, str( exception ), exc_info=True )
            trans.response.status = 500
            rval = ( "Could not get display data for dataset: " + str( exception ) )

        return rval
