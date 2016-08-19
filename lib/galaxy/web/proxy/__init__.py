import logging

from .filelock import FileLock
from galaxy.util import sockets
from galaxy.util import sqlite

log = logging.getLogger( __name__ )


DEFAULT_PROXY_TO_HOST = "localhost"
SECURE_COOKIE = "galaxysession"
# Randomly generate a password every launch


# TODO: Use the main Galaxy database or something that scales across nodes, 
#       not sqlite.

class ProxyManager(object):

    def __init__( self, config ):
        for option in [ "proxy_session_map" ]:
            setattr( self, option, getattr( config, option ) )
        # Register lookup function with uwsgi (defined here to capture
        # configuration)
        proxy_session_map = self.proxy_session_map

        def dynamic_proxy_mapper(hostname, galaxy_session):
            db_conn = sqlite.connect( proxy_session_map )
            if galaxy_session:
                # Order by rowid gives us the last row added
                row = db_conn.execute( "select key, secret from gxproxy where secret=? order by rowid desc limit 1", ( galaxy_session, ) ).fetchone()
                if row:
                    return row[0].encode()
                # No match for session found
                return None

        try:
            import uwsgi
        except ImportError:
            uwsgi = None

        if hasattr( uwsgi, 'register_rpc' ):
            uwsgi.register_rpc('galaxy_dynamic_proxy_mapper', dynamic_proxy_mapper)
        else:
            log.warn("Not in a uwsgi server, dynamic proxy will not work.")

    def shutdown( self ):
        pass

    def setup_proxy( self, trans, host=DEFAULT_PROXY_TO_HOST, port=None, proxy_prefix="", route_name="", container_ids=None ):
        if container_ids is None:
            container_ids = []
        authentication = AuthenticationToken(trans)
        proxy_requests = ProxyRequests(host=host, port=port)
        self.handle_requests(
            authentication,
            proxy_requests,
            '/%s' % route_name,
            container_ids
        )
        # TODO: These shouldn't need to be request.host and request.scheme -
        # though they are reasonable defaults.
        host = trans.request.host
        scheme = trans.request.scheme
        proxy_url = '%s://%s%s' % (scheme, host, proxy_prefix)
        return {
            'proxy_url': proxy_url,
            'proxied_port': proxy_requests.port,
            'proxied_host': proxy_requests.host,
        }

    def handle_requests(self, authentication, proxy_requests, route_name, container_ids):
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
