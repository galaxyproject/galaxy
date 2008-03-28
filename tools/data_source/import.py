#!/usr/bin/env python

"""
Script that imports locally stored data as a new dataset for the user
Usage: import id outputfile
"""
import sys, os

assert sys.version_info[:2] >= ( 2, 4 )

BUFFER = 1048576

dataid   = sys.argv[1]
out_name = sys.argv[2]


id2name = {
    'eryth'         : 'ErythPreCRMmm3_cusTrk.txt',
    'cishg16'       : 'ReglRegHBBhg16CusTrk.txt',
    'cishg17'       : 'ReglRegHBBhg17CusTrk.txt',
    'exons'         : 'ExonsKnownGenes_mm3.txt',
    'krhg16'        : 'known_regulatory_hg16.bed',
    'krhg17'        : 'known_regulatory_hg17.bed',
    'tARhg16mmc'    : 'hg16.mouse.t_AR.cold.bed',
    'tARhg16mmm'    : 'hg16.mouse.t_AR.medium.bed',
    'tARhg16mmh'    : 'hg16.mouse.t_AR.hot.bed',
    'tARhg16rnc'    : 'hg16.rat.t_AR.cold.bed',
    'tARhg16rnm'    : 'hg16.rat.t_AR.medium.bed',
    'tARhg16rnh'    : 'hg16.rat.t_AR.hot.bed',
    'phastConsHg16' : 'phastConsMost_hg16.bed',
    'omimhg16'      : 'omimDisorders_hg16.tab',
    'omimhg17'      : 'omimDisorders_hg17.tab',

}

fname = id2name.get(dataid, '')
if not fname:
    print 'Importing invalid data %s' % dataid
    sys.exit()
else:
    print 'Imported %s' % fname

# this path is hardcoded
inp_name = os.path.join('database', 'import', fname)

try:
    inp = open(inp_name, 'rt')
except:
    print 'Could not find file %s' % inp_name
    sys.exit()

out = open(out_name, 'wt')

while 1:
    data = inp.read(BUFFER)
    if not data:
        break
    out.write(data)

inp.close()
out.close()
