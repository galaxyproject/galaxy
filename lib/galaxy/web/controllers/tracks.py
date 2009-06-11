"""
Support for constructing and viewing custom "track" browsers within Galaxy.

Track browsers are currently transient -- nothing is stored to the database
when a browser is created. Building a browser consists of selecting a set
of datasets associated with the same dbkey to display. Once selected, jobs
are started to create any neccesary indexes in the background, and the user
is redirected to the browser interface, which loads the appropriate datasets.

Problems
--------
 - Assumes that the only indexing type in Galaxy is for this particular
   application. Thus, datatypes can only have one indexer, and the presence
   of an indexer results in assuming that datatype can be displayed as a track.

"""

import math

from galaxy.tracks import messages
from galaxy.util.json import to_json_string
from galaxy.web.base.controller import *
from galaxy.web.framework import simplejson

class TracksController( BaseController ):
    """
    Controller for track browser interface. Handles building a new browser from
    datasets in the current history, and display of the resulting browser.
    """
    
    @web.expose
    def index( self, trans ):
        return trans.fill_template( "tracks/index.mako" )
        
    @web.expose
    def new_browser( self, trans, dbkey=None, dataset_ids=None, browse=None ):
        """
        Build a new browser from datasets in the current history. Redirects
        to 'index' once datasets to browse have been selected.
        """
        session = trans.sa_session
        # If the user clicked the submit button explicately, try to build the browser
        if browse and dataset_ids:
            dataset_ids = ",".join( map( str, dataset_ids ) )
            trans.response.send_redirect( web.url_for( controller='tracks', action='browser', chrom="", dataset_ids=dataset_ids ) )
            return
        # Determine the set of all dbkeys that are used in the current history
        dbkeys = [ d.metadata.dbkey for d in trans.get_history().datasets if not d.deleted ]
        dbkey_set = set( dbkeys )
        # If a dbkey argument was not provided, or is no longer valid, default
        # to the first one
        if dbkey is None or dbkey not in dbkey_set:
            dbkey = dbkeys[0]
        # Find all datasets in the current history that are of that dbkey and
        # have an indexer.
        datasets = {}
        for dataset in session.query( model.HistoryDatasetAssociation ).filter_by( deleted=False, history_id=trans.history.id ):
            if dataset.metadata.dbkey == dbkey and trans.app.datatypes_registry.get_indexers_by_datatype( dataset.extension ):
                datasets[dataset.id] = dataset.name
        # Render the template
        return trans.fill_template( "tracks/new_browser.mako", dbkey=dbkey, dbkey_set=dbkey_set, datasets=datasets )

    @web.expose
    def browser(self, trans, dataset_ids, chrom=""):
        """
        Display browser for the datasets listed in `dataset_ids`.
        """
        tracks = []
        dbkey = ""
        for dataset_id in dataset_ids.split( "," ):
            dataset = trans.app.model.HistoryDatasetAssociation.get( dataset_id )
            tracks.append( {
                "type": dataset.datatype.get_track_type(),
                "name": dataset.name,
                "id": dataset.id
            } )
            dbkey = dataset.dbkey
        LEN = self._chroms(trans, dbkey ).get(chrom,0)
        return trans.fill_template( 'tracks/browser.mako', 
                                    dataset_ids=dataset_ids,
                                    tracks=tracks,
                                    chrom=chrom,
                                    dbkey=dbkey,
                                    LEN=LEN )
    
    @web.json
    def chroms(self, trans, dbkey=None ):
        return self._chroms( trans, dbkey )
        
    def _chroms( self, trans, dbkey ):
        """
        Called by the browser to get a list of valid chromosomes and lengths
        """
        db_manifest = trans.db_dataset_for( dbkey )
        if not db_manifest:
            db_manifest = os.path.join( trans.app.config.tool_data_path, 'shared','ucsc','chrom', "%s.len" % dbkey )
        else:
            db_manifest = db_manifest.file_name
        manifest = {}
        if os.path.exists( db_manifest ):
            for line in open( db_manifest ):
                if line.startswith("#"): continue
                line = line.rstrip("\r\n")
                fields = line.split("\t")
                manifest[fields[0]] = int(fields[1])
        else:
            # try to fake a manifest by reading track stores
            datasets = trans.app.model.HistoryDatasetAssociation.filter_by(deleted=False, history_id=trans.history.id).all()
            for dataset in datasets:
                if not dataset.metadata.dbkey == dbkey: continue
                track_store = trans.app.track_store.get( dataset )
                if track_store.exists:
                    try:
                        for chrom, fields in track_store.get_manifest().items():
                            manifest[chrom] = max(manifest.get(chrom, 0), int(fields[0]))
                    except track_store.DoesNotExist:
                        pass
        return manifest

    @web.json
    def data( self, trans, dataset_id, chrom="", low="", high="" ):
        """
        Called by the browser to request a block of data
        """
        dataset = trans.app.model.HistoryDatasetAssociation.get( dataset_id )
        if not dataset: return messages.NO_DATA
        if dataset.state == trans.app.model.Job.states.ERROR:
            return messages.NO_DATA
        if not dataset.state == trans.app.model.Job.states.OK:
            return messages.PENDING
        track_store = trans.app.track_store.get( dataset )
        if not track_store.exists:
            # Test if we can make a track
            indexers = trans.app.datatypes_registry.get_indexers_by_datatype( dataset.extension )
            if indexers:
                tool = indexers[0]   # They are sorted by class chain so use the top one
                # If we can, return pending and launch job
                job = trans.app.model.Job()
                job.session_id = trans.get_galaxy_session().id
                job.history_id = trans.history.id
                job.tool_id = tool.id
                job.tool_version = "1.0.0"
                job.add_input_dataset( "input_dataset", dataset )
                job.add_parameter( "input_dataset", to_json_string( dataset.id ) )
                # This is odd
                # job.add_output_dataset( "input_dataset", dataset )
                # create store path, this is rather unclear?
                track_store.set()
                job.add_parameter( "store_path", to_json_string( track_store.path ) )    
                job.flush()
                trans.app.job_manager.job_queue.put( job.id, tool )
                return messages.PENDING
            else:
                return messages.NO_DATA
        else:
            # Data for that chromosome or resolution does not exist?
            # HACK: we're "pending" because the store exists without a manifest
            try:
                track_store.get_manifest()
            except track_store.DoesNotExist:
                return messages.PENDING
            if chrom and low and high:
                low = math.floor(float(low))
                high = math.ceil(float(high))
                resolution = dataset.datatype.get_track_resolution( dataset, low, high )
                try:
                    data = track_store.get( chrom, resolution )
                except track_store.DoesNotExist:
                    return messages.NO_DATA
                window = dataset.datatype.get_track_window( dataset, data, low, high )
                glob = {"data":window, "type":dataset.datatype.get_track_type()};
                if resolution: glob["resolution"] = resolution
                return window
            else:
                return messages.DATA
