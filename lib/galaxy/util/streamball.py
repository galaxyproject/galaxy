"""
A simple wrapper for writing tarballs as a stream.
"""
from __future__ import absolute_import

import logging
import os
import tarfile

from galaxy.exceptions import ObjectNotFound
from .path import safe_walk

log = logging.getLogger(__name__)


class StreamBall(object):
    def __init__(self, mode, members=None):
        self.members = members
        if members is None:
            self.members = []
        self.mode = mode
        self.wsgi_status = None
        self.wsgi_headeritems = None

    def add(self, file, relpath, check_file=False):
        if check_file and len(file) > 0:
            if not os.path.isfile(file):
                raise ObjectNotFound
            else:
                self.members.append((file, relpath))
        else:
            self.members.append((file, relpath))

    def stream(self, environ, start_response):
        response_write = start_response(self.wsgi_status, self.wsgi_headeritems)

        class tarfileobj(object):
            def write(self, *args, **kwargs):
                response_write(*args, **kwargs)
        tf = tarfile.open(mode=self.mode, fileobj=tarfileobj())
        for (file, rel) in self.members:
            tf.add(file, arcname=rel)
        tf.close()
        return []


class ZipBall(object):
    def __init__(self, tmpf, tmpd):
        self._tmpf = tmpf
        self._tmpd = tmpd

    def stream(self, environ, start_response):
        response_write = start_response(self.wsgi_status, self.wsgi_headeritems)
        tmpfh = open(self._tmpf)
        response_write(tmpfh.read())
        tmpfh.close()
        try:
            os.unlink(self._tmpf)
            os.rmdir(self._tmpd)
        except OSError:
            log.exception("Unable to remove temporary library download archive and directory")
        return []


def stream_archive(trans, path, upstream_gzip=False):
    archive_type_string = 'w|gz'
    archive_ext = 'tgz'
    if upstream_gzip:
        archive_type_string = 'w|'
        archive_ext = 'tar'
    archive = StreamBall(mode=archive_type_string)
    for root, directories, files in safe_walk(path):
        for filename in files:
            p = os.path.join(root, filename)
            relpath = os.path.relpath(p, os.path.join(path, os.pardir))
            archive.add(file=os.path.join(path, p), relpath=relpath)
    archive_name = "%s.%s" % (os.path.basename(path), archive_ext)
    trans.response.set_content_type("application/x-tar")
    trans.response.headers["Content-Disposition"] = 'attachment; filename="{}"'.format(archive_name)
    archive.wsgi_status = trans.response.wsgi_status()
    archive.wsgi_headeritems = trans.response.wsgi_headeritems()
    return archive.stream
