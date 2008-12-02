# runs after the job (and after the default post-filter)
from galaxy import datatypes, jobs

def validate(incoming):
    """Validator"""
    #raise Exception, 'not quite right'
    pass

def exec_before_job( app, inp_data, out_data, param_dict, tool=None):
    """Sets the name of the data"""
    outputType = param_dict.get( 'hgta_outputType', None )
    if isinstance(outputType, list) and len(outputType)>0: outputType = outputType[-1]
    items = out_data.items()
    
    for name, data in items:
        data.name  = param_dict.get('display', data.name)
        data.dbkey = param_dict.get('dbkey', '???')

        if outputType == 'wigData':
            ext = "wig"
        elif outputType == 'maf':
            ext = "maf"
        elif outputType == 'gff':
            ext = "gff"
        elif outputType == 'gff3':
            ext = "gff3"
        else:
            if 'hgta_doPrintSelectedFields' in param_dict:
                ext = "interval"
            elif 'hgta_doGetBed' in param_dict:
                ext = "bed"
            elif 'hgta_doGenomicDna' in param_dict:
                ext = "fasta"
            elif 'hgta_doGenePredSequence' in param_dict:
                ext = "fasta"
            else:
                ext = "interval"
        
        data = app.datatypes_registry.change_datatype(data, ext)
        out_data[name] = data
        
def exec_after_process( app, inp_data, out_data, param_dict, tool=None, stdout=None, stderr=None):
    """Verifies the data after the run"""
    items = out_data.items()
    for name, data in items:
        data.set_size()
        try:            
            err_msg, err_flag = 'Errors:', False
            line_count = 0
            num_lines = len(file(data.file_name).readlines())
            for line in file(data.file_name):
                line_count += 1
                if line and line[0] == '-':
                    if line_count + 3 == num_lines and not err_flag:
                        err_flag = True
                        err_msg = "Warning: It appears that your results have been truncated by UCSC. View the bottom of your result file for details."
                        break
                    err_flag = True
                    err_msg = err_msg +" (line "+str(line_count)+")"+line
            data.set_peek()
            if isinstance(data.datatype, datatypes.interval.Interval) and data.missing_meta():
                data = app.datatypes_registry.change_datatype(data, 'tabular')
                out_data[name] = data
            if err_flag:
                raise Exception(err_msg)
        except Exception, exc:
            data.info  = data.info + "\n" + str(exc)
            data.blurb = "error"
