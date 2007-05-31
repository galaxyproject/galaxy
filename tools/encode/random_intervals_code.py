#build list of available data
import os, sys
#available_regions[build][uids]
available_regions = {}

loc_file = "/depot/data2/galaxy/regions.loc"


try:
    for line in open( loc_file ):
        if line[0:1] == "#" : continue
        
        fields = line.split('\t')
        #read each line, if not enough fields, go to next line
        try:
            build = fields[0]
            uid = fields[1]
            description = fields[2]
            filepath =fields[3].replace("\n","").replace("\r","")
            if build not in available_regions:
                available_regions[build]=[]
            available_regions[build].append((description,uid,False))
        except:
            continue

except Exception, exc:
    print >>sys.stdout, 'random_intervals_code.py initialization error -> %s' % exc 

#return available datasets for group and build, set None option as selected for hg16
def get_available_data( build ):
    available_sets = []
    if build in available_regions:
        return available_regions[build]
    else:
        return [('No data available for this build','None',True)]


#def exec_before_job(app, inp_data, out_data, param_dict, tool):
#    for name, data in out_data.items():
#        data.name = data.name + " [" + maf_sets[param_dict['mafType']]['description'] + "]"
