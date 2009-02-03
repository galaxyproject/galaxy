import sets, os
from galaxy import eggs
from galaxy import jobs
from galaxy.tools.parameters import DataToolParameter

def exec_after_process(app, inp_data, out_data, param_dict, tool=None, stdout=None, stderr=None):
    """
    Copy data_label to genetrack.metadata.label
    """
    out_data['genetrack'].metadata.label = param_dict['data_label']
    out_data['genetrack'].info = "Use the link below to view the custom track."
    out_data['bed_out'].info = ""
