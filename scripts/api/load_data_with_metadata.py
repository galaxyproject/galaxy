#!/usr/bin/env python
"""

This script scans a directory for files with companion '.json' files, then loads 
the data from the file, and attaches the .json contents using the 'extended_metadata'
system in the library

Sample call:
python load_data_with_metadata.py <api_key> <api_url> /data/folder "API Imports"

NOTE:  The upload method used requires the data library filesystem upload allow_library_path_paste
"""
import os
import shutil
import sys
import json
import time
sys.path.insert( 0, os.path.dirname( __file__ ) )
from common import submit, display

def main(api_key, api_url, in_folder, data_library):
    # Find/Create data library with the above name.  Assume we're putting datasets in the root folder '/'
    libs = display(api_key, api_url + 'libraries', return_formatted=False)
    library_id = None
    for library in libs:
        if library['name'] == data_library:
            library_id = library['id']
    if not library_id:
        lib_create_data = {'name':data_library}
        library = submit(api_key, api_url + 'libraries', lib_create_data, return_formatted=False)
        library_id = library[0]['id']
    folders = display(api_key, api_url + "libraries/%s/contents" % library_id, return_formatted = False)
    for f in folders:
        if f['name'] == "/":
            library_folder_id = f['id']
    if not library_id or not library_folder_id:
        print "Failure to configure library destination."
        sys.exit(1)

    for fname in os.listdir(in_folder):
        fullpath = os.path.join(in_folder, fname)
        if os.path.isfile(fullpath) and os.path.exists(fullpath + ".json"):
            print "Loading", fullpath
            data = {}
            data['folder_id'] = library_folder_id
            data['file_type'] = 'auto'
            data['dbkey'] = ''
            data['upload_option'] = 'upload_paths'
            data['filesystem_paths'] = fullpath
            data['create_type'] = 'file'

            data['link_data_only'] = 'link_to_files'

            handle = open( fullpath + ".json" )
            smeta = handle.read()
            handle.close()
            data['extended_metadata'] = json.loads(smeta)
            libset = submit(api_key, api_url + "libraries/%s/contents" % library_id, data, return_formatted = True)
            print libset

if __name__ == '__main__':
    try:
        api_key = sys.argv[1]
        api_url = sys.argv[2]
        in_folder = sys.argv[3]
        data_library = sys.argv[4]
    except IndexError:
        print 'usage: %s key url in_folder data_library' % os.path.basename( sys.argv[0] )
        sys.exit( 1 )
    main(api_key, api_url, in_folder, data_library )

