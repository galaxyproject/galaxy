class XForwardedHostMiddleware:
    """
    A WSGI middleware that changes the HTTP host header in the WSGI environ
    based on the X-Forwarded-Host header IF found
    """

    def __init__(self, app, global_conf=None):
        self.app = app

    def __call__(self, environ, start_response):
        x_forwarded_host = environ.get("HTTP_X_FORWARDED_HOST", None)
        if x_forwarded_host:
            environ["ORGINAL_HTTP_HOST"] = environ["HTTP_HOST"]
            environ["HTTP_HOST"] = x_forwarded_host.split(", ", 1)[0]
        x_forwarded_for = environ.get("HTTP_X_FORWARDED_FOR", None)
        if x_forwarded_for:
            environ["ORGINAL_REMOTE_ADDR"] = environ["REMOTE_ADDR"]
            environ["REMOTE_ADDR"] = x_forwarded_for.split(",", 1)[0].strip()
        x_forwarded_proto = environ.get("HTTP_X_FORWARDED_PROTO", None)
        if x_forwarded_proto:
            x_forwarded_proto = x_forwarded_proto.split(",", 1)[0].strip()
        x_url_scheme = environ.get("HTTP_X_URL_SCHEME", x_forwarded_proto)
        if x_url_scheme:
            environ["original_wsgi.url_scheme"] = environ["wsgi.url_scheme"]
            environ["wsgi.url_scheme"] = x_url_scheme
        return self.app(environ, start_response)
