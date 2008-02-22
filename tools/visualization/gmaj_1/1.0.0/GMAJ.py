#!/usr/bin/env python2.4

"""
Script that Creates a zip file for use by GMAJ
"""
import os, sys, zipfile
import pkg_resources; pkg_resources.require( "bx-python" )
from bx.align import maf

out_file = sys.argv[1]
maf_file = sys.argv[2]
dbkey = sys.argv[3]
if dbkey == "?": dbkey="unspecified"
exons_file = sys.argv[4]
highlights_file = sys.argv[5]
underlays_file = sys.argv[6]
repeats_file = sys.argv[7]
links_file = sys.argv[8]

def get_species_names( input_filename ):
    species={}
    
    file_in = open(input_filename, 'r')
    maf_reader = maf.Reader( file_in )
    
    for i, m in enumerate( maf_reader ):
        l = m.components
        for c in l:
            spec, chrom = maf.src_split( c.src )
            try:
            	if chrom not in species[spec]:
            	   species[spec].append(chrom)
            except:
                species[spec] = [chrom]
    
    file_in.close()
    return species


#open new zip file
out_file = zipfile.ZipFile(out_file, "w") #, ZIP_DEFLATED)

#determine organisms located in maf file.
species = get_species_names( maf_file )

GMAJ_str = "#:gmaj\n\ntitle = \"GMAJ through Galaxy\"\nalignfile = input.maf\nnowarn = bed_blocks bed_thick bed_name repeat_type_missing bed_name_prefix\ntabext = .%s\n" % (dbkey)
if dbkey in species and len(species[dbkey])>0:
    GMAJ_str = GMAJ_str + "refseq = "+dbkey+"."+species[dbkey][0]+"\n"
else:
    print "There was a problem setting the reference sequence."
GMAJ_str = GMAJ_str + "\n"
count = 0
for key in species:
    for chr in species[key]:
        GMAJ_str = GMAJ_str + "seq "+str(count)+":\nseqname = "+key+"."+chr+"\n"
        if key == dbkey:
            if os.path.isfile(exons_file):
                GMAJ_str = GMAJ_str + "exons = exons."+dbkey+"\n"
            if os.path.isfile(highlights_file):
                GMAJ_str = GMAJ_str + "highlights = highlights."+dbkey+"\n"
            if os.path.isfile(underlays_file):
                GMAJ_str = GMAJ_str + "underlays = underlays."+dbkey+"\n"
            if os.path.isfile(repeats_file):
                GMAJ_str = GMAJ_str + "repeats = repeats."+dbkey+"\n"
            if os.path.isfile(links_file):
                GMAJ_str = GMAJ_str + "links = links."+dbkey+"\n"
        GMAJ_str = GMAJ_str + "\n"
        count += 1
out_file.writestr("input.gmaj",GMAJ_str)

#add maf file
out_file.write(maf_file, "input.maf")


if os.path.isfile(exons_file):
    out_file.write(exons_file, "exons."+dbkey)
if os.path.isfile(highlights_file):
    out_file.write(highlights_file, "highlights."+dbkey)
if os.path.isfile(underlays_file):
    out_file.write(underlays_file, "underlays."+dbkey)
if os.path.isfile(repeats_file):
    out_file.write(repeats_file, "repeats."+dbkey)
if os.path.isfile(links_file):
    out_file.write(links_file, "links."+dbkey)

out_file.close()

print "GMAJ bundle file created"
