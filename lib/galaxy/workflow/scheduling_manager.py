import logging
import os
from functools import partial
from xml.etree import ElementTree

import galaxy.workflow.schedulers
from galaxy import model
from galaxy.exceptions import HandlerAssignmentError
from galaxy.util import plugin_config
from galaxy.util.monitors import Monitors
from galaxy.web.stack.handlers import ConfiguresHandlers, HANDLER_ASSIGNMENT_METHODS
from galaxy.web.stack.message import WorkflowSchedulingMessage

log = logging.getLogger(__name__)

DEFAULT_SCHEDULER_ID = "default"  # well actually this should be called DEFAULT_DEFAULT_SCHEDULER_ID...
DEFAULT_SCHEDULER_PLUGIN_TYPE = "core"

EXCEPTION_MESSAGE_SHUTDOWN = "Exception raised while attempting to shutdown workflow scheduler."
EXCEPTION_MESSAGE_NO_SCHEDULERS = "Failed to defined workflow schedulers - no workflow schedulers defined."
EXCEPTION_MESSAGE_NO_DEFAULT_SCHEDULER = "Failed to defined workflow schedulers - no workflow scheduler found for default id '%s'."
EXCEPTION_MESSAGE_DUPLICATE_SCHEDULERS = "Failed to defined workflow schedulers - workflow scheduling plugin id '%s' duplicated."
EXCEPTION_MESSAGE_SERIALIZE = "Parallelization is not desired but handler assignment methods are non-deterministic. Set DB_PREASSIGN in workflow_schedulers_conf.xml."


class WorkflowSchedulingManager(ConfiguresHandlers):
    """ A workflow scheduling manager based loosely on pattern established by
    ``galaxy.manager.JobManager``. Only schedules workflows on handler
    processes.
    """
    DEFAULT_BASE_HANDLER_POOLS = ('workflow-schedulers', 'job-handlers')
    UNSUPPORTED_HANDLER_ASSIGNMENT_METHODS = (
        HANDLER_ASSIGNMENT_METHODS.DB_TRANSACTION_ISOLATION,
        HANDLER_ASSIGNMENT_METHODS.DB_SKIP_LOCKED,
        HANDLER_ASSIGNMENT_METHODS.UWSGI_MULE_MESSAGE,
    )

    def __init__(self, app):
        self.app = app
        self.__handlers_configured = False
        self.workflow_schedulers = {}
        self.active_workflow_schedulers = {}
        # Passive workflow schedulers won't need to be monitored I guess.

        self.request_monitor = None

        self.handlers = {}
        self.handler_assignment_methods_configured = False
        self.handler_assignment_methods = None
        self.handler_max_grab = 1
        self.default_handler_id = None

        self.__plugin_classes = self.__plugins_dict()
        self.__init_schedulers()

        if self._is_workflow_handler():
            log.debug("Starting workflow schedulers")
            self.__start_schedulers()
            if self.active_workflow_schedulers:
                self.__start_request_monitor()

        # When assinging handlers to workflows being queued - use job_conf
        # if not explicit workflow scheduling handlers have be specified or
        # else use those explicit workflow scheduling handlers (on self).
        if self.__handlers_configured:
            self.__handlers_config = self
        else:
            self.__handlers_config = app.job_config

        if self._is_workflow_handler():
            if self.__handlers_config.use_messaging:
                WorkflowSchedulingMessage().bind_default_handler(self, '_handle_message')
                self.app.application_stack.register_message_handler(
                    self._handle_message,
                    name=WorkflowSchedulingMessage.target)
        else:
            # Process should not schedule workflows but should check for any unassigned to handlers
            self.__startup_recovery()

    def __startup_recovery(self):
        sa_session = self.app.model.context
        for invocation_id in model.WorkflowInvocation.poll_unhandled_workflow_ids(sa_session):
            log.info("(%s) Handler unassigned at startup, resubmitting workflow invocation for assignment",
                     invocation_id)
            workflow_invocation = sa_session.query(model.WorkflowInvocation).get(invocation_id)
            self._assign_handler(workflow_invocation)

    def _handle_setup_msg(self, workflow_invocation_id=None):
        sa_session = self.app.model.context
        workflow_invocation = sa_session.query(model.WorkflowInvocation).get(workflow_invocation_id)
        if workflow_invocation.handler is None:
            workflow_invocation.handler = self.app.config.server_name
            sa_session.add(workflow_invocation)
            sa_session.flush()
        else:
            log.warning("(%s) Handler '%s' received setup message for workflow invocation but handler '%s' is"
                        " already assigned, ignoring", workflow_invocation.id, self.app.config.server_name,
                        workflow_invocation.handler)

    def _is_workflow_handler(self):
        # If we have explicitly configured handlers, check them.
        # Else just make sure we are a job handler.
        if self.__handlers_configured:
            is_handler = self.is_handler
        else:
            is_handler = self.app.is_job_handler
        return is_handler

    def _queue_callback(self, workflow_invocation):
        # There isn't an in-memory queue for workflow schedulers, so if MEM_SELF is used just assign with the DB
        workflow_invocation.handler = self.app.config.server_name
        sa_session = self.app.model.context
        sa_session.add(workflow_invocation)
        sa_session.flush()

    def _message_callback(self, workflow_invocation):
        return WorkflowSchedulingMessage(task='setup', workflow_invocation_id=workflow_invocation.id)

    def _assign_handler(self, workflow_invocation):
        # Use random-ish integer history_id to produce a consistent index to pick
        # job handler with.
        random_index = workflow_invocation.history.id
        queue_callback = partial(self._queue_callback, workflow_invocation)
        message_callback = partial(self._message_callback, workflow_invocation)
        if self.app.config.parallelize_workflow_scheduling_within_histories:
            random_index = None
        return self.__handlers_config.assign_handler(
            workflow_invocation, configured=None, index=random_index, queue_callback=queue_callback,
            message_callback=message_callback)

    def shutdown(self):
        exception = None
        for workflow_scheduler in self.workflow_schedulers.values():
            try:
                workflow_scheduler.shutdown()
            except Exception as e:
                exception = exception or e
                log.exception(EXCEPTION_MESSAGE_SHUTDOWN)
        if self.request_monitor:
            try:
                self.request_monitor.shutdown()
            except Exception as e:
                exception = exception or e
                log.exception("Failed to shutdown workflow request monitor.")

        if exception:
            raise exception

    def queue(self, workflow_invocation, request_params):
        workflow_invocation.state = model.WorkflowInvocation.states.NEW
        workflow_invocation.scheduler = request_params.get("scheduler", None) or self.default_scheduler_id
        sa_session = self.app.model.context
        sa_session.add(workflow_invocation)

        # Assign handler (also performs the flush)
        try:
            self._assign_handler(workflow_invocation)
        except HandlerAssignmentError:
            raise RuntimeError("Unable to set a handler for workflow invocation '%s'" % workflow_invocation.id)

        return workflow_invocation

    def __start_schedulers(self):
        for workflow_scheduler in self.workflow_schedulers.values():
            workflow_scheduler.startup(self.app)

    def __plugins_dict(self):
        return plugin_config.plugins_dict(galaxy.workflow.schedulers, 'plugin_type')

    @property
    def __stack_has_pool(self):
        # TODO: In the future it should be possible to map workflows to handlers based on workflow params. When that
        # happens, we'll need to defer pool checks until execution time.
        return any(map(self.app.application_stack.has_pool, self.DEFAULT_BASE_HANDLER_POOLS))

    def __init_schedulers(self):
        config_file = self.app.config.workflow_schedulers_config_file
        use_default_scheduler = False
        if not config_file:
            log.info("No workflow schedulers plugin config file defined, using default scheduler.")
            use_default_scheduler = True
        elif not os.path.exists(config_file):
            log.info("Cannot find workflow schedulers plugin config file '%s', using default scheduler." % config_file)
            use_default_scheduler = True

        if use_default_scheduler:
            self.__init_default_scheduler()
        else:
            plugins_element = ElementTree.parse(config_file).getroot()
            self.__init_schedulers_for_element(plugins_element)

        if not self.__handlers_configured and self.__stack_has_pool:
            # Stack has a pool for us so override inherited config and use the pool
            self.__init_handlers()
            self.__handlers_configured = True

    def __init_default_scheduler(self):
        self.default_scheduler_id = DEFAULT_SCHEDULER_ID
        self.__init_plugin(DEFAULT_SCHEDULER_PLUGIN_TYPE)

    def __init_schedulers_for_element(self, plugins_element):
        plugins_kwds = dict(plugins_element.items())
        self.default_scheduler_id = plugins_kwds.get('default', DEFAULT_SCHEDULER_ID)
        for config_element in plugins_element:
            config_element_tag = config_element.tag
            if config_element_tag == "handlers":
                self.__init_handlers(config_element)

                # Determine the default handler(s)
                self.default_handler_id = self._get_default(self.app.config, config_element, list(self.handlers.keys()))
            else:
                plugin_type = config_element_tag
                plugin_element = config_element
                # Configuring a scheduling plugin...
                plugin_kwds = dict(plugin_element.items())
                workflow_scheduler_id = plugin_kwds.get('id', None)
                self.__init_plugin(plugin_type, workflow_scheduler_id, **plugin_kwds)

        if not self.workflow_schedulers:
            raise Exception(EXCEPTION_MESSAGE_NO_SCHEDULERS)
        if self.default_scheduler_id not in self.workflow_schedulers:
            raise Exception(EXCEPTION_MESSAGE_NO_DEFAULT_SCHEDULER % self.default_scheduler_id)
        if self.app.config.parallelize_workflow_scheduling_within_histories \
                and not self.deterministic_handler_assignment:
            if self.__handlers_configured:
                # There's an explicit configuration, the admin should fix it.
                raise Exception(EXCEPTION_MESSAGE_SERIALIZE)
            else:
                log.warning(EXCEPTION_MESSAGE_SERIALIZE)

    def __init_handlers(self, config_element=None):
        assert not self.__handlers_configured
        self._init_handler_assignment_methods(config_element)
        self._init_handlers(config_element)
        if not self.handler_assignment_methods_configured:
            self._set_default_handler_assignment_methods()
        else:
            self.app.application_stack.init_job_handling(self)
        log.info("Workflow scheduling handler assignment method(s): %s", ', '.join(self.handler_assignment_methods))
        for tag, handlers in [(t, h) for t, h in self.handlers.items() if isinstance(h, list)]:
            log.info("Tag [%s] handlers: %s", tag, ', '.join(handlers))
        self.__handlers_configured = True

    def __init_plugin(self, plugin_type, workflow_scheduler_id=None, **kwds):
        workflow_scheduler_id = workflow_scheduler_id or self.default_scheduler_id

        if workflow_scheduler_id in self.workflow_schedulers:
            raise Exception(EXCEPTION_MESSAGE_DUPLICATE_SCHEDULERS % workflow_scheduler_id)

        workflow_scheduler = self.__plugin_classes[plugin_type](**kwds)
        self.workflow_schedulers[workflow_scheduler_id] = workflow_scheduler
        if isinstance(workflow_scheduler, galaxy.workflow.schedulers.ActiveWorkflowSchedulingPlugin):
            self.active_workflow_schedulers[workflow_scheduler_id] = workflow_scheduler

    def __start_request_monitor(self):
        self.request_monitor = WorkflowRequestMonitor(self.app, self)
        self.app.application_stack.register_postfork_function(self.request_monitor.start)


class WorkflowRequestMonitor(Monitors):

    def __init__(self, app, workflow_scheduling_manager):
        self.app = app
        self.workflow_scheduling_manager = workflow_scheduling_manager
        self._init_monitor_thread(name="WorkflowRequestMonitor.monitor_thread", target=self.__monitor, config=app.config)

    def __monitor(self):
        to_monitor = self.workflow_scheduling_manager.active_workflow_schedulers
        while self.monitor_running:
            for workflow_scheduler_id, workflow_scheduler in to_monitor.items():
                if not self.monitor_running:
                    return

                self.__schedule(workflow_scheduler_id, workflow_scheduler)

            self._monitor_sleep(1)

    def __schedule(self, workflow_scheduler_id, workflow_scheduler):
        invocation_ids = self.__active_invocation_ids(workflow_scheduler_id)
        for invocation_id in invocation_ids:
            log.debug("Attempting to schedule workflow invocation [%s]", invocation_id)
            self.__attempt_schedule(invocation_id, workflow_scheduler)
            if not self.monitor_running:
                return

    def __attempt_schedule(self, invocation_id, workflow_scheduler):
        sa_session = self.app.model.context
        workflow_invocation = sa_session.query(model.WorkflowInvocation).get(invocation_id)

        try:
            if not workflow_invocation or not workflow_invocation.active:
                return False

            # This ensures we're only ever working on the 'first' active
            # workflow invocation in a given history, to force sequential
            # activation.
            if self.app.config.history_local_serial_workflow_scheduling:
                for i in workflow_invocation.history.workflow_invocations:
                    if i.active and i.id < workflow_invocation.id:
                        return False
            workflow_scheduler.schedule(workflow_invocation)
            log.debug("Workflow invocation [%s] scheduled", workflow_invocation.id)
        except Exception:
            # TODO: eventually fail this - or fail it right away?
            log.exception("Exception raised while attempting to schedule workflow request.")
            return False
        finally:
            sa_session.expunge_all()

        # A workflow was obtained and scheduled...
        return True

    def __active_invocation_ids(self, scheduler_id):
        sa_session = self.app.model.context
        handler = self.app.config.server_name
        return model.WorkflowInvocation.poll_active_workflow_ids(
            sa_session,
            scheduler=scheduler_id,
            handler=handler,
        )

    def start(self):
        self.monitor_thread.start()

    def shutdown(self):
        self.shutdown_monitor()
