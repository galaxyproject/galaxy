import pkg_resources; pkg_resources.require( "bx-python" )
from bx.align import maf
# No initialization required.


#def validate(incoming):
#    # check that atleast one species is specified
#    if incoming.get("species","") == "":
#        raise Exception, "You need to specify at least one species to extract."
    
#return lists of species available, showing gapped and ungapped base counts
def get_available_species( input_filename ):
    try:
        rval = []
        species={}
        
        file_in = open(input_filename, 'r')
        maf_reader = maf.Reader( file_in )
        
        for i, m in enumerate( maf_reader ):
            l = m.components
            for c in l:
                spec,chrom = maf.src_split( c.src )
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
            rval.append( (spec + ": "+str(len(species_sequence[spec]) - species_sequence[spec].count("-"))+" nongap, "+ str(len(species_sequence[spec])) + " total bases",spec,False) )
                
        return rval
    except:
        return [("Include all species. <i>If you want to limit your conversion to a set of species, you must wait for the MAF file to be created.</i>",'None',True)]
