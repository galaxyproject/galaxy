"""
Support for constructing and viewing custom "track" browsers within Galaxy.
"""

import re, pkg_resources
pkg_resources.require( "bx-python" )

from galaxy import model
from galaxy.util.json import to_json_string, from_json_string
from galaxy.web.base.controller import *
from galaxy.web.framework import simplejson
from galaxy.web.framework.helpers import time_ago, grids
from galaxy.util.bunch import Bunch
from galaxy.datatypes.interval import Gff, Bed
from galaxy.model import NoConverterException, ConverterDependencyException
from galaxy.visualization.genome.data_providers import *
from galaxy.visualization.genomes import decode_dbkey, Genomes
from galaxy.visualization.genome.visual_analytics import get_dataset_job                    
        
class TracksController( BaseUIController, UsesVisualizationMixin, SharableMixin ):
    """
    Controller for track browser interface. Handles building a new browser from
    datasets in the current history, and display of the resulting browser.
    """
            
    @web.expose
    @web.require_login()
    def index( self, trans, **kwargs ):
        config = {}
        return trans.fill_template( "tracks/browser.mako", config=config, add_dataset=kwargs.get("dataset_id", None), \
                                        default_dbkey=kwargs.get("default_dbkey", None) )
    
    @web.expose
    @web.require_login()
    def new_browser( self, trans, **kwargs ):
        return trans.fill_template( "tracks/new_browser.mako", dbkeys=trans.app.genomes.get_dbkeys_with_chrom_info( trans ), default_dbkey=kwargs.get("default_dbkey", None) )

    @web.json
    def save( self, trans, vis_json ):
        """
        Save a visualization; if visualization does not have an ID, a new 
        visualization is created. Returns JSON of visualization.
        """
        
        # TODO: Need from_dict to convert json to Visualization object.
        vis_config = from_json_string( vis_json )
        config = {
            'view': vis_config[ 'datasets' ],
            'bookmarks': vis_config[ 'bookmarks' ],
            'viewport': vis_config[ 'viewport' ]
        }
        type = vis_config[ 'type' ]
        id = vis_config.get( 'id', None )
        title = vis_config[ 'title' ]
        dbkey = vis_config[ 'dbkey' ]
        annotation = vis_config.get( 'annotation', None )
        return self.save_visualization( trans, config, type, id, title, dbkey, annotation )
        
    @web.expose
    @web.require_login()
    def browser(self, trans, id, **kwargs):
        """
        Display browser for the visualization denoted by id and add the datasets listed in `dataset_ids`.
        """
        vis = self.get_visualization( trans, id, check_ownership=False, check_accessible=True )
        viz_config = self.get_visualization_config( trans, vis )
        
        new_dataset = kwargs.get("dataset_id", None)
        if new_dataset is not None:
            if trans.security.decode_id(new_dataset) in [ d["dataset_id"] for d in viz_config.get("tracks") ]:
                new_dataset = None # Already in browser, so don't add
        return trans.fill_template( 'tracks/browser.mako', config=viz_config, add_dataset=new_dataset )
        
    @web.json
    def raw_data( self, trans, dataset_id, chrom, low, high, **kwargs ):
        """
        Uses original (raw) dataset to return data. This method is useful 
        when the dataset is not yet indexed and hence using data would
        be slow because indexes need to be created.
        """
        
        # Dataset check.
        dataset = self.get_dataset( trans, dataset_id, check_ownership=False, check_accessible=True )
        msg = self.check_dataset_state( trans, dataset )
        if msg:
            return msg

        low, high = int( low ), int( high )
            
        # Return data.
        data = None
        # TODO: for raw data requests, map dataset type to provider using dict in data_providers.py
        if isinstance( dataset.datatype, Gff ):
            data = RawGFFDataProvider( original_dataset=dataset ).get_data( chrom, low, high, **kwargs )
            data[ 'dataset_type' ] = 'interval_index'
            data[ 'extra_info' ] = None
        elif isinstance( dataset.datatype, Bed ):
            data = RawBedDataProvider( original_dataset=dataset ).get_data( chrom, low, high, **kwargs )
            data[ 'dataset_type' ] = 'interval_index'
            data[ 'extra_info' ] = None
        elif isinstance( dataset.datatype, Vcf ):
            data = RawVcfDataProvider( original_dataset=dataset ).get_data( chrom, low, high, **kwargs )
            data[ 'dataset_type' ] = 'tabix'
            data[ 'extra_info' ] = None
        return data
        
    @web.json
    def dataset_state( self, trans, dataset_id, **kwargs ):
        """ Returns state of dataset. """
        
        dataset = self.get_dataset( trans, dataset_id, check_ownership=False, check_accessible=True )
        msg = self.check_dataset_state( trans, dataset )
        if not msg:
            msg = messages.DATA

        return msg
        
    @web.json
    def converted_datasets_state( self, trans, hda_ldda, dataset_id, chrom=None ):
        """
        Init-like method that returns state of dataset's converted datasets. Returns valid chroms
        for that dataset as well.
        """
        # TODO: this code is copied from data() -- should refactor.
        
        # Dataset check.
        if hda_ldda == "hda":
            dataset = self.get_dataset( trans, dataset_id, check_ownership=False, check_accessible=True )
        else:
            dataset = trans.sa_session.query( trans.app.model.LibraryDatasetDatasetAssociation ).get( trans.security.decode_id( dataset_id ) )
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
        if data_sources.get( 'index' ):
            tracks_dataset_type = data_sources['index']['name']
            converted_dataset = dataset.get_converted_dataset( trans, tracks_dataset_type )
            indexer = get_data_provider( tracks_dataset_type )( converted_dataset, dataset )
            if not indexer.has_data( chrom ):
                return messages.NO_DATA
            #valid_chroms = indexer.valid_chroms()
        else:
            # Standalone data provider
            standalone_provider = get_data_provider( data_sources['data_standalone']['name'] )( dataset )
            kwargs = {"stats": True}
            if not standalone_provider.has_data( chrom ):
                return messages.NO_DATA
            #valid_chroms = standalone_provider.valid_chroms()
            
        # Have data if we get here
        return { "status": messages.DATA, "valid_chroms": valid_chroms }

    @web.json
    def search_features( self, trans, hda_ldda, dataset_id, query ):
        """
        Returns features, locations in dataset that match query. Format is a 
        list of features; each feature is a list itself: [name, location]
        """
        dataset = self.get_hda_or_ldda( trans, hda_ldda, dataset_id )
        if dataset.can_convert_to( "fli" ):
            converted_dataset = dataset.get_converted_dataset( trans, "fli" )
            if converted_dataset:
                data_provider = FeatureLocationIndexDataProvider( converted_dataset=converted_dataset )
                if data_provider:
                    return data_provider.get_data( query )
        
        return []
        
    @web.json
    def data( self, trans, hda_ldda, dataset_id, chrom, low, high, start_val=0, max_vals=None, **kwargs ):
        """
        Provides a block of data from a dataset.
        """
    
        # Parameter check.
        if not chrom:
            return messages.NO_DATA
        
        # Dataset check.
        if hda_ldda == "hda":
            dataset = self.get_dataset( trans, dataset_id, check_ownership=False, check_accessible=True )
        else:
            dataset = trans.sa_session.query( trans.app.model.LibraryDatasetDatasetAssociation ).get( trans.security.decode_id( dataset_id ) )
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
        if mode == "Coverage":
            # Get summary using minimal cutoffs.
            tracks_dataset_type = data_sources['index']['name']
            converted_dataset = dataset.get_converted_dataset( trans, tracks_dataset_type )
            indexer = get_data_provider( tracks_dataset_type )( converted_dataset, dataset )
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
            indexer = get_data_provider( tracks_dataset_type )( converted_dataset, dataset )
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
            data_provider_class = get_data_provider( name=tracks_dataset_type, original_dataset=dataset )
            data_provider = data_provider_class( original_dataset=dataset )
        else:
            tracks_dataset_type = data_sources['data']['name']
            data_provider_class = get_data_provider( name=tracks_dataset_type, original_dataset=dataset )
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
