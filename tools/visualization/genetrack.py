#!/usr/bin/env python
"""
Run GeneTrack(atlas) with a faked conf file to generate GeneTrack data files.

usage: %prog
    -l, --label=N: Data label for fit curve/peak plot
    -1, --fits=N/N/N/N/N,...: Data files (interval format) for fit curve/peak plot
    -2, --feats=N:M/N/N/N/N/N,...: Data files (interval format) for features.
    -d, --data=N: Output path for hdf5 and sqlite databases.
    -o, --output=N: Output path for export file.
"""
from galaxy import eggs
import pkg_resources
pkg_resources.require("GeneTrack")
pkg_resources.require("bx-python")

import commands as oscommands
from atlas import commands
from atlas import sql
from bx.cookbook import doc_optparse
from bx.intervals import io

import os
import tempfile
from functools import partial

SIGMA = 20
WIDTH = 5 * SIGMA
EXCLUSION_ZONE = 147    

def main(label, fit, feats, data_dir, output):
    os.mkdir(data_dir)
    conf = DummyConf(
        __name__=label,
        CLOBBER = True,
        DATA_SIZE = 3*10**6,
        MINIMUM_PEAK_SIZE = 0.1,
        LOADER_ENABLED = False,
        FITTER_ENABLED = False,
        PREDICTOR_ENABLED = False,
        EXPORTER_ENABLED = False,
        LOADER = loader,
        FITTER = fitter,
        PREDICTOR = predictor,
        EXPORTER = partial( commands.exporter, formatter=commands.bed_formatter),
        HDF_DATABASE = os.path.join( data_dir, "data.hdf" ),
        SQL_URI = "sqlite:///%s" % os.path.join( data_dir, "features.sqlite" ),
        SIGMA = SIGMA,
        WIDTH = WIDTH,
        DATA_LABEL = label,
        FIT_LABEL = "%s-SIGMA-%d" % ( label,SIGMA ),
        PEAK_LABEL = "PRED-%s-SIGMA-%d" % ( label,SIGMA ),
        EXCLUSION_ZONE = EXCLUSION_ZONE,
        LEFT_SHIFT = EXCLUSION_ZONE / 2,
        RIGHT_SHIFT = EXCLUSION_ZONE / 2,
        EXPORT_LABELS = [ "PRED-%s-SIGMA-%d" % ( label,SIGMA ) ],
        EXPORT_DIR = os.path.join( data_dir ),
        DATA_FILE=fit and fit[1] or None,
        fit=fit,
        feats=feats,
        )
    if fit:
        # Turn on fit processing.
        conf.LOADER_ENABLED = True,
        conf.FITTER_ENABLED = True,
        conf.PREDICTOR_ENABLED = True,
        conf.EXPORTER_ENABLED = True,
    for feat in feats:
        load_feature_files(conf, feats)
    commands.execute(conf)
    outname = "%s.%s.txt" % (conf.__name__, conf.EXPORT_LABELS[0] )
    if os.path.exists( os.path.join(data_dir, outname) ):
        os.rename( os.path.join(data_dir, outname), output)
    
# mod454 seems to be a module without a package.  The necessary funcitons are
# stubbed out here until I'm sure of their final home. INS

def loader( conf ):
    from atlas import hdf
    from mod454.schema import Mod454Schema as Schema
    last_chrom = table = None
    db = hdf.hdf_open( conf.HDF_DATABASE, mode='a', title='HDF database')
    gp = hdf.create_group( db=db, name=conf.DATA_LABEL, desc='data group', clobber=conf.CLOBBER ) 
    fit_meta = conf.fit[2]
    # iterate over the file and insert into table
    for line in open( conf.fit[1], "r" ):
        if line.startswith("chrom"): continue  #Skip possible header
        if line.startswith("#"): continue
        fields = line.rstrip('\r\n').split('\t')
        chrom = fields[fit_meta.chromCol]
        if chrom != last_chrom:
            if table: table.flush()
            table = hdf.create_table( db=db, name=chrom, where=gp, schema=Schema, clobber=False )
            last_chrom = chrom
        try:
            position = int(fields[fit_meta.positionCol])
            forward = float(fields[fit_meta.forwardCol])
            reverse = fit_meta.reverseCol > -1 and float(fields[fit_meta.reverseCol]) or 0.0
            row = ( position, forward, reverse, forward+reverse, )
            table.append( [ row ] )
        except ValueError:
            # Ignore bad lines
            pass
    table.flush()
    db.close()
    
def fitter( conf ):
    from mod454.fitter import fitter as mod454_fitter 
    return mod454_fitter( conf )

def predictor( conf ):
    from mod454.predictor import predictor as mod454_predictor
    return mod454_predictor( conf )

def load_feature_files( conf, feats):
    """
    Loads features from file names
    """
    engine = sql.get_engine( conf.SQL_URI )
    sql.drop_indices(engine)
    conn = engine.connect()
    for label, fname, col_spec in feats:
        label_id = sql.make_label(engine, name=label, clobber=False)
        reader = io.NiceReaderWrapper( open(fname,"r"),
                                       chrom_col=col_spec.chromCol,
                                       start_col=col_spec.startCol,
                                       end_col=col_spec.endCol,
                                       strand_col=col_spec.strandCol,
                                       fix_strand=False )
        values = list()
        for interval in reader:
            print interval
            if not type( interval ) is io.GenomicInterval: continue
            row = {'label_id':label_id, 
                   'name':col_spec.nameCol == -1 and "%s-%s" % (str(interval.start), str(interval.end)) or interval.fields[col_spec.nameCol],
                   'altname':"",
                   'chrom':interval.chrom,
                   'start':interval.start,
                   'end':interval.end,
                   'strand':interval.strand,
                   'value':0,
                   'freetext':""}
            values.append(row)
        insert = sql.feature_table.insert()
        conn.execute( insert, values)
    conn.close()
    sql.create_indices(engine)


class Bunch( object ):
    def __init__(self, **kwargs):
        for key,value in kwargs.items():
            setattr( self, key, value ) 

class DummyConf( Bunch ):
    """
    Fake conf module for genetrack/atlas.
    """
    pass

if __name__ == "__main__":
    options, args = doc_optparse.parse( __doc__ )
    try:
        label = options.label
        if options.fits:
            fit_name, fit_meta = options.fits.split(':')[0], [int(x)-1 for x in options.fits.split(':')[1:]]
            fit_meta = Bunch(chromCol=fit_meta[0], positionCol=fit_meta[1], forwardCol=fit_meta[2], reverseCol=fit_meta[3])
            fit = ( label, fit_name, fit_meta, )
        else:
            fit = []
        # split apart the string into nested lists, preserves order
        if options.feats:
            feats = [ ( 
                    feat_label,
                    fname,
                    Bunch(chromCol=int(chromCol)-1, startCol=int(startCol)-1, endCol=int(endCol)-1, 
                         strandCol=int(strandCol)-1, nameCol=int(nameCol)-1),
                    ) 
                 for feat_label, fname, chromCol, startCol, endCol, strandCol, nameCol
                 in ( feat.split(':') for feat in options.feats.split(',') if len(feat) > 0 )]
        else:
            feats = []
        data_dir = options.data
        output = options.output
    except:
        doc_optparse.exception()
    
    main(label, fit, feats, data_dir, output)
    