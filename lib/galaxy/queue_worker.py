"""
Galaxy control queue and worker.  This is used to handle 'app' control like
reloading the toolbox, etc., across multiple processes.
"""

import importlib
import logging
import socket
import sys
import threading
from inspect import ismodule

from kombu import (
    Consumer,
    Queue,
    uuid,
)
from kombu.mixins import ConsumerProducerMixin
from kombu.pools import producers
from six.moves import reload_module

import galaxy.queues
from galaxy import util

logging.getLogger('kombu').setLevel(logging.WARNING)
log = logging.getLogger(__name__)


def send_local_control_task(app, task, kwargs={}):
    """
    This sends a message to the process-local control worker, which is useful
    for one-time asynchronous tasks like recalculating user disk usage.
    """
    log.info("Queuing async task %s for %s." % (task, app.config.server_name))
    payload = {'task': task,
               'kwargs': kwargs}
    routing_key = 'control.%s' % app.config.server_name
    control_task = ControlTask(app.control_worker)
    control_task.send_task(payload, routing_key, local=True, get_response=False)


def send_control_task(app, task, noop_self=False, get_response=False, routing_key='control.*', kwargs={}):
    """
    This sends a control task out to all processes, useful for things like
    reloading a data table, which needs to happen individually in all
    processes.
    Set noop_self to True to not run task for current process.
    Set get_response to True to wait for and return the task results
    as a list.
    """
    log.info("Sending %s control task." % task)
    payload = {'task': task,
               'kwargs': kwargs}
    if noop_self:
        payload['noop'] = app.config.server_name
    control_task = ControlTask(app.control_worker)
    return control_task.send_task(payload=payload, routing_key=routing_key, get_response=get_response)


class ControlTask(object):

    def __init__(self, control_worker):
        self.control_worker = control_worker
        self.correlation_id = None
        self.callback_queue = Queue(uuid(), exclusive=True, auto_delete=True)
        self.response = object()
        self._response = self.response
        self._connection = None

    @property
    def connection(self):
        if self._connection is None:
            self._connection = self.control_worker.connection.clone()
        return self._connection

    @property
    def control_queues(self):
        return self.control_worker.control_queues

    @property
    def exchange(self):
        return self.control_worker.exchange_queue.exchange

    @property
    def declare_queues(self):
        return self.control_worker.declare_queues

    def on_response(self, message):
        if message.properties['correlation_id'] == self.correlation_id:
            self.response = message.payload['result']

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
            with producers[self.connection].acquire(block=True) as producer:
                producer.publish(
                    payload,
                    exchange=None if local else self.exchange,
                    declare=declare_queues,
                    routing_key=routing_key,
                    reply_to=reply_to,
                    correlation_id=self.correlation_id,
                    retry=True,
                )
            if get_response:
                with Consumer(self.connection, on_message=self.on_response, queues=callback_queue, no_ack=True):
                    while self.response is self._response:
                        self.connection.drain_events(timeout=timeout)
                return self.response
        except socket.timeout:
            log.exception("Error waiting for task: '%s' sent with routing key '%s'", (payload, routing_key))
        except Exception:
            log.exception("Error queueing async task: '%s'. for %s", (payload, routing_key))


# Tasks -- to be reorganized into a separate module as appropriate.  This is
# just an example method.  Ideally this gets pushed into atomic tasks, whether
# where they're currently invoked, or elsewhere.  (potentially using a dispatch
# decorator).

def create_panel_section(app, **kwargs):
    """
    Updates in memory toolbox dictionary.
    """
    log.debug("Updating in-memory tool panel")
    app.toolbox.create_section(kwargs)


def reload_tool(app, **kwargs):
    params = util.Params(kwargs)
    tool_id = params.get('tool_id', None)
    log.debug("Executing reload tool task for %s" % tool_id)
    if tool_id:
        app.toolbox.reload_tool_by_id(tool_id)
    else:
        log.error("Reload tool invoked without tool id.")


def reload_toolbox(app, **kwargs):
    reload_timer = util.ExecutionTimer()
    log.debug("Executing toolbox reload on '%s'", app.config.server_name)
    reload_count = app.toolbox._reload_count
    if hasattr(app, 'tool_cache'):
        app.tool_cache.cleanup()
    _get_new_toolbox(app)
    app.toolbox._reload_count = reload_count + 1
    send_local_control_task(app, 'rebuild_toolbox_search_index')
    log.debug("Toolbox reload %s", reload_timer)


def _get_new_toolbox(app):
    """
    Generate a new toolbox, by constructing a toolbox from the config files,
    and then adding pre-existing data managers from the old toolbox to the new toolbox.
    """
    from galaxy import tools
    from galaxy.tools.special_tools import load_lib_tools
    if hasattr(app, 'tool_shed_repository_cache'):
        app.tool_shed_repository_cache.rebuild()
    tool_configs = app.config.tool_configs
    if app.config.migrated_tools_config not in tool_configs:
        tool_configs.append(app.config.migrated_tools_config)

    new_toolbox = tools.ToolBox(tool_configs, app.config.tool_path, app)
    new_toolbox.data_manager_tools = app.toolbox.data_manager_tools
    app.datatypes_registry.load_datatype_converters(new_toolbox, use_cached=True)
    app.datatypes_registry.load_external_metadata_tool(new_toolbox)
    load_lib_tools(new_toolbox)
    [new_toolbox.register_tool(tool) for tool in new_toolbox.data_manager_tools.values()]
    app.toolbox = new_toolbox


def reload_data_managers(app, **kwargs):
    reload_timer = util.ExecutionTimer()
    from galaxy.tools.data_manager.manager import DataManagers
    log.debug("Executing data managers reload on '%s'", app.config.server_name)
    if hasattr(app, 'tool_shed_repository_cache'):
        app.tool_shed_repository_cache.rebuild()
    app._configure_tool_data_tables(from_shed_config=False)
    reload_tool_data_tables(app)
    reload_count = app.data_managers._reload_count
    app.data_managers = DataManagers(app)
    app.data_managers._reload_count = reload_count + 1
    if hasattr(app, 'tool_cache'):
        app.tool_cache.reset_status()
    if hasattr(app, 'watchers'):
        app.watchers.update_watch_data_table_paths()
    log.debug("Data managers reloaded %s", reload_timer)


def reload_display_application(app, **kwargs):
    display_application_ids = kwargs.get('display_application_ids', None)
    log.debug("Executing display application reload task for %s" % display_application_ids)
    app.datatypes_registry.reload_display_applications(display_application_ids)


def reload_sanitize_whitelist(app):
    log.debug("Executing reload sanitize whitelist control task.")
    app.config.reload_sanitize_whitelist()


def recalculate_user_disk_usage(app, **kwargs):
    user_id = kwargs.get('user_id', None)
    sa_session = app.model.context
    if user_id:
        user = sa_session.query(app.model.User).get(app.security.decode_id(user_id))
        if user:
            user.calculate_and_set_disk_usage()
        else:
            log.error("Recalculate user disk usage task failed, user %s not found" % user_id)
    else:
        log.error("Recalculate user disk usage task received without user_id.")


def reload_tool_data_tables(app, **kwargs):
    params = util.Params(kwargs)
    log.debug("Executing tool data table reload for %s" % params.get('table_names', 'all tables'))
    table_names = app.tool_data_tables.reload_tables(table_names=params.get('table_name', None))
    log.debug("Finished data table reload for %s" % table_names)


def rebuild_toolbox_search_index(app, **kwargs):
    if app.toolbox_search.index_count < app.toolbox._reload_count:
        app.reindex_tool_search()


def reload_job_rules(app, **kwargs):
    reload_timer = util.ExecutionTimer()
    for module in job_rule_modules(app):
        rules_module_name = module.__name__
        for name, module in sys.modules.items():
            if ((name == rules_module_name or name.startswith(rules_module_name + '.'))
                    and ismodule(module)):
                log.debug("Reloading job rules module: %s", name)
                reload_module(module)
    log.debug("Job rules reloaded %s", reload_timer)


def __job_rule_module_names(app):
    rules_module_names = set(['galaxy.jobs.rules'])
    if app.job_config.dynamic_params is not None:
        module_name = app.job_config.dynamic_params.get('rules_module')
        if module_name:
            rules_module_names.add(module_name)
    # Also look for destination level rules_module overrides
    for dest_tuple in app.job_config.destinations.values():
        module_name = dest_tuple[0].params.get('rules_module')
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
    job_lock = kwargs.get('job_lock', False)
    # job_queue is exposed in the root app, but this will be 'fixed' at some
    # point, so we're using the reference from the handler.
    app.job_manager.job_lock = job_lock
    log.info("Administrative Job Lock is now set to %s. Jobs will %s dispatch."
             % (job_lock, "not" if job_lock else "now"))


control_message_to_task = {'create_panel_section': create_panel_section,
                           'reload_tool': reload_tool,
                           'reload_toolbox': reload_toolbox,
                           'reload_data_managers': reload_data_managers,
                           'reload_display_application': reload_display_application,
                           'reload_tool_data_tables': reload_tool_data_tables,
                           'reload_job_rules': reload_job_rules,
                           'admin_job_lock': admin_job_lock,
                           'reload_sanitize_whitelist': reload_sanitize_whitelist,
                           'recalculate_user_disk_usage': recalculate_user_disk_usage,
                           'rebuild_toolbox_search_index': rebuild_toolbox_search_index}


class GalaxyQueueWorker(ConsumerProducerMixin, threading.Thread):
    """
    This is a flexible worker for galaxy's queues.  Each process, web or
    handler, will have one of these used for dispatching so called 'control'
    tasks.
    """

    def __init__(self, app, task_mapping=control_message_to_task):
        super(GalaxyQueueWorker, self).__init__()
        log.info("Initializing %s Galaxy Queue Worker on %s", app.config.server_name, util.mask_password_from_url(app.config.amqp_internal_connection))
        self.daemon = True
        self.connection = app.amqp_internal_connection_obj
        self.app = app
        self.task_mapping = task_mapping
        self.exchange_queue, self.direct_queue = galaxy.queues.control_queues_from_config(self.app.config)
        self.control_queues = [self.exchange_queue, self.direct_queue]
        # Delete messages for the current workers' control queues on startup
        for q in self.control_queues:
            q(self.connection).delete()

    @property
    def declare_queues(self):
        # dynamically produce queues, allows addressing all known processes at a given time
        return galaxy.queues.all_control_queues_for_declare(self.app.config, self.app.application_stack)

    def bind_and_start(self):
        log.info("Binding and starting galaxy control worker for %s", self.app.config.server_name)
        self.start()

    def get_consumers(self, Consumer, channel):
        return [Consumer(queues=[q],
                         callbacks=[self.process_task],
                         accept={'application/json'}) for q in self.control_queues]

    def process_task(self, body, message):
        result = 'NO_RESULT'
        if body['task'] in self.task_mapping:
            if body.get('noop', None) != self.app.config.server_name:
                try:
                    f = self.task_mapping[body['task']]
                    log.info("Instance '%s' received '%s' task, executing now.", self.app.config.server_name, body['task'])
                    result = f(self.app, **body['kwargs'])
                except Exception:
                    # this shouldn't ever throw an exception, but...
                    log.exception("Error running control task type: %s", body['task'])
            else:
                result = 'NO_OP'
        else:
            log.warning("Received a malformed task message:\n%s" % body)
        if message.properties.get('reply_to'):
            self.producer.publish(
                {'result': result},
                exchange='',
                routing_key=message.properties['reply_to'],
                correlation_id=message.properties['correlation_id'],
                serializer='json',
                retry=True,
            )
        message.ack()

    def shutdown(self):
        self.should_stop = True
