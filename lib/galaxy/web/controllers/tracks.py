"""
Support for constructing and viewing custom "track" browsers within Galaxy.

Track browsers are currently transient -- nothing is stored to the database
when a browser is created. Building a browser consists of selecting a set
of datasets associated with the same dbkey to display. Once selected, jobs
are started to create any necessary indexes in the background, and the user
is redirected to the browser interface, which loads the appropriate datasets.

Problems
--------
 - Must have a LEN file, not currently able to infer from data (not sure we
   need to support that, but need to make user defined build support better)
"""

import math, re, logging, glob
log = logging.getLogger(__name__)

from galaxy import model
from galaxy.util.json import to_json_string, from_json_string
from galaxy.web.base.controller import *
from galaxy.web.framework import simplejson
from galaxy.web.framework.helpers import time_ago, grids
from galaxy.util.bunch import Bunch

from galaxy.visualization.tracks.data.array_tree import ArrayTreeDataProvider
from galaxy.visualization.tracks.data.interval_index import IntervalIndexDataProvider
from galaxy.visualization.tracks.data.bam import BamDataProvider
from galaxy.visualization.tracks.data.summary_tree import SummaryTreeDataProvider

# Message strings returned to browser
messages = Bunch(
    PENDING = "pending",
    NO_DATA = "no data",
    NO_CHROMOSOME = "no chromosome",
    NO_CONVERTER = "no converter",
    DATA = "data",
    ERROR = "error"
)

# Mapping from dataset type to a class that can fetch data from a file of that
# type. This also needs to be more flexible.
dataset_type_to_data_provider = {
    "array_tree": ArrayTreeDataProvider,
    "interval_index": IntervalIndexDataProvider,
    "bai": BamDataProvider,
    "summary_tree": SummaryTreeDataProvider
}

class DatasetSelectionGrid( grids.Grid ):
    # Grid definition.
    available_tracks = None
    title = "Add Tracks"
    template = "/tracks/add_tracks.mako"
    async_template = "/page/select_histories_grid_async.mako"
    model_class = model.HistoryDatasetAssociation
    default_filter = { "deleted" : "False" , "shared" : "All" }
    default_sort_key = "name"
    use_async = True
    use_paging = False
    columns = [
        grids.TextColumn( "Name", key="name", model_class=model.HistoryDatasetAssociation ),
        grids.GridColumn( "Filetype", key="extension" ),
    ]
    
    def build_initial_query( self, session ):
        return session.query( self.model_class ).join( model.History.table).join( model.Dataset.table )
    def apply_default_filter( self, trans, query, **kwargs ):
        if self.available_tracks is None:
             self.available_tracks = trans.app.datatypes_registry.get_available_tracks()
        return query.filter( model.History.user == trans.user ) \
                    .filter( model.HistoryDatasetAssociation.extension.in_(self.available_tracks) ) \
                    .filter( model.Dataset.state != "error")
        
class TracksController( BaseController ):
    """
    Controller for track browser interface. Handles building a new browser from
    datasets in the current history, and display of the resulting browser.
    """
    
    available_tracks = None
    len_files = None
    
    @web.expose
    @web.require_login()
    def index( self, trans ):
        config = {}
        
        return trans.fill_template( "tracks/browser.mako", config=config )
    
    @web.expose
    @web.require_login()
    def new_browser( self, trans ):
        if not self.len_files:
            len_files = glob.glob(os.path.join( trans.app.config.tool_data_path, 'shared','ucsc','chrom', "*.len" ))
            self.len_files = [ os.path.split(f)[1].split(".len")[0] for f in len_files ] # get xxx.len
        
        user_keys = {}
        user = trans.get_user()
        if 'dbkeys' in user.preferences:
            user_keys = from_json_string( user.preferences['dbkeys'] )
            
        dbkeys = [ (k, v) for k, v in trans.db_builds if k in self.len_files or k in user_keys ]
        return trans.fill_template( "tracks/new_browser.mako", dbkeys=dbkeys )
            
    @web.json
    @web.require_login()
    def add_track_async(self, trans, id):
        dataset_id = trans.security.decode_id( id )
        
        hda_query = trans.sa_session.query( model.HistoryDatasetAssociation )
        dataset = hda_query.get( dataset_id )
        track_type, _ = dataset.datatype.get_track_type()
        
        track = {
            "track_type": track_type,
            "name": dataset.name,
            "dataset_id": dataset.id,
            "prefs": {},
        }
        return track
        
    @web.expose
    @web.require_login()
    def browser(self, trans, id, chrom=""):
        """
        Display browser for the datasets listed in `dataset_ids`.
        """
        decoded_id = trans.security.decode_id( id )
        session = trans.sa_session
        vis = session.query( model.Visualization ).get( decoded_id )
        latest_revision = vis.latest_revision
        tracks = []
        
        try:
            dbkey = latest_revision.config['dbkey']
        except KeyError:
            dbkey = None
        
        hda_query = session.query( model.HistoryDatasetAssociation )
        for t in vis.latest_revision.config['tracks']:
            dataset_id = t['dataset_id']
            try:
                prefs = t['prefs']
            except KeyError:
                prefs = {}
            dataset = hda_query.get( dataset_id )
            track_type, _ = dataset.datatype.get_track_type()
            tracks.append( {
                "track_type": track_type,
                "name": dataset.name,
                "dataset_id": dataset.id,
                "prefs": simplejson.dumps(prefs),
            } )
            if dbkey is None: dbkey = dataset.dbkey # Hack for backward compat
                
        config = { "title": vis.title, "vis_id": id, "tracks": tracks, "chrom": chrom, "dbkey": dbkey }
        return trans.fill_template( 'tracks/browser.mako', config=config )

    @web.json
    @web.require_login()
    def chroms(self, trans, dbkey=None ):
        """
        Returns a naturally sorted list of chroms/contigs for the given dbkey
        """
        def check_int(s):
            if s.isdigit():
                return int(s)
            else:
                return s

        def split_by_number(s):
            return [ check_int(c) for c in re.split('([0-9]+)', s) ]

        chroms = self._chroms( trans, dbkey )
        to_sort = [{ 'chrom': chrom, 'len': length } for chrom, length in chroms.iteritems()]
        to_sort.sort(lambda a,b: cmp( split_by_number(a['chrom']), split_by_number(b['chrom']) ))
        return to_sort

    def _chroms( self, trans, dbkey ):
        """
        Called by the browser to get a list of valid chromosomes and lengths
        """
        # If there is any dataset in the history of extension `len`, this will use it
        user = trans.get_user()
        if 'dbkeys' in user.preferences:
            user_keys = from_json_string( user.preferences['dbkeys'] )
            if dbkey in user_keys:
                return user_keys[dbkey]['chroms']
            
        db_manifest = trans.db_dataset_for( dbkey )
        if not db_manifest:
            db_manifest = os.path.join( trans.app.config.tool_data_path, 'shared','ucsc','chrom', "%s.len" % dbkey )
        else:
            db_manifest = db_manifest.file_name
        manifest = {}
        if not os.path.exists( db_manifest ):
            return None
        for line in open( db_manifest ):
            if line.startswith("#"): continue
            line = line.rstrip("\r\n")
            fields = line.split("\t")
            manifest[fields[0]] = int(fields[1])
        return manifest

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
                return messages.ERROR
                
            if not converted_dataset or converted_dataset.state != model.Dataset.states.OK:
                return messages.PENDING
            
        extra_info = None
        if 'index' in data_sources:
            # Have to choose between indexer and data provider
            indexer = dataset_type_to_data_provider[data_sources['index']]( dataset.get_converted_dataset(trans, data_sources['index']), dataset )
            summary = indexer.get_summary( chrom, low, high, **kwargs )
            if summary is not None:
                frequencies, max_v, avg_v = summary
                if frequencies != "no_detail":
                    return { "dataset_type": data_sources['index'], "data": frequencies, "max": max_v, "avg": avg_v }
                else:
                    kwargs["no_detail"] = True # meh
                    extra_info = "no_detail"
        
        dataset_type = data_sources['data']
        data_provider = dataset_type_to_data_provider[ dataset_type ]( dataset.get_converted_dataset(trans, dataset_type), dataset )

        data = data_provider.get_data( chrom, low, high, **kwargs )
        return { "dataset_type": dataset_type, "extra_info": extra_info, "data": data }
    
    @web.expose
    def list_tracks( self, trans, hid ):
        return None
    
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
            session.add( vis )
        else:
            decoded_id = trans.security.decode_id( vis_id )
            vis = session.query( model.Visualization ).get( decoded_id )
        
        decoded_payload = simplejson.loads( kwargs['payload'] )
        vis_rev = model.VisualizationRevision()
        vis_rev.visualization = vis
        vis_rev.title = vis.title
        tracks = []
        for track in decoded_payload:
            tracks.append( {    "dataset_id": str(track['dataset_id']),
                                "name": track['name'],
                                "track_type": track['track_type'],
                                "prefs": track['prefs']
            } )
        vis_rev.config = { "dbkey": dbkey, "tracks": tracks }
        vis.latest_revision = vis_rev
        session.add( vis_rev )
        session.flush()
        return trans.security.encode_id(vis.id)
    
    data_grid = DatasetSelectionGrid()
    
    @web.expose
    @web.require_login( "see all available datasets" )
    def list_datasets( self, trans, **kwargs ):
        """List all datasets that can be added as tracks"""
        
        # Render the list view
        return self.data_grid( trans, **kwargs )
