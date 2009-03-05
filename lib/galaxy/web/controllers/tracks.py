from mako import exceptions
from mako.template import Template
from mako.lookup import TemplateLookup
from galaxy.web.base.controller import *
from galaxy.web.framework import simplejson
from galaxy import web
from galaxy.tracks import messages
import mimeparse
from galaxy.util.json import to_json_string

class MultiResponse(object):
    """
    Shamelessly ripped off of a django snippet.
    """
    def __init__(self, handlers):
        self.handlers = handlers

    def __call__(self, view_func):
        def wrapper(that, trans, *args, **kwargs):
            data_resource = view_func(that, trans, *args, **kwargs)
            content_type = mimeparse.best_match(self.handlers.keys(),
                                                trans.request.environ['HTTP_ACCEPT'])
            response = self.handlers[content_type](data_resource, trans)
            trans.response.headers['Content-Type'] = "%s" % content_type
            return response
        return wrapper

    @classmethod
    def JSON( cls, data_resource, trans ):
        return simplejson.dumps( data_resource )
    
    class XML( object ):
        def __call__(self, data_resource, trans ):
            raise NotImplementedError( "XML MultiResponse handler is not implemented." )

    class AMF( object ):
        def __call__(self, data_resource, trans ):
            raise NotImplementedError( "XML MultiResponse handler is not implemented." )

    class HTML( object ):
        def __init__(self, template ):
            self.template = template

        def __call__(self, data_resource, trans ):
            return trans.fill_template( self.template, **data_resource )

    class DEBUG( HTML ):
        def __call__(self, data_resource, trans ):
            return trans.fill_template( self.template, data_resource=data_resource)

class WebRoot( BaseController ):

    @web.expose
    @MultiResponse( {'text/html':MultiResponse.JSON,
                    'text/javascript':MultiResponse.JSON} )
    def dbkeys(self, trans ):
        return list(set([x.metadata.dbkey for x in trans.get_history().datasets if not x.deleted]))
    
    @web.expose
    @MultiResponse( {'text/html':MultiResponse.JSON,
                    'text/javascript':MultiResponse.JSON} )
    def chroms(self, trans, dbkey ):
        db_manifest = os.path.join( trans.app.config.tool_data_path, 'shared','ucsc','chrom', "%s.len" % dbkey )
        manifest = {}
        if os.path.exists( db_manifest ):
            for line in open( db_manifest ):
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

    @web.expose
    @MultiResponse( {'text/html':MultiResponse.JSON,
                    'text/javascript':MultiResponse.JSON} )
    def list(self, trans, dbkey ):
        datasets = trans.app.model.HistoryDatasetAssociation.filter_by(deleted=False, history_id=trans.history.id).all()
        dataset_list = {}
        for dataset in datasets:
            if dataset.metadata.dbkey == dbkey and trans.app.datatypes_registry.get_indexers_by_datatype( dataset.extension ):
                dataset_list[dataset.id] = dataset.name
        return dataset_list

    @web.expose
    @MultiResponse( {'text/html':MultiResponse.JSON,
                    'text/javascript':MultiResponse.JSON} )
    def data(self, trans, dataset_id, chrom="", start="", end=""):
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
                job.add_output_dataset( "input_dataset", dataset )
                # create store path, this is rather unclear?
                track_store.set()
                job.add_parameter( "store_path", to_json_string( track_store.path ) )    
                job.flush()
                trans.app.job_manager.job_queue.put( job.id, tool )
                return messages.PENDING
            else:
                return messages.NO_DATA
        else:
            if chrom and start and end:
                resolution = dataset.datatype.get_track_resolution( dataset, int(start), int(end ) )
                data = track_store.get( chrom, resolution )
                window = dataset.datatype.get_track_window( dataset, data, int(start), int(end) )
                return window
            else:
                return messages.DATA

    @web.expose
    def index(self, trans, **kwargs):
        return trans.fill_template( '/tracks/index.mako' )
