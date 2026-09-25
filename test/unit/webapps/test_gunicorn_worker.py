"""Tests for the reporting Galaxy adds to uvicorn's gunicorn worker."""

import asyncio
import logging
import signal
from unittest.mock import Mock

from gunicorn.config import Config

from galaxy.web_stack import gunicorn_config
from galaxy.webapps.galaxy.workers import Worker


def make_worker(timeout=300, graceful_timeout=30):
    cfg = Config()
    cfg.set("timeout", timeout)
    cfg.set("graceful_timeout", graceful_timeout)
    gunicorn_log = Mock(
        error_log=logging.getLogger("gunicorn.error"),
        access_log=logging.getLogger("gunicorn.access"),
    )
    # gunicorn hands the worker half of cfg.timeout as its notify interval
    return Worker(0, 1, [], None, timeout / 2, cfg, gunicorn_log)


def make_server(connections=(), tasks=()):
    return Mock(
        server_state=Mock(connections=set(connections), tasks=set(tasks), total_requests=7),
        should_exit=False,
    )


def make_connection(method="GET", path="/api/jobs", query=b"", client=("10.0.0.1", 4242)):
    return Mock(
        scope={"method": method, "path": path, "query_string": query, "client": client},
        cycle=Mock(response_started=False, response_complete=False),
    )


def test_graceful_shutdown_is_bounded_by_graceful_timeout():
    # uvicorn leaves this unset, which makes the drain unbounded
    assert make_worker(graceful_timeout=30).config.timeout_graceful_shutdown == 30


def test_warns_when_graceful_timeout_leaves_no_room_under_timeout(caplog):
    make_worker(timeout=20, graceful_timeout=30)
    assert "leaves no room under timeout" in caplog.text


def test_no_warning_for_production_style_timeouts(caplog):
    make_worker(timeout=600, graceful_timeout=30)
    assert "leaves no room" not in caplog.text


def test_init_signals_restores_the_gunicorn_abort_handler():
    worker = make_worker()
    previous = signal.getsignal(signal.SIGABRT)
    try:
        worker.init_signals()
        # uvicorn's init_signals leaves this as SIG_DFL, which core dumps
        assert signal.getsignal(signal.SIGABRT) == worker.handle_abort
    finally:
        signal.signal(signal.SIGABRT, previous)


def test_summary_names_the_requests_still_in_flight():
    worker = make_worker()
    worker._uvicorn_server = make_server(connections=[make_connection(method="POST", path="/api/histories")])
    summary = worker.in_flight_summary()
    assert "1 open connection(s)" in summary
    assert "POST /api/histories" in summary
    assert "client=10.0.0.1:4242" in summary
    assert "response_complete=False" in summary


def test_summary_includes_the_query_string():
    worker = make_worker()
    worker._uvicorn_server = make_server(connections=[make_connection(query=b"state=running")])
    assert "/api/jobs?state=running" in worker.in_flight_summary()


def test_summary_reports_a_worker_that_never_started_serving():
    assert "not started" in make_worker().in_flight_summary()


def test_reports_survive_a_server_whose_internals_are_unrecognisable():
    # uvicorn internals are not API; a report that raises would mask the abort
    worker = make_worker()
    worker._uvicorn_server = object()
    assert "failed to summarize" in worker.in_flight_summary()
    assert isinstance(worker.in_flight_stacks(), str)


def test_stacks_include_the_current_thread():
    worker = make_worker()
    worker._uvicorn_server = make_server()
    assert "MainThread" in worker.in_flight_stacks()


def test_stacks_unwind_the_await_chain_of_a_running_request():
    async def inner():
        await asyncio.sleep(30)

    async def outer():
        await inner()

    async def run():
        task = asyncio.ensure_future(outer())
        await asyncio.sleep(0)  # let it reach the sleep
        worker = make_worker()
        worker._uvicorn_server = make_server(tasks=[task])
        try:
            # Task.get_stack() alone only yields the outermost coroutine frame
            return worker.in_flight_stacks()
        finally:
            task.cancel()

    stacks = asyncio.run(run())
    assert "in outer" in stacks
    assert "in inner" in stacks


def test_worker_abort_hook_is_a_no_op_for_a_foreign_worker_class():
    gunicorn_config.worker_abort(Mock(spec=[]))


def test_worker_abort_hook_logs_the_summary_at_error(caplog):
    worker = make_worker()
    worker._uvicorn_server = make_server(connections=[make_connection(path="/api/datasets")])
    gunicorn_config.worker_abort(worker)
    errors = [r for r in caplog.records if r.levelname == "ERROR"]
    assert errors and "/api/datasets" in errors[-1].getMessage()
