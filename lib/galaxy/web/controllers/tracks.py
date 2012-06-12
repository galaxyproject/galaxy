"""
Support for constructing and viewing custom "track" browsers within Galaxy.
"""

import re, pkg_resources
pkg_resources.require( "bx-python" )

from galaxy import model
from galaxy.util.json import to_json_string, from_json_string
from galaxy.web.base.controller import *
from galaxy.web.controllers.library import LibraryListGrid
from galaxy.web.framework import simplejson
from galaxy.web.framework.helpers import time_ago, grids
from galaxy.util.bunch import Bunch
from galaxy.datatypes.interval import Gff, Bed
from galaxy.model import NoConverterException, ConverterDependencyException
from galaxy.visualization.tracks.data_providers import *
from galaxy.visualization.genomes import decode_dbkey, Genomes
from galaxy.visualization.tracks.visual_analytics import get_tool_def, get_dataset_job


class NameColumn( grids.TextColumn ):
    def get_value( self, trans, grid, history ):
        return history.get_display_name()
    def get_link( self, trans, grid, history ):
        # Provide link to list all datasets in history that have a given dbkey.
        # Right now, only dbkey needs to be passed through, but pass through 
        # all for now since it's cleaner.
        d = dict( action=grid.datasets_action, show_item_checkboxes=True )
        d[ grid.datasets_param ] = trans.security.encode_id( history.id )
        for filter, value in grid.cur_filter_dict.iteritems():
            d[ "f-" + filter ] = value
        return d
        
class DbKeyPlaceholderColumn( grids.GridColumn ):
    """ Placeholder to keep track of dbkey. """
    def filter( self, trans, user, query, dbkey ):
        return query

class HistorySelectionGrid( grids.Grid ):
    """
    Grid enables user to select a history, which is then used to display 
    datasets from the history.
    """
    title = "Add Track: Select History"
    model_class = model.History
    template='/tracks/history_select_grid.mako'
    default_sort_key = "-update_time"
    datasets_action = 'list_history_datasets'
    datasets_param = "f-history"
    columns = [
        NameColumn( "History Name", key="name", filterable="standard" ),
        grids.GridColumn( "Last Updated", key="update_time", format=time_ago, visible=False ),
        DbKeyPlaceholderColumn( "Dbkey", key="dbkey", model_class=model.HistoryDatasetAssociation, visible=False )
    ]
    num_rows_per_page = 10
    use_async = True
    use_paging = True
    def apply_query_filter( self, trans, query, **kwargs ):
        return query.filter_by( user=trans.user, purged=False, deleted=False, importing=False )
        
class LibrarySelectionGrid( LibraryListGrid ):
    """
    Grid enables user to select a Library, which is then used to display 
    datasets from the history.
    """
    title = "Add Track: Select Library"
    template='/tracks/history_select_grid.mako'
    model_class = model.Library
    datasets_action = 'list_library_datasets'
    datasets_param = "f-library"
    columns = [
        NameColumn( "Library Name", key="name", filterable="standard" )
    ]
    num_rows_per_page = 10
    use_async = True
    use_paging = True
        
class DbKeyColumn( grids.GridColumn ):
    """ Column for filtering by and displaying dataset dbkey. """
    def filter( self, trans, user, query, dbkey ):
        """ Filter by dbkey; datasets without a dbkey are returned as well. """
        # use raw SQL b/c metadata is a BLOB
        dbkey_user, dbkey = decode_dbkey( dbkey )
        dbkey = dbkey.replace("'", "\\'")
        return query.filter( or_( \
                                or_( "metadata like '%%\"dbkey\": [\"%s\"]%%'" % dbkey, "metadata like '%%\"dbkey\": \"%s\"%%'" % dbkey ), \
                                or_( "metadata like '%%\"dbkey\": [\"?\"]%%'", "metadata like '%%\"dbkey\": \"?\"%%'" ) \
                                )
                            )
                    
class HistoryColumn( grids.GridColumn ):
    """ Column for filtering by history id. """
    def filter( self, trans, user, query, history_id ):
        return query.filter( model.History.id==trans.security.decode_id(history_id) )

class HistoryDatasetsSelectionGrid( grids.Grid ):
    # Grid definition.
    available_tracks = None
    title = "Add Datasets"
    template = "tracks/history_datasets_select_grid.mako"
    model_class = model.HistoryDatasetAssociation
    default_filter = { "deleted" : "False" , "shared" : "All" }
    default_sort_key = "-hid"
    use_async = True
    use_paging = False
    columns = [
        grids.GridColumn( "Id", key="hid" ),
        grids.TextColumn( "Name", key="name", model_class=model.HistoryDatasetAssociation ),
        grids.TextColumn( "Filetype", key="extension", model_class=model.HistoryDatasetAssociation ),
        HistoryColumn( "History", key="history", visible=False ),
        DbKeyColumn( "Dbkey", key="dbkey", model_class=model.HistoryDatasetAssociation, visible=True, sortable=False )
    ]
    columns.append( 
        grids.MulticolFilterColumn( "Search name and filetype", cols_to_filter=[ columns[1], columns[2] ], 
        key="free-text-search", visible=False, filterable="standard" )
    )
    
    def get_current_item( self, trans, **kwargs ):
        """ 
        Current item for grid is the history being queried. This is a bit 
        of hack since current_item typically means the current item in the grid.
        """
        return model.History.get( trans.security.decode_id( kwargs[ 'f-history' ] ) )
    def build_initial_query( self, trans, **kwargs ):
        return trans.sa_session.query( self.model_class ).join( model.History.table ).join( model.Dataset.table )
    def apply_query_filter( self, trans, query, **kwargs ):
        if self.available_tracks is None:
             self.available_tracks = trans.app.datatypes_registry.get_available_tracks()
        return query.filter( model.HistoryDatasetAssociation.extension.in_(self.available_tracks) ) \
                    .filter( model.Dataset.state == model.Dataset.states.OK ) \
                    .filter( model.HistoryDatasetAssociation.deleted == False ) \
                    .filter( model.HistoryDatasetAssociation.visible == True )
                                     
class TracksterSelectionGrid( grids.Grid ):
    # Grid definition.
    title = "Insert into visualization"
    template = "/tracks/add_to_viz.mako"
    async_template = "/page/select_items_grid_async.mako"
    model_class = model.Visualization
    default_sort_key = "-update_time"
    use_async = True
    use_paging = False
    columns = [
        grids.TextColumn( "Title", key="title", model_class=model.Visualization, filterable="standard" ),
        grids.TextColumn( "Dbkey", key="dbkey", model_class=model.Visualization ),
        grids.GridColumn( "Last Updated", key="update_time", format=time_ago )
    ]

    def build_initial_query( self, trans, **kwargs ):
        return trans.sa_session.query( self.model_class ).filter( self.model_class.deleted == False )
    def apply_query_filter( self, trans, query, **kwargs ):
        return query.filter( self.model_class.user_id == trans.user.id )                    
        
class TracksController( BaseUIController, UsesVisualizationMixin, UsesHistoryDatasetAssociationMixin, SharableMixin ):
    """
    Controller for track browser interface. Handles building a new browser from
    datasets in the current history, and display of the resulting browser.
    """
    
    libraries_grid = LibrarySelectionGrid()
    histories_grid = HistorySelectionGrid()
    history_datasets_grid = HistoryDatasetsSelectionGrid()
    tracks_grid = TracksterSelectionGrid()
            
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
    def add_track_async(self, trans, hda_id=None, ldda_id=None):
        if hda_id:
            hda_ldda = "hda"
            dataset = self.get_dataset( trans, hda_id, check_ownership=False, check_accessible=True )
        elif ldda_id:
            hda_ldda = "ldda"
            dataset = trans.sa_session.query( trans.app.model.LibraryDatasetDatasetAssociation ).get( trans.security.decode_id( ldda_id ) )
        track_type, _ = dataset.datatype.get_track_type()
        track_data_provider_class = get_data_provider( original_dataset=dataset )
        track_data_provider = track_data_provider_class( original_dataset=dataset )
        
        track = {
            "track_type": track_type,
            "name": dataset.name,
            "hda_ldda": hda_ldda,
            "dataset_id": trans.security.encode_id( dataset.id ),
            "prefs": {},
            "filters": { 'filters' : track_data_provider.get_filters() },
            "tool": get_tool_def( trans, dataset ),
            "tool_state": {}
        }
        return track

    @web.json
    def bookmarks_from_dataset( self, trans, hda_id=None, ldda_id=None ):
        if hda_id:
            hda_ldda = "hda"
            dataset = self.get_dataset( trans, hda_id, check_ownership=False, check_accessible=True )
        elif ldda_id:
            hda_ldda = "ldda"
            dataset = trans.sa_session.query( trans.app.model.LibraryDatasetDatasetAssociation ).get( trans.security.decode_id( ldda_id ) )
        rows = []
        if isinstance( dataset.datatype, Bed ):
            data = RawBedDataProvider( original_dataset=dataset ).get_iterator()
            for i, line in enumerate( data ):
                if ( i > 500 ): break
                fields = line.split()
                location = name = "%s:%s-%s" % ( fields[0], fields[1], fields[2] )
                if len( fields ) > 3:
                    name = fields[4]
                rows.append( [location, name] )
        return { 'data': rows }

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
        id = vis_config[ 'id' ]
        title = vis_config[ 'title' ]
        dbkey = vis_config[ 'dbkey' ]
        annotation = vis_config.get( 'annotation', None )
        return self.save_visualization( trans, config, type, id, title, dbkey, annotation )
        
    @web.expose
    @web.require_login()
    def browser(self, trans, id, chrom="", **kwargs):
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
    def chroms( self, trans, dbkey=None, num=None, chrom=None, low=None ):
        return self.app.genomes.chroms( trans, dbkey=dbkey, num=num, chrom=chrom, low=low )
        
    @web.json
    def reference( self, trans, dbkey, chrom, low, high, **kwargs ):
        return self.app.genomes.reference( trans, dbkey, chrom, low, high, **kwargs )
        
    @web.json
    def raw_data( self, trans, dataset_id, chrom, low, high, **kwargs ):
        """
        Uses original (raw) dataset to return data. This method is useful 
        when the dataset is not yet indexed and hence using data would
        be slow because indexes need to be created.
        """
        
        # Dataset check.
        dataset = self.get_dataset( trans, dataset_id, check_ownership=False, check_accessible=True )
        msg = self._check_dataset_state( trans, dataset )
        if msg:
            return msg
            
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
        # TODO: this code is copied from data() -- should refactor.

        # Dataset check.
        dataset = self.get_dataset( trans, dataset_id, check_ownership=False, check_accessible=True )
        msg = self._check_dataset_state( trans, dataset )
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
        msg = self._check_dataset_state( trans, dataset )
        if msg:
            return msg
            
        # Get datasources and check for messages.
        data_sources = self._get_datasources( trans, dataset )
        messages_list = [ data_source_dict[ 'message' ] for data_source_dict in data_sources.values() ]
        msg = _get_highest_priority_msg( messages_list )
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
    def data( self, trans, hda_ldda, dataset_id, chrom, low, high, start_val=0, max_vals=5000, **kwargs ):
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
        msg = self._check_dataset_state( trans, dataset )
        if msg:
            return msg
            
        # Get datasources and check for messages.
        data_sources = self._get_datasources( trans, dataset )
        messages_list = [ data_source_dict[ 'message' ] for data_source_dict in data_sources.values() ]
        return_message = _get_highest_priority_msg( messages_list )
        if return_message:
            return return_message
            
        extra_info = None
        if 'index' in data_sources and data_sources['index']['name'] == "summary_tree" and kwargs.get("mode", "Auto") == "Auto":
            # Only check for summary_tree if it's Auto mode (which is the default)
            # 
            # Have to choose between indexer and data provider
            tracks_dataset_type = data_sources['index']['name']
            converted_dataset = dataset.get_converted_dataset( trans, tracks_dataset_type )
            indexer = get_data_provider( tracks_dataset_type )( converted_dataset, dataset )
            summary = indexer.get_summary( chrom, low, high, resolution=kwargs[ 'resolution' ] )
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
        
        # Get and return data from data_provider.
        result = data_provider.get_data( chrom, low, high, int( start_val ), int( max_vals ), **kwargs )
        result.update( { 'dataset_type': tracks_dataset_type, 'extra_info': extra_info } )
        return result
                
    @web.expose
    @web.require_login( "see all available libraries" )
    def list_libraries( self, trans, **kwargs ):
        """List all libraries that can be used for selecting datasets."""

        # Render the list view
        return self.libraries_grid( trans, **kwargs )

    @web.expose
    @web.require_login( "see a library's datasets that can added to this visualization" )
    def list_library_datasets( self, trans, **kwargs ):
        """List a library's datasets that can be added to a visualization."""
        
        library = trans.sa_session.query( trans.app.model.Library ).get( trans.security.decode_id( kwargs.get('f-library') ) )
        return trans.fill_template( '/tracks/library_datasets_select_grid.mako',
                                    cntrller="library",
                                    use_panels=False,
                                    library=library,
                                    created_ldda_ids='',
                                    hidden_folder_ids='',
                                    show_deleted=False,
                                    comptypes=[],
                                    current_user_roles=trans.get_current_user_roles(),
                                    message='',
                                    status="done" )
        
    @web.expose
    @web.require_login( "see all available histories" )
    def list_histories( self, trans, **kwargs ):
        """List all histories that can be used for selecting datasets."""
        
        # Render the list view
        return self.histories_grid( trans, **kwargs )
        
    @web.expose
    @web.require_login( "see current history's datasets that can added to this visualization" )
    def list_current_history_datasets( self, trans, **kwargs ):
        """ List a history's datasets that can be added to a visualization. """
        
        kwargs[ 'f-history' ] = trans.security.encode_id( trans.get_history().id )
        kwargs[ 'show_item_checkboxes' ] = 'True'
        return self.list_history_datasets( trans, **kwargs )
        
    @web.expose
    @web.require_login( "see a history's datasets that can added to this visualization" )
    def list_history_datasets( self, trans, **kwargs ):
        """List a history's datasets that can be added to a visualization."""

        # Render the list view
        return self.history_datasets_grid( trans, **kwargs )
    
    @web.expose
    @web.require_login( "see all available datasets" )
    def list_datasets( self, trans, **kwargs ):
        """List all datasets that can be added as tracks"""
        
        # Render the list view
        return self.data_grid( trans, **kwargs )
    
    @web.expose
    def list_tracks( self, trans, **kwargs ):
        return self.tracks_grid( trans, **kwargs )
                    
    @web.expose
    @web.require_login( "use Galaxy visualizations", use_panels=True )
    def paramamonster( self, trans, hda_ldda, dataset_id ):
        # Get dataset.
        dataset = self._get_dataset( trans, hda_ldda, dataset_id )
                
        return trans.fill_template_mako( "visualization/paramamonster.mako", dataset=dataset,
                                          tool=self.app.toolbox.tools_by_id[ 'cufflinks' ].to_dict( trans, for_display=True ) )
    
    @web.expose
    @web.require_login( "use Galaxy visualizations", use_panels=True )
    def circster( self, trans, hda_ldda, dataset_id ):
        # Get dataset.
        dataset = self._get_dataset( trans, hda_ldda, dataset_id )

        # Get genome info.
        dbkey = dataset.dbkey
        chroms_info = self.app.genomes.chroms( trans, dbkey=dbkey )
        genome = { 'dbkey': dbkey, 'chroms_info': chroms_info }

        # Get summary tree data for dataset.
        data_sources = self._get_datasources( trans, dataset )
        tracks_dataset_type = data_sources['index']['name']
        converted_dataset = dataset.get_converted_dataset( trans, tracks_dataset_type )
        indexer = get_data_provider( tracks_dataset_type )( converted_dataset, dataset )
        dataset_summary = []
        for chrom_info in chroms_info[ 'chrom_info' ]:
            summary = indexer.get_summary( chrom_info[ 'chrom' ], 0, chrom_info[ 'len' ], level=4 )
            dataset_summary.append( summary )

        return trans.fill_template_mako( "visualization/circster.mako", dataset=dataset, dataset_summary=dataset_summary, genome=genome )
    
    # -----------------
    # Helper methods.
    # -----------------
        
    def _get_datasources( self, trans, dataset ):
        """
        Returns datasources for dataset; if datasources are not available
        due to indexing, indexing is started. Return value is a dictionary
        with entries of type 
        (<datasource_type> : {<datasource_name>, <indexing_message>}).
        """
        track_type, data_sources = dataset.datatype.get_track_type()
        data_sources_dict = {}
        msg = None
        for source_type, data_source in data_sources.iteritems():
            if source_type == "data_standalone":
                # Nothing to do.
                msg = None
            else:
                # Convert.
                msg = self._convert_dataset( trans, dataset, data_source )
            
            # Store msg.
            data_sources_dict[ source_type ] = { "name" : data_source, "message": msg }
        
        return data_sources_dict
                            
    def _get_dataset( self, trans, hda_ldda, dataset_id ):
        """ Returns either HDA or LDDA for hda/ldda and id combination. """
        if hda_ldda == "hda":
            return self.get_dataset( trans, dataset_id, check_ownership=False, check_accessible=True )
        else:
            return trans.sa_session.query( trans.app.model.LibraryDatasetDatasetAssociation ).get( trans.security.decode_id( dataset_id ) )