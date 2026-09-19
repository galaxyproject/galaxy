import threading
from http.server import (
    BaseHTTPRequestHandler,
    ThreadingHTTPServer,
)

from galaxy.tool_shed.galaxy_install.repository_dependencies.repository_dependency_manager import _request


class RedirectingRequestHandler(BaseHTTPRequestHandler):
    requests: list[tuple[str, bytes]] = []

    def do_POST(self):
        content_length = int(self.headers["Content-Length"])
        body = self.rfile.read(content_length)
        self.requests.append((self.path, body))
        if self.path == "/initial":
            self.send_response(307)
            self.send_header("Location", "/redirected")
            self.end_headers()
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"response")

    def log_message(self, format, *args):
        pass


def test_request_posts_form_through_307_redirect_and_closes():
    server = ThreadingHTTPServer(("127.0.0.1", 0), RedirectingRequestHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    RedirectingRequestHandler.requests = []
    try:
        url = f"http://127.0.0.1:{server.server_port}/initial"
        with _request(url, data={"encoded_str": "encoded-value"}) as response:
            assert response.content == b"response"

        assert RedirectingRequestHandler.requests == [
            ("/initial", b"encoded_str=encoded-value"),
            ("/redirected", b"encoded_str=encoded-value"),
        ]
        assert response.raw.closed
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
