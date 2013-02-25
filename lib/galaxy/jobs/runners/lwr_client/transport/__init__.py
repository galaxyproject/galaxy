from standard import Urllib2Transport
from curl import PycurlTransport
import os


def get_transport(os_module=os):
    use_curl = os_module.getenv('LWR_CURL_TRANSPORT', "0")
    ## If LWR_CURL_TRANSPORT is unset or set to 0, use default,
    ## else use curl.
    if use_curl.isdigit() and not int(use_curl):
        return Urllib2Transport()
    else:
        return PycurlTransport()


__all__ = [get_transport]
