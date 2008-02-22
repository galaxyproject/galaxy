# runs after the job (and after the default post-filter)

import pkg_resources
pkg_resources.require( "bx-python" )

from galaxy import datatypes, jobs, util
# needed to reference ParseError types, is this bad?
from bx.tabular.io import *
from bx.intervals.io import *
import sys, tempfile, os

def validate(incoming):
    """Validator"""
    #raise Exception, 'not quite right'
    pass

def exec_before_job( app, inp_data, out_data, param_dict, tool=None):
    """Build a temp file with errors in it"""
    errors = []
    for name, data in inp_data.items():
        validation_errors = data.validation_errors
        for error in validation_errors:
            # build dummy class
            try:
                temp = eval(error.err_type)()
            except:
                temp = object()
            # stuff attributes
            temp.__dict__ = util.string_to_object( error.attributes )
            errors.append(temp)
    # There *should* only be 1 input, so we assume there is and continue
    # base64 pickel
    errors_str = util.object_to_string( errors )
    # write
    database_tmp = "./database/tmp" # globaly visible path
    error_file = tempfile.NamedTemporaryFile(mode="w", dir=database_tmp, suffix=".b64")
    error_file_name = error_file.name
    error_file.close()
    error_file = open(error_file_name, "w")
    error_file.write(errors_str)
    error_file.close()
    param_dict["errorsfile"] = error_file_name
    
    
def exec_after_process( app, inp_data, out_data, param_dict, tool=None, stdout=None, stderr=None):
    # in a perfect world, changes to param_dict would persist
    # for now, unlink from tool
    # os.unlink(param_dict["errorsfile"])
    pass
