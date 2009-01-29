import time, glob, os
from itertools import cycle
import hashlib

from mako import exceptions
from mako.template import Template
from mako.lookup import TemplateLookup
from galaxy.web.base.controller import *

try:
    import pkg_resources
    pkg_resources.require("GeneTrack")
    import atlas
    from atlas import sql
    from atlas import hdf
    from atlas import util as atlas_utils
    from atlas.web import formlib, feature_query, feature_filter
    from atlas.web import label_cache as atlas_label_cache
    from atlas.plotting.const import *
    from atlas.plotting.tracks import prefab
    from atlas.plotting.tracks import chart
    from atlas.plotting import tracks
except Exception, exc:
    raise ControllerUnavailable("GeneTrack could not import a required dependency: %s" % str(exc))

pkg_resources.require( "Paste" )
import paste.httpexceptions

# Database helpers
SHOW_LABEL_LIMIT = 10000

def list_labels(session):
    """
    Returns a list of labels that will be plotted in order.
    """
    labels = sql.Label
    query = session.query(labels).order_by("-id")
    return query

def open_databases( conf ):
    """
    A helper function that returns handles to the hdf and sql databases
    """
    db = hdf.hdf_open( conf.HDF_DATABASE, mode='r' )
    session = sql.get_session( conf.SQL_URI )
    return db, session

def hdf_query(db, name, param, autosize=False ):
    """
    Schema specific hdf query. 
    Note that returns data as columns not rows.
    """
    if not hdf.has_node(db=db, name=name):
        atlas.warn( 'missing label %s' % name )
        return [], [], [], []
    data  = hdf.GroupData( db=db, name=name)
    istart, iend = data.get_indices(label=param.chrom, start=param.start, stop=param.end)
    table = data.get_table(label=param.chrom)
    if autosize:
        # attempts to reduce the number of points
        size = len( table.cols.ix[istart:iend] )
        step = max( [1, size/1200] )
    else:
        step = 1

    ix = table.cols.ix[istart:iend:step].tolist()
    wx = table.cols.wx[istart:iend:step].tolist()
    cx = table.cols.cx[istart:iend:step].tolist()
    ax = table.cols.ax[istart:iend:step].tolist()
    return ix, wx, cx, ax

# Chart helpers
def build_tracks( param, conf, data_label, fit_label, pred_label, strand, show=False ):
    """
    Builds tracks
    """
    # gets all the labels for a fast lookup
    label_cache = atlas_label_cache( conf )       

    # get database handles for hdf and sql
    db, session = open_databases( conf )

    # fetching x and y coordinates for bar and fit (line) for 
    # each strand plus (p), minus (m), all (a) 
    bix, bpy, bmy, bay = hdf_query( db=db, name=data_label, param=param )
    fix, fpy, fmy, fay = hdf_query( db=db, name=fit_label, param=param )

    # close the hdf database
    db.close()

    # get all features within the range
    all = feature_query( session=session,  param=param )

    # draws the barchart and the nucleosome chart below it
    if strand == 'composite':
        bar = prefab.composite_bartrack( fix=fix, fay=fay, bix=bix, bay=bay, param=param)
    else:
        bar = prefab.twostrand_bartrack( fix=fix, fmy=fmy, fpy=fpy, bix=bix, bmy=bmy, bpy=bpy, param=param)
    
    charts = list()
    charts.append( bar )            

    return charts

def feature_chart(param=None, session=None, label=None, label_dict={}, color=cycle( [LIGHT, WHITE] ) ):
    all = feature_filter(feature_query(session=session,  param=param), name=label, kdict=label_dict)
    flipped = []
    for feature in all:
        if feature.strand == "-":
            feature.start, feature.end = feature.end, feature.start
        flipped.append(feature)
    opts  = track_options( 
        xscale=param.xscale, w=param.width, fgColor=PURPLE,
        show_labels=param.show_labels, ylabel=str(label),
        bgColor=color.next()
    )
    return [
       tracks.split_tracks(features=flipped, options=opts, split=param.show_labels, track_type='vector')
    ]

def consolidate_charts( charts, param ):
    # create the multiplot
    opt = chart_options( w=param.width )
    multi = chart.MultiChart(options=opt, charts=charts)
    return multi

# SETUP Track Builders
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

        param = atlas.Param( word=word )
        
        # search for a given 
        try:
            session = sql.get_session( conf.SQL_URI )
        except:
            return trans.fill_template_mako('genetrack/invalid.html', dataset_id=dataset_id)

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
        color = cycle( [LIGHT, WHITE] )
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

        try:
            session = sql.get_session( conf.SQL_URI )
        except:
            return trans.fill_template_mako('genetrack/invalid.html', dataset_id=dataset_id)

        if os.path.exists( conf.HDF_DATABASE ):
            db = hdf.hdf_open( conf.HDF_DATABASE, mode='r' )
            conf.CHROM_FIELDS = [(x,x) for x in hdf.GroupData(db=db, name=conf.LABEL).labels]
            db.close()
        else:
            query = session.execute(sql.select([sql.feature_table.c.chrom]).distinct())
            conf.CHROM_FIELDS = [(x.chrom,x.chrom) for x in query]

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

        param.width  = min( [2000, int(param.img_size)] )
        param.xscale = [ param.start, param.end ] 
        param.show_labels = ( param.end - param.start ) <= SHOW_LABEL_LIMIT    
        
        # get the template and the function used to generate the tracks
        tmpl_name, track_maker  = conf.PLOT_MAPPER[param.plot]
        
        # check against a hash, display an image that already exists if it was previously created.
        hash = hashlib.sha1()
        hash.update(str(dataset_id))
        for key in sorted(kwds.keys()):
            hash.update(str(kwds[key]))
        fname = "%s.png" % hash.hexdigest()
        fpath = os.path.join(conf.IMAGE_DIR, fname)

        charts = []
        param.fname  = fname
        
        # The SHA1 hash should uniquely identify the qs that created the plot...
        if os.path.exists(fpath):
            os.utime(fpath, (time.time(), time.time()))
            return trans.fill_template_mako(tmpl_name, conf=conf, form=form, param=param, dataset_id=dataset_id)
        
        # If the hashed filename doesn't exist, create it.
        if track_maker is not None and os.path.exists( conf.HDF_DATABASE ):
            # generate the fit track
            charts = track_maker( param=param, conf=conf )
            
        for label in list_labels( session ):
            charts.extend( feature_chart(param=param, session=session, label=label.name, label_dict={label.name:label.id}, color=color))

        track_chart = consolidate_charts( charts, param )
        track_chart.save(fname=fpath)

        return trans.fill_template_mako(tmpl_name, conf=conf, form=form, param=param, dataset_id=dataset_id)
