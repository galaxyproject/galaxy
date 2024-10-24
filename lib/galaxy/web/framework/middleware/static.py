import os
from typing import (
    List,
    Tuple,
)

from paste import request
from paste.fileapp import FileApp
from paste.httpheaders import ETAG
from paste.urlparser import StaticURLParser


class CacheableStaticURLParser(StaticURLParser):
    def __init__(self, directory, cache_seconds=None, directory_per_host=None):
        StaticURLParser.__init__(self, directory)
        self.cache_seconds = cache_seconds
        self.directory_per_host = directory_per_host

    def __call__(self, environ, start_response):
        path_info = environ.get("PATH_INFO", "")
        script_name = environ.get("SCRIPT_NAME", "")
        if not path_info:
            # See if this is a static file hackishly mapped.
            if os.path.exists(self.directory) and os.path.isfile(self.directory):
                app = FileApp(self.directory)
                if self.cache_seconds:
                    app.cache_control(max_age=int(self.cache_seconds))
                return app(environ, start_response)
            return self.add_slash(environ, start_response)
        elif path_info == "/":
            # @@: This should obviously be configurable
            filename = "index.html"
        else:
            filename = request.path_info_pop(environ)

        directory = self.directory
        host = environ.get("HTTP_HOST")
        if self.directory_per_host and host:
            for host_key, host_val in self.directory_per_host.items():
                if host_key == host:
                    directory = host_val
                    break

        full = self.normpath(os.path.join(directory, filename))
        if not full.startswith(directory):
            # Out of bounds
            return self.not_found(environ, start_response)

        if not os.path.exists(full):
            return self.not_found(environ, start_response)
        if os.path.isdir(full):
            # @@: Cache?
            return self.__class__(full)(environ, start_response)
        if environ.get("PATH_INFO") and environ.get("PATH_INFO") != "/":
            return self.error_extra_path(environ, start_response)
        if if_none_match := environ.get("HTTP_IF_NONE_MATCH"):
            mytime = os.stat(full).st_mtime
            if str(mytime) == if_none_match:
                headers: List[Tuple[str, str]] = []
                ETAG.update(headers, mytime)
                start_response("304 Not Modified", headers)
                return [""]  # empty body
        app = FileApp(full)
        if self.cache_seconds:
            app.cache_control(max_age=int(self.cache_seconds))
        return app(environ, start_response)


def make_static(global_conf, document_root, cache_seconds=None):
    return CacheableStaticURLParser(document_root, cache_seconds)
