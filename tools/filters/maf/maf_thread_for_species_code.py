import pkg_resources; pkg_resources.require( "bx-python" )
from bx.align import maf
# No initialization required.

#return lists of species available, showing gapped and ungapped base counts
def get_available_species( input_filename ):
    try:
        rval = []
        species={}
        
        file_in = open(input_filename, 'r')
        try:
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
            display = "%s: %i nongap, %i total bases" % (spec, species[spec]["nongaps"], species[spec]["bases"] )
            rval.append( ( display,spec,True) )
                
        return rval
    except: 
        return [("<B>You must wait for the MAF file to be created before you can merge MAF blocks by species.</B>",'None',True)]
