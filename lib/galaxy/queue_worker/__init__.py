"""
Galaxy control queue and worker.  This is used to handle 'app' control like
reloading the toolbox, etc., across multiple processes.
"""

import importlib
import json
import logging
import math
import socket
import sys
import threading
import time
from inspect import ismodule
from typing import (
    Any,
    cast,
    Optional,
    TYPE_CHECKING,
    TypedDict,
)

from kombu import (
    Consumer,
    Queue,
    uuid,
)
from kombu.mixins import ConsumerProducerMixin
from kombu.pools import producers

import galaxy.queues
from galaxy import util
from galaxy.config import reload_config_options
from galaxy.managers.sse import (
    SSEConnectionManager,
    SSEEvent,
)
from galaxy.model import User
from galaxy.tools import ToolBox
from galaxy.tools.data_manager.manager import DataManagers
from galaxy.tools.special_tools import load_lib_tools

logging.getLogger("kombu").setLevel(logging.WARNING)
log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from galaxy.app import UniverseApplication
    from galaxy.structured_app import (
        MinimalManagerApp,
        StructuredApp,
    )


class NotifyUsersPayload(TypedDict, total=False):
    """Wire contract for the ``notify_users`` control-task kwargs."""

    user_ids: list[int]
    payload: str
    event_id: Optional[str]


class NotifyBroadcastPayload(TypedDict, total=False):
    """Wire contract for the ``notify_broadcast`` control-task kwargs."""

    payload: str
    event_id: Optional[str]


class HistoryUpdatePayload(TypedDict, total=False):
    """Wire contract for the ``history_update`` control-task kwargs.

    ``user_updates`` maps stringified user IDs to lists of (unencoded) history IDs.
    ``session_updates`` is the parallel route for anonymous-owned histories,
    keyed by stringified ``galaxy_session.id`` (the dispatch key never leaves
    the server — browsers never see it). Stringified because AMQP JSON
    serialization coerces dict keys to strings.
    """

    user_updates: dict[str, list[int]]
    session_updates: dict[str, list[int]]
    event_id: Optional[str]


class EntryPointUpdatePayload(TypedDict, total=False):
    """Wire contract for the ``entry_point_update`` control-task kwargs."""

    user_id: int
    event_id: Optional[str]


def send_local_control_task(
    app: "StructuredApp",
    task: str,
    get_response: bool = False,
    kwargs: Optional[dict] = None,
) -> Any:
    """
    This sends a message to the process-local control worker, which is useful
    for one-time asynchronous tasks like recalculating user disk usage.
    """
    if kwargs is None:
        kwargs = {}
    log.info(f"Queuing {'sync' if get_response else 'async'} task {task} for {app.config.server_name}.")
    payload = {"task": task, "kwargs": kwargs}
    routing_key = f"control.{app.config.server_name}@{socket.gethostname()}"
    control_task = ControlTask(app.queue_worker)
    return control_task.send_task(payload, routing_key, local=True, get_response=get_response)


def send_control_task(
    app: "StructuredApp",
    task: str,
    noop_self: bool = False,
    get_response: bool = False,
    routing_key: str = "control.*",
    kwargs: Optional[dict] = None,
    expiration: Optional[int] = None,
    declare_queues: Optional[list[Queue]] = None,
) -> Any:
    """
    This sends a control task out to all processes, useful for things like
    reloading a data table, which needs to happen individually in all
    processes.
    Set noop_self to True to not run task for current process.
    Set get_response to True to wait for and return the task results
    as a list.
    Set expiration to a number of seconds for message TTL.
    Pass ``declare_queues`` to override the default active-processes list —
    e.g. the SSE dispatcher uses this to restrict fan-out to webapp processes.
    """
    if kwargs is None:
        kwargs = {}
    log.info(f"Sending {task} control task.")
    payload = {"task": task, "kwargs": kwargs}
    if noop_self:
        payload["noop"] = app.config.server_name
    control_task = ControlTask(app.queue_worker)
    return control_task.send_task(
        payload=payload,
        routing_key=routing_key,
        get_response=get_response,
        expiration=expiration,
        declare_queues=declare_queues,
    )


class ControlTask:
    def __init__(self, queue_worker):
        self.queue_worker = queue_worker
        self.correlation_id = None
        self.callback_queue = Queue(uuid(), exclusive=True, auto_delete=True)
        self.response = object()
        self._response = self.response
        self._connection = None

    @property
    def connection(self):
        if self._connection is None:
            self._connection = self.queue_worker.connection.clone()
        return self._connection

    @property
    def control_queues(self):
        return self.queue_worker.control_queues

    @property
    def exchange(self):
        return self.queue_worker.exchange_queue.exchange

    @property
    def declare_queues(self):
        return self.queue_worker.declare_queues

    def on_response(self, message):
        if message.properties["correlation_id"] == self.correlation_id:
            self.response = message.payload["result"]

    def send_task(
        self,
        payload: dict,
        routing_key: str,
        local: bool = False,
        get_response: bool = False,
        timeout: int = 10,
        expiration: Optional[int] = None,
        declare_queues: Optional[list[Queue]] = None,
    ):
        if local:
            declare_queues = self.control_queues
        elif declare_queues is None:
            declare_queues = self.declare_queues
        reply_to = None
        callback_queue = []
        if get_response:
            reply_to = self.callback_queue.name
            callback_queue = [self.callback_queue]
            self.correlation_id = uuid()
        try:
            with producers[self.connection].acquire(block=True, timeout=10) as producer:
                producer.publish(
                    payload,
                    exchange=None if local else self.exchange,
                    declare=declare_queues,
                    routing_key=routing_key,
                    reply_to=reply_to,
                    correlation_id=self.correlation_id,
                    retry=True,
                    headers={"epoch": time.time()},
                    expiration=expiration,
                )
            if get_response:
                with Consumer(
                    self.connection,
                    on_message=self.on_response,
                    queues=callback_queue,
                    no_ack=True,
                ):
                    while self.response is self._response:
                        self.connection.drain_events(timeout=timeout)
                return self.response
        except TimeoutError:
            log.exception(
                "Error waiting for task: '%s' sent with routing key '%s'",
                payload,
                routing_key,
            )
        except Exception:
            log.exception("Error queueing async task: '%s'. for %s", payload, routing_key)


# Tasks -- to be reorganized into a separate module as appropriate.  This is
# just an example method.  Ideally this gets pushed into atomic tasks, whether
# where they're currently invoked, or elsewhere.  (potentially using a dispatch
# decorator).


def reconfigure_watcher(app, **kwargs):
    app.database_heartbeat.update_watcher_designation()


def create_panel_section(app, **kwargs):
    """
    Updates in memory toolbox dictionary.
    """
    log.debug("Updating in-memory tool panel")
    app.toolbox.create_section(kwargs)


def reload_tool(app, **kwargs):
    params = util.Params(kwargs)
    tool_id = params.get("tool_id", None)
    log.debug(f"Executing reload tool task for {tool_id}")
    if tool_id:
        app.toolbox.reload_tool_by_id(tool_id)
    else:
        log.error("Reload tool invoked without tool id.")


def reload_toolbox(app: "UniverseApplication", save_integrated_tool_panel: bool = True, **kwargs) -> None:
    reload_timer = util.ExecutionTimer()
    log.debug("Executing toolbox reload on '%s'", app.config.server_name)
    reload_count = app.toolbox._reload_count
    if hasattr(app, "tool_cache"):
        app.tool_cache.cleanup()
    _get_new_toolbox(app, save_integrated_tool_panel)
    app.toolbox._reload_count = reload_count + 1
    send_local_control_task(app, "rebuild_toolbox_search_index")
    log.debug("Toolbox reload %s", reload_timer)


def _get_new_toolbox(app: "UniverseApplication", save_integrated_tool_panel: bool = True) -> None:
    """
    Generate a new toolbox, by constructing a toolbox from the config files,
    and then adding pre-existing data managers from the old toolbox to the new toolbox.
    """
    tool_configs = app.config.tool_configs

    new_toolbox = ToolBox(
        tool_configs,
        app.config.tool_path,
        app,
        save_integrated_tool_panel=save_integrated_tool_panel,
    )
    new_toolbox.data_manager_tools = app.toolbox.data_manager_tools
    app.datatypes_registry.load_datatype_converters(new_toolbox, use_cached=True)
    app.datatypes_registry.load_external_metadata_tool(new_toolbox)
    load_lib_tools(new_toolbox)
    for tool in new_toolbox.data_manager_tools.values():
        new_toolbox.register_tool(tool)
    app._toolbox = new_toolbox


def reload_data_managers(app, **kwargs):
    reload_timer = util.ExecutionTimer()

    log.debug("Executing data managers reload on '%s'", app.config.server_name)
    reload_tool_data_tables(app)
    reload_count = app.data_managers._reload_count + 1
    app.data_managers = DataManagers(app, None, reload_count)
    if hasattr(app, "tool_cache"):
        app.tool_cache.reset_status()
    if hasattr(app, "watchers"):
        app.watchers.update_watch_data_table_paths()
    log.debug("Data managers reloaded %s", reload_timer)


def reload_display_application(app, **kwargs):
    display_application_ids = kwargs.get("display_application_ids", None)
    log.debug(f"Executing display application reload task for {display_application_ids}")
    app.datatypes_registry.reload_display_applications(display_application_ids)


def reload_sanitize_allowlist(app):
    log.debug("Executing reload sanitize allowlist control task.")
    app.config.reload_sanitize_allowlist()


def recalculate_user_disk_usage(app, **kwargs):
    sa_session = app.model.context
    if user_id := kwargs.get("user_id", None):
        user = sa_session.get(User, user_id)
        if user:
            user.calculate_and_set_disk_usage(app.object_store)
        else:
            log.error(f"Recalculate user disk usage task failed, user {user_id} not found")
    else:
        log.error("Recalculate user disk usage task received without user_id.")


def reload_tool_data_tables(app, **kwargs):
    path = kwargs.get("path")
    table_name = kwargs.get("table_name")
    table_names = path or table_name or "all tables"
    log.debug("Executing tool data table reload for %s", table_names)
    table_names = app.tool_data_tables.reload_tables(table_names=table_name, path=path)
    log.debug("Finished data table reload for %s", table_names)


def rebuild_toolbox_search_index(app, **kwargs):
    if app.is_webapp and app.database_heartbeat.is_config_watcher:
        if app.toolbox_search.index_count < app.toolbox._reload_count:
            app.reindex_tool_search()
    else:
        log.debug("App is not a webapp, not building a search index")


def reload_job_rules(app: "MinimalManagerApp", **kwargs):
    reload_timer = util.ExecutionTimer()
    for module in job_rule_modules(app):
        rules_module_name = module.__name__
        for name, module in sys.modules.items():
            if (name == rules_module_name or name.startswith(f"{rules_module_name}.")) and ismodule(module):
                log.debug("Reloading job rules module: %s", name)
                importlib.reload(module)
    log.debug("Job rules reloaded %s", reload_timer)


def reload_core_config(app, **kwargs):
    reload_config_options(app.config)


def reload_tour(app, **kwargs):
    path = kwargs.get("path")
    app.tour_registry.reload_tour(path)
    log.debug("Tour reloaded")


def __job_rule_module_names(app: "MinimalManagerApp"):
    rules_module_names = {"galaxy.jobs.rules"}
    if app.job_config.dynamic_params is not None:
        module_name = app.job_config.dynamic_params.get("rules_module")
        if module_name:
            rules_module_names.add(module_name)
    # Also look for destination level rules_module overrides
    for dest_tuple in app.job_config.destinations.values():
        module_name = dest_tuple[0].params.get("rules_module")
        if module_name:
            rules_module_names.add(module_name)
    return rules_module_names


def job_rule_modules(app: "MinimalManagerApp"):
    rules_module_list = []
    for rules_module_name in __job_rule_module_names(app):
        rules_module = sys.modules.get(rules_module_name, None)
        if not rules_module:
            # if using a non-default module, it's not imported until a JobRunnerMapper is instantiated when the first
            # JobWrapper is created
            rules_module = importlib.import_module(rules_module_name)
        rules_module_list.append(rules_module)
    return rules_module_list


def admin_job_lock(app, **kwargs):
    job_lock = kwargs.get("job_lock", False)
    # job_queue is exposed in the root app, but this will be 'fixed' at some
    # point, so we're using the reference from the handler.
    app.job_manager.job_lock = job_lock
    log.info(f"Administrative Job Lock is now set to {job_lock}. Jobs will {'not' if job_lock else 'now'} dispatch.")


def notify_users(app: "MinimalManagerApp", **kwargs) -> None:
    """Push SSE events to connected users on this worker process."""
    payload = cast(NotifyUsersPayload, kwargs)
    sse_manager = app[SSEConnectionManager]
    event = SSEEvent(
        event="notification_update",
        data=payload.get("payload", "{}"),
        id=payload.get("event_id"),
    )
    for user_id in payload.get("user_ids", []):
        sse_manager.push_to_user(user_id, event)


def notify_broadcast(app: "MinimalManagerApp", **kwargs) -> None:
    """Push SSE broadcast events to all connected clients on this worker process."""
    payload = cast(NotifyBroadcastPayload, kwargs)
    sse_manager = app[SSEConnectionManager]
    event = SSEEvent(
        event="broadcast_update",
        data=payload.get("payload", "{}"),
        id=payload.get("event_id"),
    )
    sse_manager.push_broadcast(event)


def history_update(app: "MinimalManagerApp", **kwargs) -> None:
    """Push SSE history update events to connected users on this worker process.

    Encodes integer history IDs here (not in the monitor) so the manager layer
    stays free of presentation/security concerns. Handles both user-keyed
    routing (registered users) and galaxy_session-keyed routing (anonymous
    histories, which have ``user_id IS NULL``).
    """
    payload = cast(HistoryUpdatePayload, kwargs)
    sse_manager = app[SSEConnectionManager]
    event_id = payload.get("event_id")
    encode = app.security.encode_id
    for user_id_str, history_ids in payload.get("user_updates", {}).items():
        user_id = int(user_id_str)
        encoded_ids = [encode(hid) for hid in history_ids]
        data = json.dumps({"history_ids": encoded_ids})
        event = SSEEvent(event="history_update", data=data, id=event_id)
        sse_manager.push_to_user(user_id, event)
    for session_id_str, history_ids in payload.get("session_updates", {}).items():
        session_id = int(session_id_str)
        encoded_ids = [encode(hid) for hid in history_ids]
        data = json.dumps({"history_ids": encoded_ids})
        event = SSEEvent(event="history_update", data=data, id=event_id)
        sse_manager.push_to_session(session_id, event)


def entry_point_update(app: "MinimalManagerApp", **kwargs) -> None:
    """Push a wake-up SSE event to a single connected user.

    The payload is empty by design: the client refetches ``/api/entry_points``
    (the canonical source) on receipt, so there's nothing to narrow or merge.
    Dropping the IDs from the payload also avoids per-event ``encode_id`` work
    at 1000+ events/s.
    """
    payload = cast(EntryPointUpdatePayload, kwargs)
    sse_manager = app[SSEConnectionManager]
    event = SSEEvent(event="entry_point_update", data="{}", id=payload.get("event_id"))
    sse_manager.push_to_user(int(payload["user_id"]), event)


control_message_to_task = {
    "create_panel_section": create_panel_section,
    "reload_tool": reload_tool,
    "reload_toolbox": reload_toolbox,
    "reload_data_managers": reload_data_managers,
    "reload_display_application": reload_display_application,
    "reload_tool_data_tables": reload_tool_data_tables,
    "reload_job_rules": reload_job_rules,
    "admin_job_lock": admin_job_lock,
    "reload_sanitize_allowlist": reload_sanitize_allowlist,
    "recalculate_user_disk_usage": recalculate_user_disk_usage,
    "rebuild_toolbox_search_index": rebuild_toolbox_search_index,
    "reconfigure_watcher": reconfigure_watcher,
    "reload_tour": reload_tour,
    "reload_core_config": reload_core_config,
    "notify_users": notify_users,
    "notify_broadcast": notify_broadcast,
    "history_update": history_update,
    "entry_point_update": entry_point_update,
}


class GalaxyQueueWorker(ConsumerProducerMixin, threading.Thread):
    """
    This is a flexible worker for galaxy's queues.  Each process, web or
    handler, will have one of these used for dispatching so called 'control'
    tasks.
    """

    def __init__(self, app, task_mapping=None):
        super().__init__()
        log.info(
            "Initializing %s Galaxy Queue Worker on %s",
            app.config.server_name,
            util.mask_password_from_url(app.config.amqp_internal_connection),
        )
        self.daemon = True
        self.connection = app.amqp_internal_connection_obj
        # Force connection instead of lazy-connecting the first time it is required.
        # Fixes `'kombu.transport.sqlalchemy.Message' is not mapped` error.
        self.connection.connect()
        self.connection.release()
        self.app = app
        self.task_mapping = task_mapping or control_message_to_task
        self.exchange_queue = None
        self.direct_queue = None
        self.control_queues = []
        self.epoch = 0

    def send_control_task(
        self,
        task,
        noop_self=False,
        get_response=False,
        routing_key="control.*",
        kwargs=None,
    ):
        return send_control_task(
            app=self.app,
            task=task,
            noop_self=noop_self,
            get_response=get_response,
            routing_key=routing_key,
            kwargs=kwargs,
        )

    def send_local_control_task(self, task, get_response=False, kwargs=None):
        return send_local_control_task(app=self.app, get_response=get_response, task=task, kwargs=kwargs)

    @property
    def declare_queues(self):
        # Dynamically produce queues, allows addressing all known processes at a given time.
        return galaxy.queues.all_control_queues_for_declare(self.app.application_stack)

    def bind_publisher(self):
        """Set up the queues needed to PUBLISH control tasks (no consumer thread).

        Safe to call from any process that needs to produce control messages — notably
        Celery workers, which want to fan out SSE events to web workers but must not
        start a consumer themselves.

        Always (re)binds. A prefork call in ``GalaxyManagerApplication.__init__`` binds
        using the parent's ``config.server_name``; under gunicorn with ``--preload``
        the child's ``set_postfork_server_name`` mutates ``server_name`` to e.g.
        ``main.1`` after fork. ``bind_and_start`` calls back into this so the
        consumer's queues match what post-fork producers declare.
        """
        self.exchange_queue, self.direct_queue = galaxy.queues.control_queues_from_config(self.app.config)
        self.control_queues = [self.exchange_queue, self.direct_queue]

    def bind_and_start(self):
        # This is post-forking, so we got the correct sever name
        log.info(
            "Binding and starting galaxy control worker for %s",
            self.app.config.server_name,
        )
        self.bind_publisher()
        self.epoch = time.time()
        self.start()

    def get_consumers(self, Consumer, channel):
        return [
            Consumer(queues=[q], callbacks=[self.process_task], accept={"application/json"})
            for q in self.control_queues
        ]

    def process_task(self, body, message):
        result = "NO_RESULT"
        task_name = body.get("task")
        statsd_client = self.app.execution_timer_factory.galaxy_statsd_client
        if statsd_client is not None and task_name is not None:
            statsd_client.incr("galaxy.control_queue.task.count", tags={"task": task_name})
        if body["task"] in self.task_mapping:
            if body.get("noop", None) != self.app.config.server_name:
                outcome = "ok"
                handler_start = time.perf_counter() if statsd_client is not None else 0.0
                try:
                    f = self.task_mapping[body["task"]]
                    if message.headers.get("epoch", math.inf) > self.epoch:
                        # Message was created after QueueWorker was started, execute
                        log.info(
                            "Instance '%s' received '%s' task, executing now.",
                            self.app.config.server_name,
                            body["task"],
                        )
                        result = f(self.app, **body["kwargs"])
                    else:
                        # Message was created before QueueWorker was started, ack message but don't run task
                        log.info(
                            "Instance '%s' received '%s' task from the past, discarding it",
                            self.app.config.server_name,
                            body["task"],
                        )
                        result = "NO_OP"
                except Exception:
                    # this shouldn't ever throw an exception, but...
                    outcome = "error"
                    log.exception("Error running control task type: %s", body["task"])
                finally:
                    if statsd_client is not None and task_name is not None:
                        dt_ms = int((time.perf_counter() - handler_start) * 1000)
                        statsd_client.timing(
                            "galaxy.control_queue.task.latency_ms",
                            dt_ms,
                            tags={"task": task_name, "outcome": outcome},
                        )
            else:
                result = "NO_OP"
        else:
            log.warning(f"Received a malformed task message:\n{body}")
        if message.properties.get("reply_to"):
            self.producer.publish(
                {"result": result},
                exchange="",
                routing_key=message.properties["reply_to"],
                correlation_id=message.properties["correlation_id"],
                serializer="json",
                retry=True,
            )
        message.ack()

    def shutdown(self):
        self.should_stop = True
        self.join()
