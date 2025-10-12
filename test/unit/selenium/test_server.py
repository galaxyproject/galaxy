"""Test server infrastructure for running selenium tests locally."""

import http.server
import socketserver
import threading
from pathlib import Path
from typing import Optional


class TestHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom request handler for serving test HTML files."""

    def __init__(self, *args, directory: Optional[str] = None, **kwargs):
        """Initialize handler with custom directory."""
        super().__init__(*args, directory=directory, **kwargs)

    def log_message(self, format: str, *args):
        """Suppress log messages during tests."""
        pass


class TestHTTPServer:
    """Simple HTTP server for serving test HTML pages."""

    def __init__(self, port: int = 0, directory: Optional[Path] = None):
        """
        Initialize test HTTP server.

        Args:
            port: Port to bind to (0 for random available port)
            directory: Directory to serve files from
        """
        self.port = port
        self.directory = directory or Path(__file__).parent / "fixtures"
        self.server: Optional[socketserver.TCPServer] = None
        self.thread: Optional[threading.Thread] = None

    def start(self):
        """Start the HTTP server in a background thread."""

        def handler(*args, **kwargs):
            return TestHTTPRequestHandler(*args, directory=str(self.directory), **kwargs)

        self.server = socketserver.TCPServer(("localhost", self.port), handler)
        self.port = self.server.server_address[1]  # Get actual port if 0 was specified

        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop the HTTP server."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        if self.thread:
            self.thread.join(timeout=5)

    def get_url(self, path: str = "") -> str:
        """
        Get full URL for a given path.

        Args:
            path: Path relative to served directory

        Returns:
            Full URL including protocol, host, port, and path
        """
        path = path.lstrip("/")
        return f"http://localhost:{self.port}/{path}"

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
