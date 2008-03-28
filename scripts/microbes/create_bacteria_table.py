#!/usr/bin/env python
#Dan Blankenberg

import sys, os

assert sys.version_info[:2] >= ( 2, 4 )

def __main__():
    base_dir = os.path.join( os.getcwd(), "bacteria" )
    try:
        base_dir = sys.argv[1]
    except:
        pass
        #print "using default base_dir:", base_dir

    organisms = {}
    for result in os.walk(base_dir):
        this_base_dir,sub_dirs,files = result
        for file in files:
            if file[-5:] == ".info":
                dict = {}
                info_file = open(os.path.join(this_base_dir,file),'r')
                info = info_file.readlines()
                info_file.close()
                for line in info:
                    fields = line.replace("\n","").split("=")
                    dict[fields[0]]="=".join(fields[1:])
                if 'genome project id' in dict.keys():
                    name = dict['genome project id']
                    if 'build' in dict.keys():
                        name = dict['build']
                    if name not in organisms.keys():
                        organisms[name] = {'chrs':{},'base_dir':this_base_dir}
                    for key in dict.keys():
                        organisms[name][key]=dict[key]
                else:
                    if dict['organism'] not in organisms.keys():
                        organisms[dict['organism']] = {'chrs':{},'base_dir':this_base_dir}
                    organisms[dict['organism']]['chrs'][dict['chromosome']]=dict

    orgs = organisms.keys()
    for org in orgs:
        if 'name' not in organisms[org]:del organisms[org]

    orgs = organisms.keys()
    #need to sort by name
    swap_test = False
    for i in range(0, len(orgs) - 1):
        for j in range(0, len(orgs) - i - 1):
            if organisms[orgs[j]]['name'] >  organisms[orgs[j + 1]]['name']:
                orgs[j], orgs[j + 1] = orgs[j + 1], orgs[j]
            swap_test = True
        if swap_test == False:
            break




    print "||'''Organism'''||'''Kingdom'''||'''Group'''||'''Links to UCSC Archaea Browser'''||"


    for org in orgs:
        org = organisms[org]
        at_ucsc = False
        #if no gpi, then must be a ncbi chr which corresponds to a UCSC org, w/o matching UCSC designation
        try:
            build = org['genome project id']
        except: continue
        if 'build' in org:
            build = org['build']
            at_ucsc = True
            
        out_str = "||"+org['name']+"||"+org['kingdom']+"||"+org['group']+"||"
        if at_ucsc:
            out_str = out_str + "Yes"
        out_str = out_str + "||"
        print out_str

if __name__ == "__main__": __main__()
