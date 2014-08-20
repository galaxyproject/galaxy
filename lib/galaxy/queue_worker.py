"""
Galaxy control queue and worker.  This is used to handle 'app' control like
reloading the toolbox, etc., across multiple processes.
"""

import logging
import threading
import sys

import galaxy.queues
from galaxy import eggs, util
eggs.require('anyjson')
if sys.version_info < (2, 7, 0):
    # Kombu requires importlib and ordereddict to function under Python 2.6.
    eggs.require('importlib')
    eggs.require('ordereddict')
eggs.require('kombu')

from kombu import Connection
from kombu.mixins import ConsumerMixin
from kombu.pools import producers


log = logging.getLogger(__name__)


class GalaxyQueueWorker(ConsumerMixin, threading.Thread):
    """
    This is a flexible worker for galaxy's queues.  Each process, web or
    handler, will have one of these used for dispatching so called 'control'
    tasks.
    """
    def __init__(self, app, queue, task_mapping):
        super(GalaxyQueueWorker, self).__init__()
        log.info("Initalizing Galaxy Queue Worker on %s" % app.config.amqp_internal_connection)
        self.connection = Connection(app.config.amqp_internal_connection)
        self.app = app
        # Eventually we may want different workers w/ their own queues and task
        # mappings.  Right now, there's only the one.
        self.control_queue = queue
        self.task_mapping = task_mapping
        self.declare_queues = galaxy.queues.all_control_queues_for_declare(app.config)
        # TODO we may want to purge the queue at the start to avoid executing
        # stale 'reload_tool', etc messages.  This can happen if, say, a web
        # process goes down and messages get sent before it comes back up.
        # Those messages will no longer be useful (in any current case)

    def get_consumers(self, Consumer, channel):
        return [Consumer(queues=self.control_queue,
                         callbacks=[self.process_task])]

    def process_task(self, body, message):
        if body['task'] in self.task_mapping:
            if body.get('noop', None) != self.app.config.server_name:
                try:
                    f = self.task_mapping[body['task']]
                    log.info("Instance recieved '%s' task, executing now." % body['task'])
                    f(self.app, **body['kwargs'])
                except Exception:
                    # this shouldn't ever throw an exception, but...
                    log.exception("Error running control task type: %s" % body['task'])
        else:
            log.warning("Recieved a malformed task message:\n%s" % body)
        message.ack()

    def shutdown(self):
        self.should_stop = True


def send_control_task(trans, task, noop_self=False, kwargs={}):
    log.info("Sending %s control task." % task)
    payload = {'task': task,
               'kwargs': kwargs}
    if noop_self:
        payload['noop'] = trans.app.config.server_name
    try:
        c = Connection(trans.app.config.amqp_internal_connection)
        with producers[c].acquire(block=True) as producer:
            producer.publish(payload, exchange=galaxy.queues.galaxy_exchange,
                             declare=[galaxy.queues.galaxy_exchange] + galaxy.queues.all_control_queues_for_declare(trans.app.config),
                             routing_key='control')
    except Exception:
        # This is likely connection refused.
        # TODO Use the specific Exception above.
        log.exception("Error sending control task: %s." % payload)


# Tasks -- to be reorganized into a separate module as appropriate.  This is
# just an example method.  Ideally this gets pushed into atomic tasks, whether
# where they're currently invoked, or elsewhere.  (potentially using a dispatch
# decorator).
def reload_tool(app, **kwargs):
    params = util.Params(kwargs)
    tool_id = params.get('tool_id', None)
    log.debug("Executing reload tool task for %s" % tool_id)
    if tool_id:
        app.toolbox.reload_tool_by_id( tool_id )
    else:
        log.error("Reload tool invoked without tool id.")


def reload_tool_data_tables(app, **kwargs):
    params = util.Params(kwargs)
    log.debug("Executing tool data table reload for %s" % params.get('table_names', 'all tables'))
    table_names = app.tool_data_tables.reload_tables( table_names=params.get('table_name', None))
    log.debug("Finished data table reload for %s" % table_names)


def admin_job_lock(app, **kwargs):
    job_lock = kwargs.get('job_lock', False)
    # job_queue is exposed in the root app, but this will be 'fixed' at some
    # point, so we're using the reference from the handler.
    app.job_manager.job_handler.job_queue.job_lock = job_lock
    log.info("Administrative Job Lock is now set to %s. Jobs will %s dispatch."
             % (job_lock, "not" if job_lock else "now"))

control_message_to_task = { 'reload_tool': reload_tool,
                            'reload_tool_data_tables': reload_tool_data_tables,
                            'admin_job_lock': admin_job_lock}
