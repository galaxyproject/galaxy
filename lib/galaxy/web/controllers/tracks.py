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
from galaxy.visualization.tracks.genomes import decode_dbkey, Genomes
from galaxy.visualization.tracks.visual_analytics import get_tool_def, get_dataset_job

# Message strings returned to browser
messages = Bunch(
    PENDING = "pending",
    NO_DATA = "no data",
    NO_CHROMOSOME = "no chromosome",
    NO_CONVERTER = "no converter",
    NO_TOOL = "no tool",
    DATA = "data",
    ERROR = "error",
    OK = "ok"
)

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
        
class TracksController( BaseUIController, UsesVisualization, UsesHistoryDatasetAssociation, Sharable ):
    """
    Controller for track browser interface. Handles building a new browser from
    datasets in the current history, and display of the resulting browser.
    """
    
    libraries_grid = LibrarySelectionGrid()
    histories_grid = HistorySelectionGrid()
    history_datasets_grid = HistoryDatasetsSelectionGrid()
    tracks_grid = TracksterSelectionGrid()
    
    def __init__(self, app ):
        BaseUIController.__init__( self, app )
        self.genomes = Genomes( self.app )
            
    @web.expose
    @web.require_login()
    def index( self, trans, **kwargs ):
        config = {}
        return trans.fill_template( "tracks/browser.mako", config=config, add_dataset=kwargs.get("dataset_id", None), \
                                        default_dbkey=kwargs.get("default_dbkey", None) )
    
    @web.expose
    @web.require_login()
    def new_browser( self, trans, **kwargs ):
        return trans.fill_template( "tracks/new_browser.mako", dbkeys=self._get_dbkeys( trans ), default_dbkey=kwargs.get("default_dbkey", None) )
            
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
        return self.genomes.chroms( trans, dbkey=dbkey, num=num, chrom=chrom, low=low )
        
    @web.json
    def reference( self, trans, dbkey, chrom, low, high, **kwargs ):
        return self.genomes.reference( trans, dbkey, chrom, low, high, **kwargs )
        
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
        
    @web.json
    def save( self, trans, config, type, id=None, title=None, dbkey=None, annotation=None ):
        return self.save_visualization( trans, from_json_string( config ), type, id, title, dbkey, annotation )
        
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
    def run_tool( self, trans, tool_id, target_dataset_id, **kwargs ):
        """
        Run a tool. This method serves as a general purpose way to run tools asynchronously.
        """
        
        #
        # Set target history (the history that tool will use for outputs) using
        # target dataset. If user owns dataset, put new data in original 
        # dataset's history; if user does not own dataset (and hence is accessing
        # dataset via sharing), put new data in user's current history.
        #
        target_dataset = self.get_dataset( trans, target_dataset_id, check_ownership=False, check_accessible=True )
        if target_dataset.history.user == trans.user:
            target_history = target_dataset.history
        else:
            target_history = trans.get_history( create=True )
        
        # HACK: tools require unencoded parameters but kwargs are typically 
        # encoded, so try decoding all parameter values.
        for key, value in kwargs.items():
            try:
                value = trans.security.decode_id( value )
                kwargs[ key ] = value
            except:
                pass
        
        #        
        # Execute tool.
        #
        tool = trans.app.toolbox.get_tool( tool_id )
        if not tool:
            return messages.NO_TOOL
        
        # HACK: add run button so that tool.handle_input will run tool.
        kwargs['runtool_btn'] = 'Execute'
        params = util.Params( kwargs, sanitize = False )
        template, vars = tool.handle_input( trans, params.__dict__, history=target_history )
        
        # TODO: check for errors and ensure that output dataset is available.
        output_datasets = vars[ 'out_data' ].values()
        return self.add_track_async( trans, output_datasets[0].id )
                
    @web.expose
    def rerun_tool( self, trans, dataset_id, tool_id, chrom=None, low=None, high=None, **kwargs ):
        """
        Rerun a tool to produce a new output dataset that corresponds to a 
        dataset that a user is currently viewing.
        """
        
        #
        # TODO: refactor to use same code as run_tool.
        #        
        
        # Run tool on region if region is specificied.
        run_on_region = False
        if chrom and low and high:
            run_on_region = True
            low, high = int( low ), int( high )
        
        # Dataset check.
        original_dataset = self.get_dataset( trans, dataset_id, check_ownership=False, check_accessible=True )
        msg = self._check_dataset_state( trans, original_dataset )
        if msg:
            return to_json_string( msg )
            
        #
        # Set tool parameters--except non-hidden dataset parameters--using combination of
        # job's previous parameters and incoming parameters. Incoming parameters
        # have priority.
        #
        original_job = get_dataset_job( original_dataset )
        tool = trans.app.toolbox.get_tool( original_job.tool_id )
        if not tool:
            return messages.NO_TOOL
        tool_params = dict( [ ( p.name, p.value ) for p in original_job.parameters ] )
        # TODO: need to handle updates to conditional parameters; conditional 
        # params are stored in dicts (and dicts within dicts).
        tool_params.update( dict( [ ( key, value ) for key, value in kwargs.items() if key in tool.inputs ] ) )
        tool_params = tool.params_from_strings( tool_params, self.app )
        
        #
        # If running tool on region, convert input datasets (create indices) so
        # that can regions of data can be quickly extracted.
        # 
        messages_list = []
        if run_on_region:
            for jida in original_job.input_datasets:
                input_dataset = jida.dataset
                if get_data_provider( original_dataset=input_dataset ):
                    # Can index dataset.
                    track_type, data_sources = input_dataset.datatype.get_track_type()
                    # Convert to datasource that provides 'data' because we need to
                    # extract the original data.
                    data_source = data_sources[ 'data' ]
                    msg = self._convert_dataset( trans, input_dataset, data_source )
                    if msg is not None:
                        messages_list.append( msg )

        # Return any messages generated during conversions.
        return_message = _get_highest_priority_msg( messages_list )
        if return_message:
            return to_json_string( return_message )
            
        #
        # Set target history (the history that tool will use for inputs/outputs).
        # If user owns dataset, put new data in original dataset's history; if 
        # user does not own dataset (and hence is accessing dataset via sharing), 
        # put new data in user's current history.
        #
        if original_dataset.history.user == trans.user:
            target_history = original_dataset.history
        else:
            target_history = trans.get_history( create=True )
        hda_permissions = trans.app.security_agent.history_get_default_permissions( target_history )
        
        def set_param_value( param_dict, param_name, param_value ):
            """
            Set new parameter value in a tool's parameter dictionary.
            """
            
            # Recursive function to set param value.
            def set_value( param_dict, group_name, group_index, param_name, param_value ):
                if group_name in param_dict:
                    param_dict[ group_name ][ group_index ][ param_name ] = param_value
                    return True
                elif param_name in param_dict:
                    param_dict[ param_name ] = param_value
                    return True
                else:
                    # Recursive search.
                    return_val = False
                    for name, value in param_dict.items():
                        if isinstance( value, dict ):
                            return_val = set_value( value, group_name, group_index, param_name, param_value)
                            if return_val:
                                return return_val
                    return False
            
            # Parse parameter name if necessary.
            if param_name.find( "|" ) == -1:
                # Non-grouping parameter.
                group_name = group_index = None
            else:
                # Grouping parameter.
                group, param_name = param_name.split( "|" )
                index = group.rfind( "_" )
                group_name = group[ :index ]
                group_index = int( group[ index + 1: ] )
            
            return set_value( param_dict, group_name, group_index, param_name, param_value )
        
        # Set parameters based tool's trackster config.
        params_set = {}
        for action in tool.trackster_conf.actions:
            success = False
            for joda in original_job.output_datasets:
                if joda.name == action.output_name:
                    set_param_value( tool_params, action.name, joda.dataset )
                    params_set[ action.name ] = True
                    success = True
                    break
                    
            if not success:
                return messages.ERROR
                
        #
        # Set input datasets for tool. If running on region, extract and use subset
        # when possible.
        #
        location = "%s:%i-%i" % ( chrom, low, high )
        for jida in original_job.input_datasets:
            # If param set previously by config actions, do nothing.
            if jida.name in params_set:
                continue
                
            input_dataset = jida.dataset
            if input_dataset is None: #optional dataset and dataset wasn't selected
                tool_params[ jida.name ] = None
            elif run_on_region and hasattr( input_dataset.datatype, 'get_track_type' ):
                # Dataset is indexed and hence a subset can be extracted and used
                # as input.
                
                # Look for subset.
                subset_dataset_association = trans.sa_session.query( trans.app.model.HistoryDatasetAssociationSubset ) \
                                                             .filter_by( hda=input_dataset, location=location ) \
                                                             .first()
                if subset_dataset_association:
                    # Data subset exists.
                    subset_dataset = subset_dataset_association.subset
                else:
                    # Need to create subset.
                    track_type, data_sources = input_dataset.datatype.get_track_type()
                    data_source = data_sources[ 'data' ]
                    converted_dataset = input_dataset.get_converted_dataset( trans, data_source )
                    deps = input_dataset.get_converted_dataset_deps( trans, data_source )
                            
                    # Create new HDA for input dataset's subset.
                    new_dataset = trans.app.model.HistoryDatasetAssociation( extension=input_dataset.ext, \
                                                                             dbkey=input_dataset.dbkey, \
                                                                             create_dataset=True, \
                                                                             sa_session=trans.sa_session,
                                                                             name="Subset [%s] of data %i" % \
                                                                                 ( location, input_dataset.hid ),
                                                                             visible=False )
                    target_history.add_dataset( new_dataset )
                    trans.sa_session.add( new_dataset )
                    trans.app.security_agent.set_all_dataset_permissions( new_dataset.dataset, hda_permissions )
            
                    # Write subset of data to new dataset
                    data_provider_class = get_data_provider( original_dataset=input_dataset )
                    data_provider = data_provider_class( original_dataset=input_dataset, 
                                                         converted_dataset=converted_dataset,
                                                         dependencies=deps )
                    trans.app.object_store.create( new_dataset.dataset )
                    data_provider.write_data_to_file( chrom, low, high, new_dataset.file_name )
            
                    # TODO: (a) size not working; (b) need to set peek.
                    new_dataset.set_size()
                    new_dataset.info = "Data subset for trackster"
                    new_dataset.set_dataset_state( trans.app.model.Dataset.states.OK )
                
                    # Set metadata.
                    # TODO: set meta internally if dataset is small enough?
                    if trans.app.config.set_metadata_externally:
                        trans.app.datatypes_registry.set_external_metadata_tool.tool_action.execute( trans.app.datatypes_registry.set_external_metadata_tool, 
                                                                                                     trans, incoming = { 'input1':new_dataset }, 
                                                                                                     overwrite=False, job_params={ "source" : "trackster" } )
                    else:
                        message = 'Attributes updated'
                        new_dataset.set_meta()
                        new_dataset.datatype.after_setting_metadata( new_dataset )
                        
                    # Add HDA subset association.
                    subset_association = trans.app.model.HistoryDatasetAssociationSubset( hda=input_dataset, subset=new_dataset, location=location )
                    trans.sa_session.add( subset_association )
                    
                    subset_dataset = new_dataset
                    
                trans.sa_session.flush()
                
                # Add dataset to tool's parameters.
                if not set_param_value( tool_params, jida.name, subset_dataset ):
                    return to_json_string( { "error" : True, "message" : "error setting parameter %s" % jida.name } )
        
        #        
        # Execute tool and handle outputs.
        #
        try:
            subset_job, subset_job_outputs = tool.execute( trans, incoming=tool_params, 
                                                           history=target_history, 
                                                           job_params={ "source" : "trackster" } )
        except Exception, e:
            # Lots of things can go wrong when trying to execute tool.
            return to_json_string( { "error" : True, "message" : e.__class__.__name__ + ": " + str(e) } )
        if run_on_region:
            for output in subset_job_outputs.values():
                output.visible = False
            trans.sa_session.flush()
            
        #    
        # Return new track that corresponds to the original dataset.
        #
        output_name = None
        for joda in original_job.output_datasets:
            if joda.dataset == original_dataset:
                output_name = joda.name
                break
        for joda in subset_job.output_datasets:
            if joda.name == output_name:
                output_dataset = joda.dataset
        
        return self.add_track_async( trans, output_dataset.id )
    
    @web.expose
    @web.require_login( "use Galaxy visualizations", use_panels=True )
    def circos( self, trans, hda_ldda, dataset_id ):
        # Get dataset.
        dataset = self._get_dataset( trans, hda_ldda, dataset_id )

        # Get genome info.
        dbkey = dataset.dbkey
        chroms_info = self.genomes.chroms( trans, dbkey=dbkey )
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

        return trans.fill_template_mako( "visualization/circos.mako", dataset=dataset, dataset_summary=dataset_summary, genome=genome )
    
    # -----------------
    # Helper methods.
    # -----------------
        
    def _check_dataset_state( self, trans, dataset ):
        """
        Returns a message if dataset is not ready to be used in visualization.
        """
        if not dataset:
            return messages.NO_DATA
        if dataset.state == trans.app.model.Job.states.ERROR:
            return messages.ERROR
        if dataset.state != trans.app.model.Job.states.OK:
            return messages.PENDING
        return None
        
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
                    
    def _convert_dataset( self, trans, dataset, target_type ):
        """
        Converts a dataset to the target_type and returns a message indicating 
        status of the conversion. None is returned to indicate that dataset
        was converted successfully. 
        """
        
        # Get converted dataset; this will start the conversion if necessary.
        try:
            converted_dataset = dataset.get_converted_dataset( trans, target_type )
        except NoConverterException:
            return messages.NO_CONVERTER
        except ConverterDependencyException, dep_error:
            return { 'kind': messages.ERROR, 'message': dep_error.value }
            
        # Check dataset state and return any messages.
        msg = None
        if converted_dataset and converted_dataset.state == model.Dataset.states.ERROR:
            job_id = trans.sa_session.query( trans.app.model.JobToOutputDatasetAssociation ) \
                        .filter_by( dataset_id=converted_dataset.id ).first().job_id
            job = trans.sa_session.query( trans.app.model.Job ).get( job_id )
            msg = { 'kind': messages.ERROR, 'message': job.stderr }
        elif not converted_dataset or converted_dataset.state != model.Dataset.states.OK:
            msg = messages.PENDING
        
        return msg
        
    def _get_dataset( self, trans, hda_ldda, dataset_id ):
        """ Returns either HDA or LDDA for hda/ldda and id combination. """
        if hda_ldda == "hda":
            return self.get_dataset( trans, dataset_id, check_ownership=False, check_accessible=True )
        else:
            return trans.sa_session.query( trans.app.model.LibraryDatasetDatasetAssociation ).get( trans.security.decode_id( dataset_id ) )
        
        
def _get_highest_priority_msg( message_list ):
    """
    Returns highest priority message from a list of messages.
    """
    return_message = None
    
    # For now, priority is: job error (dict), no converter, pending.
    for message in message_list:
        if message is not None:
            if isinstance(message, dict):
                return_message = message
                break
            elif message == messages.NO_CONVERTER:
                return_message = message
            elif return_message == None and message == messages.PENDING:
                return_message = message
    return return_message
