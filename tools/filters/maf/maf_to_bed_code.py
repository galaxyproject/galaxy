import pkg_resources; pkg_resources.require( "bx-python" )
from bx.align import maf
# No initialization required.

    
#return lists of species available, showing gapped and ungapped base counts
def get_available_species( dbkey, input_filename ):
    try:
        rval = []
        species={}
        
        
        try:
            file_in = open(input_filename, 'r')
            maf_reader = maf.Reader( file_in )
            
            
            for i, m in enumerate( maf_reader ):
                l = m.components
                for c in l:
                    spec,chrom = maf.src_split( c.src )
                    if not spec or not chrom:
                        spec = chrom = c.src
                    if spec not in species:
                        species[spec]={"bases":0,"nongaps":0}
                    species[spec]["bases"] = species[spec]["bases"] + c.size + c.text.count("-")
                    species[spec]["nongaps"] = species[spec]["nongaps"] + c.size 
            
            file_in.close()
        except:
            return [("There is a problem with your MAF file",'None',True)]
        species_names = species.keys()
        species_names.sort()
        
        for spec in species_names:
            #species_sequence[spec] = "".join(species_sequence[spec])
            
            if spec == dbkey:
                display = "<b>%s: %i nongap, %i total bases</b>" % (spec, species[spec]["nongaps"], species[spec]["bases"] )
                rval.append( ( display,spec,True) )
            else:
                display = "%s: %i nongap, %i total bases" % (spec, species[spec]["nongaps"], species[spec]["bases"] )
                rval.append( ( display,spec,False) )
            
        return rval
    except:
        return [("Include all species.",'None',True)]


from galaxy import datatypes, config, jobs 
from shutil import move
def exec_after_process(app, inp_data, out_data, param_dict, tool, stdout, stderr):
    output_data = out_data.items()[0][1]
    history = output_data.history
    if history == None:
        print "unknown history!"
        return
    new_stdout = ""
    split_stdout = stdout.split("\n")
    basic_name = output_data.name
    output_data_list = []
    for line in split_stdout:
        if line.startswith("#FILE1"):
            fields = line.split("\t")
            dbkey = fields[1]
            filepath = fields[2]
            output_data.dbkey = dbkey
            output_data.name = basic_name + " (" + dbkey + ")"
            output_data.flush()
            app.model.flush()
            output_data_list.append(output_data)
        elif line.startswith("#FILE"):
            fields = line.split("\t")
            dbkey = fields[1]
            filepath = fields[2]

            newdata = app.model.Dataset()
            newdata.extension = "bed"
            newdata.name = basic_name + " (" + dbkey + ")"
            newdata.flush()
            history.add_dataset( newdata )
            newdata.flush()
            history.flush()
            app.model.flush()
            try:
                move(filepath,newdata.file_name)
                newdata.info = newdata.name
                newdata.state = newdata.states.OK
            except:
                newdata.info = "The requested file is missing from the system."
                newdata.state = newdata.states.ERROR
            newdata.dbkey = dbkey
            newdata.init_meta()
            newdata.set_peek()
            app.model.flush()
            output_data_list.append(newdata)
        else:
            new_stdout = new_stdout + line
        for data in output_data_list:
            if data.state == data.states.OK:
                data.info = new_stdout
                data.flush()
