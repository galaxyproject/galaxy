from __future__ import absolute_import

import logging

try:
    import requests
except ImportError:
    requests = None

try:
    import requests_toolbelt
    requests_multipart_post_available = True
except ImportError:
    requests_multipart_post_available = False
    requests_toolbelt = None


REQUESTS_UNAVAILABLE_MESSAGE = "Pulsar configured to use requests module - but it is unavailable. Please install requests."
REQUESTS_TOOLBELT_UNAVAILABLE_MESSAGE = "Pulsar configured to use requests_toolbelt module - but it is unavailable. Please install requests_toolbelt."

log = logging.getLogger(__name__)


def post_file(url, path):
    if requests_toolbelt is None:
        raise ImportError(REQUESTS_TOOLBELT_UNAVAILABLE_MESSAGE)

    __ensure_requests()
    m = requests_toolbelt.MultipartEncoder(
        fields={'file': ('filename', open(path, 'rb'))}
    )
    requests.post(url, data=m, headers={'Content-Type': m.content_type})


def get_file(url, path):
    __ensure_requests()
    r = requests.get(url, stream=True)
    with open(path, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)
                f.flush()


def __ensure_requests():
    if requests is None:
        raise ImportError(REQUESTS_UNAVAILABLE_MESSAGE)
