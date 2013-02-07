"""
Support for running a tool in Galaxy via an internal job management system
"""

import os
import sys
import pwd
import time
import copy
import random
import logging
import datetime
import threading
import traceback
import subprocess

import galaxy
from galaxy import util, model
from galaxy.util.bunch import Bunch
from galaxy.datatypes.tabular import *
from galaxy.datatypes.interval import *
# tabular/interval imports appear to be unused.  Clean up?
from galaxy.datatypes import metadata
from galaxy.util.json import from_json_string
from galaxy.util.expressions import ExpressionContext
from galaxy.jobs.actions.post import ActionBox
from galaxy.exceptions import ObjectInvalid
from galaxy.jobs.mapper import JobRunnerMapper
from galaxy.jobs.runners import BaseJobRunner

log = logging.getLogger( __name__ )

# This file, if created in the job's working directory, will be used for
# setting advanced metadata properties on the job and its associated outputs.
# This interface is currently experimental, is only used by the upload tool,
# and should eventually become API'd
TOOL_PROVIDED_JOB_METADATA_FILE = 'galaxy.json'

class Sleeper( object ):
    """
    Provides a 'sleep' method that sleeps for a number of seconds *unless*
    the notify method is called (from a different thread).
    """
    def __init__( self ):
        self.condition = threading.Condition()
    def sleep( self, seconds ):
        self.condition.acquire()
        self.condition.wait( seconds )
        self.condition.release()
    def wake( self ):
        self.condition.acquire()
        self.condition.notify()
        self.condition.release()

class JobDestination( Bunch ):
    """
    Provides details about where a job runs
    """
    def __init__(self, **kwds):
        self['id'] = None
        self['url'] = None
        self['tags'] = None
        self['runner'] = None
        self['legacy'] = False
        self['converted'] = False
        # dict is appropriate (rather than a bunch) since keys may not be valid as attributes
        self['params'] = dict()
        super(JobDestination, self).__init__(**kwds)

        # Store tags as a list
        if self.tags is not None:
            self['tags'] = [ x.strip() for x in self.tags.split(',') ]

class JobToolConfiguration( Bunch ):
    """
    Provides details on what handler and destination a tool should use

    A JobToolConfiguration will have the required attribute 'id' and optional
    attributes 'handler', 'destination', and 'params'
    """
    def __init__(self, **kwds):
        self['handler'] = None
        self['destination'] = None
        self['params'] = dict()
        super(JobToolConfiguration, self).__init__(**kwds)

class JobConfiguration( object ):
    """A parser and interface to advanced job management features.
    
    These features are configured in the job configuration, by default, ``job_conf.xml``
    """
    DEFAULT_NWORKERS = 4
    def __init__(self, app):
        """Parse the job configuration XML.
        """
        self.app = app
        self.runner_plugins = []
        self.handlers = {}
        self.default_handler_id = None
        self.destinations = {}
        self.destination_tags = {}
        self.default_destination_id = None
        self.tools = {}
        self.limits = Bunch()

        # Initialize the config
        try:
            tree = util.parse_xml(self.app.config.job_config_file)
            self.__parse_job_conf_xml(tree)
        except IOError:
            log.warning( 'Job configuration "%s" does not exist, using legacy job configuration from Galaxy config file "%s" instead' % ( self.app.config.job_config_file, self.app.config.config_file ) )
            self.__parse_job_conf_legacy()

    def __parse_job_conf_xml(self, tree):
        """Loads the new-style job configuration from options in the job config file (by default, job_conf.xml).

        :param tree: Object representing the root ``<job_conf>`` object in the job config file.
        :type tree: ``xml.etree.ElementTree.Element``
        """
        root = tree.getroot()
        log.debug('Loading job configuration from %s' % self.app.config.job_config_file)

        # Parse job plugins
        plugins = root.find('plugins')
        if plugins is not None:
            for plugin in self.__findall_with_required(plugins, 'plugin', ('id', 'type', 'load')):
                if plugin.get('type') == 'runner':
                    workers = plugin.get('workers', plugins.get('workers', JobConfiguration.DEFAULT_NWORKERS))
                    self.runner_plugins.append(dict(id=plugin.get('id'), load=plugin.get('load'), workers=int(workers)))
                else:
                    log.error('Unknown plugin type: %s' % plugin.get('type'))
        # Load tasks if configured
        if self.app.config.use_tasked_jobs:
            self.runner_plugins.append(dict(id='tasks', load='tasks', workers=self.app.config.local_task_queue_workers))

        # Parse handlers
        handlers = root.find('handlers')
        if handlers is not None:
            for handler in self.__findall_with_required(handlers, 'handler'):
                id = handler.get('id')
                if id in self.handlers:
                    log.error("Handler '%s' overlaps handler with the same name, ignoring" % id)
                else:
                    log.debug("Read definition for handler '%s'" % id)
                    self.handlers[id] = (id,)
                    if handler.get('tags', None) is not None:
                        for tag in [ x.strip() for x in handler.get('tags').split(',') ]:
                            if tag in self.handlers:
                                self.handlers[tag].append(id)
                            else:
                                self.handlers[tag] = [id]

        # Determine the default handler(s)
        self.default_handler_id = self.__get_default(handlers, self.handlers.keys())

        # Parse destinations
        destinations = root.find('destinations')
        for destination in self.__findall_with_required(destinations, 'destination', ('id', 'runner')):
            id = destination.get('id')
            job_destination = JobDestination(**dict(destination.items()))
            job_destination['params'] = self.__get_params(destination)
            self.destinations[id] = (job_destination,)
            if job_destination.tags is not None:
                for tag in job_destination.tags:
                    if tag not in self.destinations:
                        self.destinations[tag] = []
                    self.destinations[tag].append(job_destination)

        # Determine the default destination
        self.default_destination_id = self.__get_default(destinations, self.destinations.keys())

        # Parse tool mappings
        tools = root.find('tools')
        if tools is not None:
            for tool in self.__findall_with_required(tools, 'tool'):
                # There can be multiple definitions with identical ids, but different params
                id = tool.get('id')
                if id not in self.tools:
                    self.tools[id] = list()
                self.tools[id].append(JobToolConfiguration(**dict(tool.items())))
                self.tools[id][-1]['params'] = self.__get_params(tool)

        self.limits = Bunch(registered_user_concurrent_jobs = None,
                            anonymous_user_concurrent_jobs = None,
                            walltime = None,
                            walltime_delta = None,
                            output_size = None,
                            concurrent_jobs = {})

        # Parse job limits
        limits = root.find('limits')
        if limits is not None:
            for limit in self.__findall_with_required(limits, 'limit', ('type',)):
                type = limit.get('type')
                if type == 'concurrent_jobs':
                    id = limit.get('tag', None) or limit.get('id')
                    self.limits.concurrent_jobs[id] = int(limit.text)
                elif limit.text:
                    self.limits.__dict__[type] = limit.text

        if self.limits.walltime is not None:
            h, m, s = [ int( v ) for v in self.limits.walltime.split( ':' ) ]
            self.limits.walltime_delta = datetime.timedelta( 0, s, 0, 0, m, h )

        log.debug('Done loading job configuration')

    def __parse_job_conf_legacy(self):
        """Loads the old-style job configuration from options in the galaxy config file (by default, universe_wsgi.ini).
        """
        log.debug('Loading job configuration from %s' % self.app.config.config_file)

        # Always load local and lwr
        self.runner_plugins = [dict(id='local', load='local', workers=self.app.config.local_job_queue_workers), dict(id='lwr', load='lwr', workers=self.app.config.cluster_job_queue_workers)]
        # Load tasks if configured
        if self.app.config.use_tasked_jobs:
            self.runner_plugins.append(dict(id='tasks', load='tasks', workers=self.app.config.local_task_queue_workers))
        for runner in self.app.config.start_job_runners:
            self.runner_plugins.append(dict(id=runner, load=runner, workers=self.app.config.cluster_job_queue_workers))

        # Set the handlers
        for id in self.app.config.job_handlers:
            self.handlers[id] = (id,)

        self.handlers['default_job_handlers'] = self.app.config.default_job_handlers
        self.default_handler_id = 'default_job_handlers'

        # Set tool handler configs
        for id, tool_handlers in self.app.config.tool_handlers.items():
            self.tools[id] = list()
            for handler_config in tool_handlers:
                # rename the 'name' key to 'handler'
                handler_config['handler'] = handler_config.pop('name')
                self.tools[id].append(JobToolConfiguration(**handler_config))

        # Set tool runner configs
        for id, tool_runners in self.app.config.tool_runners.items():
            # Might have been created in the handler parsing above
            if id not in self.tools:
                self.tools[id] = list()
            for runner_config in tool_runners:
                url = runner_config['url']
                if url not in self.destinations:
                    # Create a new "legacy" JobDestination - it will have its URL converted to a destination params once the appropriate plugin has loaded
                    self.destinations[url] = (JobDestination(id=url, runner=url.split(':', 1)[0], url=url, legacy=True, converted=False),)
                for tool_conf in self.tools[id]:
                    if tool_conf.params == runner_config.get('params', {}):
                        tool_conf['destination'] = url
                        break
                else:
                    # There was not an existing config (from the handlers section) with the same params
                    # rename the 'url' key to 'destination'
                    runner_config['destination'] = runner_config.pop('url')
                    self.tools[id].append(JobToolConfiguration(**runner_config))

        self.destinations[self.app.config.default_cluster_job_runner] = (JobDestination(id=self.app.config.default_cluster_job_runner, runner=self.app.config.default_cluster_job_runner.split(':', 1)[0], url=self.app.config.default_cluster_job_runner, legacy=True, converted=False),)
        self.default_destination_id = self.app.config.default_cluster_job_runner

        # Set the job limits
        self.limits = Bunch(registered_user_concurrent_jobs = self.app.config.registered_user_job_limit,
                            anonymous_user_concurrent_jobs = self.app.config.anonymous_user_job_limit,
                            walltime = self.app.config.job_walltime,
                            walltime_delta = self.app.config.job_walltime_delta,
                            output_size = self.app.config.output_size_limit,
                            concurrent_jobs = {})

        log.debug('Done loading job configuration')

    def __get_default(self, parent, names):
        """Returns the default attribute set in a parent tag like <handlers> or <destinations>, or return the ID of the child, if there is no explicit default and only one child.

        :param parent: Object representing a tag that may or may not have a 'default' attribute.
        :type parent: ``xml.etree.ElementTree.Element``
        :param names: The list of destination or handler IDs or tags that were loaded.
        :type names: list of str

        :returns: str -- id or tag representing the default.
        """
        rval = parent.get('default')
        if rval is not None:
            # If the parent element has a 'default' attribute, use the id or tag in that attribute
            if rval not in names:
                raise Exception("<%s> default attribute '%s' does not match a defined id or tag in a child element" % (parent.tag, rval))
            log.debug("<%s> default set to child with id or tag '%s'" % (parent.tag, rval))
        elif len(names) == 1:
            log.info("Setting <%s> default to child with id '%s'" % (parent.tag, names[0]))
            rval = names[0]
        else:
            raise Exception("No <%s> default specified, please specify a valid id or tag with the 'default' attribute" % parent.tag)
        return rval

    def __findall_with_required(self, parent, match, attribs=None):
        """Like ``xml.etree.ElementTree.Element.findall()``, except only returns children that have the specified attribs.

        :param parent: Parent element in which to find.
        :type parent: ``xml.etree.ElementTree.Element``
        :param match: Name of child elements to find.
        :type match: str
        :param attribs: List of required attributes in children elements.
        :type attribs: list of str

        :returns: list of ``xml.etree.ElementTree.Element``
        """
        rval = []
        if attribs is None:
            attribs = ('id',)
        for elem in parent.findall(match):
            for attrib in attribs:
                if attrib not in elem.attrib:
                    log.warning("required '%s' attribute is missing from <%s> element" % (attrib, match))
                    break
            else:
                rval.append(elem)
        return rval

    def __get_params(self, parent):
        """Parses any child <param> tags in to a dictionary suitable for persistence.

        :param parent: Parent element in which to find child <param> tags.
        :type parent: ``xml.etree.ElementTree.Element``

        :returns: dict
        """
        rval = {}
        for param in parent.findall('param'):
            rval[param.get('id')] = param.text
        return rval

    @property
    def default_job_tool_configuration(self):
        """The default JobToolConfiguration, used if a tool does not have an explicit defintion in the configuration.  It consists of a reference to the default handler and default destination.

        :returns: JobToolConfiguration -- a representation of a <tool> element that uses the default handler and destination
        """
        return JobToolConfiguration(id='default', handler=self.default_handler_id, destination=self.default_destination_id)

    # Called upon instantiation of a Tool object
    def get_job_tool_configurations(self, ids):
        """Get all configured JobToolConfigurations for a tool ID, or, if given a list of IDs, the JobToolConfigurations for the first id in ``ids`` matching a tool definition.

        .. note::

            You should not mix tool shed tool IDs, versionless tool shed IDs, and tool config tool IDs that refer to the same tool.

        :param ids: Tool ID or IDs to fetch the JobToolConfiguration of.
        :type ids: list or str.
        :returns: list -- JobToolConfiguration Bunches representing <tool> elements matching the specified ID(s).

        Example tool ID strings include:

        * Full tool shed id: ``toolshed.example.org/repos/nate/filter_tool_repo/filter_tool/1.0.0``
        * Tool shed id less version: ``toolshed.example.org/repos/nate/filter_tool_repo/filter_tool``
        * Tool config tool id: ``filter_tool``
        """
        rval = []
        # listify if ids is a single (string) id
        ids = util.listify(ids)
        for id in ids:
            if id in self.tools:
                # If a tool has definitions that include job params but not a
                # definition for jobs without params, include the default
                # config
                for job_tool_configuration in self.tools[id]:
                    if not job_tool_configuration.params:
                        break
                else:
                    rval.append(self.default_job_tool_configuration)
                rval.extend(self.tools[id])
                break
        else:
            rval.append(self.default_job_tool_configuration)
        return rval

    def __get_single_item(self, collection):
        """Given a collection of handlers or destinations, return one item from the collection at random.
        """
        # Done like this to avoid random under the assumption it's faster to avoid it
        if len(collection) == 1:
            return collection[0]
        else:
            return random.choice(collection)

    # This is called by Tool.get_job_handler()
    def get_handler(self, id_or_tag):
        """Given a handler ID or tag, return the provided ID or an ID matching the provided tag

        :param id_or_tag: A handler ID or tag.
        :type id_or_tag: str

        :returns: str -- A valid job handler ID.
        """
        return self.__get_single_item(self.handlers[id_or_tag])

    def get_destination(self, id_or_tag):
        """Given a destination ID or tag, return the JobDestination matching the provided ID or tag

        :param id_or_tag: A destination ID or tag.
        :type id_or_tag: str

        :returns: JobDestination -- A valid destination

        Destinations are deepcopied as they are expected to be passed in to job
        runners, which will modify them for persisting params set at runtime.
        """
        return copy.deepcopy(self.__get_single_item(self.destinations[id_or_tag]))

    def get_destinations(self, id_or_tag):
        """Given a destination ID or tag, return all JobDestinations matching the provided ID or tag

        :param id_or_tag: A destination ID or tag.
        :type id_or_tag: str

        :returns: list or tuple of JobDestinations

        Destinations are not deepcopied, so they should not be passed to
        anything which might modify them.
        """
        return self.destinations.get(id_or_tag, None)

    def get_job_runner_plugins(self):
        """Load all configured job runner plugins

        :returns: list of job runner plugins
        """
        rval = {}
        for runner in self.runner_plugins:
            class_names = []
            module = None
            id = runner['id']
            load = runner['load']
            if ':' in load:
                # Name to load was specified as '<module>:<class>'
                module_name, class_name = load.rsplit(':', 1)
                class_names = [ class_name ]
                module = __import__( module_name )
            else:
                # Name to load was specified as '<module>'
                if '.' not in load:
                    # For legacy reasons, try from galaxy.jobs.runners first if there's no '.' in the name
                    module_name = 'galaxy.jobs.runners.' + load
                    try:
                        module = __import__( module_name )
                    except ImportError:
                        # No such module, we'll retry without prepending galaxy.jobs.runners.
                        # All other exceptions (e.g. something wrong with the module code) will raise
                        pass
                if module is None:
                    # If the name included a '.' or loading from the static runners path failed, try the original name
                    module = __import__( load )
                    module_name = load
            if module is None:
                # Module couldn't be loaded, error should have already been displayed
                continue
            for comp in module_name.split( "." )[1:]:
                module = getattr( module, comp )
            if not class_names:
                # If there's not a ':', we check <module>.__all__ for class names
                try:
                    assert module.__all__
                    class_names = module.__all__
                except AssertionError:
                    log.error( 'Runner "%s" does not contain a list of exported classes in __all__' % load )
                    continue
            for class_name in class_names:
                runner_class = getattr( module, class_name )
                try:
                    assert issubclass(runner_class, BaseJobRunner)
                except TypeError:
                    log.warning("A non-class name was found in __all__, ignoring: %s" % id)
                    continue
                except AssertionError:
                    log.warning("Job runner classes must be subclassed from BaseJobRunner, %s has bases: %s" % (id, runner_class.__bases__))
                    continue
                try:
                    rval[id] = runner_class( self.app, runner['workers'] )
                except TypeError:
                    log.warning( "Job runner '%s:%s' has not been converted to a new-style runner" % ( module_name, class_name ) )
                    rval[id] = runner_class( self.app )
                log.debug( "Loaded job runner '%s:%s' as '%s'" % ( module_name, class_name, id ) )
        return rval

    def is_id(self, collection):
        """Given a collection of handlers or destinations, indicate whether the collection represents a tag or a real ID

        :param collection: A representation of a destination or handler
        :type collection: tuple or list

        :returns: bool
        """
        return type(collection) == tuple

    def is_tag(self, collection):
        """Given a collection of handlers or destinations, indicate whether the collection represents a tag or a real ID

        :param collection: A representation of a destination or handler
        :type collection: tuple or list

        :returns: bool
        """
        return type(collection) == list

    def is_handler(self, server_name):
        """Given a server name, indicate whether the server is a job handler

        :param server_name: The name to check
        :type server_name: str

        :return: bool
        """
        for collection in self.handlers.values():
            if server_name in collection:
                return True
        return False

    def convert_legacy_destinations(self, job_runners):
        """Converts legacy (from a URL) destinations to contain the appropriate runner params defined in the URL.

        :param job_runners: All loaded job runner plugins.
        :type job_runners: list of job runner plugins
        """
        for id, destination in [ ( id, destinations[0] ) for id, destinations in self.destinations.items() if self.is_id(destinations) ]:
            # Only need to deal with real destinations, not members of tags
            if destination.legacy and not destination.converted:
                if destination.runner in job_runners:
                    destination.params = job_runners[destination.runner].url_to_destination(destination.url).params
                    destination.converted = True
                    if destination.params:
                        log.debug("Legacy destination with id '%s', url '%s' converted, got params:" % (id, destination.url))
                        for k, v in destination.params.items():
                            log.debug("    %s: %s" % (k, v))
                    else:
                        log.debug("Legacy destination with id '%s', url '%s' converted, got params:" % (id, destination.url))
                else:
                    log.warning("Legacy destination with id '%s' could not be converted: Unknown runner plugin: %s" % (id, destination.runner))

class JobWrapper( object ):
    """
    Wraps a 'model.Job' with convenience methods for running processes and
    state management.
    """
    def __init__( self, job, queue ):
        self.job_id = job.id
        self.session_id = job.session_id
        self.user_id = job.user_id
        self.tool = queue.app.toolbox.tools_by_id.get( job.tool_id, None )
        self.queue = queue
        self.app = queue.app
        self.sa_session = self.app.model.context
        self.extra_filenames = []
        self.command_line = None
        # Tool versioning variables
        self.version_string_cmd = None
        self.version_string = ""
        self.galaxy_lib_dir = None
        # With job outputs in the working directory, we need the working
        # directory to be set before prepare is run, or else premature deletion
        # and job recovery fail.
        # Create the working dir if necessary
        try:
            self.app.object_store.create(job, base_dir='job_work', dir_only=True, extra_dir=str(self.job_id))
            self.working_directory = self.app.object_store.get_filename(job, base_dir='job_work', dir_only=True, extra_dir=str(self.job_id))
            log.debug('(%s) Working directory for job is: %s' % (self.job_id, self.working_directory))
        except ObjectInvalid:
            raise Exception('Unable to create job working directory, job failure')
        self.output_paths = None
        self.output_hdas_and_paths = None
        self.tool_provided_job_metadata = None
        # Wrapper holding the info required to restore and clean up from files used for setting metadata externally
        self.external_output_metadata = metadata.JobExternalOutputMetadataWrapper( job )
        self.job_runner_mapper = JobRunnerMapper( self, queue.dispatcher.url_to_destination )
        self.params = None
        if job.params:
            self.params = from_json_string( job.params )

        self.__user_system_pwent = None
        self.__galaxy_system_pwent = None

    def can_split( self ):
        # Should the job handler split this job up?
        return self.app.config.use_tasked_jobs and self.tool.parallelism

    def get_job_runner_url( self ):
        log.warning('(%s) Job runner URLs are deprecated, use destinations instead.' % self.job_id)
        return self.job_destination.url

    def get_parallelism(self):
        return self.tool.parallelism

    # legacy naming
    get_job_runner = get_job_runner_url

    @property
    def job_destination(self):
        """Return the JobDestination that this job will use to run.  This will
        either be a configured destination, a randomly selected destination if
        the configured destination was a tag, or a dynamically generated
        destination from the dynamic runner.

        Calling this method for the first time causes the dynamic runner to do
        its calculation, if any.
        
        :returns: ``JobDestination``
        """
        return self.job_runner_mapper.get_job_destination(self.params)

    def get_job( self ):
        return self.sa_session.query( model.Job ).get( self.job_id )

    def get_id_tag(self):
        # For compatability with drmaa, which uses job_id right now, and TaskWrapper
        return self.get_job().get_id_tag()

    def get_param_dict( self ):
        """
        Restore the dictionary of parameters from the database.
        """
        job = self.get_job()
        param_dict = dict( [ ( p.name, p.value ) for p in job.parameters ] )
        param_dict = self.tool.params_from_strings( param_dict, self.app )
        return param_dict

    def get_version_string_path( self ):
        return os.path.abspath(os.path.join(self.app.config.new_file_path, "GALAXY_VERSION_STRING_%s" % self.job_id))

    def prepare( self ):
        """
        Prepare the job to run by creating the working directory and the
        config files.
        """
        self.sa_session.expunge_all() #this prevents the metadata reverting that has been seen in conjunction with the PBS job runner

        if not os.path.exists( self.working_directory ):
            os.mkdir( self.working_directory )

        # Restore parameters from the database
        job = self.get_job()
        if job.user is None and job.galaxy_session is None:
            raise Exception( 'Job %s has no user and no session.' % job.id )

        incoming = dict( [ ( p.name, p.value ) for p in job.parameters ] )
        incoming = self.tool.params_from_strings( incoming, self.app )
        # Do any validation that could not be done at job creation
        self.tool.handle_unvalidated_param_values( incoming, self.app )
        # Restore input / output data lists
        inp_data = dict( [ ( da.name, da.dataset ) for da in job.input_datasets ] )
        out_data = dict( [ ( da.name, da.dataset ) for da in job.output_datasets ] )
        inp_data.update( [ ( da.name, da.dataset ) for da in job.input_library_datasets ] )
        out_data.update( [ ( da.name, da.dataset ) for da in job.output_library_datasets ] )

        # Set up output dataset association for export history jobs. Because job
        # uses a Dataset rather than an HDA or LDA, it's necessary to set up a
        # fake dataset association that provides the needed attributes for
        # preparing a job.
        class FakeDatasetAssociation ( object ):
            def __init__( self, dataset=None ):
                self.dataset = dataset
                self.file_name = dataset.file_name
                self.metadata = dict()
                self.children = []
        special = self.sa_session.query( model.JobExportHistoryArchive ).filter_by( job=job ).first()
        if not special:
            special = self.sa_session.query( model.GenomeIndexToolData ).filter_by( job=job ).first()
        if special:
            out_data[ "output_file" ] = FakeDatasetAssociation( dataset=special.dataset )
            
        # These can be passed on the command line if wanted as $__user_*__
        if job.history and job.history.user:
            user_id = '%d' % job.history.user.id
            user_email = str(job.history.user.email)
            user_name = str(job.history.user.username)
        else:
            user_id = 'Anonymous'
            user_email = 'Anonymous'
            user_name = 'Anonymous'
        incoming['__user_id__'] = incoming['userId'] = user_id
        incoming['__user_email__'] = incoming['userEmail'] = user_email
        incoming['__user_name__'] = user_name
        # Build params, done before hook so hook can use
        param_dict = self.tool.build_param_dict( incoming, inp_data, out_data, self.get_output_fnames(), self.working_directory )
        # Certain tools require tasks to be completed prior to job execution
        # ( this used to be performed in the "exec_before_job" hook, but hooks are deprecated ).
        self.tool.exec_before_job( self.queue.app, inp_data, out_data, param_dict )
        # Run the before queue ("exec_before_job") hook
        self.tool.call_hook( 'exec_before_job', self.queue.app, inp_data=inp_data,
                             out_data=out_data, tool=self.tool, param_dict=incoming)
        self.sa_session.flush()
        # Build any required config files
        config_filenames = self.tool.build_config_files( param_dict, self.working_directory )
        # FIXME: Build the param file (might return None, DEPRECATED)
        param_filename = self.tool.build_param_file( param_dict, self.working_directory )
        # Build the job's command line
        self.command_line = self.tool.build_command_line( param_dict )
        # FIXME: for now, tools get Galaxy's lib dir in their path
        if self.command_line and self.command_line.startswith( 'python' ):
            self.galaxy_lib_dir = os.path.abspath( "lib" ) # cwd = galaxy root
        # Shell fragment to inject dependencies
        if self.app.config.use_tool_dependencies:
            self.dependency_shell_commands = self.tool.build_dependency_shell_commands()
        else:
            self.dependency_shell_commands = None
        # We need command_line persisted to the db in order for Galaxy to re-queue the job
        # if the server was stopped and restarted before the job finished
        job.command_line = self.command_line
        self.sa_session.add( job )
        self.sa_session.flush()
        # Return list of all extra files
        extra_filenames = config_filenames
        if param_filename is not None:
            extra_filenames.append( param_filename )
        self.param_dict = param_dict
        self.extra_filenames = extra_filenames
        self.version_string_cmd = self.tool.version_string_cmd
        return extra_filenames

    def fail( self, message, exception=False, stdout="", stderr="", exit_code=None ):
        """
        Indicate job failure by setting state and message on all output
        datasets.
        """
        job = self.get_job()
        self.sa_session.refresh( job )
        # if the job was deleted, don't fail it
        if not job.state == job.states.DELETED:
            # Check if the failure is due to an exception
            if exception:
                # Save the traceback immediately in case we generate another
                # below
                job.traceback = traceback.format_exc()
                # Get the exception and let the tool attempt to generate
                # a better message
                etype, evalue, tb =  sys.exc_info()
                m = self.tool.handle_job_failure_exception( evalue )
                if m:
                    message = m
            if self.app.config.outputs_to_working_directory:
                for dataset_path in self.get_output_fnames():
                    try:
                        shutil.move( dataset_path.false_path, dataset_path.real_path )
                        log.debug( "fail(): Moved %s to %s" % ( dataset_path.false_path, dataset_path.real_path ) )
                    except ( IOError, OSError ), e:
                        log.error( "fail(): Missing output file in working directory: %s" % e )
            for dataset_assoc in job.output_datasets + job.output_library_datasets:
                dataset = dataset_assoc.dataset
                self.sa_session.refresh( dataset )
                dataset.state = dataset.states.ERROR
                dataset.blurb = 'tool error'
                dataset.info = message
                dataset.set_size()
                dataset.dataset.set_total_size()
                dataset.mark_unhidden()
                if dataset.ext == 'auto':
                    dataset.extension = 'data'
                # Update (non-library) job output datasets through the object store
                if dataset not in job.output_library_datasets:
                    self.app.object_store.update_from_file(dataset.dataset, create=True)
                # Pause any dependent jobs (and those jobs' outputs)
                for dep_job_assoc in dataset.dependent_jobs:
                    self.pause( dep_job_assoc.job, "Execution of this dataset's job is paused because its input datasets are in an error state." )
                self.sa_session.add( dataset )
                self.sa_session.flush()
            job.state = job.states.ERROR
            job.command_line = self.command_line
            job.info = message
            # TODO: Put setting the stdout, stderr, and exit code in one place
            # (not duplicated with the finish method).
            if ( len( stdout ) > 32768 ):
                stdout = stdout[:32768]
                log.info( "stdout for job %d is greater than 32K, only first part will be logged to database" % job.id )
            job.stdout = stdout 
            if ( len( stderr ) > 32768 ):
                stderr = stderr[:32768]
                log.info( "stderr for job %d is greater than 32K, only first part will be logged to database" % job.id )
            job.stderr = stderr  
            # Let the exit code be Null if one is not provided:
            if ( exit_code != None ):
                job.exit_code = exit_code

            self.sa_session.add( job )
            self.sa_session.flush()
        #Perform email action even on failure.
        for pja in [pjaa.post_job_action for pjaa in job.post_job_actions if pjaa.post_job_action.action_type == "EmailAction"]:
            ActionBox.execute(self.app, self.sa_session, pja, job)
        # If the job was deleted, call tool specific fail actions (used for e.g. external metadata) and clean up
        if self.tool:
            self.tool.job_failed( self, message, exception )
        if self.app.config.cleanup_job == 'always' or (self.app.config.cleanup_job == 'onsuccess' and job.state == job.states.DELETED):
            self.cleanup()

    def pause( self, job=None, message=None ):
        if job is None:
            job = self.get_job()
        if message is None:
            message = "Execution of this dataset's job is paused"
        if job.state == job.states.NEW:
            for dataset_assoc in job.output_datasets + job.output_library_datasets:
                dataset_assoc.dataset.dataset.state = dataset_assoc.dataset.dataset.states.PAUSED
                dataset_assoc.dataset.info = message
                self.sa_session.add( dataset_assoc.dataset )
            job.state = job.states.PAUSED
            self.sa_session.add( job )

    def change_state( self, state, info = False ):
        job = self.get_job()
        self.sa_session.refresh( job )
        for dataset_assoc in job.output_datasets + job.output_library_datasets:
            dataset = dataset_assoc.dataset
            self.sa_session.refresh( dataset )
            dataset.state = state
            if info:
                dataset.info = info
            self.sa_session.add( dataset )
            self.sa_session.flush()
        if info:
            job.info = info
        job.state = state
        self.sa_session.add( job )
        self.sa_session.flush()

    def get_state( self ):
        job = self.get_job()
        self.sa_session.refresh( job )
        return job.state

    def set_runner( self, runner_url, external_id ):
        log.warning('set_runner() is deprecated, use set_job_destination()')
        self.set_job_destination(self.job_destination, external_id)

    def set_job_destination(self, job_destination, external_id):
        """
        Persist job destination params in the database for recovery.

        self.job_destination is not used because a runner may choose to rewrite
        parts of the destination (e.g. the params).
        """
        job = self.get_job()
        self.sa_session.refresh(job)
        log.debug('(%s) Persisting job destination (destination id: %s)' % (job.id, job_destination.id))
        job.destination_id = job_destination.id
        job.destination_params = job_destination.params
        job.job_runner_name = job_destination.runner
        job.job_runner_external_id = external_id
        self.sa_session.add(job)
        self.sa_session.flush()

    def finish( self, stdout, stderr, tool_exit_code=None ):
        """
        Called to indicate that the associated command has been run. Updates
        the output datasets based on stderr and stdout from the command, and
        the contents of the output files.
        """
        # default post job setup
        self.sa_session.expunge_all()
        job = self.get_job()

        # TODO: After failing here, consider returning from the function. 
        try:
            self.reclaim_ownership()
        except:
            log.exception( '(%s) Failed to change ownership of %s, failing' % ( job.id, self.working_directory ) )
            return self.fail( job.info, stdout=stdout, stderr=stderr, exit_code=tool_exit_code )

        # if the job was deleted, don't finish it
        if job.state == job.states.DELETED or job.state == job.states.ERROR:
            # SM: Note that, at this point, the exit code must be saved in case
            # there was an error. Errors caught here could mean that the job
            # was deleted by an administrator (based on old comments), but it
            # could also mean that a job was broken up into tasks and one of
            # the tasks failed. So include the stderr, stdout, and exit code:
            return self.fail( job.info, stderr=stderr, stdout=stdout, exit_code=tool_exit_code )

        # Check the tool's stdout, stderr, and exit code for errors, but only
        # if the job has not already been marked as having an error. 
        # The job's stdout and stderr will be set accordingly.
        if job.states.ERROR != job.state:
            if ( self.check_tool_output( stdout, stderr, tool_exit_code, job )):
                job.state = job.states.OK
            else:
                job.state = job.states.ERROR

        if self.version_string_cmd:
            version_filename = self.get_version_string_path()
            if os.path.exists(version_filename):
                self.version_string = open(version_filename).read()
                os.unlink(version_filename)

        if self.app.config.outputs_to_working_directory and not self.__link_file_check():
            for dataset_path in self.get_output_fnames():
                try:
                    shutil.move( dataset_path.false_path, dataset_path.real_path )
                    log.debug( "finish(): Moved %s to %s" % ( dataset_path.false_path, dataset_path.real_path ) )
                except ( IOError, OSError ):
                    # this can happen if Galaxy is restarted during the job's
                    # finish method - the false_path file has already moved,
                    # and when the job is recovered, it won't be found.
                    if os.path.exists( dataset_path.real_path ) and os.stat( dataset_path.real_path ).st_size > 0:
                        log.warning( "finish(): %s not found, but %s is not empty, so it will be used instead" % ( dataset_path.false_path, dataset_path.real_path ) )
                    else:
                        return self.fail( "Job %s's output dataset(s) could not be read" % job.id )
        job_context = ExpressionContext( dict( stdout = job.stdout, stderr = job.stderr ) )
        job_tool = self.app.toolbox.tools_by_id.get( job.tool_id, None )

        
        for dataset_assoc in job.output_datasets + job.output_library_datasets:
            context = self.get_dataset_finish_context( job_context, dataset_assoc.dataset.dataset )
            #should this also be checking library associations? - can a library item be added from a history before the job has ended? - lets not allow this to occur
            for dataset in dataset_assoc.dataset.dataset.history_associations + dataset_assoc.dataset.dataset.library_associations: #need to update all associated output hdas, i.e. history was shared with job running
                dataset.blurb = 'done'
                dataset.peek  = 'no peek'
                dataset.info = ( dataset.info  or '' ) + context['stdout'] + context['stderr']
                dataset.tool_version = self.version_string
                dataset.set_size()
                # Update (non-library) job output datasets through the object store
                if dataset not in job.output_library_datasets:
                    self.app.object_store.update_from_file(dataset.dataset, create=True)
                # TODO: The context['stderr'] holds stderr's contents. An error
                # only really occurs if the job also has an error. So check the
                # job's state:
                if job.states.ERROR == job.state:
                    dataset.blurb = "error"
                    dataset.mark_unhidden()
                elif dataset.has_data():
                    # If the tool was expected to set the extension, attempt to retrieve it
                    if dataset.ext == 'auto':
                        dataset.extension = context.get( 'ext', 'data' )
                        dataset.init_meta( copy_from=dataset )
                    #if a dataset was copied, it won't appear in our dictionary:
                    #either use the metadata from originating output dataset, or call set_meta on the copies
                    #it would be quicker to just copy the metadata from the originating output dataset,
                    #but somewhat trickier (need to recurse up the copied_from tree), for now we'll call set_meta()
                    if not self.app.config.set_metadata_externally or \
                     ( not self.external_output_metadata.external_metadata_set_successfully( dataset, self.sa_session ) \
                       and self.app.config.retry_metadata_internally ):
                        dataset.datatype.set_meta( dataset, overwrite = False ) #call datatype.set_meta directly for the initial set_meta call during dataset creation
                    # TODO: The context['stderr'] used to indicate that there
                    # was an error. Now we must rely on the job's state instead;
                    # that indicates whether the tool relied on stderr to indicate
                    # the state or whether the tool used exit codes and regular
                    # expressions to do so. So we use 
                    # job.state == job.states.ERROR to replace this same test.
                    elif not self.external_output_metadata.external_metadata_set_successfully( dataset, self.sa_session ) and job.states.ERROR != job.state: 
                        dataset._state = model.Dataset.states.FAILED_METADATA
                    else:
                        #load metadata from file
                        #we need to no longer allow metadata to be edited while the job is still running,
                        #since if it is edited, the metadata changed on the running output will no longer match
                        #the metadata that was stored to disk for use via the external process,
                        #and the changes made by the user will be lost, without warning or notice
                        dataset.metadata.from_JSON_dict( self.external_output_metadata.get_output_filenames_by_dataset( dataset, self.sa_session ).filename_out )
                    try:
                        assert context.get( 'line_count', None ) is not None
                        if ( not dataset.datatype.composite_type and dataset.dataset.is_multi_byte() ) or self.tool.is_multi_byte:
                            dataset.set_peek( line_count=context['line_count'], is_multi_byte=True )
                        else:
                            dataset.set_peek( line_count=context['line_count'] )
                    except:
                        if ( not dataset.datatype.composite_type and dataset.dataset.is_multi_byte() ) or self.tool.is_multi_byte:
                            dataset.set_peek( is_multi_byte=True )
                        else:
                            dataset.set_peek()
                    try:
                        # set the name if provided by the tool
                        dataset.name = context['name']
                    except:
                        pass
                else:
                    dataset.blurb = "empty"
                    if dataset.ext == 'auto':
                        dataset.extension = 'txt'
                self.sa_session.add( dataset )
            # TODO: job.states.ERROR == job.state now replaces checking
            # stderr for a problem:
            #if context['stderr']:
            if job.states.ERROR == job.state:
                log.debug( "setting dataset state to ERROR" )
                # TODO: This is where the state is being set to error. Change it!
                dataset_assoc.dataset.dataset.state = model.Dataset.states.ERROR
                # Pause any dependent jobs (and those jobs' outputs)
                for dep_job_assoc in dataset_assoc.dataset.dependent_jobs:
                    self.pause( dep_job_assoc.job, "Execution of this dataset's job is paused because its input datasets are in an error state." )
            else:
                dataset_assoc.dataset.dataset.state = model.Dataset.states.OK
            # If any of the rest of the finish method below raises an
            # exception, the fail method will run and set the datasets to
            # ERROR.  The user will never see that the datasets are in error if
            # they were flushed as OK here, since upon doing so, the history
            # panel stops checking for updates.  So allow the
            # self.sa_session.flush() at the bottom of this method set
            # the state instead.

        for pja in job.post_job_actions:
            ActionBox.execute(self.app, self.sa_session, pja.post_job_action, job)
        # Flush all the dataset and job changes above.  Dataset state changes
        # will now be seen by the user.
        self.sa_session.flush()
        # Save stdout and stderr
        if len( job.stdout ) > 32768:
            log.info( "stdout for job %d is greater than 32K, only first part will be logged to database" % job.id )
        job.stdout = job.stdout[:32768]
        if len( job.stderr ) > 32768:
            log.info( "stderr for job %d is greater than 32K, only first part will be logged to database" % job.id )
        job.stderr = job.stderr[:32768]
        # The exit code will be null if there is no exit code to be set.
        # This is so that we don't assign an exit code, such as 0, that
        # is either incorrect or has the wrong semantics. 
        if None != tool_exit_code:
            job.exit_code = tool_exit_code
        # custom post process setup
        inp_data = dict( [ ( da.name, da.dataset ) for da in job.input_datasets ] )
        out_data = dict( [ ( da.name, da.dataset ) for da in job.output_datasets ] )
        inp_data.update( [ ( da.name, da.dataset ) for da in job.input_library_datasets ] )
        out_data.update( [ ( da.name, da.dataset ) for da in job.output_library_datasets ] )
        param_dict = dict( [ ( p.name, p.value ) for p in job.parameters ] ) # why not re-use self.param_dict here? ##dunno...probably should, this causes tools.parameters.basic.UnvalidatedValue to be used in following methods instead of validated and transformed values during i.e. running workflows
        param_dict = self.tool.params_from_strings( param_dict, self.app )
        # Check for and move associated_files
        self.tool.collect_associated_files(out_data, self.working_directory)
        gitd = self.sa_session.query( model.GenomeIndexToolData ).filter_by( job=job ).first()
        if gitd:
            self.tool.collect_associated_files({'' : gitd}, self.working_directory)
        # Create generated output children and primary datasets and add to param_dict
        collected_datasets = {'children':self.tool.collect_child_datasets(out_data, self.working_directory),'primary':self.tool.collect_primary_datasets(out_data, self.working_directory)}
        param_dict.update({'__collected_datasets__':collected_datasets})
        # Certain tools require tasks to be completed after job execution
        # ( this used to be performed in the "exec_after_process" hook, but hooks are deprecated ).
        self.tool.exec_after_process( self.queue.app, inp_data, out_data, param_dict, job = job )
        # Call 'exec_after_process' hook
        self.tool.call_hook( 'exec_after_process', self.queue.app, inp_data=inp_data,
                             out_data=out_data, param_dict=param_dict,
                             tool=self.tool, stdout=job.stdout, stderr=job.stderr )
        job.command_line = self.command_line

        bytes = 0
        # Once datasets are collected, set the total dataset size (includes extra files)
        for dataset_assoc in job.output_datasets:
            dataset_assoc.dataset.dataset.set_total_size()
            bytes += dataset_assoc.dataset.dataset.get_total_size()

        if job.user:
            job.user.total_disk_usage += bytes

        # fix permissions
        for path in [ dp.real_path for dp in self.get_mutable_output_fnames() ]:
            util.umask_fix_perms( path, self.app.config.umask, 0666, self.app.config.gid )
        self.sa_session.flush()
        log.debug( 'job %d ended' % self.job_id )
        if self.app.config.cleanup_job == 'always' or ( not stderr and self.app.config.cleanup_job == 'onsuccess' ):
            self.cleanup()

    def check_tool_output( self, stdout, stderr, tool_exit_code, job ):
        """
        Check the output of a tool - given the stdout, stderr, and the tool's
        exit code, return True if the tool exited succesfully and False 
        otherwise. No exceptions should be thrown. If this code encounters
        an exception, it returns True so that the workflow can continue;
        otherwise, a bug in this code could halt workflow progress. 
        Note that, if the tool did not define any exit code handling or
        any stdio/stderr handling, then it reverts back to previous behavior:
        if stderr contains anything, then False is returned.
        Note that the job id is just for messages.
        """
        # By default, the tool succeeded. This covers the case where the code 
        # has a bug but the tool was ok, and it lets a workflow continue.
        success = True 

        try:
            # Check exit codes and match regular expressions against stdout and 
            # stderr if this tool was configured to do so.
            # If there is a regular expression for scanning stdout/stderr,
            # then we assume that the tool writer overwrote the default 
            # behavior of just setting an error if there is *anything* on
            # stderr. 
            if ( len( self.tool.stdio_regexes ) > 0 or
                 len( self.tool.stdio_exit_codes ) > 0 ):
                # Check the exit code ranges in the order in which
                # they were specified. Each exit_code is a StdioExitCode
                # that includes an applicable range. If the exit code was in
                # that range, then apply the error level and add a message.
                # If we've reached a fatal error rule, then stop.
                max_error_level = galaxy.tools.StdioErrorLevel.NO_ERROR
                if tool_exit_code != None:
                    for stdio_exit_code in self.tool.stdio_exit_codes:
                        if ( tool_exit_code >= stdio_exit_code.range_start and 
                             tool_exit_code <= stdio_exit_code.range_end ):
                            # Tack on a generic description of the code 
                            # plus a specific code description. For example,
                            # this might prepend "Job 42: Warning (Out of Memory)\n".
                            code_desc = stdio_exit_code.desc
                            if ( None == code_desc ):
                                code_desc = ""
                            tool_msg = ( "%s: Exit code %d (%s)" % (
                                         galaxy.tools.StdioErrorLevel.desc( stdio_exit_code.error_level ),
                                         tool_exit_code,
                                         code_desc ) )
                            log.info( "Job %s: %s" % (job.get_id_tag(), tool_msg) )
                            stderr = tool_msg + "\n" + stderr
                            max_error_level = max( max_error_level, 
                                                   stdio_exit_code.error_level )
                            if ( max_error_level >= 
                                 galaxy.tools.StdioErrorLevel.FATAL ):
                                break
    
                if max_error_level < galaxy.tools.StdioErrorLevel.FATAL:
                    # We'll examine every regex. Each regex specifies whether
                    # it is to be run on stdout, stderr, or both. (It is 
                    # possible for neither stdout nor stderr to be scanned,
                    # but those regexes won't be used.) We record the highest
                    # error level, which are currently "warning" and "fatal".
                    # If fatal, then we set the job's state to ERROR.
                    # If warning, then we still set the job's state to OK
                    # but include a message. We'll do this if we haven't seen 
                    # a fatal error yet
                    for regex in self.tool.stdio_regexes:
                        # If ( this regex should be matched against stdout )
                        #   - Run the regex's match pattern against stdout
                        #   - If it matched, then determine the error level.
                        #       o If it was fatal, then we're done - break.
                        # Repeat the stdout stuff for stderr.
                        # TODO: Collapse this into a single function.
                        if ( regex.stdout_match ):
                            regex_match = re.search( regex.match, stdout, 
                                                     re.IGNORECASE )
                            if ( regex_match ):
                                rexmsg = self.regex_err_msg( regex_match, regex)
                                log.info( "Job %s: %s" 
                                        % ( job.get_id_tag(), rexmsg ) )
                                stdout = rexmsg + "\n" + stdout
                                max_error_level = max( max_error_level, 
                                                       regex.error_level )
                                if ( max_error_level >= 
                                     galaxy.tools.StdioErrorLevel.FATAL ):
                                    break

                        if ( regex.stderr_match ):
                            regex_match = re.search( regex.match, stderr,
                                                     re.IGNORECASE )
                            if ( regex_match ):
                                rexmsg = self.regex_err_msg( regex_match, regex)
                                log.info( "Job %s: %s" 
                                        % ( job.get_id_tag(), rexmsg ) )
                                stderr = rexmsg + "\n" + stderr
                                max_error_level = max( max_error_level, 
                                                       regex.error_level )
                                if ( max_error_level >= 
                                     galaxy.tools.StdioErrorLevel.FATAL ):
                                    break
    
                # If we encountered a fatal error, then we'll need to set the
                # job state accordingly. Otherwise the job is ok:
                if max_error_level >= galaxy.tools.StdioErrorLevel.FATAL:
                    success = False 
                else:
                    success = True 
    
            # When there are no regular expressions and no exit codes to check,
            # default to the previous behavior: when there's anything on stderr
            # the job has an error, and the job is ok otherwise. 
            else:
                # TODO: Add in the tool and job id: 
                log.debug( "Tool did not define exit code or stdio handling; "
                         + "checking stderr for success" )
                if stderr:
                    success = False 
                else:
                    success = True 

        # On any exception, return True.
        except:
            tb = traceback.format_exc()
            log.warning( "Tool check encountered unexpected exception; "
                       + "assuming tool was successful: " + tb )
            success = True
        
        # Store the modified stdout and stderr in the job:
        if None != job:
            job.stdout = stdout
            job.stderr = stderr

        return success

    def regex_err_msg( self, match, regex ):
        """
        Return a message about the match on tool output using the given
        ToolStdioRegex regex object. The regex_match is a MatchObject
        that will contain the string matched on.
        """
        # Get the description for the error level: 
        err_msg = galaxy.tools.StdioErrorLevel.desc( regex.error_level ) + ": "
        # If there's a description for the regular expression, then use it.
        # Otherwise, we'll take the first 256 characters of the match.
        if None != regex.desc:
            err_msg += regex.desc
        else:
            mstart = match.start()
            mend = match.end()
            err_msg += "Matched on "
            # TODO: Move the constant 256 somewhere else besides here.
            if mend - mstart > 256:
                err_msg += match.string[ mstart : mstart+256 ] + "..."
            else:
                err_msg += match.string[ mstart: mend ] 
        return err_msg

    def cleanup( self ):
        # remove temporary files
        try:
            for fname in self.extra_filenames:
                os.remove( fname )
            if self.app.config.set_metadata_externally:
                self.external_output_metadata.cleanup_external_metadata( self.sa_session )
            galaxy.tools.imp_exp.JobExportHistoryArchiveWrapper( self.job_id ).cleanup_after_job( self.sa_session )
            galaxy.tools.imp_exp.JobImportHistoryArchiveWrapper( self.app, self.job_id ).cleanup_after_job()
            galaxy.tools.genome_index.GenomeIndexToolWrapper( self.job_id ).postprocessing( self.sa_session, self.app )
            self.app.object_store.delete(self.get_job(), base_dir='job_work', entire_dir=True, dir_only=True, extra_dir=str(self.job_id))
        except:
            log.exception( "Unable to cleanup job %d" % self.job_id )

    def get_output_sizes( self ):
        sizes = []
        output_paths = self.get_output_fnames()
        for outfile in [ str( o ) for o in output_paths ]:
            if os.path.exists( outfile ):
                sizes.append( ( outfile, os.stat( outfile ).st_size ) )
            else:
                sizes.append( ( outfile, 0 ) )
        return sizes

    def check_limits(self, runtime=None):
        if self.app.job_config.limits.output_size > 0:
            for outfile, size in self.get_output_sizes():
                if size > self.app.config.output_size_limit:
                    log.warning( '(%s) Job output %s is over the output size limit' % ( self.get_id_tag(), os.path.basename( outfile ) ) )
                    return 'Job output file grew too large (greater than %s), please try different inputs or parameters' % util.nice_size( self.app.job_config.limits.output_size )
        if self.app.job_config.limits.walltime_delta is not None and runtime is not None:
            if runtime > self.app.job_config.limits.walltime_delta:
                log.warning( '(%s) Job has reached walltime, it will be terminated' % ( self.get_id_tag() ) )
                return 'Job ran longer than the maximum allowed execution time (%s), please try different inputs or parameters' % self.app.job_config.limits.walltime
        return None

    def get_command_line( self ):
        return self.command_line

    def get_session_id( self ):
        return self.session_id

    def get_env_setup_clause( self ):
        if self.app.config.environment_setup_file is None:
            return ''
        return '[ -f "%s" ] && . %s' % ( self.app.config.environment_setup_file, self.app.config.environment_setup_file )

    def get_input_dataset_fnames( self,  ds ):
        filenames = []
        filenames = [ ds.file_name ]
        #we will need to stage in metadata file names also
        #TODO: would be better to only stage in metadata files that are actually needed (found in command line, referenced in config files, etc.)
        for key, value in ds.metadata.items():
            if isinstance( value, model.MetadataFile ):
                filenames.append( value.file_name )
        return filenames

    def get_input_fnames( self ):
        job = self.get_job()
        filenames = []
        for da in job.input_datasets + job.input_library_datasets: #da is JobToInputDatasetAssociation object
            if da.dataset:
                filenames.extend(self.get_input_dataset_fnames(da.dataset))
        return filenames

    def get_output_fnames( self ):
        if self.output_paths is None:
            self.compute_outputs()
        return self.output_paths

    def get_mutable_output_fnames( self ):
        if self.output_paths is None:
            self.compute_outputs()
        return filter( lambda dsp: dsp.mutable, self.output_paths )

    def get_output_hdas_and_fnames( self ):
        if self.output_hdas_and_paths is None:
            self.compute_outputs()
        return self.output_hdas_and_paths

    def compute_outputs( self ) :
        class DatasetPath( object ):
            def __init__( self, dataset_id, real_path, false_path = None, mutable = True ):
                self.dataset_id = dataset_id
                self.real_path = real_path
                self.false_path = false_path
                self.mutable = mutable
            def __str__( self ):
                if self.false_path is None:
                    return self.real_path
                else:
                    return self.false_path
        job = self.get_job()
        # Job output datasets are combination of history, library, jeha and gitd datasets.
        special = self.sa_session.query( model.JobExportHistoryArchive ).filter_by( job=job ).first()
        if not special:
            special = self.sa_session.query( model.GenomeIndexToolData ).filter_by( job=job ).first()
        false_path = None
        if self.app.config.outputs_to_working_directory:
            self.output_paths = []
            self.output_hdas_and_paths = {}
            for name, hda in [ ( da.name, da.dataset ) for da in job.output_datasets + job.output_library_datasets ]:
                false_path = os.path.abspath( os.path.join( self.working_directory, "galaxy_dataset_%d.dat" % hda.dataset.id ) )
                dsp = DatasetPath( hda.dataset.id, hda.dataset.file_name, false_path, mutable = hda.dataset.external_filename is None  )
                self.output_paths.append( dsp )
                self.output_hdas_and_paths[name] = hda, dsp
            if special:
                false_path = os.path.abspath( os.path.join( self.working_directory, "galaxy_dataset_%d.dat" % special.dataset.id ) )
        else:
            results = [ ( da.name, da.dataset, DatasetPath( da.dataset.dataset.id, da.dataset.file_name, mutable = da.dataset.dataset.external_filename is None ) ) for da in job.output_datasets + job.output_library_datasets ]
            self.output_paths = [t[2] for t in results]
            self.output_hdas_and_paths = dict([(t[0],  t[1:]) for t in results])
        if special:
            dsp = DatasetPath( special.dataset.id, special.dataset.file_name, false_path )
            self.output_paths.append( dsp )
        return self.output_paths

    def get_output_file_id( self, file ):
        if self.output_paths is None:
            self.get_output_fnames()
        for dp in self.output_paths:
            if self.app.config.outputs_to_working_directory and os.path.basename( dp.false_path ) == file:
                return dp.dataset_id
            elif os.path.basename( dp.real_path ) == file:
                return dp.dataset_id
        return None

    def get_tool_provided_job_metadata( self ):
        if self.tool_provided_job_metadata is not None:
            return self.tool_provided_job_metadata

        # Look for JSONified job metadata
        self.tool_provided_job_metadata = []
        meta_file = os.path.join( self.working_directory, TOOL_PROVIDED_JOB_METADATA_FILE )
        if os.path.exists( meta_file ):
            for line in open( meta_file, 'r' ):
                try:
                    line = from_json_string( line )
                    assert 'type' in line
                except:
                    log.exception( '(%s) Got JSON data from tool, but data is improperly formatted or no "type" key in data' % self.job_id )
                    log.debug( 'Offending data was: %s' % line )
                    continue
                # Set the dataset id if it's a dataset entry and isn't set.
                # This isn't insecure.  We loop the job's output datasets in
                # the finish method, so if a tool writes out metadata for a
                # dataset id that it doesn't own, it'll just be ignored.
                if line['type'] == 'dataset' and 'dataset_id' not in line:
                    try:
                        line['dataset_id'] = self.get_output_file_id( line['dataset'] )
                    except KeyError:
                        log.warning( '(%s) Tool provided job dataset-specific metadata without specifying a dataset' % self.job_id )
                        continue
                self.tool_provided_job_metadata.append( line )
        return self.tool_provided_job_metadata

    def get_dataset_finish_context( self, job_context, dataset ):
        for meta in self.get_tool_provided_job_metadata():
            if meta['type'] == 'dataset' and meta['dataset_id'] == dataset.id:
                return ExpressionContext( meta, job_context )
        return job_context

    def setup_external_metadata( self, exec_dir=None, tmp_dir=None, dataset_files_path=None, config_root=None, config_file=None, datatypes_config=None, set_extension=True, **kwds ):
        # extension could still be 'auto' if this is the upload tool.
        job = self.get_job()
        if set_extension:
            for output_dataset_assoc in job.output_datasets:
                if output_dataset_assoc.dataset.ext == 'auto':
                    context = self.get_dataset_finish_context( dict(), output_dataset_assoc.dataset.dataset )
                    output_dataset_assoc.dataset.extension = context.get( 'ext', 'data' )
            self.sa_session.flush()
        if tmp_dir is None:
            #this dir should should relative to the exec_dir
            tmp_dir = self.app.config.new_file_path
        if dataset_files_path is None:
            dataset_files_path = self.app.model.Dataset.file_path
        if config_root is None:
            config_root = self.app.config.root
        if config_file is None:
            config_file = self.app.config.config_file
        if datatypes_config is None:
            datatypes_config = self.app.datatypes_registry.integrated_datatypes_configs
        return self.external_output_metadata.setup_external_metadata( [ output_dataset_assoc.dataset for output_dataset_assoc in job.output_datasets ],
                                                                      self.sa_session,
                                                                      exec_dir = exec_dir,
                                                                      tmp_dir = tmp_dir,
                                                                      dataset_files_path = dataset_files_path,
                                                                      config_root = config_root,
                                                                      config_file = config_file,
                                                                      datatypes_config = datatypes_config,
                                                                      job_metadata = os.path.join( self.working_directory, TOOL_PROVIDED_JOB_METADATA_FILE ),
                                                                      **kwds )

    @property
    def user( self ):
        job = self.get_job()
        if job.user is not None:
            return job.user.email
        elif job.galaxy_session is not None and job.galaxy_session.user is not None:
            return job.galaxy_session.user.email
        elif job.history is not None and job.history.user is not None:
            return job.history.user.email
        elif job.galaxy_session is not None:
            return 'anonymous@' + job.galaxy_session.remote_addr.split()[-1]
        else:
            return 'anonymous@unknown'

    def __link_file_check( self ):
        """ outputs_to_working_directory breaks library uploads where data is
        linked.  This method is a hack that solves that problem, but is
        specific to the upload tool and relies on an injected job param.  This
        method should be removed ASAP and replaced with some properly generic
        and stateful way of determining link-only datasets. -nate
        """
        job = self.get_job()
        param_dict = job.get_param_values( self.app )
        return self.tool.id == 'upload1' and param_dict.get( 'link_data_only', None ) == 'link_to_files'

    def _change_ownership( self, username, gid ):
        job = self.get_job()
        # FIXME: hardcoded path
        cmd = [ '/usr/bin/sudo', '-E', self.app.config.external_chown_script, self.working_directory, username, str( gid ) ]
        log.debug( '(%s) Changing ownership of working directory with: %s' % ( job.id, ' '.join( cmd ) ) )
        p = subprocess.Popen( cmd, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE )
        # TODO: log stdout/stderr
        stdout, stderr = p.communicate()
        assert p.returncode == 0

    def change_ownership_for_run( self ):
        job = self.get_job()
        if self.app.config.external_chown_script and job.user is not None:
            try:
                self._change_ownership( self.user_system_pwent[0], str( self.user_system_pwent[3] ) )
            except:
                log.exception( '(%s) Failed to change ownership of %s, making world-writable instead' % ( job.id, self.working_directory ) )
                os.chmod( self.working_directory, 0777 )

    def reclaim_ownership( self ):
        job = self.get_job()
        if self.app.config.external_chown_script and job.user is not None:
            self._change_ownership( self.galaxy_system_pwent[0], str( self.galaxy_system_pwent[3] ) )

    @property
    def user_system_pwent( self ):
        if self.__user_system_pwent is None:
            job = self.get_job()
            try:
                self.__user_system_pwent = pwd.getpwnam( job.user.email.split('@')[0] )
            except:
                pass
        return self.__user_system_pwent

    @property
    def galaxy_system_pwent( self ):
        if self.__galaxy_system_pwent is None:
            self.__galaxy_system_pwent = pwd.getpwuid(os.getuid())
        return self.__galaxy_system_pwent

class TaskWrapper(JobWrapper):
    """
    Extension of JobWrapper intended for running tasks.
    Should be refactored into a generalized executable unit wrapper parent, then jobs and tasks.
    """
    # Abstract this to be more useful for running tasks that *don't* necessarily compose a job.

    def __init__(self, task, queue):
        super(TaskWrapper, self).__init__(task.job, queue)
        self.task_id = task.id
        self.working_directory = task.working_directory
        if task.prepare_input_files_cmd is not None:
            self.prepare_input_files_cmds = [ task.prepare_input_files_cmd ]
        else:
            self.prepare_input_files_cmds = None
        self.status = task.states.NEW

    def can_split( self ):
        # Should the job handler split this job up? TaskWrapper should 
        # always return False as the job has already been split.
        return False

    def get_job( self ):
        if self.job_id:
            return self.sa_session.query( model.Job ).get( self.job_id )
        else:
            return None

    def get_task( self ):
        return self.sa_session.query(model.Task).get(self.task_id)

    def get_id_tag(self):
        # For compatibility with drmaa job runner and TaskWrapper, instead of using job_id directly
        return self.get_task().get_id_tag()

    def get_param_dict( self ):
        """
        Restore the dictionary of parameters from the database.
        """
        job = self.sa_session.query( model.Job ).get( self.job_id )
        param_dict = dict( [ ( p.name, p.value ) for p in job.parameters ] )
        param_dict = self.tool.params_from_strings( param_dict, self.app )
        return param_dict

    def prepare( self ):
        """
        Prepare the job to run by creating the working directory and the
        config files.
        """
        # Restore parameters from the database
        job = self.get_job()
        task = self.get_task()
        if job.user is None and job.galaxy_session is None:
            raise Exception( 'Job %s has no user and no session.' % job.id )
        incoming = dict( [ ( p.name, p.value ) for p in job.parameters ] )
        incoming = self.tool.params_from_strings( incoming, self.app )
        # Do any validation that could not be done at job creation
        self.tool.handle_unvalidated_param_values( incoming, self.app )
        # Restore input / output data lists
        inp_data = dict( [ ( da.name, da.dataset ) for da in job.input_datasets ] )
        out_data = dict( [ ( da.name, da.dataset ) for da in job.output_datasets ] )
        inp_data.update( [ ( da.name, da.dataset ) for da in job.input_library_datasets ] )
        out_data.update( [ ( da.name, da.dataset ) for da in job.output_library_datasets ] )
        # DBTODO New method for generating command line for a task?
        # These can be passed on the command line if wanted as $userId $userEmail
        if job.history and job.history.user: # check for anonymous user!
            userId = '%d' % job.history.user.id
            userEmail = str(job.history.user.email)
        else:
            userId = 'Anonymous'
            userEmail = 'Anonymous'
        incoming['userId'] = userId
        incoming['userEmail'] = userEmail
        # Build params, done before hook so hook can use
        param_dict = self.tool.build_param_dict( incoming, inp_data, out_data, self.get_output_fnames(), self.working_directory )
        fnames = {}
        for v in self.get_input_fnames():
            fnames[v] = os.path.join(self.working_directory, os.path.basename(v))
        for dp in [x.real_path for x in self.get_output_fnames()]:
            fnames[dp] = os.path.join(self.working_directory, os.path.basename(dp))
        # Certain tools require tasks to be completed prior to job execution
        # ( this used to be performed in the "exec_before_job" hook, but hooks are deprecated ).
        self.tool.exec_before_job( self.queue.app, inp_data, out_data, param_dict )
        # Run the before queue ("exec_before_job") hook
        self.tool.call_hook( 'exec_before_job', self.queue.app, inp_data=inp_data,
                             out_data=out_data, tool=self.tool, param_dict=incoming)
        self.sa_session.flush()
        # Build any required config files
        config_filenames = self.tool.build_config_files( param_dict, self.working_directory )
        # FIXME: Build the param file (might return None, DEPRECATED)
        param_filename = self.tool.build_param_file( param_dict, self.working_directory )
        # Build the job's command line
        self.command_line = self.tool.build_command_line( param_dict )
        # HACK, Fix this when refactored.
        for k, v in fnames.iteritems():
            self.command_line = self.command_line.replace(k, v)
        # FIXME: for now, tools get Galaxy's lib dir in their path
        if self.command_line and self.command_line.startswith( 'python' ):
            self.galaxy_lib_dir = os.path.abspath( "lib" ) # cwd = galaxy root
        # Shell fragment to inject dependencies
        if self.app.config.use_tool_dependencies:
            self.dependency_shell_commands = self.tool.build_dependency_shell_commands()
        else:
            self.dependency_shell_commands = None
        # We need command_line persisted to the db in order for Galaxy to re-queue the job
        # if the server was stopped and restarted before the job finished
        task.command_line = self.command_line
        self.sa_session.add( task )
        self.sa_session.flush()
        # # Return list of all extra files
        extra_filenames = config_filenames
        if param_filename is not None:
            extra_filenames.append( param_filename )
        self.param_dict = param_dict
        self.extra_filenames = extra_filenames
        self.status = 'prepared'
        return extra_filenames

    def fail( self, message, exception=False ):
        log.error("TaskWrapper Failure %s" % message)
        self.status = 'error'
        # How do we want to handle task failure?  Fail the job and let it clean up?

    def change_state( self, state, info = False ):
        task = self.get_task()
        self.sa_session.refresh( task )
        if info:
            task.info = info
        task.state = state
        self.sa_session.add( task )
        self.sa_session.flush()

    def get_state( self ):
        task = self.get_task()
        self.sa_session.refresh( task )
        return task.state

    def get_exit_code( self ):
        task = self.get_task()
        self.sa_session.refresh( task )
        return task.exit_code

    def set_runner( self, runner_url, external_id ):
        task = self.get_task()
        self.sa_session.refresh( task )
        task.task_runner_name = runner_url
        task.task_runner_external_id = external_id
        # DBTODO Check task job_runner_stuff
        self.sa_session.add( task )
        self.sa_session.flush()

    def finish( self, stdout, stderr, tool_exit_code=None ):
        # DBTODO integrate previous finish logic.
        # Simple finish for tasks.  Just set the flag OK.
        """
        Called to indicate that the associated command has been run. Updates
        the output datasets based on stderr and stdout from the command, and
        the contents of the output files.
        """
        # This may have ended too soon
        log.debug( 'task %s for job %d ended; exit code: %d' 
                 % (self.task_id, self.job_id, 
                    tool_exit_code if tool_exit_code != None else -256 ) )
        # default post job setup_external_metadata
        self.sa_session.expunge_all()
        task = self.get_task()
        # if the job was deleted, don't finish it
        if task.state == task.states.DELETED:
            # Job was deleted by an administrator
            if self.app.config.cleanup_job in ( 'always', 'onsuccess' ):
                self.cleanup()
            return
        elif task.state == task.states.ERROR:
            self.fail( task.info )
            return

        # Check what the tool returned. If the stdout or stderr matched 
        # regular expressions that indicate errors, then set an error.
        # The same goes if the tool's exit code was in a given range.
        if ( self.check_tool_output( stdout, stderr, tool_exit_code, task ) ):
            task.state = task.states.OK
        else: 
            task.state = task.states.ERROR

        # Save stdout and stderr
        if len( stdout ) > 32768:
            log.error( "stdout for task %d is greater than 32K, only first part will be logged to database" % task.id )
        task.stdout = stdout[:32768]
        if len( stderr ) > 32768:
            log.error( "stderr for job %d is greater than 32K, only first part will be logged to database" % task.id )
        task.stderr = stderr[:32768]
        task.exit_code = tool_exit_code
        task.command_line = self.command_line
        self.sa_session.flush()

    def cleanup( self ):
        # There is no task cleanup.  The job cleans up for all tasks.
        pass

    def get_command_line( self ):
        return self.command_line

    def get_session_id( self ):
        return self.session_id

    def get_output_file_id( self, file ):
        # There is no permanent output file for tasks.
        return None

    def get_tool_provided_job_metadata( self ):
        # DBTODO Handle this as applicable for tasks.
        return None

    def get_dataset_finish_context( self, job_context, dataset ):
        # Handled at the parent job level.  Do nothing here.
        pass

    def setup_external_metadata( self, exec_dir=None, tmp_dir=None, dataset_files_path=None, config_root=None, config_file=None, datatypes_config=None, set_extension=True, **kwds ):
        # There is no metadata setting for tasks.  This is handled after the merge, at the job level.
        return ""

class NoopQueue( object ):
    """
    Implements the JobQueue / JobStopQueue interface but does nothing
    """
    def put( self, *args ):
        return
    def put_stop( self, *args ):
        return
    def shutdown( self ):
        return

class ParallelismInfo(object):
    """
    Stores the information (if any) for running multiple instances of the tool in parallel
    on the same set of inputs.
    """
    def __init__(self, tag):
        self.method = tag.get('method')
        if isinstance(tag, dict):
            items = tag.iteritems()
        else:
            items = tag.attrib.items()
        self.attributes = dict([item for item in items if item[0] != 'method' ])
        if len(self.attributes) == 0:
            # legacy basic mode - provide compatible defaults
            self.attributes['split_size'] = 20
            self.attributes['split_mode'] = 'number_of_parts'
