#EMBOSS format corrector

import operator
#from galaxy import datatypes

#Properly set file formats after job run
def exec_after_process( app, inp_data, out_data, param_dict,tool, stdout, stderr):
#Properly set file formats before job run
#def exec_before_job(trans, inp_data, out_data, param_dict,tool):
    #why isn't items an ordered list?
    items = out_data.items()
    #lets sort it ourselves....
    items = sorted(items, key=operator.itemgetter(0))
    #items is now sorted...
    
    #normal filetype correction
    data_count=1
    for name, data in items:
        outputType = param_dict.get( 'out_format'+str(data_count), None )
        #print "data_count",data_count, "name", name, "outputType", outputType
        if outputType !=None:
            if outputType == 'ncbi':
                outputType = "fasta"
            elif outputType == 'excel':
                outputType = "tabular"
            elif outputType == 'text':
                outputType = "txt"
            data = app.datatypes_registry.change_datatype(data, outputType)
            app.model.context.add( data )
            app.model.context.flush()
        data_count+=1
    
    #html filetype correction
    data_count=1
    for name, data in items:
        wants_plot = param_dict.get( 'html_out'+str(data_count), None )
        ext = "html"
        if wants_plot == "yes":
            data = app.datatypes_registry.change_datatype(data, ext)
            app.model.context.add( data )
            app.model.context.flush()
        data_count+=1
    
    #png file correction
    data_count=1
    for name, data in items:
        wants_plot = param_dict.get( 'plot'+str(data_count), None )
        ext = "png"
        if wants_plot == "yes":
            data = app.datatypes_registry.change_datatype(data, ext)
            app.model.context.add( data )
            app.model.context.flush()
        data_count+=1
