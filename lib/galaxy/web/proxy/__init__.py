import logging
import os
import json

from .filelock import FileLock
from galaxy.util import sockets
from galaxy.util.lazy_process import LazyProcess, NoOpLazyProcess
from galaxy.util import sqlite

log = logging.getLogger( __name__ )


DEFAULT_PROXY_TO_HOST = "localhost"
SECURE_COOKIE = "galaxysession"


class ProxyManager(object):

    def __init__( self, config ):
        for option in [ "manage_dynamic_proxy", "dynamic_proxy_bind_port", "dynamic_proxy_bind_ip", "dynamic_proxy_debug", "dynamic_proxy_external_proxy" ]:
            setattr( self, option, getattr( config, option ) )
        self.launch_by = "node"  # TODO: Support docker
        if self.manage_dynamic_proxy:
            self.lazy_process = self.__setup_lazy_process( config )
        else:
            self.lazy_process = NoOpLazyProcess()
        self.proxy_ipc = proxy_ipc(config)

    def shutdown( self ):
        self.lazy_process.shutdown()

    def setup_proxy( self, trans, host=DEFAULT_PROXY_TO_HOST, port=None ):
        if self.manage_dynamic_proxy:
            log.info("Attempting to start dynamic proxy process")
            self.lazy_process.start_process()

        authentication = AuthenticationToken(trans)
        proxy_requests = ProxyRequests(host=host, port=port)
        self.proxy_ipc.handle_requests(authentication, proxy_requests)
        # TODO: These shouldn't need to be request.host and request.scheme -
        # though they are reasonable defaults.
        host = trans.request.host
        if ':' in host:
            host = host[0:host.index(':')]
        scheme = trans.request.scheme
        if not self.dynamic_proxy_external_proxy:
            proxy_url = '%s://%s:%d' % (scheme, host, self.dynamic_proxy_bind_port)
        else:
            proxy_url = '%s://%s' % (scheme, host)
        return {
            'proxy_url': proxy_url,
            'proxied_port': proxy_requests.port,
            'proxied_host': proxy_requests.host,
        }

    def __setup_lazy_process( self, config ):
        launcher = proxy_launcher(self)
        command = launcher.launch_proxy_command(config)
        return LazyProcess(command)


def proxy_launcher(config):
    return NodeProxyLauncher()


class ProxyLauncher(object):

    def launch_proxy_command(self, config):
        raise NotImplementedError()


class NodeProxyLauncher(object):

    def launch_proxy_command(self, config):
        args = [
            "--sessions", config.proxy_session_map,
            "--ip", config.dynamic_proxy_bind_ip,
            "--port", str(config.dynamic_proxy_bind_port),
        ]
        if config.dynamic_proxy_debug:
            args.append("--verbose")

        parent_directory = os.path.dirname( __file__ )
        path_to_application = os.path.join( parent_directory, "js", "lib", "main.js" )
        command = [ path_to_application ] + args
        return command


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


def proxy_ipc(config):
    proxy_session_map = config.proxy_session_map
    if proxy_session_map.endswith(".sqlite"):
        return SqliteProxyIpc(proxy_session_map)
    else:
        return JsonFileProxyIpc(proxy_session_map)


class ProxyIpc(object):

    def handle_requests(self, cookie, host, port):
        raise NotImplementedError()


class JsonFileProxyIpc(object):

    def __init__(self, proxy_session_map):
        self.proxy_session_map = proxy_session_map

    def handle_requests(self, authentication, proxy_requests):
        key = "%s:%s" % ( proxy_requests.host, proxy_requests.port )
        secure_id = authentication.cookie_value
        with FileLock( self.proxy_session_map ):
            if not os.path.exists( self.proxy_session_map ):
                open( self.proxy_session_map, "w" ).write( "{}" )
            json_data = open( self.proxy_session_map, "r" ).read()
            session_map = json.loads( json_data )
            to_remove = []
            for k, value in session_map.items():
                if value == secure_id:
                    to_remove.append( k )
            for k in to_remove:
                del session_map[ k ]
            session_map[ key ] = secure_id
            new_json_data = json.dumps( session_map )
            open( self.proxy_session_map, "w" ).write( new_json_data )


class SqliteProxyIpc(object):

    def __init__(self, proxy_session_map):
        self.proxy_session_map = proxy_session_map

    def handle_requests(self, authentication, proxy_requests):
        key = "%s:%s" % ( proxy_requests.host, proxy_requests.port )
        secure_id = authentication.cookie_value
        with FileLock( self.proxy_session_map ):
            conn = sqlite.connect(self.proxy_session_map)
            try:
                c = conn.cursor()
                try:
                    # Create table
                    c.execute('''CREATE TABLE gxproxy
                                 (key text PRIMARY_KEY, secret text)''')
                except Exception:
                    pass
                insert_tmpl = '''INSERT INTO gxproxy (key, secret) VALUES ('%s', '%s');'''
                insert = insert_tmpl % (key, secure_id)
                c.execute(insert)
                conn.commit()
            finally:
                conn.close()

# TODO: RESTful API driven proxy?
# TODO: MQ diven proxy?
