"""
Pulsar HTTP Client layer based on Python Standard Library (urllib2)
"""
from __future__ import with_statement
from os.path import getsize
import mmap
try:
    from urllib2 import urlopen
except ImportError:
    from urllib.request import urlopen
try:
    from urllib2 import Request
except ImportError:
    from urllib.request import Request


class Urllib2Transport(object):

    def _url_open(self, request, data):
        return urlopen(request, data)

    def execute(self, url, method=None, data=None, input_path=None, output_path=None):
        request = self.__request(url, data, method)
        input = None
        try:
            if input_path:
                if getsize(input_path):
                    input = open(input_path, 'rb')
                    data = mmap.mmap(input.fileno(), 0, access=mmap.ACCESS_READ)
                else:
                    data = b""
            response = self._url_open(request, data)
        finally:
            if input:
                input.close()
        if output_path:
            with open(output_path, 'wb') as output:
                while True:
                    buffer = response.read(1024)
                    if not buffer:
                        break
                    output.write(buffer)
            return response
        else:
            return response.read()

    def __request(self, url, data, method):
        request = Request(url=url, data=data)
        if method:
            request.get_method = lambda: method
        return request
