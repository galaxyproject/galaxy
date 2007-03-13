#!/usr/bin/env python2.4

"""
Script that imports locally stored data as a new dataset for the user
Usage: import id outputfile
"""
import sys, os
from shutil import copyfile
#tempfile, shutil
BUFFER = 1048576

uids = sys.argv[1].split(",")
out_file1 = sys.argv[2]

#remove NONE from uids
have_none = True
while have_none:
    try:
        uids.remove('None')
    except:
        have_none = False


#create dictionary keyed by uid of tuples of (displayName,filePath,build) for all files
available_files = {}
try:
    for line in open( "/depot/data2/galaxy/encode_datasets.loc" ):
        if line[0:1] == "#" : continue
        
        fields = line.split('\t')
        #read each line, if not enough fields, go to next line
        try:
            encode_group = fields[0]
            build = fields[1]
            description = fields[2]
            uid = fields[3]
            path = fields[4]
            path = path.replace("\n","")
            path = path.replace("\r","")
            try:
                file_type = fields[5]
                #remove newlines from file type
                file_type = file_type.replace("\n","")
                file_type = file_type.replace("\r","")
            except:
                file_type = "bed"
                
        except:
            continue
        available_files[uid]=(description,path,build,file_type)
except:
    print >>sys.stderr, "It appears that the configuration file for this tool is missing."

#create list of tuples of (displayName,FileName,build) for desired files
desired_files = []
for uid in uids:
    try:
        desired_files.append(available_files[uid])
    except:
        continue

#copy first file to contents of given output file
file1_copied = False
while not file1_copied:
    try:
        first_file = desired_files.pop(0)
    except:
        print >>sys.stderr, "There were no valid files requested."
        sys.exit()
    file1_desc, file1_path, file1_build, file1_type = first_file
    try:
        copyfile(file1_path,out_file1)
        print "#File1\t"+file1_desc+"\t"+file1_build+"\t"+file1_type
        file1_copied = True
    except:
        print >>sys.stderr, "The file specified is missing."
        continue
        #print >>sys.stderr, "The file specified is missing."
    

#Tell post-process filter where remaining files reside
for extra_output in desired_files:
    file_desc, file_path, file_build, file_type = extra_output
    print "#NewFile\t"+file_desc+"\t"+file_build+"\t"+file_path+"\t"+file_type
