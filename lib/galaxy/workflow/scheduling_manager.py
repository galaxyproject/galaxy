import os
import time
import logging
import threading

from xml.etree import ElementTree

from galaxy import model
from galaxy.util import plugin_config

import galaxy.workflow.schedulers

log = logging.getLogger( __name__ )

DEFAULT_SCHEDULER_ID = "default"  # well actually this should be called DEFAULT_DEFAULT_SCHEDULER_ID...
DEFAULT_SCHEDULER_PLUGIN_TYPE = "core"

EXCEPTION_MESSAGE_SHUTDOWN = "Exception raised while attempting to shutdown workflow scheduler."
EXCEPTION_MESSAGE_NO_SCHEDULERS = "Failed to defined workflow schedulers - no workflow schedulers defined."
EXCEPTION_MESSAGE_NO_DEFAULT_SCHEDULER = "Failed to defined workflow schedulers - no workflow scheduler found for default id '%s'."
EXCEPTION_MESSAGE_DUPLICATE_SCHEDULERS = "Failed to defined workflow schedulers - workflow scheduling plugin id '%s' duplicated."


class WorkflowSchedulingManager( object ):
    """ A workflow scheduling manager based loosely on pattern established by
    ``galaxy.manager.JobManager``. Only schedules workflows on handler
    processes.
    """

    def __init__( self, app ):
        self.app = app
        self.__job_config = app.job_config
        self.workflow_schedulers = {}
        self.active_workflow_schedulers = {}
        # Passive workflow schedulers won't need to be monitored I guess.

        self.request_monitor = None

        self.__plugin_classes = self.__plugins_dict()
        self.__init_schedulers()

        if self._is_workflow_handler():
            log.debug("Starting workflow schedulers")
            self.__start_schedulers()
            if self.active_workflow_schedulers:
                self.__start_request_monitor()
        else:
            # Process should not schedule workflows - do nothing.
            pass

    # Provide a handler config-like interface by delegating to job handler
    # config. Perhaps it makes sense to let there be explicit workflow
    # handlers?
    def _is_workflow_handler( self ):
        return self.app.is_job_handler()

    def _get_handler( self ):
        return self.__job_config.get_handler( None )

    def shutdown( self ):
        for workflow_scheduler in self.workflow_schedulers.itervalues():
            try:
                workflow_scheduler.shutdown()
            except Exception:
                log.exception( EXCEPTION_MESSAGE_SHUTDOWN )
        if self.request_monitor:
            try:
                self.request_monitor.shutdown()
            except Exception:
                log.exception( "Failed to shutdown workflow request monitor." )

    def queue( self, workflow_invocation, request_params ):
        workflow_invocation.state = model.WorkflowInvocation.states.NEW
        scheduler = request_params.get( "scheduler", None ) or self.default_scheduler_id
        handler = self._get_handler()
        log.info("Queueing workflow invocation for handler [%s]" % handler)

        workflow_invocation.scheduler = scheduler
        workflow_invocation.handler = handler

        sa_session = self.app.model.context
        sa_session.add( workflow_invocation )
        sa_session.flush()
        return workflow_invocation

    def __start_schedulers( self ):
        for workflow_scheduler in self.workflow_schedulers.itervalues():
            workflow_scheduler.startup( self.app )

    def __plugins_dict( self ):
        return plugin_config.plugins_dict( galaxy.workflow.schedulers, 'plugin_type' )

    def __init_schedulers( self ):
        config_file = self.app.config.workflow_schedulers_config_file
        use_default_scheduler = False
        if not config_file:
            log.info( "Not workflow schedulers plugin config file defined, using default scheduler." )
            use_default_scheduler = True
        elif not os.path.exists( config_file ):
            log.info( "Cannot find workflow schedulers plugin config file '%s', using default scheduler." % config_file )
            use_default_scheduler = True

        if use_default_scheduler:
            self.__init_default_scheduler()
        else:
            plugins_element = ElementTree.parse( config_file ).getroot()
            self.__init_schedulers_for_element( plugins_element )

    def __init_default_scheduler( self ):
        self.default_scheduler_id = DEFAULT_SCHEDULER_ID
        self.__init_plugin( DEFAULT_SCHEDULER_PLUGIN_TYPE )

    def __init_schedulers_for_element( self, plugins_element ):
        plugins_kwds = dict( plugins_element.items() )
        self.default_scheduler_id = plugins_kwds.get( 'default', DEFAULT_SCHEDULER_ID )
        for plugin_element in plugins_element:
            plugin_type = plugin_element.tag
            plugin_kwds = dict( plugin_element.items() )
            workflow_scheduler_id = plugin_kwds.get( 'id', None )
            self.__init_plugin( plugin_type, workflow_scheduler_id, **plugin_kwds )

        if not self.workflow_schedulers:
            raise Exception( EXCEPTION_MESSAGE_NO_SCHEDULERS )
        if self.default_scheduler_id not in self.workflow_schedulers:
            raise Exception( EXCEPTION_MESSAGE_NO_DEFAULT_SCHEDULER % self.default_scheduler_id )

    def __init_plugin( self, plugin_type, workflow_scheduler_id=None, **kwds ):
        workflow_scheduler_id = workflow_scheduler_id or self.default_scheduler_id

        if workflow_scheduler_id in self.workflow_schedulers:
            raise Exception( EXCEPTION_MESSAGE_DUPLICATE_SCHEDULERS % workflow_scheduler_id )

        workflow_scheduler = self.__plugin_classes[ plugin_type ]( **kwds )
        self.workflow_schedulers[ workflow_scheduler_id ] = workflow_scheduler
        if isinstance( workflow_scheduler, galaxy.workflow.schedulers.ActiveWorkflowSchedulingPlugin ):
            self.active_workflow_schedulers[ workflow_scheduler_id ] = workflow_scheduler

    def __start_request_monitor( self ):
        self.request_monitor = WorkflowRequestMonitor( self.app, self )


class WorkflowRequestMonitor( object ):

    def __init__( self, app, workflow_scheduling_manager ):
        self.app = app
        self.active = True
        self.workflow_scheduling_manager = workflow_scheduling_manager
        self.monitor_thread = threading.Thread( name="WorkflowRequestMonitor.monitor_thread", target=self.__monitor )
        self.monitor_thread.setDaemon( True )
        self.monitor_thread.start()

    def __monitor( self ):
        to_monitor = self.workflow_scheduling_manager.active_workflow_schedulers
        while self.active:
            for workflow_scheduler_id, workflow_scheduler in to_monitor.iteritems():
                if not self.active:
                    return

                self.__schedule( workflow_scheduler_id, workflow_scheduler )
                # TODO: wake if stopped
                time.sleep(1)

    def __schedule( self, workflow_scheduler_id, workflow_scheduler ):
        invocation_ids = self.__active_invocation_ids( workflow_scheduler_id )
        for invocation_id in invocation_ids:
            self.__attempt_schedule( invocation_id, workflow_scheduler )
            if not self.active:
                return

    def __attempt_schedule( self, invocation_id, workflow_scheduler ):
        sa_session = self.app.model.context
        workflow_invocation = sa_session.query( model.WorkflowInvocation ).get( invocation_id )

        if not workflow_invocation or not workflow_invocation.active:
            return False

        try:
            workflow_scheduler.schedule( workflow_invocation )
        except Exception:
            # TODO: eventually fail this - or fail it right away?
            log.exception( "Exception raised while attempting to schedule workflow request." )
            return False

        # A workflow was obtained and scheduled...
        return True

    def __active_invocation_ids( self, scheduler_id ):
        sa_session = self.app.model.context
        handler = self.app.config.server_name
        return model.WorkflowInvocation.poll_active_workflow_ids(
            sa_session,
            scheduler=scheduler_id,
            handler=handler,
        )

    def shutdown( self ):
        self.active = False
