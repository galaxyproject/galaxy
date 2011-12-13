import os
import sys
import imp
import pkg_resources
import mimetypes
from paste import request
from paste import fileapp
from paste.util import import_string
from paste.deploy import converters
from paste import httpexceptions
from paste.httpheaders import ETAG

from paste.urlparser import StaticURLParser

class CacheableStaticURLParser( StaticURLParser ):
    def __init__( self, directory, cache_seconds=None ):
        StaticURLParser.__init__( self, directory )
        self.cache_seconds = cache_seconds
    def __call__( self, environ, start_response ):
        path_info = environ.get('PATH_INFO', '')
        if not path_info:
            #See if this is a static file hackishly mapped.
            if os.path.exists(self.directory) and os.path.isfile(self.directory):
                app = fileapp.FileApp(self.directory)
                if self.cache_seconds:
                    app.cache_control( max_age = int( self.cache_seconds ) )
                return app(environ, start_response)
            return self.add_slash(environ, start_response)
        if path_info == '/':
            # @@: This should obviously be configurable
            filename = 'index.html'
        else:
            filename = request.path_info_pop(environ)
        full = os.path.join(self.directory, filename)
        if not os.path.exists(full):
            return self.not_found(environ, start_response)
        if os.path.isdir(full):
            # @@: Cache?
            return self.__class__(full)(environ, start_response)
        if environ.get('PATH_INFO') and environ.get('PATH_INFO') != '/':
            return self.error_extra_path(environ, start_response)
        if_none_match = environ.get('HTTP_IF_NONE_MATCH')
        if if_none_match:
            mytime = os.stat(full).st_mtime
            if str(mytime) == if_none_match:
                headers = []
                ETAG.update(headers, mytime)
                start_response('304 Not Modified',headers)
                return [''] # empty body
        app = fileapp.FileApp(full)
        if self.cache_seconds:
            app.cache_control( max_age = int( self.cache_seconds ) )
        return app(environ, start_response)

def make_static( global_conf, document_root, cache_seconds=None ):
    return CacheableStaticURLParser( document_root, cache_seconds )
