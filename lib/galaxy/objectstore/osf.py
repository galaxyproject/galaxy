#!/usr/bin/env python

from __future__ import print_function
import httplib2
import json
import tempfile
from galaxy.objectstore import ObjectStore
from galaxy.util.bunch import Bunch
import sys

content_type = "application/vnd.api+json"
root = "https://staging-api.osf.io/v2/"

cookie = sys.argv[1]

h = httplib2.Http(".cache")
'''
(resp_headers, content) = h.request(root, "GET",
        headers={
            'content-type': content_type,
            'Cookie': cookie
            })

body = json.loads(content)
print(body)

userid = body["meta"]["current_user"]["data"]["id"]

print(userid)


(resp_headers, content) = h.request(root+"users/"+userid+"/nodes/", "GET",
        headers={
            'content-type': content_type,
            'Cookie': cookie
            })

print(resp_headers)

print(content)

galaxy_node_creation = {
        "data": {
            "type": "nodes",
            "attributes": {
                "title": "Test Node for Galaxy Storage",
                "category": "",
                }
            }
        }

galaxy_node = "wyfvt"

(resp_headers, content) = h.request(
        root+"nodes/",
        "POST",
        json.dumps(galaxy_node_creation),
        headers={
            'content-type': content_type,
            'Cookie': cookie
            })

print(resp_headers)

print(content)
'''

class OSFObjectStore(ObjectStore):

    content_type = "application/vnd.api+json"
    root = "https://staging-api.osf.io/v2/"
    galaxy_node = "wyfvt"

    root_folder = "/560de5d7029bdb08bf722871"


    def __init__(self, config, cookie, **kwargs):
        super(OSFObjectStore, self).__init__(config=config, **kwargs)
        self.h = httplib2.Http(".cache")
        self.cache = {}
        self.cookie = cookie

    def __get_root_URL(self): 
        return "https://staging-files.osf.io/v1/resources/wyfvt/providers/osfstorage/560de42d029bdb08c572289a/"

    def __get_remotepath_for_id(self):
        (resp_headers, content) = h.request(
            self.__get_root_URL(),
            "GET",
            headers={
                'content-type': content_type,
                'Cookie': cookie
                    })



    def exists(self, obj, base_dir=None, dir_only=False, extra_dir=None,
            extra_dir_at_root=False, alt_name=None):
        pass
               

    def create(self, obj, base_dir=None, dir_only=False, extra_dir=None,
            extra_dir_at_root=False, alt_name=None, obj_dir=False):

        upload_URL = self.__get_root_URL() + "?kind=file&name=" + str(obj.id)
        print(upload_URL)
        (resp_headers, content) = h.request(
            upload_URL,
            "PUT",
            headers={
                'content-type': content_type,
                'Cookie': cookie
                    })

        print(resp_headers)
        print(content)
        body=json.loads(content)
        remote_path = body["path"]
        self.cache[id] = remote_path


file_path=tempfile.mkdtemp()
ostore = OSFObjectStore(Bunch(
    object_store_check_old_style=False,
    job_working_directory=file_path,
    new_file_path=file_path,
    cookie=sys.argv[1]))

ostore.create(Bunch(id=0))
