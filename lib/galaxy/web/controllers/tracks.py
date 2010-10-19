"""
Support for constructing and viewing custom "track" browsers within Galaxy.

Track browsers are currently transient -- nothing is stored to the database
when a browser is created. Building a browser consists of selecting a set
of datasets associated with the same dbkey to display. Once selected, jobs
are started to create any necessary indexes in the background, and the user
is redirected to the browser interface, which loads the appropriate datasets.

"""

import re, pkg_resources
pkg_resources.require( "bx-python" )

from bx.seq.twobit import TwoBitFile
from galaxy import model
from galaxy.util.json import to_json_string, from_json_string
from galaxy.web.base.controller import *
from galaxy.web.framework import simplejson
from galaxy.web.framework.helpers import grids
from galaxy.util.bunch import Bunch

from galaxy.visualization.tracks.data_providers import *

# Message strings returned to browser
messages = Bunch(
    PENDING = "pending",
    NO_DATA = "no data",
    NO_CHROMOSOME = "no chromosome",
    NO_CONVERTER = "no converter",
    DATA = "data",
    ERROR = "error"
)

class DatasetSelectionGrid( grids.Grid ):
    class DbKeyColumn( grids.GridColumn ):
        def filter( self, trans, user, query, dbkey ):
            """ Filter by dbkey. """
            # use raw SQL b/c metadata is a BLOB
            dbkey = dbkey.replace("'", "\\'")
            return query.filter( or_( "metadata like '%%\"dbkey\": [\"%s\"]%%'" % dbkey, "metadata like '%%\"dbkey\": \"%s\"%%'" % dbkey ) )
    
    # Grid definition.
    available_tracks = None
    title = "Add Tracks"
    template = "/tracks/add_tracks.mako"
    async_template = "/page/select_items_grid_async.mako"
    model_class = model.HistoryDatasetAssociation
    default_filter = { "deleted" : "False" , "shared" : "All" }
    default_sort_key = "name"
    use_async = True
    use_paging = False
    columns = [
        grids.TextColumn( "Name", key="name", model_class=model.HistoryDatasetAssociation ),
        grids.TextColumn( "Filetype", key="extension", model_class=model.HistoryDatasetAssociation ),
        DbKeyColumn( "Dbkey", key="dbkey", model_class=model.HistoryDatasetAssociation, visible=False )
    ]
    columns.append( 
        grids.MulticolFilterColumn( "Search", cols_to_filter=[ columns[0], columns[1] ], 
        key="free-text-search", visible=False, filterable="standard" )
    )
    
    def build_initial_query( self, trans, **kwargs ):
        return trans.sa_session.query( self.model_class ).join( model.History.table).join( model.Dataset.table )
    def apply_query_filter( self, trans, query, **kwargs ):
        if self.available_tracks is None:
             self.available_tracks = trans.app.datatypes_registry.get_available_tracks()
        return query.filter( model.History.user == trans.user ) \
                    .filter( model.HistoryDatasetAssociation.extension.in_(self.available_tracks) ) \
                    .filter( model.Dataset.state == model.Dataset.states.OK ) \
                    .filter( model.History.deleted == False ) \
                    .filter( model.HistoryDatasetAssociation.deleted == False )
                    
class TracksterSelectionGrid( grids.Grid ):

    # Grid definition.
    title = "Insert into visualization"
    template = "/tracks/add_to_viz.mako"
    async_template = "/page/select_items_grid_async.mako"
    model_class = model.Visualization
    default_filter = { "deleted" : "False" , "shared" : "All" }
    default_sort_key = "title"
    use_async = True
    use_paging = False
    columns = [
        grids.TextColumn( "Title", key="title", model_class=model.Visualization ),
        grids.TextColumn( "Dbkey", key="dbkey", model_class=model.Visualization )
    ]
    columns.append( 
        grids.MulticolFilterColumn( "Search", cols_to_filter=[ columns[0] ], 
        key="free-text-search", visible=False, filterable="standard" )
    )

    def build_initial_query( self, trans, **kwargs ):
        return trans.sa_session.query( self.model_class )
    def apply_query_filter( self, trans, query, **kwargs ):
        return query.filter( self.model_class.user_id == trans.user.id )                    
        
class TracksController( BaseController, UsesVisualization ):
    """
    Controller for track browser interface. Handles building a new browser from
    datasets in the current history, and display of the resulting browser.
    """
    
    available_tracks = None
    available_genomes = None
    
    def _init_references(self, trans):
        avail_genomes = {}
        for line in open( os.path.join( trans.app.config.tool_data_path, "twobit.loc" ) ):
            if line.startswith("#"): continue
            val = line.split()
            if len(val) == 2:
                key, path = val
                avail_genomes[key] = path
        self.available_genomes = avail_genomes
    
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
    @web.require_login()
    def add_track_async(self, trans, id):
        dataset_id = trans.security.decode_id( id )
        
        hda_query = trans.sa_session.query( model.HistoryDatasetAssociation )
        dataset = hda_query.get( dataset_id )
        track_type, _ = dataset.datatype.get_track_type()
        track_data_provider_class = get_data_provider( original_dataset=dataset )
        track_data_provider = track_data_provider_class( original_dataset=dataset )
        
        track = {
            "track_type": track_type,
            "name": dataset.name,
            "dataset_id": dataset.id,
            "prefs": {},
            "filters": track_data_provider.get_filters()
        }
        return track
        
    @web.expose
    @web.require_login()
    def browser(self, trans, id, chrom="", **kwargs):
        """
        Display browser for the datasets listed in `dataset_ids`.
        """
        decoded_id = trans.security.decode_id( id )
        session = trans.sa_session
        vis = session.query( model.Visualization ).get( decoded_id )
        viz_config = self.get_visualization_config( trans, vis )
        
        new_dataset = kwargs.get("dataset_id", None)
        if new_dataset is not None:
            if trans.security.decode_id(new_dataset) in [ d["dataset_id"] for d in viz_config.get("tracks") ]:
                new_dataset = None # Already in browser, so don't add
        return trans.fill_template( 'tracks/browser.mako', config=viz_config, add_dataset=new_dataset )

    @web.json
    def chroms(self, trans, vis_id=None, dbkey=None ):
        """
        Returns a naturally sorted list of chroms/contigs for either a given visualization or a given dbkey.
        """
        def check_int(s):
            if s.isdigit():
                return int(s)
            else:
                return s

        def split_by_number(s):
            return [ check_int(c) for c in re.split('([0-9]+)', s) ]
            
        # Must specify either vis_id or dbkey.
        if not vis_id and not dbkey:
            return trans.show_error_message("No visualization id or dbkey specified.")
            
        # Need to get user and dbkey in order to get chroms data.
        if vis_id:
            # Use user, dbkey from viz.
            visualization = self.get_visualization( trans, vis_id, check_ownership=False, check_accessible=True )
            visualization.config = self.get_visualization_config( trans, visualization )
            vis_user = visualization.user
            vis_dbkey = visualization.dbkey
        else:
            # No vis_id, so visualization is new. User is current user, dbkey must be given.
            vis_user = trans.user
            vis_dbkey = dbkey
        
        # Get chroms data.
        chroms = self._chroms( trans, vis_user, vis_dbkey )
        
        # Check for reference chrom
        if self.available_genomes is None: self._init_references(trans)        
        
        to_sort = [{ 'chrom': chrom, 'len': length } for chrom, length in chroms.iteritems()]
        to_sort.sort(lambda a,b: cmp( split_by_number(a['chrom']), split_by_number(b['chrom']) ))
        return { 'reference': vis_dbkey in self.available_genomes, 'chrom_info': to_sort }

    def _chroms( self, trans, user, dbkey ):
        """
        Helper method that returns chrom lengths for a given user and dbkey.
        """
        len_file = None
        len_ds = None
        # If there is any dataset in the history of extension `len`, this will use it
        if 'dbkeys' in user.preferences:
            user_keys = from_json_string( user.preferences['dbkeys'] )
            if dbkey in user_keys:
                len_file = trans.sa_session.query( trans.app.model.HistoryDatasetAssociation ).get( user_keys[dbkey]['len'] ).file_name
            
        if not len_file:
            len_ds = trans.db_dataset_for( dbkey )
            if not len_ds:
                len_file = os.path.join( trans.app.config.tool_data_path, 'shared','ucsc','chrom', "%s.len" % dbkey )
            else:
                len_file = len_ds.file_name
        manifest = {}
        if not os.path.exists( len_file ):
            return None
        for line in open( len_file ):
            if line.startswith("#"): continue
            line = line.rstrip("\r\n")
            fields = line.split("\t")
            manifest[fields[0]] = int(fields[1])
        return manifest
        
    @web.json
    def reference( self, trans, dbkey, chrom, low, high, **kwargs ):
        if self.available_genomes is None: self._init_references(trans)

        if dbkey not in self.available_genomes: 
            return None
        
        try:
            twobit = TwoBitFile( open(self.available_genomes[dbkey]) )
        except IOError:
            return None
            
        if chrom in twobit:
            return twobit[chrom].get(int(low), int(high))        
        
        return None
        
    @web.json
    def data( self, trans, dataset_id, chrom, low, high, **kwargs ):
        """
        Called by the browser to request a block of data
        """
        dataset = trans.sa_session.query( trans.app.model.HistoryDatasetAssociation ).get( dataset_id )
        if not dataset or not chrom:
            return messages.NO_DATA
        if dataset.state == trans.app.model.Job.states.ERROR:
            return messages.ERROR
        if dataset.state != trans.app.model.Job.states.OK:
            return messages.PENDING
        
        track_type, data_sources = dataset.datatype.get_track_type()
        for source_type, data_source in data_sources.iteritems():
            try:
                converted_dataset = dataset.get_converted_dataset(trans, data_source)
            except ValueError:
                return messages.NO_CONVERTER

            # Need to check states again for the converted version
            if converted_dataset and converted_dataset.state == model.Dataset.states.ERROR:
                job_id = trans.sa_session.query( trans.app.model.JobToOutputDatasetAssociation ).filter_by( dataset_id=converted_dataset.id ).first().job_id
                job = trans.sa_session.query( trans.app.model.Job ).get( job_id )
                return { 'kind': messages.ERROR, 'message': job.stderr }
                
            if not converted_dataset or converted_dataset.state != model.Dataset.states.OK:
                return messages.PENDING
            
        extra_info = None
        if 'index' in data_sources:
            # Have to choose between indexer and data provider
            indexer = get_data_provider( name=data_sources['index'] )( dataset.get_converted_dataset(trans, data_sources['index']), dataset )
            summary = indexer.get_summary( chrom, low, high, **kwargs )
            if summary is not None and kwargs.get("mode", "Auto") == "Auto":
                # Only check for summary if it's Auto mode (which is the default)
                if summary == "no_detail":
                    kwargs["no_detail"] = True # meh
                    extra_info = "no_detail"
                else:
                    frequencies, max_v, avg_v, delta = summary
                    return { 'dataset_type': data_sources['index'], 'data': frequencies, 'max': max_v, 'avg': avg_v, 'delta': delta }
        
        # Get data provider.
        tracks_dataset_type = data_sources['data']
        data_provider_class = get_data_provider( name=tracks_dataset_type, original_dataset=dataset )
        data_provider = data_provider_class( dataset.get_converted_dataset(trans, tracks_dataset_type), dataset )
        
        # Get and return data from data_provider.
        data = data_provider.get_data( chrom, low, high, **kwargs )
        message = None
        if isinstance(data, dict) and 'message' in data:
            message = data['message']
            tracks_dataset_type = data.get( 'data_type', tracks_dataset_type )
            track_data = data['data']
        else:
            track_data = data
        return { 'dataset_type': tracks_dataset_type, 'extra_info': extra_info, 'data': track_data, 'message': message }
        
    
    @web.json
    def save( self, trans, **kwargs ):
        session = trans.sa_session
        vis_id = "undefined"
        if 'vis_id' in kwargs:
            vis_id = kwargs['vis_id'].strip('"')
        dbkey = kwargs['dbkey']
        
        if vis_id == "undefined": # new vis
            vis = model.Visualization()
            vis.user = trans.user
            vis.title = kwargs['vis_title']
            vis.type = "trackster"
            vis.dbkey = dbkey
            session.add( vis )
        else:
            decoded_id = trans.security.decode_id( vis_id )
            vis = session.query( model.Visualization ).get( decoded_id )
        
        decoded_payload = simplejson.loads( kwargs['payload'] )
        vis_rev = model.VisualizationRevision()
        vis_rev.visualization = vis
        vis_rev.title = vis.title
        vis_rev.dbkey = dbkey
        tracks = []
        for track in decoded_payload:
            tracks.append( {    "dataset_id": str(track['dataset_id']),
                                "name": track['name'],
                                "track_type": track['track_type'],
                                "prefs": track['prefs']
            } )
        vis_rev.config = { "tracks": tracks }
        vis.latest_revision = vis_rev
        session.add( vis_rev )
        session.flush()
        return trans.security.encode_id(vis.id)
    
    data_grid = DatasetSelectionGrid()
    tracks_grid = TracksterSelectionGrid()
    
    @web.expose
    @web.require_login( "see all available datasets" )
    def list_datasets( self, trans, **kwargs ):
        """List all datasets that can be added as tracks"""
        
        # Render the list view
        return self.data_grid( trans, **kwargs )
    
    @web.expose
    def list_tracks( self, trans, **kwargs ):
        return self.tracks_grid( trans, **kwargs )
            