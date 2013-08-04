"""
# after running the qc, need to rename various output files
       <data format="html" name="html_file" />
       <data format="txt" name="log_file" parent="html_file" />
       <data format="tabular" name="marker_file" parent="html_file" />
       <data format="tabular" name="subject_file" parent="html_file" />
       <data format="tabular" name="freq_file" parent="html_file" />
   </outputs>
"""
from galaxy import datatypes,model
import sys


def exec_after_process(app, inp_data, out_data, param_dict, tool, stdout, stderr):
    """Change data file names

    """
    job_name = param_dict.get( 'out_prefix', 'rgQCdefault' )
    html = ['html','%s_QC.html' % job_name]
    log = ['txt','%s_log.txt' % job_name]
    marker = ['tabular','%s_marker.txt' % job_name]
    subj = ['tabular','%s_subject.txt' % job_name]
    lookup={}
    lookup['html_file'] = html
    lookup['log_file'] = log
    lookup['marker_file'] = marker
    lookup['subject_file'] = subj
    for aname in lookup.keys():
       data = out_data[aname]
       data_type,newname = lookup[aname]
       data = app.datatypes_registry.change_datatype(data, data_type)
       data.name = newname
       out_data[aname] = data



