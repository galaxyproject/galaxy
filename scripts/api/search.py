"""
Sample script for Galaxy Search API
"""

import json
import requests
import sys

class RemoteGalaxy(object):

    def __init__(self, url, api_key):
        self.url = url
        self.api_key = api_key

    def get(self, path):
        c_url = self.url + path
        params = {}
        params['key'] = self.api_key
        req = requests.get(c_url, params=params)
        return req.json()

    def post(self, path, payload):
        c_url = self.url + path
        params = {}
        params['key'] = self.api_key
        req = requests.post(c_url, data=json.dumps(payload), params=params, headers = {'Content-Type': 'application/json'} )
        return req.json()

if __name__ == "__main__":
    server = sys.argv[1]
    api_key = sys.argv[2]

    rg = RemoteGalaxy(server, api_key)

    print "select name, id, file_size from hda"
    print rg.post("/api/search", { "query" : "select name, id, file_size from hda" })

    print "select name from hda"
    print rg.post("/api/search", { "query" : "select name from hda" })

    print "select name, model_class from ldda"
    print rg.post("/api/search", { "query" : "select name, model_class from ldda" })

    print "select * from history"
    print rg.post("/api/search", { "query" : "select * from history" })

    print "select * from tool"
    print rg.post("/api/search", { "query" : "select * from tool" })

    print "select * from workflow"
    print rg.post("/api/search", { "query" : "select * from workflow" })

    print "select id, name from history where name='Unnamed history'"
    print rg.post("/api/search", {"query" : "select id, name from history where name='Unnamed history'"})

    print "select * from history where name='Unnamed history'"
    print rg.post("/api/search", {"query" : "select * from history where name='Unnamed history'"})
