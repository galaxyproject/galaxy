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

from atlas import commands
from bx.cookbook import doc_optparse
import os
import commands as oscommands
import tempfile

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
        LOADER_ENABLED = True,
        FITTER_ENABLED = True,
        PREDICTOR_ENABLED = True,
        EXPORTER_ENABLED = True,
        LOADER = loader,
        FITTER = fitter,
        PREDICTOR = predictor,
        EXPORTER = exporter,
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
        DATA_FILE=fit[1],
        fit=fit,
        feats=feats,
        )
    commands.execute(conf)

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

def exporter( conf ):
    return commands.bed_exporter(conf)

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
        fit_name, fit_meta = options.fits.split(':')[0], [int(x)-1 for x in options.fits.split(':')[1:]]
        fit_meta = Bunch(chromCol=fit_meta[0], positionCol=fit_meta[1], forwardCol=fit_meta[2], reverseCol=fit_meta[3])
        fit = ( label, fit_name, fit_meta, )
        # split apart the string into nested lists, preserves order
        if options.feats:
            feats = [ ( 
                    feat_label,
                    fname,
                    Bunch(chromCol=int(chromCol)-1, startCol=int(startCol)-1, endCol=int(endCol)-1, 
                         strandCol=int(strandCol)-1, nameCol=int(nameCol)-1),
                    ) 
                 for feat_label, fname, chromCol, startCol, endCol, strandCol, nameCol
                 in ( feat.split(':') for feat in options.feats.split(',') )]
        else:
            feats = []
        data_dir = options.data
        output = options.output
    except:
        doc_optparse.exception()
    
    main(label, fit, feats, data_dir, output)
    