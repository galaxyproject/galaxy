import logging

from six import string_types
from six import BytesIO

try:
    from pycurl import Curl, HTTP_CODE
    curl_available = True
except ImportError:
    curl_available = False

import os.path


PYCURL_UNAVAILABLE_MESSAGE = \
    "You are attempting to use the Pycurl version of the Pulsar client but pycurl is unavailable."

NO_SUCH_FILE_MESSAGE = "Attempt to post file %s to URL %s, but file does not exist."
POST_FAILED_MESSAGE = "Failed to post_file properly for url %s, remote server returned status code of %s."
GET_FAILED_MESSAGE = "Failed to get_file properly for url %s, remote server returned status code of %s."

log = logging.getLogger(__name__)


class PycurlTransport(object):

    def execute(self, url, method=None, data=None, input_path=None, output_path=None):
        buf = _open_output(output_path)
        try:
            c = _new_curl_object_for_url(url)
            c.setopt(c.WRITEFUNCTION, buf.write)
            if method:
                c.setopt(c.CUSTOMREQUEST, method)
            if input_path:
                c.setopt(c.UPLOAD, 1)
                c.setopt(c.READFUNCTION, open(input_path, 'rb').read)
                filesize = os.path.getsize(input_path)
                c.setopt(c.INFILESIZE, filesize)
            if data:
                c.setopt(c.POST, 1)
                if isinstance(data, string_types):
                    data = data.encode('UTF-8')
                c.setopt(c.POSTFIELDS, data)
            c.perform()
            if not output_path:
                return buf.getvalue()
        finally:
            buf.close()


def post_file(url, path):
    if not os.path.exists(path):
        # pycurl doesn't always produce a great exception for this,
        # wrap it in a better one.
        message = NO_SUCH_FILE_MESSAGE % (path, url)
        raise Exception(message)
    c = _new_curl_object_for_url(url)
    c.setopt(c.HTTPPOST, [("file", (c.FORM_FILE, path.encode('ascii')))])
    c.perform()
    status_code = c.getinfo(HTTP_CODE)
    if int(status_code) != 200:
        message = POST_FAILED_MESSAGE % (url, status_code)
        raise Exception(message)


def get_file(url, path):
    if path and os.path.exists(path):
        buf = _open_output(path, 'ab')
        size = os.path.getsize(path)
        success_codes = (200, 206)
    else:
        buf = _open_output(path)
        size = 0
        success_codes = (200,)
    try:
        c = _new_curl_object_for_url(url)
        c.setopt(c.WRITEFUNCTION, buf.write)
        if size > 0:
            log.info('transfer of %s will resume at %s bytes', url, size)
            c.setopt(c.RESUME_FROM, size)
        c.perform()
        status_code = int(c.getinfo(HTTP_CODE))
        if status_code not in success_codes:
            message = GET_FAILED_MESSAGE % (url, status_code)
            raise Exception(message)
    finally:
        buf.close()


def _open_output(output_path, mode='wb'):
    return open(output_path, mode) if output_path else BytesIO()


def _new_curl_object_for_url(url):
    c = _new_curl_object()
    c.setopt(c.URL, url.encode('ascii'))
    return c


def _new_curl_object():
    try:
        return Curl()
    except NameError:
        raise ImportError(PYCURL_UNAVAILABLE_MESSAGE)

__all__ = [
    'PycurlTransport',
    'post_file',
    'get_file'
]
