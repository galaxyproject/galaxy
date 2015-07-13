from __future__ import absolute_import

import logging

try:
    from urllib2 import urlopen
except ImportError:
    from urllib.request import urlopen
try:
    from urllib2 import Request
except ImportError:
    from urllib.request import Request

import poster

log = logging.getLogger(__name__)


if poster is not None:
    poster.streaminghttp.register_openers()


def post_file(url, path):
    try:
        datagen, headers = poster.encode.multipart_encode({"file": open(path, "rb")})
        request = Request(url, datagen, headers)
        return urlopen(request).read()
    except:
        log.exception("problem")
        raise


def get_file(url, path):
    __ensure_poster()
    request = Request(url=url)
    response = urlopen(request)
    with open(path, 'wb') as output:
        while True:
            buffer = response.read(1024)
            if not buffer:
                break
            output.write(buffer)
