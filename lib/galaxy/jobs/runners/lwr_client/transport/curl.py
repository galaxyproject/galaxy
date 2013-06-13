from cStringIO import StringIO
try:
    from pycurl import Curl
except:
    pass
from os.path import getsize


PYCURL_UNAVAILABLE_MESSAGE = \
    "You are attempting to use the Pycurl version of the LWR client by pycurl is unavailable."


class PycurlTransport(object):

    def execute(self, url, data=None, input_path=None, output_path=None):
        buf = self._open_output(output_path)
        try:
            c = self._new_curl_object()
            c.setopt(c.URL, url.encode('ascii'))
            c.setopt(c.WRITEFUNCTION, buf.write)
            if input_path:
                c.setopt(c.UPLOAD, 1)
                c.setopt(c.READFUNCTION, open(input_path, 'rb').read)
                filesize = getsize(input_path)
                c.setopt(c.INFILESIZE, filesize)
            if data:
                c.setopt(c.POST, 1)
                c.setopt(c.POSTFIELDS, data)
            c.perform()
            if not output_path:
                return buf.getvalue()
        finally:
            buf.close()

    def _new_curl_object(self):
        try:
            return Curl()
        except NameError:
            raise ImportError(PYCURL_UNAVAILABLE_MESSAGE)

    def _open_output(self, output_path):
        return open(output_path, 'wb') if output_path else StringIO()
