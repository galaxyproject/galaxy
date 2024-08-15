import uuid


class RequestIDMiddleware:
    """
    A WSGI middleware that creates a unique ID for the request and
    puts it in the environment
    """

    def __init__(self, app, global_conf=None):
        self.app = app

    def __call__(self, environ, start_response):
        environ["request_id"] = uuid.uuid1().hex
        return self.app(environ, start_response)
