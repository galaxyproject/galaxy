#!/usr/bin/env python
"""
Simple example script that watches a folder for new files, imports that data to a data library, and then
execute a workflow on it, creating a new history for each workflow invocation.

This assumes a workflow with only one input, though it could be adapted to many.

Sample call:
python example_watch_folder.py <api_key> <api_url> /tmp/g_inbox/ /tmp/g_inbox/done/ "API Imports" f2db41e1fa331b3e

NOTE:  The upload method used requires the data library filesystem upload allow_library_path_paste
"""
import os
import shutil
import sys
import time
sys.path.insert( 0, os.path.dirname( __file__ ) )
from common import submit, display

def main(api_key, api_url, in_folder, out_folder, data_library, workflow):
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
    workflow = display(api_key, api_url + 'workflows/%s' % workflow, return_formatted = False)
    if not workflow:
        print "Workflow %s not found, terminating."
        sys.exit(1)
    if not library_id or not library_folder_id:
        print "Failure to configure library destination."
        sys.exit(1)
    while 1:
        # Watch in_folder, upload anything that shows up there to data library and get ldda,
        # invoke workflow, move file to out_folder.
        for fname in os.listdir(in_folder):
            fullpath = os.path.join(in_folder, fname)
            if os.path.isfile(fullpath):
                data = {}
                data['folder_id'] = library_folder_id
                data['file_type'] = 'auto'
                data['dbkey'] = ''
                data['upload_option'] = 'upload_paths'
                data['filesystem_paths'] = fullpath
                data['create_type'] = 'file'
                libset = submit(api_key, api_url + "libraries/%s/contents" % library_id, data, return_formatted = False)
                #TODO Handle this better, but the datatype isn't always
                # set for the followup workflow execution without this
                # pause.
                time.sleep(5)
                for ds in libset:
                    if 'id' in ds:
                        # Successful upload of dataset, we have the ldda now.  Run the workflow.
                        wf_data = {}
                        wf_data['workflow_id'] = workflow['id']
                        wf_data['history'] = "%s - %s" % (fname, workflow['name'])
                        wf_data['ds_map'] = {}
                        for step_id, ds_in in workflow['inputs'].iteritems():
                            wf_data['ds_map'][step_id] = {'src':'ld', 'id':ds['id']}
                        res = submit( api_key, api_url + 'workflows', wf_data, return_formatted=False)
                        if res:
                            print res
                            # Successful workflow execution, safe to move dataset.
                            shutil.move(fullpath, os.path.join(out_folder, fname))
        time.sleep(10)

if __name__ == '__main__':
    try:
        api_key = sys.argv[1]
        api_url = sys.argv[2]
        in_folder = sys.argv[3]
        out_folder = sys.argv[4]
        data_library = sys.argv[5]
        workflow = sys.argv[6]
    except IndexError:
        print 'usage: %s key url in_folder out_folder data_library workflow' % os.path.basename( sys.argv[0] )
        sys.exit( 1 )
    main(api_key, api_url, in_folder, out_folder, data_library, workflow )

