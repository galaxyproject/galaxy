"""
# for eigenstrat
also need to deal with
   <outputs>
       <data format="text" name="logfile" />
       <data format="text" name="title" />
       <data format="ps" name="ps_eigenplot" />
       <data format="pdf" name="pdf_eigenplot" /> 
       <data name="eigenlog" format="text" />  
       <data name="eigenout" format="tabular" />
       <data name="eigenout.evec" format="tabular" />
       <data name="eigenvals" format="tabular" />
       <data name="eigenout.par" format="tabular" /> 
   </outputs>

"""
from galaxy import datatypes


def exec_after_process(app, inp_data, out_data, param_dict, tool, stdout, stderr):
    """Sets the name of the data"""
    job_name = param_dict.get( 'title', 'rgPedEig' )
    data = out_data['out_file1']
    data.name = job_name
    out_data['out_file1'] = data
    data.flush()


