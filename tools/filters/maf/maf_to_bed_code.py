import pkg_resources; pkg_resources.require( "bx-python" )
from bx.align import maf
# No initialization required.

    
#return lists of species available, showing gapped and ungapped base counts
def get_available_species( dbkey, input_filename ):
    try:
        rval = []
        species={}
        
        file_in = open(input_filename, 'r')
        maf_reader = maf.Reader( file_in )
        
        for i, m in enumerate( maf_reader ):
            l = m.components
            for c in l:
                spec,chrom = maf.src_split( c.src )
                if not spec or not chrom:
                    spec = chrom = c.src
                species[spec]=spec
        
        file_in.close()
        
        species = species.keys()
        species.sort()

        file_in = open(input_filename, 'r')
        maf_reader = maf.Reader( file_in )
        
        species_sequence={}
        for s in species: species_sequence[s] = []
        
        for m in maf_reader:
            for s in species:
                c = m.get_component_by_src_start( s ) 
                if c: species_sequence[s].append( c.text )
                else: species_sequence[s].append( "-" * m.text_size )
        
        file_in.close()
        
        rval.append( ("Include all species.",'None',False) )
        for spec in species:
            species_sequence[spec] = "".join(species_sequence[spec])
            if spec == dbkey:
                rval.append( ("<b>"+spec + ": "+str(len(species_sequence[spec]) - species_sequence[spec].count("-"))+" nongap, "+ str(len(species_sequence[spec])) + " total bases</b>",spec,True) )
            else:
                rval.append( (spec + ": "+str(len(species_sequence[spec]) - species_sequence[spec].count("-"))+" nongap, "+ str(len(species_sequence[spec])) + " total bases",spec,False) )
                
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
