import time, glob, os

import pkg_resources
pkg_resources.require("GeneTrack")

import atlas
from atlas import sql
from atlas import util as atlas_utils
from atlas.web import formlib
from mako import exceptions
from mako.template import Template
from mako.lookup import TemplateLookup
from galaxy.web.base.controller import *

pkg_resources.require( "Paste" )
import paste.httpexceptions

# SETUP Track Builders
from mod454.trackbuilder import build_tracks
import functools
def twostrand_tracks( param=None, conf=None ):
    return build_tracks( data_label=conf.LABEL, fit_label=conf.FIT_LABEL, pred_label=conf.PRED_LABEL, param=param, conf=conf, strand='twostrand')
def composite_tracks( param=None, conf=None ):
    return build_tracks( data_label=conf.LABEL, fit_label=conf.FIT_LABEL, pred_label=conf.PRED_LABEL, param=param, conf=conf, strand='composite')

class BaseConf( object ):
    """
    Fake web_conf for atlas.
    """
    IMAGE_DIR = "static/genetrack/plots/"
    LEVELS = [str(x) for x in [ 50, 100, 250, 500, 1000, 2500, 5000, 10000, 20000, 50000, 100000, 200000 ]]
    ZOOM_LEVELS = zip(LEVELS, LEVELS)
    PLOT_SETUP = [
        ('comp-id', 'Composite' ,  'genetrack/index.html', composite_tracks ),
        ('two-id' , 'Two Strand',  'genetrack/index.html', twostrand_tracks ),
    ]
    PLOT_CHOICES = [ (id, name) for (id, name, page, func) in PLOT_SETUP ]
    PLOT_MAPPER = dict( [ (id, (page, func)) for (id, name, page, func) in PLOT_SETUP ] )
    
    def __init__(self, **kwds):
        for key,value in kwds.items():
            setattr( self, key, value)
            
class WebRoot(BaseController):   
    @web.expose
    def search(self, trans, word='', dataset_id=None, submit=''):
        """
        Default search page
        """
        data = trans.app.model.HistoryDatasetAssociation.get( dataset_id )
        if not data:
            raise paste.httpexceptions.HTTPRequestRangeNotSatisfiable( "Invalid reference dataset id: %s." % str( dataset_id ) )
        # the main configuration file
        conf = BaseConf(
            TITLE = "<i>%s</i>: %s" % (data.metadata.dbkey, data.metadata.label),
            HDF_DATABASE = os.path.join( data.extra_files_path, data.metadata.hdf ),
            SQL_URI = "sqlite:///%s" % os.path.join( data.extra_files_path, data.metadata.sqlite ),
            LABEL = data.metadata.label,
            FIT_LABEL = "%s-SIGMA-%d" % (data.metadata.label, 20),
            PRED_LABEL = "PRED-%s-SIGMA-%d" % (data.metadata.label, 20),
            )
        from atlas import hdf
        db = hdf.hdf_open( conf.HDF_DATABASE, mode='r' )
        conf.CHROM_FIELDS = [(x,x) for x in hdf.GroupData(db=db, name=conf.LABEL).labels]
        db.close()

        param = atlas.Param( word=word )
        # search with features based on param.feature
        
        # search for a given 
        session = sql.get_session( conf.SQL_URI )

        if param.word:
            def search_query( word, text ):
                query = session.query(sql.Feature).filter( "name LIKE :word or freetext LIKE :text" ).params(word=word, text=text)
                query = list(query[:20])
                return query

            # a little heuristics to match most likely target
            targets = [ 
                (param.word+'%', 'No match'), # match beginning
                ('%'+param.word+'%', 'No match'), # match name anywhere
                ('%'+param.word+'%', '%'+param.word+'%'), # match json anywhere
            ]
            for word, text in targets:
                query = search_query( word=word, text=text)
                if query:
                    break
        else:
            query = []

        return trans.fill_template_mako('genetrack/search.html', param=param, query=query, dataset_id=dataset_id)

    @web.expose
    def index(self, trans, dataset_id=None, **kwds):
        """
        Main request handler
        """
        data = trans.app.model.HistoryDatasetAssociation.get( dataset_id )
        if not data:
            raise paste.httpexceptions.HTTPRequestRangeNotSatisfiable( "Invalid reference dataset id: %s." % str( dataset_id ) )
        # the main configuration file
        conf = BaseConf(
            TITLE = "<i>%s</i>: %s" % (data.metadata.dbkey, data.metadata.label),
            HDF_DATABASE = os.path.join( data.extra_files_path, data.metadata.hdf ),
            SQL_URI = "sqlite:///%s" % os.path.join( data.extra_files_path, data.metadata.sqlite ),
            LABEL = data.metadata.label,
            FIT_LABEL = "%s-SIGMA-%d" % (data.metadata.label, 20),
            PRED_LABEL = "PRED-%s-SIGMA-%d" % (data.metadata.label, 20),
            )
        from atlas import hdf
        db = hdf.hdf_open( conf.HDF_DATABASE, mode='r' )
        conf.CHROM_FIELDS = [(x,x) for x in hdf.GroupData(db=db, name=conf.LABEL).labels]
        db.close()

        # generate a new form based on the configuration
        form = formlib.main_form( conf )
        
        # clear the tempdir every once in a while
        atlas_utils.clear_tempdir( dir=conf.IMAGE_DIR, days=1, chance=10)

        incoming = form.defaults()
        incoming.update( kwds )
        
        # manage the zoom and pan requests
        incoming = formlib.zoom_change( kdict=incoming, levels=conf.LEVELS)
        incoming = formlib.pan_view( kdict=incoming )
        
        # process the form
        param = atlas.Param( **incoming )
        form.process( incoming )

        if kwds and form.isSuccessful():
            # adds the sucessfull parameters
            param.update( form.values() )

        # if it was a search word not a number go to search page
        try:
            center = int( param.feature )
        except ValueError:
            # go and search for these
            return trans.response.send_redirect( web.url_for( controller='genetrack', action='search', word=param.feature, dataset_id=dataset_id ) )

        # keep image at a sane size
        param.width  = min( [2000, int(param.img_size)] )
        
        # get the template and the function used to generate the tracks
        tmpl_name, track_maker  = conf.PLOT_MAPPER[param.plot]
        
        if track_maker is not None:
            # generate the name that the image will be stored at
            fname, fpath = atlas_utils.make_tempfile( dir=conf.IMAGE_DIR, suffix='.png')
            param.fname  = fname

            # generate the track
            track_chart = track_maker( param=param, conf=conf )
            track_chart.save(fname=fpath)
        
        return trans.fill_template_mako(tmpl_name, conf=conf, form=form, param=param, dataset_id=dataset_id)


