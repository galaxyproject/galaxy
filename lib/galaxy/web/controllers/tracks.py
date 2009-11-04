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

import math, re, logging
log = logging.getLogger(__name__)

from galaxy.util.json import to_json_string
from galaxy.web.base.controller import *
from galaxy.web.framework import simplejson
from galaxy.util.bunch import Bunch

from galaxy.visualization.tracks.data.array_tree import ArrayTreeDataProvider
from galaxy.visualization.tracks.data.interval_index import IntervalIndexDataProvider

# Message strings returned to browser
messages = Bunch(
    PENDING = "pending",
    NO_DATA = "no data",
    NO_CHROMOSOME = "no chromosome",
    DATA = "data",
    ERROR = "error"
)

# Dataset type required for each track type. This needs to be more flexible,
# there might be multiple types of indexes that suffice for a given track type.
track_type_to_dataset_type = {
    "line": "array_tree",
    "feature": "interval_index"
}

# Mapping from dataset type to a class that can fetch data from a file of that
# type. This also needs to be more flexible.
dataset_type_to_data_provider = {
    "array_tree": ArrayTreeDataProvider,
    "interval_index": IntervalIndexDataProvider
}

# FIXME: hardcoding this for now, but it should be derived from the available
#        converters
browsable_types = ( "wig", "bed" )


class TracksController( BaseController ):
    """
    Controller for track browser interface. Handles building a new browser from
    datasets in the current history, and display of the resulting browser.
    """

    @web.expose
    def index( self, trans ):
        return trans.fill_template( "tracks/index.mako" )

    @web.expose
    @web.require_login()
    def new_browser( self, trans, dbkey=None, dataset_ids=None, browse=None, title=None ):
        """
        Build a new browser from datasets in the current history. Redirects
        to 'browser' once datasets to browse have been selected.
        """
        session = trans.sa_session
        # If the user clicked the submit button explicitly, try to build the browser
        if title and browse and dataset_ids:
            if not isinstance( dataset_ids, list ):
                dataset_ids = [ dataset_ids ]
            # Build config
            tracks = []
            for dataset_id in dataset_ids:
                tracks.append( { "dataset_id": str( dataset_id ) } )
            config = { "tracks": tracks }
            # Build visualization object
            vis = model.Visualization()
            vis.user = trans.user
            vis.title = title
            vis.type = "trackster"
            vis_rev = model.VisualizationRevision()
            vis_rev.visualization = vis
            vis_rev.title = title
            vis_rev.config = config
            vis.latest_revision = vis_rev
            session.add( vis )
            session.add( vis_rev )
            session.flush()
            trans.response.send_redirect( web.url_for( controller='tracks', action='browser', id=trans.security.encode_id( vis.id ) ) )
        else:
            # Determine the set of all dbkeys that are used in the current history
            dbkeys = [ d.metadata.dbkey for d in trans.get_history().datasets if not d.deleted ]
            dbkey_set = set( dbkeys )
            if not dbkey_set:
                return trans.show_error_message( "Current history has no valid datasets to visualize." )

            # If a dbkey argument was not provided, or is no longer valid, default
            # to the first one
            if dbkey is None or dbkey not in dbkey_set:
                dbkey = dbkeys[0]
            # Find all datasets in the current history that are of that dbkey
            # and can be displayed
            datasets = {}
            for dataset in session.query( model.HistoryDatasetAssociation ).filter_by( deleted=False, history_id=trans.history.id ):
                if dataset.metadata.dbkey == dbkey and dataset.extension in browsable_types:
                    datasets[dataset.id] = (dataset.extension, dataset.name)
            # Render the template
            return trans.fill_template( "tracks/new_browser.mako", converters=browsable_types, dbkey=dbkey, dbkey_set=dbkey_set, datasets=datasets )

    @web.expose
    def browser(self, trans, id, chrom=""):
        """
        Display browser for the datasets listed in `dataset_ids`.
        """
        decoded_id = trans.security.decode_id( id )
        session = trans.sa_session
        vis = session.query( model.Visualization ).get( decoded_id )
        tracks = []
        dbkey = ""
        hda_query = session.query( model.HistoryDatasetAssociation )
        for t in vis.latest_revision.config['tracks']:
            dataset_id = t['dataset_id']
            dataset = hda_query.get( dataset_id )
            tracks.append( {
                "type": dataset.datatype.get_track_type(),
                "name": dataset.name,
                "dataset_id": dataset.id
            } )
            dbkey = dataset.dbkey
        chrom_lengths = self._chroms( trans, dbkey )
        if chrom_lengths is None:
            error( "No chromosome lengths file found for '%s'" % dataset.name )
        return trans.fill_template( 'tracks/browser.mako',
                                    #dataset_ids=dataset_ids,
                                    id=id,
                                    tracks=tracks,
                                    chrom=chrom,
                                    dbkey=dbkey,
                                    LEN=chrom_lengths.get(chrom, 0) )

    @web.json
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
    def data( self, trans, dataset_id, track_type, chrom, low, high, **kwargs ):
        """
        Called by the browser to request a block of data
        """
        # Load the requested dataset
        dataset = trans.sa_session.query( trans.app.model.HistoryDatasetAssociation ).get( dataset_id )
        # No dataset for that id
        if not dataset:
            return messages.NO_DATA
        # Dataset is in error state, can't display
        if dataset.state == trans.app.model.Job.states.ERROR:
            return messages.ERROR
        # Dataset is still being generated
        if dataset.state != trans.app.model.Job.states.OK:
            return messages.PENDING
        # Determine what to return based on the type of track being drawn.
        converted_dataset_type = track_type_to_dataset_type[track_type]
        converted_dataset = self.__dataset_as_type( trans, dataset, converted_dataset_type )
        # If at this point we still don't have an `array_tree_dataset`, there
        # is no way we can display this data as an array tree
        if not converted_dataset:
            return messages.ERROR
        # Need to check states again for the converted version
        if converted_dataset.state == model.Dataset.states.ERROR:
            return messages.ERROR
        if converted_dataset.state != model.Dataset.states.OK:
            return messages.PENDING
        # We have a dataset in the right format that is ready to use, wrap in
        # a data provider that knows how to access it
        data_provider = dataset_type_to_data_provider[ converted_dataset_type ]( converted_dataset, dataset )

        # Return stats if we need them
        if 'stats' in kwargs: return data_provider.get_stats( chrom )

        # Get the requested chunk of data
        return data_provider.get_data( chrom, low, high, **kwargs )

    def __dataset_as_type( self, trans, dataset, type ):
        """
        Given a dataset, try to find a way to adapt it to a different type. If the
        dataset is already of that type it is returned, if it can be converted a
        converted dataset (possibly new) is returned, if it cannot be converted,
        None is returned.
        """
        # Already of correct type
        if dataset.extension == type:
            return dataset
        # See if we can convert the dataset
        if type not in dataset.get_converter_types():
            log.debug( "Conversion from '%s' to '%s' not possible", dataset.extension, type )
            return None
        # See if converted dataset already exists
        converted_datasets = [c for c in dataset.get_converted_files_by_type( type ) if c != None]
        if converted_datasets:
            for d in converted_datasets:
                if d.state != 'error':
                    return d
                else:
                    return None
                    
        # Conversion is possible but hasn't been done yet, run converter here
        # FIXME: this is largely duplicated from DefaultToolAction
        assoc = model.ImplicitlyConvertedDatasetAssociation( parent = dataset, file_type = type, metadata_safe = False )
        new_dataset = dataset.datatype.convert_dataset( trans, dataset, type, return_output = True, visible = False ).values()[0]
        new_dataset.hid = dataset.hid # Hrrmmm....
        new_dataset.name = dataset.name
        new_dataset.flush()
        assoc.dataset = new_dataset
        assoc.flush()
        return new_dataset
