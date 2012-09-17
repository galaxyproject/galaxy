"""
API operations on the contents of a dataset.
"""
import logging, os, string, shutil, urllib, re, socket
from cgi import escape, FieldStorage
from galaxy import util, datatypes, jobs, web, util
from galaxy.web.base.controller import *
from galaxy.util.sanitize_html import sanitize_html
from galaxy.model.orm import *
from galaxy.visualization.data_providers.genome import *
from galaxy.visualization.data_providers.basic import ColumnDataProvider
from galaxy.datatypes.tabular import Vcf
from galaxy.model import NoConverterException, ConverterDependencyException

log = logging.getLogger( __name__ )

class DatasetsController( BaseAPIController, UsesVisualizationMixin ):

    @web.expose_api
    def index( self, trans, **kwd ):
        """
        GET /api/datasets
        Lists datasets.
        """
        pass
        
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
        if data_type == 'state':
            rval = self._dataset_state( trans, dataset )
        elif data_type == 'converted_datasets_state':
            rval = self._converted_datasets_state( trans, dataset, kwd.get( 'chrom', None ) )
        elif data_type == 'data':
            rval = self._data( trans, dataset, **kwd )
        elif data_type == 'features':
            rval = self._search_features( trans, dataset, kwd.get( 'query ' ) )
        elif data_type == 'raw_data':
            rval = self._raw_data( trans, dataset, **kwd )
        elif data_type == 'track_config':
            rval = self.get_new_track_config( trans, dataset )
        else:
            # Default: return dataset as API value.
            try:
                rval = dataset.get_api_value()
            except Exception, e:
                rval = "Error in dataset API at listing contents"
                log.error( rval + ": %s" % str(e) )
                trans.response.status = 500
        return rval

    def _dataset_state( self, trans, dataset, **kwargs ):
        """ Returns state of dataset. """
            
        msg = self.check_dataset_state( trans, dataset )
        if not msg:
            msg = messages.DATA

        return msg
        
    def _converted_datasets_state( self, trans, dataset, chrom=None ):
        """
        Init-like method that returns state of dataset's converted datasets. Returns valid chroms
        for that dataset as well.
        """

        msg = self.check_dataset_state( trans, dataset )
        if msg:
            return msg
            
        # Get datasources and check for messages.
        data_sources = self._get_datasources( trans, dataset )
        messages_list = [ data_source_dict[ 'message' ] for data_source_dict in data_sources.values() ]
        msg = get_highest_priority_msg( messages_list )
        if msg:
            return msg
            
        # NOTE: finding valid chroms is prohibitive for large summary trees and is not currently used by
        # the client.
        valid_chroms = None
        # Check for data in the genome window.
        data_provider_registry = trans.app.data_provider_registry
        if data_sources.get( 'index' ):
            tracks_dataset_type = data_sources['index']['name']
            converted_dataset = dataset.get_converted_dataset( trans, tracks_dataset_type )
            indexer = data_provider_registry.get_data_provider( tracks_dataset_type )( converted_dataset, dataset )
            if not indexer.has_data( chrom ):
                return messages.NO_DATA
            #valid_chroms = indexer.valid_chroms()
        else:
            # Standalone data provider
            standalone_provider = data_provider_registry.get_data_provider( data_sources['data_standalone']['name'] )( dataset )
            kwargs = {"stats": True}
            if not standalone_provider.has_data( chrom ):
                return messages.NO_DATA
            #valid_chroms = standalone_provider.valid_chroms()
            
        # Have data if we get here
        return { "status": messages.DATA, "valid_chroms": valid_chroms }

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
            return messages.NO_DATA
        
        # Dataset check.
        msg = self.check_dataset_state( trans, dataset )
        if msg:
            return msg
            
        # Get datasources and check for messages.
        data_sources = self._get_datasources( trans, dataset )
        messages_list = [ data_source_dict[ 'message' ] for data_source_dict in data_sources.values() ]
        return_message = get_highest_priority_msg( messages_list )
        if return_message:
            return return_message
            
        extra_info = None
        mode = kwargs.get( "mode", "Auto" )
        # Handle histogram mode uniquely for now:
        data_provider_registry = trans.app.data_provider_registry
        if mode == "Coverage":
            # Get summary using minimal cutoffs.
            tracks_dataset_type = data_sources['index']['name']
            converted_dataset = dataset.get_converted_dataset( trans, tracks_dataset_type )
            indexer = data_provider_registry.get_data_provider( tracks_dataset_type )( converted_dataset, dataset )
            summary = indexer.get_data( chrom, low, high, resolution=kwargs[ 'resolution' ], detail_cutoff=0, draw_cutoff=0 )
            if summary == "detail":
                # Use maximum level of detail--2--to get summary data no matter the resolution.
                summary = indexer.get_data( chrom, low, high, resolution=kwargs[ 'resolution' ], level=2, detail_cutoff=0, draw_cutoff=0 )
            frequencies, max_v, avg_v, delta = summary
            return { 'dataset_type': tracks_dataset_type, 'data': frequencies, 'max': max_v, 'avg': avg_v, 'delta': delta }

        if 'index' in data_sources and data_sources['index']['name'] == "summary_tree" and mode == "Auto":
            # Only check for summary_tree if it's Auto mode (which is the default)
            # 
            # Have to choose between indexer and data provider
            tracks_dataset_type = data_sources['index']['name']
            converted_dataset = dataset.get_converted_dataset( trans, tracks_dataset_type )
            indexer = data_provider_registry.get_data_provider( tracks_dataset_type )( converted_dataset, dataset )
            summary = indexer.get_data( chrom, low, high, resolution=kwargs[ 'resolution' ] )
            if summary is None:
                return { 'dataset_type': tracks_dataset_type, 'data': None }
                
            if summary == "draw":
                kwargs["no_detail"] = True # meh
                extra_info = "no_detail"
            elif summary != "detail":
                frequencies, max_v, avg_v, delta = summary
                return { 'dataset_type': tracks_dataset_type, 'data': frequencies, 'max': max_v, 'avg': avg_v, 'delta': delta }
        
        # Get data provider.
        if "data_standalone" in data_sources:
            tracks_dataset_type = data_sources['data_standalone']['name']
            data_provider_class = data_provider_registry.get_data_provider( name=tracks_dataset_type, original_dataset=dataset )
            data_provider = data_provider_class( original_dataset=dataset )
        else:
            tracks_dataset_type = data_sources['data']['name']
            data_provider_class = data_provider_registry.get_data_provider( name=tracks_dataset_type, original_dataset=dataset )
            converted_dataset = dataset.get_converted_dataset( trans, tracks_dataset_type )
            deps = dataset.get_converted_dataset_deps( trans, tracks_dataset_type )
            data_provider = data_provider_class( converted_dataset=converted_dataset, original_dataset=dataset, dependencies=deps )
        
        # Allow max_vals top be data provider set if not passed
        if max_vals is None:
            max_vals = data_provider.get_default_max_vals()

        # Get and return data from data_provider.
        result = data_provider.get_data( chrom, int( low ), int( high ), int( start_val ), int( max_vals ), **kwargs )
        result.update( { 'dataset_type': tracks_dataset_type, 'extra_info': extra_info } )
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
        data = None
        data_provider = trans.app.data_provider_registry.get_data_provider( raw=True, original_dataset=dataset )
        
        if data_provider == ColumnDataProvider:
            #pre: should have column kwargs
            #print 'kwargs:', kwargs
            #TODO??: could default to first two here
            assert 'cols' in kwargs, (
                "ColumnDataProvider needs a 'cols' parameter in the query string" )
            data = data_provider( original_dataset=dataset ).get_data( **kwargs )
            
        else:
            # Default to genomic data.
            # FIXME: need better way to set dataset_type.
            low, high = int( kwargs.get( 'low' ) ), int( kwargs.get( 'high' ) )
            data = data_provider( original_dataset=dataset ).get_data( start=low, end=high, **kwargs )
            data[ 'dataset_type' ] = 'interval_index'
            data[ 'extra_info' ] = None
            if isinstance( dataset.datatype, Vcf ):
                data[ 'dataset_type' ] = 'tabix'
        return data
