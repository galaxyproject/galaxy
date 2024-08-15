"""
Galaxy control queue and worker.  This is used to handle 'app' control like
reloading the toolbox, etc., across multiple processes.
"""

import importlib
import logging
import math
import socket
import sys
import threading
import time
from inspect import ismodule

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
from galaxy.model import User
from galaxy.tools import ToolBox
from galaxy.tools.data_manager.manager import DataManagers
from galaxy.tools.special_tools import load_lib_tools

logging.getLogger("kombu").setLevel(logging.WARNING)
log = logging.getLogger(__name__)


def send_local_control_task(app, task, get_response=False, kwargs=None):
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


def send_control_task(app, task, noop_self=False, get_response=False, routing_key="control.*", kwargs=None):
    """
    This sends a control task out to all processes, useful for things like
    reloading a data table, which needs to happen individually in all
    processes.
    Set noop_self to True to not run task for current process.
    Set get_response to True to wait for and return the task results
    as a list.
    """
    if kwargs is None:
        kwargs = {}
    log.info(f"Sending {task} control task.")
    payload = {"task": task, "kwargs": kwargs}
    if noop_self:
        payload["noop"] = app.config.server_name
    control_task = ControlTask(app.queue_worker)
    return control_task.send_task(payload=payload, routing_key=routing_key, get_response=get_response)


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

    def send_task(self, payload, routing_key, local=False, get_response=False, timeout=10):
        if local:
            declare_queues = self.control_queues
        else:
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
                )
            if get_response:
                with Consumer(self.connection, on_message=self.on_response, queues=callback_queue, no_ack=True):
                    while self.response is self._response:
                        self.connection.drain_events(timeout=timeout)
                return self.response
        except socket.timeout:
            log.exception("Error waiting for task: '%s' sent with routing key '%s'", payload, routing_key)
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


def reload_toolbox(app, save_integrated_tool_panel=True, **kwargs):
    reload_timer = util.ExecutionTimer()
    log.debug("Executing toolbox reload on '%s'", app.config.server_name)
    reload_count = app.toolbox._reload_count
    if hasattr(app, "tool_cache"):
        app.tool_cache.cleanup()
    _get_new_toolbox(app, save_integrated_tool_panel)
    app.toolbox._reload_count = reload_count + 1
    send_local_control_task(app, "rebuild_toolbox_search_index")
    log.debug("Toolbox reload %s", reload_timer)


def _get_new_toolbox(app, save_integrated_tool_panel=True):
    """
    Generate a new toolbox, by constructing a toolbox from the config files,
    and then adding pre-existing data managers from the old toolbox to the new toolbox.
    """
    tool_configs = app.config.tool_configs

    new_toolbox = ToolBox(
        tool_configs, app.config.tool_path, app, save_integrated_tool_panel=save_integrated_tool_panel
    )
    new_toolbox.data_manager_tools = app.toolbox.data_manager_tools
    app.datatypes_registry.load_datatype_converters(new_toolbox, use_cached=True)
    app.datatypes_registry.load_external_metadata_tool(new_toolbox)
    load_lib_tools(new_toolbox)
    [new_toolbox.register_tool(tool) for tool in new_toolbox.data_manager_tools.values()]
    app._toolbox = new_toolbox
    app.toolbox.persist_cache()


def reload_data_managers(app, **kwargs):
    reload_timer = util.ExecutionTimer()

    log.debug("Executing data managers reload on '%s'", app.config.server_name)
    app._configure_tool_data_tables(from_shed_config=False)
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


def reload_job_rules(app, **kwargs):
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


def __job_rule_module_names(app):
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


def job_rule_modules(app):
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

    def send_control_task(self, task, noop_self=False, get_response=False, routing_key="control.*", kwargs=None):
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
        # dynamically produce queues, allows addressing all known processes at a given time
        return galaxy.queues.all_control_queues_for_declare(self.app.application_stack)

    def bind_and_start(self):
        # This is post-forking, so we got the correct sever name
        log.info("Binding and starting galaxy control worker for %s", self.app.config.server_name)
        self.exchange_queue, self.direct_queue = galaxy.queues.control_queues_from_config(self.app.config)
        self.control_queues = [self.exchange_queue, self.direct_queue]
        self.epoch = time.time()
        self.start()

    def get_consumers(self, Consumer, channel):
        return [
            Consumer(queues=[q], callbacks=[self.process_task], accept={"application/json"})
            for q in self.control_queues
        ]

    def process_task(self, body, message):
        result = "NO_RESULT"
        if body["task"] in self.task_mapping:
            if body.get("noop", None) != self.app.config.server_name:
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
                    log.exception("Error running control task type: %s", body["task"])
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
