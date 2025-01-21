"""
A simple WSGI application/framework.
"""

import io
import json
import logging
import os
import socket
import tarfile
import tempfile
import time
import types
from http.cookies import (
    CookieError,
    SimpleCookie,
)
from importlib import import_module
from urllib.parse import urljoin

import routes
import webob.compat
import webob.cookies
import webob.exc
import webob.exc as httpexceptions

# We will use some very basic HTTP/wsgi utilities from the paste library
from paste.response import HeaderDict

from galaxy.util import smart_str
from galaxy.util.resources import resource_string

log = logging.getLogger(__name__)

#: time of the most recent server startup
server_starttime = int(time.time())
try:
    meta_json = json.loads(resource_string(__name__, "meta.json"))
    server_starttime = meta_json.get("epoch") or server_starttime
except Exception:
    meta_json = {}


def __resource_with_deleted(self, member_name, collection_name, **kwargs):
    """
    Method to monkeypatch on to routes.mapper.Mapper which does the same thing
    as resource() with the addition of standardized routes for handling
    elements in Galaxy's "deleted but not really deleted" fashion.
    """
    collection_path = f"{kwargs.get('path_prefix', '')}/{collection_name}/deleted"
    member_path = f"{collection_path}/{{id}}"
    self.connect(
        f"deleted_{collection_name}",
        collection_path,
        controller=collection_name,
        action="index",
        deleted=True,
        conditions=dict(method=["GET"]),
    )
    self.connect(
        f"deleted_{member_name}",
        member_path,
        controller=collection_name,
        action="show",
        deleted=True,
        conditions=dict(method=["GET"]),
    )
    self.connect(
        f"undelete_deleted_{member_name}",
        f"{member_path}/undelete",
        controller=collection_name,
        action="undelete",
        conditions=dict(method=["POST"]),
    )
    self.resource(member_name, collection_name, **kwargs)


routes.Mapper.resource_with_deleted = __resource_with_deleted


class WebApplication:
    """
    A simple web application which maps requests to objects using routes,
    and to methods on those objects in the CherryPy style. Thus simple
    argument mapping in the CherryPy style occurs automatically, but more
    complicated encoding of arguments in the PATH_INFO can be performed
    with routes.
    """

    def __init__(self):
        """
        Create a new web application object. To actually connect some
        controllers use `add_controller` and `add_route`. Call
        `finalize_config` when all controllers and routes have been added
        and `__call__` to handle a request (WSGI style).
        """
        self.controllers = {}
        self.api_controllers = {}
        self.mapper = routes.Mapper()
        self.clientside_routes = routes.Mapper(controller_scan=None, register=False)
        # FIXME: The following two options are deprecated and should be
        # removed.  Consult the Routes documentation.
        self.mapper.minimization = True
        self.transaction_factory = DefaultWebTransaction
        # Set if trace logging is enabled
        self.trace_logger = None
        self.session_factories = []

    def add_ui_controller(self, controller_name, controller):
        """
        Add a controller class to this application. A controller class has
        methods which handle web requests. To connect a URL to a controller's
        method use `add_route`.
        """
        log.debug("Enabling '%s' controller, class: %s", controller_name, controller.__class__.__name__)
        self.controllers[controller_name] = controller

    def add_api_controller(self, controller_name, controller):
        log.debug("Enabling '%s' API controller, class: %s", controller_name, controller.__class__.__name__)
        self.api_controllers[controller_name] = controller

    def add_route(self, route, **kwargs):
        """
        Add a route to match a URL with a method. Accepts all keyword
        arguments of `routes.Mapper.connect`. Every route should result in
        at least a controller value which corresponds to one of the
        objects added with `add_controller`. It optionally may yield an
        `action` argument which will be used to locate the method to call
        on the controller. Additional arguments will be passed to the
        method as keyword args.
        """
        self.mapper.connect(route, **kwargs)

    def add_client_route(self, route, controller="root"):
        self.clientside_routes.connect(route, controller=controller, action="client")

    def set_transaction_factory(self, transaction_factory):
        """
        Use the callable `transaction_factory` to create the transaction
        which will be passed to requests.
        """
        self.transaction_factory = transaction_factory

    def finalize_config(self):
        """
        Call when application is completely configured and ready to serve
        requests
        """
        # Create/compile the regular expressions for route mapping
        self.mapper.create_regs(list(self.controllers.keys()))
        self.clientside_routes.create_regs()

    def trace(self, **fields):
        if self.trace_logger:
            self.trace_logger.log("WebApplication", **fields)

    def __call__(self, environ, start_response):
        """
        Call interface as specified by WSGI. Wraps the environment in user
        friendly objects, finds the appropriate method to handle the request
        and calls it.
        """
        # Get request_id (set by RequestIDMiddleware):
        # Used for logging + ensuring request-scoped SQLAlchemy sessions.
        request_id = environ["request_id"]

        if self.trace_logger:
            self.trace_logger.context_set("request_id", request_id)
        self.trace(message="Starting request")

        path_info = environ.get("PATH_INFO", "")

        try:
            for session_factory in self.session_factories:
                session_factory.set_request_id(request_id)  # Start SQLAlchemy session scope
            return self.handle_request(request_id, path_info, environ, start_response)
        finally:
            for session_factory in self.session_factories:
                session_factory.unset_request_id(request_id)  # End SQLAlchemy session scope
            self.trace(message="Handle request finished")
            if self.trace_logger:
                self.trace_logger.context_remove("request_id")

    def _resolve_map_match(self, map_match, path_info, controllers, use_default=True):
        # Get the controller class
        controller_name = map_match.pop("controller", None)
        controller = controllers.get(controller_name, None)
        if controller is None:
            raise webob.exc.HTTPNotFound(f"No controller for {path_info}")
        # Resolve action method on controller
        # This is the easiest way to make the controller/action accessible for
        # url_for invocations.  Specifically, grids.
        action = map_match.pop("action", "index")
        method = getattr(controller, action, None)
        if method is None and not use_default:
            # Skip default, we do this, for example, when we want to fail
            # through to another mapper.
            raise webob.exc.HTTPNotFound(f"No action for {path_info}")
        if method is None:
            # no matching method, we try for a default
            method = getattr(controller, "default", None)
        if method is None:
            raise webob.exc.HTTPNotFound(f"No action for {path_info}")
        # Is the method exposed
        if not getattr(method, "exposed", False):
            raise webob.exc.HTTPNotFound(f"Action not exposed for {path_info}")
        # Is the method callable
        if not callable(method):
            raise webob.exc.HTTPNotFound(f"Action not callable for {path_info}")
        return (controller_name, controller, action, method)

    def handle_request(self, request_id, path_info, environ, start_response, body_renderer=None):
        # Map url using routes
        client_match = self.clientside_routes.match(path_info, environ)
        map_match = self.mapper.match(path_info, environ) or client_match
        if path_info.startswith("/api"):
            environ["is_api_request"] = True
            controllers = self.api_controllers
        else:
            environ["is_api_request"] = False
            controllers = self.controllers
        if map_match is None:
            raise webob.exc.HTTPNotFound(f"No route for {path_info}")
        self.trace(path_info=path_info, map_match=map_match)
        # Setup routes
        rc = routes.request_config()
        rc.mapper = self.mapper
        rc.mapper_dict = map_match
        server_port = environ["SERVER_PORT"]
        if isinstance(server_port, int):
            # Workaround bug in the routes package, which would concatenate this
            # without casting to str in
            # https://github.com/bbangert/routes/blob/c4d5a5fb693ce8dc7cf5dbc591861acfc49d5c23/routes/__init__.py#L73
            environ["SERVER_PORT"] = str(server_port)
        rc.environ = environ
        # Setup the transaction
        trans = self.transaction_factory(environ)
        trans.request_id = request_id
        rc.redirect = trans.response.send_redirect
        # Resolve mapping to controller/method
        try:
            # We don't use default methods if there's a clientside match for this route.
            use_default = client_match is None
            controller_name, controller, action, method = self._resolve_map_match(
                map_match, path_info, controllers, use_default=use_default
            )
        except webob.exc.HTTPNotFound:
            # Failed, let's check client routes
            if not environ["is_api_request"] and client_match is not None:
                controller_name, controller, action, method = self._resolve_map_match(
                    client_match, path_info, controllers
                )
            else:
                raise
        trans.controller = controller_name
        trans.action = action

        # Action can still refer to invalid and/or inaccurate paths here, so we use the actual
        # controller and method names to set the timing key.

        action_tag = getattr(method, "__name__", "default")
        environ["controller_action_key"] = (
            f"{'api' if environ['is_api_request'] else 'web'}.{controller_name}.{action_tag}"
        )
        # Combine mapper args and query string / form args and call
        kwargs = trans.request.params.mixed()
        kwargs.update(map_match)
        # Special key for AJAX debugging, remove to avoid confusing methods
        kwargs.pop("_", None)
        try:
            body = method(trans, **kwargs)
        except Exception as e:
            body = self.handle_controller_exception(e, trans, method, **kwargs)
            if not body:
                trans.response.headers.pop("content-length", None)
                raise
        body_renderer = body_renderer or self._render_body
        return body_renderer(trans, body, environ, start_response)

    def _render_body(self, trans, body, environ, start_response):
        # Now figure out what we got back and try to get it to the browser in
        # a smart way
        if callable(body):
            # Assume the callable is another WSGI application to run
            return body(environ, start_response)
        elif isinstance(body, tarfile.ExFileObject):
            # Stream the tarfile member back to the browser
            body = iterate_file(body)
            start_response(trans.response.wsgi_status(), trans.response.wsgi_headeritems())
            return body
        elif isinstance(body, io.IOBase):
            # Stream the file back to the browser
            return send_file(start_response, trans, body)
        else:
            start_response(trans.response.wsgi_status(), trans.response.wsgi_headeritems())
            return self.make_body_iterable(trans, body)

    def make_body_iterable(self, trans, body):
        if isinstance(body, (types.GeneratorType, list, tuple)):
            # Recursively stream the iterable
            return flatten(body)
        elif body is None:
            # Returns an empty body
            return []
        else:
            # Worst case scenario
            return [smart_str(body)]

    def handle_controller_exception(self, e, trans, method, **kwargs):
        """
        Allow handling of exceptions raised in controller methods.
        """
        return False


class WSGIEnvironmentProperty:
    """
    Descriptor that delegates a property to a key in the environ member of the
    associated object (provides property style access to keys in the WSGI
    environment)
    """

    def __init__(self, key, default=""):
        self.key = key
        self.default = default

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        return obj.environ.get(self.key, self.default)


class LazyProperty:
    """
    Property that replaces itself with a calculated value the first time
    it is used.
    """

    def __init__(self, func):
        self.func = func

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        value = self.func(obj)
        setattr(obj, self.func.__name__, value)
        return value


lazy_property = LazyProperty


class DefaultWebTransaction:
    """
    Wraps the state of a single web transaction (request/response cycle).

    TODO: Provide hooks to allow application specific state to be included
          in here.
    """

    def __init__(self, environ):
        self.environ = environ
        self.request = Request(environ)
        self.response = Response()

    @lazy_property
    def session(self):
        """
        Get the user's session state. This is laze since we rarely use it
        and the creation/serialization cost is high.
        """
        if "com.saddi.service.session" in self.environ:
            return self.environ["com.saddi.service.session"].session
        elif "beaker.session" in self.environ:
            return self.environ["beaker.session"]
        else:
            return None


def _make_file(self, binary=None):
    # For request.params, override cgi.FieldStorage.make_file to create persistent
    # tempfiles.  Necessary for externalizing the upload tool.  It's a little hacky
    # but for performance reasons it's way better to use Paste's tempfile than to
    # create a new one and copy.
    if self._binary_file or self.length >= 0:
        return tempfile.NamedTemporaryFile("wb+", delete=False)
    else:
        return tempfile.NamedTemporaryFile("w+", encoding=self.encoding, newline="\n", delete=False)


def _read_lines(self):
    # Always make a new file
    self.file = self.make_file()
    # Adapt `self.__file = None` to Python name mangling of class-private attributes.
    # We need to patch the original FieldStorage class attribute, not the cgi_FieldStorage
    # class.
    self._FieldStorage__file = None
    if self.outerboundary:
        self.read_lines_to_outerboundary()
    else:
        self.read_lines_to_eof()


webob.compat.cgi_FieldStorage.make_file = _make_file
webob.compat.cgi_FieldStorage.read_lines = _read_lines


class Request(webob.Request):
    """
    Encapsulates an HTTP request.
    """

    def __init__(self, environ):
        """
        Create a new request wrapping the WSGI environment `environ`
        """
        #  self.environ = environ
        webob.Request.__init__(self, environ, charset="utf-8")

    # Properties that are computed and cached on first use

    @lazy_property
    def remote_host(self):
        try:
            return socket.gethostbyname(self.remote_addr)
        except OSError:
            return self.remote_addr

    @lazy_property
    def remote_hostname(self):
        try:
            return socket.gethostbyaddr(self.remote_addr)[0]
        except OSError:
            return self.remote_addr

    @lazy_property
    def cookies(self):
        cookies = SimpleCookie()
        if cookie_header := self.environ.get("HTTP_COOKIE"):
            all_cookies = webob.cookies.parse_cookie(cookie_header)
            galaxy_cookies = {k.decode(): v.decode() for k, v in all_cookies if k.startswith(b"galaxy")}
            if galaxy_cookies:
                try:
                    cookies.load(galaxy_cookies)
                except CookieError:
                    pass
        return cookies

    @lazy_property
    def base(self):
        return f"{self.scheme}://{self.host}"

    @lazy_property
    def url_path(self):
        return urljoin(self.base, self.environ.get("SCRIPT_NAME", ""))

    # @lazy_property
    # def params( self ):
    #     return parse_formvars( self.environ )

    @lazy_property
    def path(self):
        return self.environ.get("SCRIPT_NAME", "") + self.environ["PATH_INFO"]

    @lazy_property
    def browser_url(self):
        return self.base + self.path

    # Descriptors that map properties to the associated environment

    # scheme = WSGIEnvironmentProperty( 'wsgi.url_scheme' )
    # remote_addr = WSGIEnvironmentProperty( 'REMOTE_ADDR' )

    remote_port = WSGIEnvironmentProperty("REMOTE_PORT")

    # method = WSGIEnvironmentProperty( 'REQUEST_METHOD' )
    # script_name = WSGIEnvironmentProperty( 'SCRIPT_NAME' )

    protocol = WSGIEnvironmentProperty("SERVER_PROTOCOL")

    # query_string = WSGIEnvironmentProperty( 'QUERY_STRING' )
    # path_info = WSGIEnvironmentProperty( 'PATH_INFO' )


class Response:
    """
    Describes an HTTP response. Currently very simple since the actual body
    of the request is handled separately.
    """

    def __init__(self):
        """
        Create a new Response defaulting to HTML content and "200 OK" status
        """
        self.status = "200 OK"
        self.headers = HeaderDict({"content-type": "text/html; charset=UTF-8"})
        self.cookies = SimpleCookie()

    def set_content_type(self, type_):
        """
        Sets the Content-Type header
        """
        self.headers["content-type"] = type_

    def get_content_type(self):
        return self.headers.get("content-type", None)

    def send_redirect(self, url):
        """
        Send an HTTP redirect response to (target `url`)
        """
        if "\n" in url or "\r" in url:
            raise webob.exc.HTTPInternalServerError("Invalid redirect URL encountered.")
        raise webob.exc.HTTPFound(location=url, headers=self.wsgi_headeritems())

    def wsgi_headeritems(self):
        """
        Return headers in format appropriate for WSGI `start_response`
        """
        result = self.headers.headeritems()
        # Add cookie to header
        for crumb in self.cookies.values():
            header, value = str(crumb).split(": ", 1)
            result.append((header, value))
        return result

    def wsgi_status(self):
        """
        Return status line in format appropriate for WSGI `start_response`
        """
        if isinstance(self.status, int):
            exception = webob.exc.status_map.get(self.status)
            return f"{exception.code} {exception.title}"
        else:
            return self.status


# ---- Utilities ------------------------------------------------------------

CHUNK_SIZE = 2**16


def send_file(start_response, trans, body):
    # If configured use X-Accel-Redirect header for nginx
    base = trans.app.config.nginx_x_accel_redirect_base
    apache_xsendfile = trans.app.config.apache_xsendfile
    if base:
        trans.response.headers.pop("content-length", None)
        trans.response.headers["X-Accel-Redirect"] = base + os.path.abspath(body.name)
        body = [b""]
    elif apache_xsendfile:
        trans.response.headers.pop("content-length", None)
        trans.response.headers["X-Sendfile"] = os.path.abspath(body.name)
        body = [b""]
    # Fall back on sending the file in chunks
    else:
        trans.response.headers["accept-ranges"] = "bytes"
        start = None
        end = None
        if trans.request.method == "HEAD":
            trans.response.headers["content-length"] = os.path.getsize(body.name)
            body = b""
        if trans.request.range:
            start = int(trans.request.range.start)
            file_size = int(trans.response.headers["content-length"])
            end = int(file_size if end is None else trans.request.range.end)
            trans.response.headers["content-length"] = str(end - start)
            trans.response.headers["content-range"] = f"bytes {start}-{end - 1}/{file_size}"
            trans.response.status = 206
        if body:
            body = iterate_file(body, start, end)
    start_response(trans.response.wsgi_status(), trans.response.wsgi_headeritems())
    return body


def iterate_file(fh, start=None, stop=None):
    """
    Progressively return chunks from `file`.
    """
    length = None
    if start:
        fh.seek(start)
    if stop:
        length = stop - start
    while 1:
        read_size = CHUNK_SIZE
        if length:
            read_size = min(CHUNK_SIZE, length)
            length -= read_size
        chunk = fh.read(read_size)
        if not chunk:
            break
        yield chunk
        if length is not None and length == 0:
            break


def flatten(seq):
    """
    Flatten a possible nested set of iterables
    """
    for x in seq:
        if isinstance(x, (types.GeneratorType, list, tuple)):
            for y in flatten(x):
                yield smart_str(y)
        else:
            yield smart_str(x)


def walk_controller_modules(package_name):
    package = import_module(package_name)
    controller_dir = package.__path__[0]
    for fname in os.listdir(controller_dir):
        if not (fname.startswith("_")) and fname.endswith(".py"):
            name = fname[:-3]
            module_name = f"{package_name}.{name}"
            module = import_module(module_name)
            yield name, module


__all__ = (
    "DefaultWebTransaction",
    "httpexceptions",
    "lazy_property",
    "routes",
    "server_starttime",
    "walk_controller_modules",
    "WebApplication",
)
