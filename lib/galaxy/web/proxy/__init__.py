import logging
import json
import urllib2

from galaxy.util import sockets
from galaxy.util.lazy_process import LazyProcess, NoOpLazyProcess

log = logging.getLogger( __name__ )


DEFAULT_PROXY_TO_HOST = "localhost"
SECURE_COOKIE = "galaxysession"
API_KEY = "test"


class ProxyManager(object):

    def __init__( self, config ):
        for option in ["manage_dynamic_proxy", "dynamic_proxy_bind_port",
                       "dynamic_proxy_bind_ip", "dynamic_proxy_debug",
                       "dynamic_proxy_external_proxy", "dynamic_proxy_prefix"]:
            setattr( self, option, getattr( config, option ) )
        self.launch_by = "node"  # TODO: Support docker
        if self.manage_dynamic_proxy:
            self.lazy_process = self.__setup_lazy_process( config )
        else:
            self.lazy_process = NoOpLazyProcess()

    def shutdown( self ):
        self.lazy_process.shutdown()

    def setup_proxy( self, trans, host=DEFAULT_PROXY_TO_HOST, port=None, proxy_prefix="", route_name="" ):
        if self.manage_dynamic_proxy:
            log.info("Attempting to start dynamic proxy process")
            self.lazy_process.start_process()

        authentication = AuthenticationToken(trans)
        proxy_requests = ProxyRequests(host=host, port=port)
        self.register_proxy_route(authentication, proxy_requests, route_name)
        # TODO: These shouldn't need to be request.host and request.scheme -
        # though they are reasonable defaults.
        host = trans.request.host
        if ':' in host:
            host = host[0:host.index(':')]
        scheme = trans.request.scheme
        if not self.dynamic_proxy_external_proxy:
            proxy_url = '%s://%s:%d' % (scheme, host, self.dynamic_proxy_bind_port)
        else:
            proxy_url = '%s://%s%s' % (scheme, host, proxy_prefix)
        return {
            'proxy_url': proxy_url,
            'proxied_port': proxy_requests.port,
            'proxied_host': proxy_requests.host,
        }

    def register_proxy_route( self, auth, proxy_requests, route_name ):
        """Make a POST request to the GO proxy to register a route
        """
        url = 'http://127.0.0.1:%s/api?api_key=%s' % (self.dynamic_proxy_bind_port, API_KEY)
        values = {
            'frontend': route_name,
            'backendAddr': "%s:%s" % ( proxy_requests.host, proxy_requests.port ),
            'cookie': auth.cookie_value,
        }

        log.debug(values)
        log.debug(url)

        req = urllib2.Request(url)
        req.add_header('Content-Type', 'application/json')
        urllib2.urlopen(req, json.dumps(values))

    def __setup_lazy_process( self, config ):
        launcher = proxy_launcher(self)
        command = launcher.launch_proxy_command(config)
        return LazyProcess(command)


def proxy_launcher(config):
    return GoProxyLauncher()
    # return NodeProxyLauncher()


class ProxyLauncher(object):

    def launch_proxy_command(self, config):
        raise NotImplementedError()


class GoProxyLauncher(object):

    def launch_proxy_command(self, config):
        args = [
            '/home/hxr/work/galaxy/gxproxy',
            '-api_key', API_KEY,
            '-cookie_name', SECURE_COOKIE,
            '-listen', '%s:%s' % (config.dynamic_proxy_bind_ip, config.dynamic_proxy_bind_port),
            '-storage', config.proxy_session_map,
            '-listen_path', '/galaxy/gie_proxy',
        ]
        return args


class AuthenticationToken(object):

    def __init__(self, trans):
        self.cookie_name = SECURE_COOKIE
        self.cookie_value = trans.get_cookie( self.cookie_name )


class ProxyRequests(object):

    def __init__(self, host=None, port=None):
        if host is None:
            host = DEFAULT_PROXY_TO_HOST
        if port is None:
            port = sockets.unused_port()
            log.info("Obtained unused port %d" % port)
        self.host = host
        self.port = port


# TODO: RESTful API driven proxy?
# TODO: MQ diven proxy?
