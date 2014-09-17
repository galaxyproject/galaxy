try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO
curl_available = True
try:
    from pycurl import Curl
except ImportError:
    curl_available = False
from os.path import getsize


PYCURL_UNAVAILABLE_MESSAGE = \
    "You are attempting to use the Pycurl version of the Pulsar client but pycurl is unavailable."


class PycurlTransport(object):

    def execute(self, url, method=None, data=None, input_path=None, output_path=None):
        buf = _open_output(output_path)
        try:
            c = _new_curl_object()
            c.setopt(c.URL, url.encode('ascii'))
            c.setopt(c.WRITEFUNCTION, buf.write)
            if method:
                c.setopt(c.CUSTOMREQUEST, method)
            if input_path:
                c.setopt(c.UPLOAD, 1)
                c.setopt(c.READFUNCTION, open(input_path, 'rb').read)
                filesize = getsize(input_path)
                c.setopt(c.INFILESIZE, filesize)
            if data:
                c.setopt(c.POST, 1)
                if type(data).__name__ == 'unicode':
                    data = data.encode('UTF-8')
                c.setopt(c.POSTFIELDS, data)
            c.perform()
            if not output_path:
                return buf.getvalue()
        finally:
            buf.close()


def post_file(url, path):
    c = _new_curl_object()
    c.setopt(c.URL, url.encode('ascii'))
    c.setopt(c.HTTPPOST, [("file", (c.FORM_FILE, path.encode('ascii')))])
    c.perform()


def get_file(url, path):
    buf = _open_output(path)
    try:
        c = _new_curl_object()
        c.setopt(c.URL, url.encode('ascii'))
        c.setopt(c.WRITEFUNCTION, buf.write)
        c.perform()
    finally:
        buf.close()


def _open_output(output_path):
    return open(output_path, 'wb') if output_path else StringIO()


def _new_curl_object():
    try:
        return Curl()
    except NameError:
        raise ImportError(PYCURL_UNAVAILABLE_MESSAGE)

___all__ = [PycurlTransport, post_file, get_file]
