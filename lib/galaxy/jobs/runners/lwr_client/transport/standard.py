"""
LWR HTTP Client layer based on Python Standard Library (urllib2)
"""
from __future__ import with_statement
import mmap
import urllib2


class Urllib2Transport(object):

    def _url_open(self, request, data):
        return urllib2.urlopen(request, data)

    def execute(self, url, data=None, input_path=None, output_path=None):
        request = urllib2.Request(url=url, data=data)
        input = None
        try:
            if input_path:
                input = open(input_path, 'rb')
                data = mmap.mmap(input.fileno(), 0, access=mmap.ACCESS_READ)
            response = self._url_open(request, data)
        finally:
            if input:
                input.close()
        if output_path:
            with open(output_path, 'wb') as output:
                while True:
                    buffer = response.read(1024)
                    if buffer == "":
                        break
                    output.write(buffer)
            return response
        else:
            return response.read()
