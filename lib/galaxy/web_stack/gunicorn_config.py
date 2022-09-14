"""
Gunicorn config file based on https://gist.github.com/hynek/ba655c8756924a5febc5285c712a7946
"""
import os
import sys


def on_starting(server):
    """
    Attach a set of IDs that can be temporarily re-used.

    Used on reloads when each worker exists twice.
    """
    server._worker_id_overload = set()


def nworkers_changed(server, new_value, old_value):
    """
    Gets called on startup too.

    Set the current number of workers. Required if we raise the worker count
    temporarily using TTIN because server.cfg.workers won't be updated and if
    one of those workers dies, we wouldn't know the ids go that far.
    """
    server._worker_id_current_workers = new_value


def _next_worker_id(server):
    """
    If there are IDs open for re-use, take one. Else look for a free one.
    """
    if server._worker_id_overload:
        return server._worker_id_overload.pop()

    in_use = {w._worker_id for w in tuple(server.WORKERS.values()) if w.alive}
    free = set(range(1, server._worker_id_current_workers + 1)) - in_use

    return free.pop()


def on_reload(server):
    """
    Add a full set of ids into overload so it can be re-used once.
    """
    server._worker_id_overload = set(range(1, server.cfg.workers + 1))


def pre_fork(server, worker):
    """
    Attach the next free worker_id before forking off.
    """
    worker._worker_id = _next_worker_id(server)


def post_fork(server, worker):
    """
    Put worker_id and listeners into an env variable for further use within the app.
    """
    os.environ["GUNICORN_WORKER_ID"] = str(worker._worker_id)
    os.environ["GUNICORN_LISTENERS"] = ",".join(str(bind) for bind in server.LISTENERS)
    if "--preload" in os.environ.get("GUNICORN_CMD_ARGS", "") or "--preload" in sys.argv:
        from galaxy.web_stack import GunicornApplicationStack

        GunicornApplicationStack.late_postfork_event.set()
