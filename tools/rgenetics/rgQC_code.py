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
import sys,time

def timenow():
    """return current time as a string
    """
    return time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(time.time()))


def exec_after_process(app, inp_data, out_data, param_dict, tool, stdout, stderr):
    """Change data file names

    """
    job_name = param_dict.get( 'out_prefix', 'rgQCdefault' )
    html = ['html','%s.html' % job_name]
    lookup={}
    lookup['html_file'] = html
    info = '%s QC report by rgQC at %s' % (job_name,timenow())
    for aname in lookup.keys():
       data = out_data[aname]
       data_type,newname = lookup[aname]
       data = app.datatypes_registry.change_datatype(data, data_type)
       data.name = newname
       data.info = info
       out_data[aname] = data
    app.model.context.flush()



