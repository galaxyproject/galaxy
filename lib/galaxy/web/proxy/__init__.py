import json
import logging
import os
import time
from collections import namedtuple

import requests

from galaxy.util import (
    sockets,
    sqlite,
    unique_id
)
from galaxy.util.filelock import FileLock
from galaxy.util.lazy_process import LazyProcess, NoOpLazyProcess

log = logging.getLogger(__name__)


DEFAULT_PROXY_TO_HOST = "localhost"
SECURE_COOKIE = "galaxysession"
# Randomly generate a password every launch


class ProxyManager(object):

    valid_update_keys = (
        'host',
        'port',
    )

    def __init__(self, config):
        for option in ["manage_dynamic_proxy", "dynamic_proxy_bind_port",
                       "dynamic_proxy_bind_ip", "dynamic_proxy_debug",
                       "dynamic_proxy_external_proxy", "dynamic_proxy_prefix",
                       "proxy_session_map",
                       "dynamic_proxy", "cookie_path",
                       "dynamic_proxy_golang_noaccess",
                       "dynamic_proxy_golang_clean_interval",
                       "dynamic_proxy_golang_docker_address",
                       "dynamic_proxy_golang_api_key"]:

            setattr(self, option, getattr(config, option))

        if self.manage_dynamic_proxy:
            self.lazy_process = self.__setup_lazy_process(config)
        else:
            self.lazy_process = NoOpLazyProcess()

        if self.dynamic_proxy_golang_api_key is None:
            self.dynamic_proxy_golang_api_key = unique_id()

        self.proxy_ipc = proxy_ipc(config)

    def shutdown(self):
        self.lazy_process.shutdown()

    def setup_proxy(self, trans, host=DEFAULT_PROXY_TO_HOST, port=None, proxy_prefix="", route_name="", container_ids=None, container_interface=None):
        if self.manage_dynamic_proxy:
            log.info("Attempting to start dynamic proxy process")
            log.debug("Cmd: " + ' '.join(self.lazy_process.command_and_args))
            self.lazy_process.start_process()

        if container_ids is None:
            container_ids = []

        authentication = AuthenticationToken(trans)
        proxy_requests = ProxyRequests(host=host, port=port)
        self.proxy_ipc.handle_requests(
            authentication,
            proxy_requests,
            '/%s' % route_name,
            container_ids,
            container_interface,
        )
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

    def update_proxy(self, trans, **kwargs):
        authentication = AuthenticationToken(trans)
        for k in kwargs.keys():
            if k not in self.valid_update_keys:
                raise Exception("Invalid proxy request update key: %s" % k)
        return self.proxy_ipc.update_requests(authentication, **kwargs)

    def query_proxy(self, trans):
        authentication = AuthenticationToken(trans)
        return self.proxy_ipc.fetch_requests(authentication)

    def __setup_lazy_process(self, config):
        launcher = self.proxy_launcher()
        command = launcher.launch_proxy_command(config)
        return LazyProcess(command)

    def proxy_launcher(self):
        if self.dynamic_proxy == "node":
            return NodeProxyLauncher()
        elif self.dynamic_proxy == "golang":
            return GolangProxyLauncher()
        else:
            raise Exception("Unknown proxy type")


class ProxyLauncher(object):

    def launch_proxy_command(self, config):
        raise NotImplementedError()


class NodeProxyLauncher(object):

    def launch_proxy_command(self, config):
        args = [
            "--sessions", config.proxy_session_map,
            "--ip", config.dynamic_proxy_bind_ip,
            "--port", str(config.dynamic_proxy_bind_port),
            "--reverseProxy",
        ]
        if config.dynamic_proxy_debug:
            args.append("--verbose")

        parent_directory = os.path.dirname(__file__)
        path_to_application = os.path.join(parent_directory, "js", "lib", "main.js")
        command = [path_to_application] + args
        return command


class GolangProxyLauncher(object):

    def launch_proxy_command(self, config):
        args = [
            "gxproxy",  # Must be on path. TODO: wheel?
            "--listenAddr", '%s:%d' % (
                config.dynamic_proxy_bind_ip,
                config.dynamic_proxy_bind_port,
            ),
            "--listenPath", "/".join((
                config.cookie_path,
                config.dynamic_proxy_prefix
            )),
            "--cookieName", "galaxysession",
            "--storage", config.proxy_session_map.replace('.sqlite', '.xml'),  # just in case.
            "--apiKey", config.dynamic_proxy_golang_api_key,
            "--noAccess", config.dynamic_proxy_golang_noaccess,
            "--cleanInterval", config.dynamic_proxy_golang_clean_interval,
            "--dockerAddr", config.dynamic_proxy_golang_docker_address,
        ]
        if config.dynamic_proxy_debug:
            args.append("--verbose")
        return args


class AuthenticationToken(object):

    def __init__(self, trans):
        self.cookie_name = SECURE_COOKIE
        self.cookie_value = trans.get_cookie(self.cookie_name)


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
    if config.dynamic_proxy == "node":
        if proxy_session_map.endswith(".sqlite"):
            return SqliteProxyIpc(proxy_session_map)
        else:
            return JsonFileProxyIpc(proxy_session_map)
    elif config.dynamic_proxy == "golang":
        return RestGolangProxyIpc(config)


class ProxyIpc(object):

    def handle_requests(self, authentication, proxy_requests, route_name, container_ids, container_interface):
        raise NotImplementedError()

    def fetch_requests(self, authentication, key):
        raise NotImplementedError()


class JsonFileProxyIpc(object):

    def __init__(self, proxy_session_map):
        self.proxy_session_map = proxy_session_map

    def handle_requests(self, authentication, proxy_requests, route_name, container_ids, container_interface):
        key = authentication.cookie_value
        with FileLock(self.proxy_session_map):
            if not os.path.exists(self.proxy_session_map):
                open(self.proxy_session_map, "w").write("{}")
            json_data = open(self.proxy_session_map, "r").read()
            session_map = json.loads(json_data)
            session_map[key] = {
                'host': proxy_requests.host,
                'port': proxy_requests.port,
                'container_ids': container_ids,
                'container_interface': container_interface,
            }
            new_json_data = json.dumps(session_map)
            open(self.proxy_session_map, "w").write(new_json_data)

    def update_requests(self, authentication, host=None, port=None):
        key = authentication.cookie_value
        with FileLock(self.proxy_session_map):
            session_map = json.load(open(self.proxy_session_map))
            session_map[key]['host'] = host
            session_map[key]['port'] = port
            new_json_data = json.dumps(session_map)
            open(self.proxy_session_map, "w").write(new_json_data)

    def fetch_requests(self, authentication):
        key = authentication.cookie_value
        try:
            with open(self.proxy_session_map) as fh:
                session_map = json.load(fh)
                m = session_map[key]
                return ProxyMapping(
                    host=m['host'],
                    port=m['port'],
                    container_ids=m['container_ids'],
                    container_interface=m['container_interface'],
                )
        except (TypeError, KeyError):
            log.warning('fetch_requests(): invalid key: %s', key)
            return None


class SqliteProxyIpc(object):

    def __init__(self, proxy_session_map):
        self.proxy_session_map = proxy_session_map

    def handle_requests(self, authentication, proxy_requests, route_name, container_ids, container_interface):
        key = authentication.cookie_value
        with FileLock(self.proxy_session_map):
            conn = sqlite.connect(self.proxy_session_map)
            try:
                c = conn.cursor()
                try:
                    # Create table
                    c.execute('''CREATE TABLE gxproxy2
                                 (key text PRIMARY KEY,
                                  host text,
                                  port integer,
                                  container_ids text,
                                  container_interface text)''')
                except Exception:
                    pass
                delete = '''DELETE FROM gxproxy2 WHERE key=?'''
                c.execute(delete, (key,))
                insert = '''INSERT INTO gxproxy2
                            (key, host, port, container_ids, container_interface)
                            VALUES (?, ?, ?, ?, ?)'''
                c.execute(insert,
                          (key,
                           proxy_requests.host,
                           proxy_requests.port,
                           json.dumps(container_ids),
                           container_interface))
                conn.commit()
            finally:
                conn.close()

    def update_requests(self, authentication, host=None, port=None):
        key = authentication.cookie_value
        with FileLock(self.proxy_session_map):
            conn = sqlite.connect(self.proxy_session_map)
            try:
                c = conn.cursor()
                update = '''UPDATE gxproxy2
                            SET host = ?, port = ?
                            WHERE key = ?'''
                c.execute(update, (host, port, key))
                conn.commit()
            finally:
                conn.close()

    def fetch_requests(self, authentication):
        key = authentication.cookie_value
        with FileLock(self.proxy_session_map):
            conn = sqlite.connect(self.proxy_session_map)
            try:
                c = conn.cursor()
                select = '''SELECT host, port, container_ids, container_interface
                            FROM gxproxy2
                            WHERE key=?'''
                c.execute(select, (key,))
                try:
                    host, port, container_ids, container_interface = c.fetchone()
                except TypeError:
                    log.warning('fetch_requests(): invalid key: %s', key)
                    return None
                return ProxyMapping(
                    host=host,
                    port=port,
                    container_ids=json.loads(container_ids),
                    container_interface=container_interface)
            finally:
                conn.close()


class RestGolangProxyIpc(object):

    def __init__(self, config):
        self.config = config
        self.api_url = 'http://127.0.0.1:%s/api?api_key=%s' % (self.config.dynamic_proxy_bind_port, self.config.dynamic_proxy_golang_api_key)

    def handle_requests(self, authentication, proxy_requests, route_name, container_ids, container_interface, sleep=1):
        """Make a POST request to the GO proxy to register a route
        """
        values = {
            'FrontendPath': route_name,
            'BackendAddr': "%s:%s" % (proxy_requests.host, proxy_requests.port),
            'AuthorizedCookie': authentication.cookie_value,
            'ContainerIds': container_ids,
        }

        # Sometimes it takes our poor little proxy a second or two to get
        # going, so if this fails, re-call ourselves with an increased timeout.
        try:
            requests.get(self.api_url, headers={'Content-Type': 'application/json'}, data=json.dumps(values))
        except requests.exceptions.ConnectionError as err:
            log.exception(err)
            if sleep > 5:
                excp = "Could not contact proxy after %s seconds" % sum(range(sleep + 1))
                raise Exception(excp)
            time.sleep(sleep)
            self.handle_requests(authentication, proxy_requests, route_name, container_ids, container_interface, sleep=sleep + 1)


ProxyMapping = namedtuple('ProxyMapping', ['host', 'port', 'container_ids', 'container_interface'])


# TODO: MQ diven proxy?
