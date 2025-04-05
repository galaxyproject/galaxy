import asyncio
import contextlib
import threading
import time
from typing import Optional

import pytest
import requests
import uvicorn
from fastapi import status
from fastapi.applications import FastAPI
from requests import ReadTimeout
from starlette.middleware.base import BaseHTTPMiddleware

from galaxy.util import sockets

error_encountered: Optional[str] = None


@pytest.fixture()
def reset_global_vars():
    global error_encountered
    error_encountered = None


class SomeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        try:
            return await call_next(request)
        except Exception as e:
            global error_encountered
            error_encountered = str(e)
            raise


class OuterMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        return response


class Server(uvicorn.Server):
    """Uvicorn server in a thread.

    https://stackoverflow.com/a/66589593
    """

    def install_signal_handlers(self):
        pass

    @contextlib.contextmanager
    def run_in_thread(self):
        thread = threading.Thread(target=self.run)
        thread.start()
        try:
            while not self.started:
                time.sleep(1e-3)
            yield
        finally:
            self.should_exit = True
            thread.join()


def setup_fastAPI():
    app = FastAPI()
    # Looks weird, but we need at least 2 middlewares based on BaseHTTPMiddleware to trigger this.
    # xref https://github.com/encode/starlette/discussions/1527#discussion-3893922
    app.add_middleware(SomeMiddleware)
    app.add_middleware(SomeMiddleware)

    @app.get("/")
    async def index():
        await asyncio.sleep(1)
        return

    return app


def test_client_disconnect(reset_global_vars):
    app = setup_fastAPI()
    port = sockets.unused_port()
    server = Server(config=uvicorn.Config(app=app, host="127.0.0.1", port=port))
    with server.run_in_thread():
        try:
            requests.get(f"http://127.0.0.1:{port}/", timeout=0.1)
        except ReadTimeout:
            pass

    assert not error_encountered
