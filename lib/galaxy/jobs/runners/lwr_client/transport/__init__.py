from .standard import Urllib2Transport
from .curl import PycurlTransport
import os


def get_transport(transport_type=None, os_module=os):
    transport_type = __get_transport_type(transport_type, os_module)
    if transport_type == 'urllib':
        transport = Urllib2Transport()
    else:
        transport = PycurlTransport()
    return transport


def __get_transport_type(transport_type, os_module):
    if not transport_type:
        use_curl = os_module.getenv('LWR_CURL_TRANSPORT', "0")
        # If LWR_CURL_TRANSPORT is unset or set to 0, use default,
        # else use curl.
        if use_curl.isdigit() and not int(use_curl):
            transport_type = 'urllib'
        else:
            transport_type = 'curl'
    return transport_type

# TODO: Provide urllib implementation if these unavailable,
# also explore a requests+poster option.
from .curl import get_file
from .curl import post_file

__all__ = [get_transport, get_file, post_file]
