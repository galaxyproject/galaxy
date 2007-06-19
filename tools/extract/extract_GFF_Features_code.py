#!/usr/bin/env python2.4

import os, sys, tempfile

def get_unique_elems(elems): 
    #return list(set(elems))
    seen = set()
    return [x for x in elems if x not in seen and not seen.add(x)]

#return available unique entries from the specified column of the input data
def get_features( data, index ):
    elem_list = []
    unique_list = []
    datafile = "./database/files/dataset_" + str(data.id) + ".dat"
    try:
        finp = open(datafile, "r")
    except:
        return [("Input datafile doesn't exist",'None',True)]
    try:
        for line in finp:
            line = line.rstrip("\r\n")
            if not(line) or line == "" or line[0:1] == '#':
                continue
            elems = line.split('\t')
            elem_list.append(elems[index])
    except:
        pass
    finp.close()
    if not(elem_list):
        return[('No elements to display. Please choose another column','None',True)]
    try:
        for ind, elem in enumerate(get_unique_elems(elem_list)):
            if ind == 0:
                unique_list.append((elem,elem,True))
            else:
                unique_list.append((elem,elem,False))
        return unique_list
    except:
        pass
    """
    if len(unique_list) == 1:
        return[('Column has only one feature. Please choose another column','None',True)]
    
    if len(unique_list) > 10:
        return [('Too many elements to display.Choose another column with at most 10 entries','None',True)]
    """
    
    
def get_length( feature ):
    return len(feature)