# runs after the job (and after the default post-filter)
import os
from galaxy import eggs
from galaxy import jobs
from galaxy.tools.parameters import DataToolParameter

from galaxy.jobs.handler import JOB_ERROR

# Older py compatibility
try:
    set()
except:
    from sets import Set as set

#def exec_before_process(app, inp_data, out_data, param_dict, tool=None):
#    """Sets the name of the data"""
#    dbkeys = sets.Set( [data.dbkey for data in inp_data.values() ] ) 
#    if len(dbkeys) != 1:
#        raise Exception, '<p><font color="yellow">Both Queries must be from the same genome build</font></p>'

def validate_input( trans, error_map, param_values, page_param_map ):
    dbkeys = set()
    data_param_names = set()
    data_params = 0
    for name, param in page_param_map.iteritems():
        if isinstance( param, DataToolParameter ):
            # for each dataset parameter
            if param_values.get(name, None) != None:
                dbkeys.add( param_values[name].dbkey )
                data_params += 1
                # check meta data
                try:
                    param = param_values[name]
                    if isinstance( param.datatype, trans.app.datatypes_registry.get_datatype_by_extension( 'gff' ).__class__ ):
                        # TODO: currently cannot validate GFF inputs b/c they are not derived from interval.
                        pass
                    else: # Validate interval datatype.
                        startCol = int( param.metadata.startCol )
                        endCol = int( param.metadata.endCol )
                        chromCol = int( param.metadata.chromCol )
                        if param.metadata.strandCol is not None:
                            strandCol = int ( param.metadata.strandCol )
                        else:
                            strandCol = 0
                except:
                    error_msg = "The attributes of this dataset are not properly set. " + \
                    "Click the pencil icon in the history item to set the chrom, start, end and strand columns."
                    error_map[name] = error_msg
            data_param_names.add( name )
    if len( dbkeys ) > 1:
        for name in data_param_names:
            error_map[name] = "All datasets must belong to same genomic build, " \
                "this dataset is linked to build '%s'" % param_values[name].dbkey
    if data_params != len(data_param_names):
        for name in data_param_names:
            error_map[name] = "A dataset of the appropriate type is required"

# Commented out by INS, 5/30/2007.  What is the PURPOSE of this?
def exec_after_process(app, inp_data, out_data, param_dict, tool=None, stdout=None, stderr=None):
    """Verify the output data after each run"""
    items = out_data.items()

    for name, data in items:
        try:
            if stderr and len( stderr ) > 0:
                raise Exception( stderr )

        except Exception, exc:
            data.blurb = JOB_ERROR
            data.state = JOB_ERROR

## def exec_after_process(app, inp_data, out_data, param_dict, tool=None, stdout=None, stderr=None):
##     pass


def exec_after_merge(app, inp_data, out_data, param_dict, tool=None, stdout=None, stderr=None):
    exec_after_process(
        app, inp_data, out_data, param_dict, tool=tool, stdout=stdout, stderr=stderr)

    # strip strand column if clusters were merged
    items = out_data.items()
    for name, data in items:
        if param_dict['returntype'] == True:
            data.metadata.chromCol = 1
            data.metadata.startCol = 2
            data.metadata.endCol = 3
        # merge always clobbers strand
        data.metadata.strandCol = None
            

def exec_after_cluster(app, inp_data, out_data, param_dict, tool=None, stdout=None, stderr=None):
    exec_after_process(
        app, inp_data, out_data, param_dict, tool=tool, stdout=stdout, stderr=stderr)

    # strip strand column if clusters were merged
    if param_dict["returntype"] == '1':
        items = out_data.items()
        for name, data in items:
            data.metadata.strandCol = None
