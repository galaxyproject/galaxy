import tempfile,shutil
from galaxy import app,datatypes

def exec_before_job_hook(app, inp_data, out_data, param_dict, tool=None):
    """Sets the name of the data"""
    data_name = param_dict.get( 'name', 'rgHapmapGeno' )
    data_name = '%s.log' % data_name
    data_type = param_dict.get( 'type', 'interval' ) # transform later
    name, data = out_data.items()[0]
    data = app.datatypes_registry.change_datatype(data, data_type)
    data.set_meta(first_line_is_header=True)                
    data.name = data_name
    out_data[name] = data

def exec_after_process(app, inp_data, out_data, param_dict, tool, stdout, stderr):
    """convert spaces to tabs and remove comment lines"""
    items = out_data.items()
    for name, data in items:
            #try:            
            err_msg, err_flag = 'Errors:', False
            temp = tempfile.NamedTemporaryFile('w')
            temp_filename = temp.name
            temp.close()
            temp = open(temp_filename,'w')
            line_count = 0
            for line in file(data.file_name,'r'):
                if line[0] <> '#':
                   ll = line.split()
                   ll[2] = ll[2].lower() # Chr to chr
                   ll.append('\n')
                   temp.write('\t'.join(ll)) # tab sep and no comments
                   line_count += 1
            if line_count < 2: # only a header?
                err_flag = True
                err_msg = "Warning: no genotypes - are your chrom/start/stop sensible? %s" % data.file_name
            else:
		shutil.move(temp_filename,data.file_name)
            data.set_peek()
            data.metadata.chromCol = 3
            data.metadata.startCol = 4
            data.metadata.endCol = 4
            data.metadata.strandCol = 5
            data.dbkey = 'hg18'
            if err_flag:
                raise Exception(err_msg)
            else:
                out_data[name] = data
            #except Exception, exc:
            #data.info  = data.info + "\n" + str(exc)
            #data.blurb = "error"
    
    
