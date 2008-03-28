#!/usr/bin/env python

"""
Script that imports locally stored data as a new dataset for the user
Usage: import id outputfile
"""
import sys, os
from shutil import copyfile

assert sys.version_info[:2] >= ( 2, 4 )

BUFFER = 1048576

def stop_err( msg ):
    sys.stderr.write( msg )
    sys.exit()

def main():
    uids = sys.argv[1].split(",")
    out_file1 = sys.argv[2]
    file_name = "%s/encode_datasets.loc" % sys.argv[3]
    
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
        for i, line in enumerate( file ( file_name ) ):
            line = line.rstrip( '\r\n' )
            if line and not line.startswith( '#' ):
                fields = line.split( '\t' )
                try:
                    encode_group = fields[0].strip()
                    build = fields[1].strip()
                    description = fields[2].strip()
                    uid = fields[3].strip()
                    path = fields[4].strip()
                    try:
                        file_type = fields[5].strip()
                    except:
                        file_type = "bed"
                except:
                    continue
                available_files[uid] = ( description, path, build, file_type )
    except:
        stop_err( "It appears that the configuration file for this tool is missing." )

    #create list of tuples of ( displayName, FileName, build ) for desired files
    desired_files = []
    for uid in uids:
        try:
            desired_files.append( available_files[uid] )
        except:
            continue
    
    #copy first file to contents of given output file
    file1_copied = False
    while not file1_copied:
        try:
            first_file = desired_files.pop(0)
        except:
            stop_err( "There were no valid files requested." )
        file1_desc, file1_path, file1_build, file1_type = first_file
        try:
            copyfile( file1_path, out_file1 )
            print "#File1\t" + file1_desc + "\t" + file1_build + "\t" + file1_type
            file1_copied = True
        except:
            stop_err( "The file '%s' is missing." %str( file1_path ) )
        
    #Tell post-process filter where remaining files reside
    for extra_output in desired_files:
        file_desc, file_path, file_build, file_type = extra_output
        print "#NewFile\t" + file_desc + "\t" + file_build + "\t" + file_path + "\t" + file_type

if __name__ == "__main__": main()
