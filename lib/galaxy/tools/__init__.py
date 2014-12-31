"""
Classes encapsulating galaxy tools and tool configuration.
"""

import binascii
import glob
import json
import logging
import os
import re
import shutil
import threading
import types
import urllib

from galaxy import eggs
eggs.require( "MarkupSafe" )  # MarkupSafe must load before mako
eggs.require( "Mako" )
eggs.require( "elementtree" )
eggs.require( "Paste" )
eggs.require( "SQLAlchemy >= 0.4" )

from cgi import FieldStorage
from elementtree import ElementTree
from mako.template import Template
from paste import httpexceptions

from galaxy import jobs, model
from galaxy.datatypes.metadata import JobExternalOutputMetadataWrapper
from galaxy import exceptions
from galaxy.tools.actions import DefaultToolAction
from galaxy.tools.actions.upload import UploadToolAction
from galaxy.tools.actions.data_source import DataSourceToolAction
from galaxy.tools.actions.data_manager import DataManagerToolAction
from galaxy.tools.deps import build_dependency_manager
from galaxy.tools.parameters import check_param, params_from_strings, params_to_strings
from galaxy.tools.parameters import output_collect
from galaxy.tools.parameters.basic import (BaseURLToolParameter,
                                           DataToolParameter, HiddenToolParameter, LibraryDatasetToolParameter,
                                           SelectToolParameter, ToolParameter, UnvalidatedValue,
                                           IntegerToolParameter, FloatToolParameter)
from galaxy.tools.parameters.grouping import Conditional, ConditionalWhen, Repeat, UploadDataset
from galaxy.tools.parameters.input_translation import ToolInputTranslator
from galaxy.tools.parameters.output import ToolOutputActionGroup
from galaxy.tools.parameters.validation import LateValidationError
from galaxy.tools.test import parse_tests
from galaxy.tools.parser import get_tool_source
from galaxy.tools.parser.xml import XmlPageSource
from galaxy.tools.toolbox import AbstractToolBox
from galaxy.util import rst_to_html, string_as_bool, string_to_object
from galaxy.tools.parameters.meta import expand_meta_parameters
from galaxy.util.bunch import Bunch
from galaxy.util.expressions import ExpressionContext
from galaxy.util.hash_util import hmac_new
from galaxy.util.odict import odict
from galaxy.util.template import fill_template
from galaxy.web import url_for
from galaxy.model.item_attrs import Dictifiable
from tool_shed.util import shed_util_common as suc
from .loader import template_macro_params, raw_tool_xml_tree, imported_macro_paths
from .execute import execute as execute_job
from .wrappers import (
    ToolParameterValueWrapper,
    RawObjectWrapper,
    LibraryDatasetValueWrapper,
    InputValueWrapper,
    SelectToolParameterWrapper,
    DatasetFilenameWrapper,
    DatasetListWrapper,
    DatasetCollectionWrapper,
)


log = logging.getLogger( __name__ )

WORKFLOW_PARAMETER_REGULAR_EXPRESSION = re.compile( '''\$\{.+?\}''' )

JOB_RESOURCE_CONDITIONAL_XML = """<conditional name="__job_resource">
    <param name="__job_resource__select" type="select" label="Job Resource Parameters">
        <option value="no">Use default job resource parameters</option>
        <option value="yes">Specify job resource parameters</option>
    </param>
    <when value="no"></when>
    <when value="yes">
    </when>
</conditional>"""

HELP_UNINITIALIZED = threading.Lock()


class ToolNotFoundException( Exception ):
    pass


class ToolBox( AbstractToolBox ):
    """ A derivative of AbstractToolBox with knowledge about Tool internals -
    how to construct them, action types, dependency management, etc....
    """

    def __init__( self, config_filenames, tool_root_dir, app ):
        super( ToolBox, self ).__init__(
            config_filenames=config_filenames,
            tool_root_dir=tool_root_dir,
            app=app,
        )
        self._init_dependency_manager()

    @property
    def tools_by_id( self ):
        # Deprecated method, TODO - eliminate calls to this in test/.
        return self._tools_by_id

    def create_tool( self, config_file, repository_id=None, guid=None, **kwds ):
        tool_source = get_tool_source( config_file, getattr( self.app.config, "enable_beta_tool_formats", False ) )
        # Allow specifying a different tool subclass to instantiate
        tool_module = tool_source.parse_tool_module()
        if tool_module is not None:
            module, cls = tool_module
            mod = __import__( module, globals(), locals(), [cls] )
            ToolClass = getattr( mod, cls )
        elif tool_source.parse_tool_type():
            tool_type = tool_source.parse_tool_type()
            ToolClass = tool_types.get( tool_type )
        else:
            # Normal tool - only insert dynamic resource parameters for these
            # tools.
            root = getattr( tool_source, "root", None )
            # TODO: mucking with the XML directly like this is terrible,
            # modify inputs directly post load if possible.
            if root is not None and hasattr( self.app, "job_config" ):  # toolshed may not have job_config?
                tool_id = root.get( 'id' )
                parameters = self.app.job_config.get_tool_resource_parameters( tool_id )
                if parameters:
                    inputs = root.find('inputs')
                    # If tool has not inputs, create some so we can insert conditional
                    if inputs is None:
                        inputs = ElementTree.fromstring( "<inputs></inputs>")
                        root.append( inputs )
                    # Insert a conditional allowing user to specify resource parameters.
                    conditional_element = ElementTree.fromstring( JOB_RESOURCE_CONDITIONAL_XML )
                    when_yes_elem = conditional_element.findall( "when" )[ 1 ]
                    for parameter in parameters:
                        when_yes_elem.append( parameter )
                    inputs.append( conditional_element )

            ToolClass = Tool
        tool = ToolClass( config_file, tool_source, self.app, guid=guid, repository_id=repository_id, **kwds )
        return tool

    def _init_dependency_manager( self ):
        self.dependency_manager = build_dependency_manager( self.app.config )

    def handle_datatypes_changed( self ):
        """ Refresh upload tools when new datatypes are added. """
        for tool_id in self._tools_by_id:
            tool = self._tools_by_id[ tool_id ]
            if isinstance( tool.tool_action, UploadToolAction ):
                self.reload_tool_by_id( tool_id )


class DefaultToolState( object ):
    """
    Keeps track of the state of a users interaction with a tool between
    requests. The default tool state keeps track of the current page (for
    multipage "wizard" tools) and the values of all
    """
    def __init__( self ):
        self.page = 0
        self.rerun_remap_job_id = None
        self.inputs = None

    def encode( self, tool, app, secure=True ):
        """
        Convert the data to a string
        """
        # Convert parameters to a dictionary of strings, and save curent
        # page in that dict
        value = params_to_strings( tool.inputs, self.inputs, app )
        value["__page__"] = self.page
        value["__rerun_remap_job_id__"] = self.rerun_remap_job_id
        value = json.dumps( value )
        # Make it secure
        if secure:
            a = hmac_new( app.config.tool_secret, value )
            b = binascii.hexlify( value )
            return "%s:%s" % ( a, b )
        else:
            return value

    def decode( self, value, tool, app, secure=True ):
        """
        Restore the state from a string
        """
        if secure:
            # Extract and verify hash
            a, b = value.split( ":" )
            value = binascii.unhexlify( b )
            test = hmac_new( app.config.tool_secret, value )
            assert a == test
        # Restore from string
        values = json_fix( json.loads( value ) )
        self.page = values.pop( "__page__" )
        if '__rerun_remap_job_id__' in values:
            self.rerun_remap_job_id = values.pop( "__rerun_remap_job_id__" )
        else:
            self.rerun_remap_job_id = None
        self.inputs = params_from_strings( tool.inputs, values, app, ignore_errors=True )

    def copy( self ):
        """
        WARNING! Makes a shallow copy, *SHOULD* rework to have it make a deep
        copy.
        """
        new_state = DefaultToolState()
        new_state.page = self.page
        new_state.rerun_remap_job_id = self.rerun_remap_job_id
        # This need to be copied.
        new_state.inputs = self.inputs
        return new_state


class ToolOutput( object, Dictifiable ):
    """
    Represents an output datasets produced by a tool. For backward
    compatibility this behaves as if it were the tuple::

      (format, metadata_source, parent)
    """

    dict_collection_visible_keys = ( 'name', 'format', 'label', 'hidden' )

    def __init__( self, name, format=None, format_source=None, metadata_source=None,
                  parent=None, label=None, filters=None, actions=None, hidden=False ):
        self.name = name
        self.format = format
        self.format_source = format_source
        self.metadata_source = metadata_source
        self.parent = parent
        self.label = label
        self.filters = filters or []
        self.actions = actions
        self.hidden = hidden

    # Tuple emulation

    def __len__( self ):
        return 3

    def __getitem__( self, index ):
        if index == 0:
            return self.format
        elif index == 1:
            return self.metadata_source
        elif index == 2:
            return self.parent
        else:
            raise IndexError( index )

    def __iter__( self ):
        return iter( ( self.format, self.metadata_source, self.parent ) )


class Tool( object, Dictifiable ):
    """
    Represents a computational tool that can be executed through Galaxy.
    """

    tool_type = 'default'
    requires_setting_metadata = True
    default_tool_action = DefaultToolAction
    dict_collection_visible_keys = ( 'id', 'name', 'version', 'description' )
    default_template = 'tool_form.mako'

    def __init__( self, config_file, tool_source, app, guid=None, repository_id=None ):
        """Load a tool from the config named by `config_file`"""
        # Determine the full path of the directory where the tool config is
        self.config_file = config_file
        self.tool_dir = os.path.dirname( config_file )
        self.app = app
        self.repository_id = repository_id
        #setup initial attribute values
        self.inputs = odict()
        self.stdio_exit_codes = list()
        self.stdio_regexes = list()
        self.inputs_by_page = list()
        self.display_by_page = list()
        self.action = '/tool_runner/index'
        self.target = 'galaxy_main'
        self.method = 'post'
        self.check_values = True
        self.nginx_upload = False
        self.input_required = False
        self.display_interface = True
        self.require_login = False
        self.rerun = False
        # Define a place to keep track of all input   These
        # differ from the inputs dictionary in that inputs can be page
        # elements like conditionals, but input_params are basic form
        # parameters like SelectField objects.  This enables us to more
        # easily ensure that parameter dependencies like index files or
        # tool_data_table_conf.xml entries exist.
        self.input_params = []
        # Attributes of tools installed from Galaxy tool sheds.
        self.tool_shed = None
        self.repository_name = None
        self.repository_owner = None
        self.installed_changeset_revision = None
        # The tool.id value will be the value of guid, but we'll keep the
        # guid attribute since it is useful to have.
        self.guid = guid
        self.old_id = None
        self.version = None
        # Enable easy access to this tool's version lineage.
        self.lineage_ids = []
        #populate toolshed repository info, if available
        self.populate_tool_shed_info()
        # Parse XML element containing configuration
        self.parse( tool_source, guid=guid )
        self.external_runJob_script = app.config.drmaa_external_runjob_script

    @property
    def sa_session( self ):
        """Returns a SQLAlchemy session"""
        return self.app.model.context

    @property
    def tool_version( self ):
        """Return a ToolVersion if one exists for our id"""
        return self.app.install_model.context.query( self.app.install_model.ToolVersion ) \
                                             .filter( self.app.install_model.ToolVersion.table.c.tool_id == self.id ) \
                                             .first()

    @property
    def tool_versions( self ):
        # If we have versions, return them.
        tool_version = self.tool_version
        if tool_version:
            return tool_version.get_versions( self.app )
        return []

    @property
    def tool_shed_repository( self ):
        # If this tool is included in an installed tool shed repository, return it.
        if self.tool_shed:
            return suc.get_tool_shed_repository_by_shed_name_owner_installed_changeset_revision( self.app,
                                                                                                 self.tool_shed,
                                                                                                 self.repository_name,
                                                                                                 self.repository_owner,
                                                                                                 self.installed_changeset_revision )
        return None

    def __get_job_tool_configuration(self, job_params=None):
        """Generalized method for getting this tool's job configuration.

        :type job_params: dict or None
        :returns: `galaxy.jobs.JobToolConfiguration` -- JobToolConfiguration that matches this `Tool` and the given `job_params`
        """
        rval = None
        if len(self.job_tool_configurations) == 1:
            # If there's only one config, use it rather than wasting time on comparisons
            rval = self.job_tool_configurations[0]
        elif job_params is None:
            for job_tool_config in self.job_tool_configurations:
                if not job_tool_config.params:
                    rval = job_tool_config
                    break
        else:
            for job_tool_config in self.job_tool_configurations:
                if job_tool_config.params:
                    # There are job params and this config has params defined
                    for param, value in job_params.items():
                        if param not in job_tool_config.params or job_tool_config.params[param] != job_params[param]:
                            break
                    else:
                        # All params match, use this config
                        rval = job_tool_config
                        break
                else:
                    rval = job_tool_config
        assert rval is not None, 'Could not get a job tool configuration for Tool %s with job_params %s, this is a bug' % (self.id, job_params)
        return rval

    def get_job_handler(self, job_params=None):
        """Get a suitable job handler for this `Tool` given the provided `job_params`.  If multiple handlers are valid for combination of `Tool` and `job_params` (e.g. the defined handler is a handler tag), one will be selected at random.

        :param job_params: Any params specific to this job (e.g. the job source)
        :type job_params: dict or None

        :returns: str -- The id of a job handler for a job run of this `Tool`
        """
        # convert tag to ID if necessary
        return self.app.job_config.get_handler(self.__get_job_tool_configuration(job_params=job_params).handler)

    def get_job_destination(self, job_params=None):
        """
        :returns: galaxy.jobs.JobDestination -- The destination definition and runner parameters.
        """
        return self.app.job_config.get_destination(self.__get_job_tool_configuration(job_params=job_params).destination)

    def get_panel_section( self ):
        return self.app.toolbox.get_integrated_section_for_tool( self )

    def parse( self, tool_source, guid=None ):
        """
        Read tool configuration from the element `root` and fill in `self`.
        """
        # Get the (user visible) name of the tool
        self.name = tool_source.parse_name()
        if not self.name:
            raise Exception( "Missing tool 'name'" )
        # Get the UNIQUE id for the tool
        self.old_id = tool_source.parse_id()
        if guid is None:
            self.id = self.old_id
        else:
            self.id = guid
        if not self.id:
            raise Exception( "Missing tool 'id'" )
        self.version = tool_source.parse_version()
        if not self.version:
            # For backward compatibility, some tools may not have versions yet.
            self.version = "1.0.0"

        # Support multi-byte tools
        self.is_multi_byte = tool_source.parse_is_multi_byte()
        # Legacy feature, ignored by UI.
        self.force_history_refresh = False

        self.display_interface = tool_source.parse_display_interface( default=self.display_interface )

        self.require_login = tool_source.parse_require_login( self.require_login )

        request_param_translation_elem = tool_source.parse_request_param_translation_elem()
        if request_param_translation_elem is not None:
            # Load input translator, used by datasource tools to change names/values of incoming parameters
            self.input_translator = ToolInputTranslator.from_element( request_param_translation_elem )
        else:
            self.input_translator = None

        # Command line (template). Optional for tools that do not invoke a local program
        command = tool_source.parse_command()
        if command is not None:
            self.command = command.lstrip()  # get rid of leading whitespace
            # Must pre-pend this AFTER processing the cheetah command template
            self.interpreter = tool_source.parse_interpreter()
        else:
            self.command = ''
            self.interpreter = None

        # Parameters used to build URL for redirection to external app
        redirect_url_params = tool_source.parse_redirect_url_params_elem()
        if redirect_url_params is not None and redirect_url_params.text is not None:
            # get rid of leading / trailing white space
            redirect_url_params = redirect_url_params.text.strip()
            # Replace remaining white space with something we can safely split on later
            # when we are building the params
            self.redirect_url_params = redirect_url_params.replace( ' ', '**^**' )
        else:
            self.redirect_url_params = ''

        # Short description of the tool
        self.description = tool_source.parse_description()

        # Versioning for tools
        self.version_string_cmd = None
        version_command = tool_source.parse_version_command()
        if version_command is not None:
            self.version_string_cmd = version_command.strip()

            version_cmd_interpreter = tool_source.parse_version_command_interpreter()
            if version_cmd_interpreter:
                executable = self.version_string_cmd.split()[0]
                abs_executable = os.path.abspath(os.path.join(self.tool_dir, executable))
                command_line = self.version_string_cmd.replace(executable, abs_executable, 1)
                self.version_string_cmd = version_cmd_interpreter + " " + command_line

        # Parallelism for tasks, read from tool config.
        self.parallelism = tool_source.parse_parallelism()

        # Get JobToolConfiguration(s) valid for this particular Tool.  At least
        # a 'default' will be provided that uses the 'default' handler and
        # 'default' destination.  I thought about moving this to the
        # job_config, but it makes more sense to store here. -nate
        self_ids = [ self.id.lower() ]
        if self.old_id != self.id:
            # Handle toolshed guids
            self_ids = [ self.id.lower(), self.id.lower().rsplit('/', 1)[0], self.old_id.lower() ]
        self.all_ids = self_ids
        # In the toolshed context, there is no job config.
        if 'job_config' in dir(self.app):
            self.job_tool_configurations = self.app.job_config.get_job_tool_configurations(self_ids)

        # Is this a 'hidden' tool (hidden in tool menu)
        self.hidden = tool_source.parse_hidden()

        self.__parse_legacy_features(tool_source)

        # Load any tool specific options (optional)
        self.options = dict( sanitize=True, refresh=False )
        self.__update_options_dict( tool_source )
        self.options = Bunch(** self.options)

        # Parse tool inputs (if there are any required)
        self.parse_inputs( tool_source )

        # Parse tool help
        self.parse_help( tool_source )

        # Description of outputs produced by an invocation of the tool
        self.parse_outputs( tool_source )

        # Parse result handling for tool exit codes and stdout/stderr messages:
        self.parse_stdio( tool_source )
        # Any extra generated config files for the tool
        self.__parse_config_files(tool_source)
        # Action
        action = tool_source.parse_action_module()
        if action is None:
            self.tool_action = self.default_tool_action()
        else:
            module, cls = action
            mod = __import__( module, globals(), locals(), [cls])
            self.tool_action = getattr( mod, cls )()
        # Tests
        self.__parse_tests(tool_source)

        # Requirements (dependencies)
        requirements, containers = tool_source.parse_requirements_and_containers()
        self.requirements = requirements
        self.containers = containers

        self.citations = self._parse_citations( tool_source )

        # Determine if this tool can be used in workflows
        self.is_workflow_compatible = self.check_workflow_compatible(tool_source)
        self.__parse_trackster_conf( tool_source )

    def __parse_legacy_features(self, tool_source):
        self.code_namespace = dict()
        self.hook_map = {}
        self.uihints = {}

        if not hasattr(tool_source, 'root'):
            return

        # TODO: Move following logic into XmlToolSource.
        root = tool_source.root
        # Load any tool specific code (optional) Edit: INS 5/29/2007,
        # allow code files to have access to the individual tool's
        # "module" if it has one.  Allows us to reuse code files, etc.
        for code_elem in root.findall("code"):
            for hook_elem in code_elem.findall("hook"):
                for key, value in hook_elem.items():
                    # map hook to function
                    self.hook_map[key] = value
            file_name = code_elem.get("file")
            code_path = os.path.join( self.tool_dir, file_name )
            execfile( code_path, self.code_namespace )

        # User interface hints
        uihints_elem = root.find( "uihints" )
        if uihints_elem is not None:
            for key, value in uihints_elem.attrib.iteritems():
                self.uihints[ key ] = value

    def __update_options_dict(self, tool_source):
        # TODO: Move following logic into ToolSource abstraction.
        if not hasattr(tool_source, 'root'):
            return

        root = tool_source.root
        for option_elem in root.findall("options"):
            for option, value in self.options.copy().items():
                if isinstance(value, type(False)):
                    self.options[option] = string_as_bool(option_elem.get(option, str(value)))
                else:
                    self.options[option] = option_elem.get(option, str(value))

    def __parse_tests(self, tool_source):
        self.__tests_source = tool_source
        self.__tests_populated = False

    def __parse_config_files(self, tool_source):
        self.config_files = []
        if not hasattr(tool_source, 'root'):
            return

        root = tool_source.root
        conf_parent_elem = root.find("configfiles")
        if conf_parent_elem is not None:
            for conf_elem in conf_parent_elem.findall( "configfile" ):
                name = conf_elem.get( "name" )
                filename = conf_elem.get( "filename", None )
                text = conf_elem.text
                self.config_files.append( ( name, filename, text ) )

    def __parse_trackster_conf(self, tool_source):
        self.trackster_conf = None
        if not hasattr(tool_source, 'root'):
            return

        # Trackster configuration.
        trackster_conf = tool_source.root.find( "trackster_conf" )
        if trackster_conf is not None:
            self.trackster_conf = TracksterConfig.parse( trackster_conf )

    @property
    def tests( self ):
        if not self.__tests_populated:
            tests_source = self.__tests_source
            if tests_source:
                try:
                    self.__tests = parse_tests( self, tests_source )
                except:
                    self.__tests = None
                    log.exception( "Failed to parse tool tests" )
            else:
                self.__tests = None
            self.__tests_populated = True
        return self.__tests

    def parse_inputs( self, tool_source ):
        """
        Parse the "<inputs>" element and create appropriate `ToolParameter`s.
        This implementation supports multiple pages and grouping constructs.
        """
        # Load parameters (optional)
        pages = tool_source.parse_input_pages()
        enctypes = set()
        if pages.inputs_defined:
            if hasattr(pages, "input_elem"):
                input_elem = pages.input_elem
                # Handle properties of the input form
                self.check_values = string_as_bool( input_elem.get("check_values", self.check_values ) )
                self.nginx_upload = string_as_bool( input_elem.get( "nginx_upload", self.nginx_upload ) )
                self.action = input_elem.get( 'action', self.action )
                # If we have an nginx upload, save the action as a tuple instead of
                # a string. The actual action needs to get url_for run to add any
                # prefixes, and we want to avoid adding the prefix to the
                # nginx_upload_path. This logic is handled in the tool_form.mako
                # template.
                if self.nginx_upload and self.app.config.nginx_upload_path:
                    if '?' in urllib.unquote_plus( self.action ):
                        raise Exception( 'URL parameters in a non-default tool action can not be used '
                                         'in conjunction with nginx upload.  Please convert them to '
                                         'hidden POST parameters' )
                    self.action = (self.app.config.nginx_upload_path + '?nginx_redir=',
                                   urllib.unquote_plus(self.action))
                self.target = input_elem.get( "target", self.target )
                self.method = input_elem.get( "method", self.method )
                # Parse the actual parameters
                # Handle multiple page case
            for page_source in pages.page_sources:
                display, inputs = self.parse_input_page( page_source, enctypes )
                self.inputs_by_page.append( inputs )
                self.inputs.update( inputs )
                self.display_by_page.append( display )
        else:
            self.inputs_by_page.append( self.inputs )
            self.display_by_page.append( None )
        self.display = self.display_by_page[0]
        self.npages = len( self.inputs_by_page )
        self.last_page = len( self.inputs_by_page ) - 1
        self.has_multiple_pages = bool( self.last_page )
        # Determine the needed enctype for the form
        if len( enctypes ) == 0:
            self.enctype = "application/x-www-form-urlencoded"
        elif len( enctypes ) == 1:
            self.enctype = enctypes.pop()
        else:
            raise Exception( "Conflicting required enctypes: %s" % str( enctypes ) )
        # Check if the tool either has no parameters or only hidden (and
        # thus hardcoded)  FIXME: hidden parameters aren't
        # parameters at all really, and should be passed in a different
        # way, making this check easier.
        template_macros = {}
        if hasattr(tool_source, 'root'):
            template_macros = template_macro_params(tool_source.root)
        self.template_macro_params = template_macros
        for param in self.inputs.values():
            if not isinstance( param, ( HiddenToolParameter, BaseURLToolParameter ) ):
                self.input_required = True
                break

    def parse_help( self, tool_source ):
        """
        Parse the help text for the tool. Formatted in reStructuredText, but
        stored as Mako to allow for dynamic image paths.
        This implementation supports multiple pages.
        """
        # TODO: Allow raw HTML or an external link.
        self.__help = HELP_UNINITIALIZED
        self.__help_by_page = HELP_UNINITIALIZED
        self.__help_source = tool_source

    def parse_outputs( self, tool_source ):
        """
        Parse <outputs> elements and fill in self.outputs (keyed by name)
        """
        self.outputs = odict()
        for output in tool_source.parse_outputs(self):
            self.outputs[ output.name ] = output

    # TODO: Include the tool's name in any parsing warnings.
    def parse_stdio( self, tool_source ):
        """
        Parse <stdio> element(s) and fill in self.return_codes,
        self.stderr_rules, and self.stdout_rules. Return codes have a range
        and an error type (fault or warning).  Stderr and stdout rules have
        a regular expression and an error level (fault or warning).
        """
        exit_codes, regexes = tool_source.parse_stdio()
        self.stdio_exit_codes = exit_codes
        self.stdio_regexes = regexes

    def _parse_citations( self, tool_source ):
        # TODO: Move following logic into ToolSource abstraction.
        if not hasattr(tool_source, 'root'):
            return []

        root = tool_source.root
        citations = []
        citations_elem = root.find("citations")
        if citations_elem is None:
            return citations

        for citation_elem in citations_elem:
            if citation_elem.tag != "citation":
                pass
            citation = self.app.citations_manager.parse_citation( citation_elem, self.tool_dir )
            if citation:
                citations.append( citation )
        return citations

    def parse_input_page( self, page_source, enctypes ):
        """
        Parse a page of inputs. This basically just calls 'parse_input_elem',
        but it also deals with possible 'display' elements which are supported
        only at the top/page level (not in groups).
        """
        inputs = self.parse_input_elem( page_source, enctypes )
        # Display
        display = page_source.parse_display()
        return display, inputs

    def parse_input_elem( self, page_source, enctypes, context=None ):
        """
        Parse a parent element whose children are inputs -- these could be
        groups (repeat, conditional) or param elements. Groups will be parsed
        recursively.
        """
        rval = odict()
        context = ExpressionContext( rval, context )
        for input_source in page_source.parse_input_sources():
            # Repeat group
            input_type = input_source.parse_input_type()
            if input_type == "repeat":
                group = Repeat()
                group.name = input_source.get( "name" )
                group.title = input_source.get( "title" )
                group.help = input_source.get( "help", None )
                page_source = input_source.parse_nested_inputs_source()
                group.inputs = self.parse_input_elem( page_source, enctypes, context )
                group.default = int( input_source.get( "default", 0 ) )
                group.min = int( input_source.get( "min", 0 ) )
                # Use float instead of int so that 'inf' can be used for no max
                group.max = float( input_source.get( "max", "inf" ) )
                assert group.min <= group.max, \
                    ValueError( "Min repeat count must be less-than-or-equal to the max." )
                # Force default to be within min-max range
                group.default = min( max( group.default, group.min ), group.max )
                rval[group.name] = group
            elif input_type == "conditional":
                group = Conditional()
                group.name = input_source.get( "name" )
                group.value_ref = input_source.get( 'value_ref', None )
                group.value_ref_in_group = input_source.get_bool( 'value_ref_in_group', True )
                value_from = input_source.get("value_from", None)
                if value_from:
                    value_from = value_from.split( ':' )
                    group.value_from = locals().get( value_from[0] )
                    group.test_param = rval[ group.value_ref ]
                    group.test_param.refresh_on_change = True
                    for attr in value_from[1].split( '.' ):
                        group.value_from = getattr( group.value_from, attr )
                    for case_value, case_inputs in group.value_from( context, group, self ).iteritems():
                        case = ConditionalWhen()
                        case.value = case_value
                        if case_inputs:
                            page_source = XmlPageSource( ElementTree.XML( "<when>%s</when>" % case_inputs ) )
                            case.inputs = self.parse_input_elem( page_source, enctypes, context )
                        else:
                            case.inputs = odict()
                        group.cases.append( case )
                else:
                    # Should have one child "input" which determines the case
                    test_param_input_source = input_source.parse_test_input_source()
                    group.test_param = self.parse_param_elem( test_param_input_source, enctypes, context )
                    possible_cases = list( group.test_param.legal_values )  # store possible cases, undefined whens will have no inputs
                    # Must refresh when test_param changes
                    group.test_param.refresh_on_change = True
                    # And a set of possible cases
                    for (value, case_inputs_source) in input_source.parse_when_input_sources():
                        case = ConditionalWhen()
                        case.value = value
                        case.inputs = self.parse_input_elem( case_inputs_source, enctypes, context )
                        group.cases.append( case )
                        try:
                            possible_cases.remove( case.value )
                        except:
                            log.warning( "Tool %s: a when tag has been defined for '%s (%s) --> %s', but does not appear to be selectable." %
                                         ( self.id, group.name, group.test_param.name, case.value ) )
                    for unspecified_case in possible_cases:
                        log.warning( "Tool %s: a when tag has not been defined for '%s (%s) --> %s', assuming empty inputs." %
                                     ( self.id, group.name, group.test_param.name, unspecified_case ) )
                        case = ConditionalWhen()
                        case.value = unspecified_case
                        case.inputs = odict()
                        group.cases.append( case )
                rval[group.name] = group
            elif input_type == "upload_dataset":
                elem = input_source.elem()
                group = UploadDataset()
                group.name = elem.get( "name" )
                group.title = elem.get( "title" )
                group.file_type_name = elem.get( 'file_type_name', group.file_type_name )
                group.default_file_type = elem.get( 'default_file_type', group.default_file_type )
                group.metadata_ref = elem.get( 'metadata_ref', group.metadata_ref )
                rval[ group.file_type_name ].refresh_on_change = True
                rval[ group.file_type_name ].refresh_on_change_values = \
                    self.app.datatypes_registry.get_composite_extensions()
                group_page_source = XmlPageSource(elem)
                group.inputs = self.parse_input_elem( group_page_source, enctypes, context )
                rval[ group.name ] = group
            elif input_type == "param":
                param = self.parse_param_elem( input_source, enctypes, context )
                rval[param.name] = param
                if hasattr( param, 'data_ref' ):
                    param.ref_input = context[ param.data_ref ]
                self.input_params.append( param )
        return rval

    def parse_param_elem( self, input_source, enctypes, context ):
        """
        Parse a single "<param>" element and return a ToolParameter instance.
        Also, if the parameter has a 'required_enctype' add it to the set
        enctypes.
        """
        param = ToolParameter.build( self, input_source )
        param_enctype = param.get_required_enctype()
        if param_enctype:
            enctypes.add( param_enctype )
        # If parameter depends on any other paramters, we must refresh the
        # form when it changes
        for name in param.get_dependencies():
            context[ name ].refresh_on_change = True
        return param

    def populate_tool_shed_info( self ):
        if self.repository_id is not None and self.app.name == 'galaxy':
            repository_id = self.app.security.decode_id( self.repository_id )
            tool_shed_repository = self.app.install_model.context.query( self.app.install_model.ToolShedRepository ).get( repository_id )
            if tool_shed_repository:
                self.tool_shed = tool_shed_repository.tool_shed
                self.repository_name = tool_shed_repository.name
                self.repository_owner = tool_shed_repository.owner
                self.installed_changeset_revision = tool_shed_repository.installed_changeset_revision

    @property
    def help(self):
        if self.__help is HELP_UNINITIALIZED:
            self.__ensure_help()
        return self.__help

    @property
    def help_by_page(self):
        if self.__help_by_page is HELP_UNINITIALIZED:
            self.__ensure_help()
        return self.__help_by_page

    def __ensure_help(self):
        with HELP_UNINITIALIZED:
            if self.__help is HELP_UNINITIALIZED:
                self.__inititalize_help()

    def __inititalize_help(self):
        tool_source = self.__help_source
        self.__help = None
        self.__help_by_page = []
        help_header = ""
        help_footer = ""
        help_text = tool_source.parse_help()
        if help_text is not None:
            if self.repository_id and help_text.find( '.. image:: ' ) >= 0:
                # Handle tool help image display for tools that are contained in repositories in the tool shed or installed into Galaxy.
                try:
                    help_text = suc.set_image_paths( self.app, self.repository_id, help_text )
                except Exception, e:
                    log.exception( "Exception in parse_help, so images may not be properly displayed:\n%s" % str( e ) )
            try:
                self.__help = Template( rst_to_html(help_text), input_encoding='utf-8',
                                        output_encoding='utf-8', default_filters=[ 'decode.utf8' ],
                                        encoding_errors='replace' )
            except:
                log.exception( "error in help for tool %s" % self.name )

            # Handle deprecated multi-page help text in XML case.
            if hasattr(tool_source, "root"):
                help_elem = tool_source.root.find("help")
                help_header = help_text
                help_pages = help_elem.findall( "page" )
                # Multiple help page case
                if help_pages:
                    for help_page in help_pages:
                        self.__help_by_page.append( help_page.text )
                        help_footer = help_footer + help_page.tail
                # Each page has to rendered all-together because of backreferences allowed by rst
                try:
                    self.__help_by_page = [ Template( rst_to_html( help_header + x + help_footer ),
                                                    input_encoding='utf-8', output_encoding='utf-8',
                                                    default_filters=[ 'decode.utf8' ],
                                                    encoding_errors='replace' )
                                            for x in self.__help_by_page ]
                except:
                    log.exception( "error in multi-page help for tool %s" % self.name )
        # Pad out help pages to match npages ... could this be done better?
        while len( self.__help_by_page ) < self.npages:
            self.__help_by_page.append( self.__help )

    def check_workflow_compatible( self, tool_source ):
        """
        Determine if a tool can be used in workflows. External tools and the
        upload tool are currently not supported by workflows.
        """
        # Multiple page tools are not supported -- we're eliminating most
        # of these anyway
        if self.has_multiple_pages:
            return False
        # This is probably the best bet for detecting external web tools
        # right now
        if self.tool_type.startswith( 'data_source' ):
            return False

        if hasattr( tool_source, "root"):
            root = tool_source.root
            if not string_as_bool( root.get( "workflow_compatible", "True" ) ):
                return False
        # TODO: Anyway to capture tools that dynamically change their own
        #       outputs?
        return True
    def new_state( self, trans, all_pages=False, history=None ):
        """
        Create a new `DefaultToolState` for this tool. It will be initialized
        with default values for inputs.

        Only inputs on the first page will be initialized unless `all_pages` is
        True, in which case all inputs regardless of page are initialized.
        """
        state = DefaultToolState()
        state.inputs = {}
        if all_pages:
            inputs = self.inputs
        else:
            inputs = self.inputs_by_page[ 0 ]
        self.fill_in_new_state( trans, inputs, state.inputs, history=history )
        return state
    def fill_in_new_state( self, trans, inputs, state, context=None, history=None ):
        """
        Fill in a tool state dictionary with default values for all parameters
        in the dictionary `inputs`. Grouping elements are filled in recursively.
        """
        context = ExpressionContext( state, context )
        for input in inputs.itervalues():
            state[ input.name ] = input.get_initial_value( trans, context, history=history )
    def get_param_html_map( self, trans, page=0, other_values={} ):
        """
        Return a dictionary containing the HTML representation of each
        parameter. This is used for rendering display elements. It is
        currently not compatible with grouping constructs.

        NOTE: This should be considered deprecated, it is only used for tools
              with `display` elements. These should be eliminated.
        """
        rval = dict()
        for key, param in self.inputs_by_page[page].iteritems():
            if not isinstance( param, ToolParameter ):
                raise Exception( "'get_param_html_map' only supported for simple paramters" )
            rval[key] = param.get_html( trans, other_values=other_values )
        return rval

    def get_param( self, key ):
        """
        Returns the parameter named `key` or None if there is no such
        parameter.
        """
        return self.inputs.get( key, None )

    def get_hook(self, name):
        """
        Returns an object from the code file referenced by `code_namespace`
        (this will normally be a callable object)
        """
        if self.code_namespace:
            # Try to look up hook in self.hook_map, otherwise resort to default
            if name in self.hook_map and self.hook_map[name] in self.code_namespace:
                return self.code_namespace[self.hook_map[name]]
            elif name in self.code_namespace:
                return self.code_namespace[name]
        return None

    def visit_inputs( self, value, callback ):
        """
        Call the function `callback` on each parameter of this tool. Visits
        grouping parameters recursively and constructs unique prefixes for
        each nested set of  The callback method is then called as:

        `callback( level_prefix, parameter, parameter_value )`
        """
        # HACK: Yet another hack around check_values -- WHY HERE?
        if not self.check_values:
            return
        for input in self.inputs.itervalues():
            if isinstance( input, ToolParameter ):
                callback( "", input, value[input.name] )
            else:
                input.visit_inputs( "", value[input.name], callback )

    def handle_input( self, trans, incoming, history=None, old_errors=None, process_state='update', source='html' ):
        """
        Process incoming parameters for this tool from the dict `incoming`,
        update the tool state (or create if none existed), and either return
        to the form or execute the tool (only if 'execute' was clicked and
        there were no errors).

        process_state can be either 'update' (to incrementally build up the state
        over several calls - one repeat per handle for instance) or 'populate'
        force a complete build of the state and submission all at once (like
        from API). May want an incremental version of the API also at some point,
        that is why this is not just called for_api.
        """
        all_pages = ( process_state == "populate" )  # If process_state = update, handle all pages at once.
        rerun_remap_job_id = None
        if 'rerun_remap_job_id' in incoming:
            try:
                rerun_remap_job_id = trans.app.security.decode_id( incoming[ 'rerun_remap_job_id' ] )
            except Exception:
                message = 'Failure executing tool (attempting to rerun invalid job).'
                return 'message.mako', dict( status='error', message=message, refresh_frames=[] )

        # Fixed set of input parameters may correspond to any number of jobs.
        # Expand these out to individual parameters for given jobs (tool
        # executions).
        expanded_incomings, collection_info = expand_meta_parameters( trans, self, incoming )

        if not expanded_incomings:
            raise exceptions.MessageException( "Tool execution failed, trying to run a tool over an empty collection." )

        # Remapping a single job to many jobs doesn't make sense, so disable
        # remap if multi-runs of tools are being used.
        if rerun_remap_job_id and len( expanded_incomings ) > 1:
            message = 'Failure executing tool (cannot create multiple jobs when remapping existing job).'
            return 'message.mako', dict( status='error', message=message, refresh_frames=[] )

        all_states = []
        for expanded_incoming in expanded_incomings:
            state, state_new = self.__fetch_state( trans, expanded_incoming, history, all_pages=all_pages )
            all_states.append( state )
        if state_new:
            # This feels a bit like a hack. It allows forcing full processing
            # of inputs even when there is no state in the incoming dictionary
            # by providing either 'runtool_btn' (the name of the submit button
            # on the standard run form) or "URL" (a parameter provided by
            # external data source tools).
            if "runtool_btn" not in incoming and "URL" not in incoming:
                if not self.display_interface:
                    return self.__no_display_interface_response()
                if len(incoming):
                    self.update_state( trans, self.inputs_by_page[state.page], state.inputs, incoming, old_errors=old_errors or {}, source=source )
                return self.default_template, dict( errors={}, tool_state=state, param_values={}, incoming={} )

        all_errors = []
        all_params = []
        for expanded_incoming, expanded_state in zip(expanded_incomings, all_states):
            errors, params = self.__check_param_values( trans, expanded_incoming, expanded_state, old_errors, process_state, history=history, source=source )
            all_errors.append( errors )
            all_params.append( params )

        if self.__should_refresh_state( incoming ):
            template, template_vars = self.__handle_state_refresh( trans, state, errors )
        else:
            # User actually clicked next or execute.

            # If there were errors, we stay on the same page and display
            # error messages
            if any( all_errors ):
                error_message = "One or more errors were found in the input you provided. The specific errors are marked below."
                template = self.default_template
                template_vars = dict( errors=errors, tool_state=state, incoming=incoming, error_message=error_message )
            # If we've completed the last page we can execute the tool
            elif all_pages or state.page == self.last_page:
                execution_tracker = execute_job( trans, self, all_params, history=history, rerun_remap_job_id=rerun_remap_job_id, collection_info=collection_info )
                if execution_tracker.successful_jobs:
                    template = 'tool_executed.mako'
                    template_vars = dict(
                        out_data=execution_tracker.output_datasets,
                        num_jobs=len( execution_tracker.successful_jobs ),
                        job_errors=execution_tracker.execution_errors,
                        jobs=execution_tracker.successful_jobs,
                        implicit_collections=execution_tracker.implicit_collections,
                    )
                else:
                    template = 'message.mako'
                    template_vars = dict( status='error', message=execution_tracker.execution_errors[0], refresh_frames=[] )
            # Otherwise move on to the next page
            else:
                template, template_vars = self.__handle_page_advance( trans, state, errors )
        return template, template_vars

    def __should_refresh_state( self, incoming ):
        return not( 'runtool_btn' in incoming or 'URL' in incoming or 'ajax_upload' in incoming )

    def handle_single_execution( self, trans, rerun_remap_job_id, params, history ):
        """
        Return a pair with whether execution is successful as well as either
        resulting output data or an error message indicating the problem.
        """
        try:
            params = self.__remove_meta_properties( params )
            job, out_data = self.execute( trans, incoming=params, history=history, rerun_remap_job_id=rerun_remap_job_id )
        except httpexceptions.HTTPFound, e:
            #if it's a paste redirect exception, pass it up the stack
            raise e
        except Exception, e:
            log.exception('Exception caught while attempting tool execution:')
            message = 'Error executing tool: %s' % str(e)
            return False, message
        if isinstance( out_data, odict ):
            return job, out_data.items()
        else:
            if isinstance( out_data, str ):
                message = out_data
            else:
                message = 'Failure executing tool (invalid data returned from tool execution)'
            return False, message

    def __handle_state_refresh( self, trans, state, errors ):
            try:
                self.find_fieldstorage( state.inputs )
            except InterruptedUpload:
                # If inputs contain a file it won't persist.  Most likely this
                # is an interrupted upload.  We should probably find a more
                # standard method of determining an incomplete POST.
                return self.handle_interrupted( trans, state.inputs )
            except:
                pass
            # Just a refresh, render the form with updated state and errors.
            if not self.display_interface:
                return self.__no_display_interface_response()
            return self.default_template, dict( errors=errors, tool_state=state )

    def __handle_page_advance( self, trans, state, errors ):
        state.page += 1
        # Fill in the default values for the next page
        self.fill_in_new_state( trans, self.inputs_by_page[ state.page ], state.inputs )
        if not self.display_interface:
            return self.__no_display_interface_response()
        return self.default_template, dict( errors=errors, tool_state=state )

    def __no_display_interface_response( self ):
        return 'message.mako', dict( status='info', message="The interface for this tool cannot be displayed", refresh_frames=['everything'] )

    def __fetch_state( self, trans, incoming, history, all_pages ):
        # Get the state or create if not found
        if "tool_state" in incoming:
            encoded_state = string_to_object( incoming["tool_state"] )
            state = DefaultToolState()
            state.decode( encoded_state, self, trans.app )
            new = False
        else:
            state = self.new_state( trans, history=history, all_pages=all_pages )
            new = True
        return state, new

    def __check_param_values( self, trans, incoming, state, old_errors, process_state, history, source ):
        # Process incoming data
        if not( self.check_values ):
            # If `self.check_values` is false we don't do any checking or
            # processing on input  This is used to pass raw values
            # through to/from external sites. FIXME: This should be handled
            # more cleanly, there is no reason why external sites need to
            # post back to the same URL that the tool interface uses.
            errors = {}
            params = incoming
        else:
            # Update state for all inputs on the current page taking new
            # values from `incoming`.
            if process_state == "update":
                inputs = self.inputs_by_page[state.page]
                errors = self.update_state( trans, inputs, state.inputs, incoming, old_errors=old_errors or {}, source=source )
            elif process_state == "populate":
                inputs = self.inputs
                errors = self.populate_state( trans, inputs, state.inputs, incoming, history, source=source )
            else:
                raise Exception("Unknown process_state type %s" % process_state)
            # If the tool provides a `validate_input` hook, call it.
            validate_input = self.get_hook( 'validate_input' )
            if validate_input:
                validate_input( trans, errors, state.inputs, inputs )
            params = state.inputs
        return errors, params

    def find_fieldstorage( self, x ):
        if isinstance( x, FieldStorage ):
            raise InterruptedUpload( None )
        elif type( x ) is types.DictType:
            [ self.find_fieldstorage( y ) for y in x.values() ]
        elif type( x ) is types.ListType:
            [ self.find_fieldstorage( y ) for y in x ]

    def handle_interrupted( self, trans, inputs ):
        """
        Upon handling inputs, if it appears that we have received an incomplete
        form, do some cleanup or anything else deemed necessary.  Currently
        this is only likely during file uploads, but this method could be
        generalized and a method standardized for handling other tools.
        """
        # If the async upload tool has uploading datasets, we need to error them.
        if 'async_datasets' in inputs and inputs['async_datasets'] not in [ 'None', '', None ]:
            for id in inputs['async_datasets'].split(','):
                try:
                    data = self.sa_session.query( trans.model.HistoryDatasetAssociation ).get( int( id ) )
                except:
                    log.exception( 'Unable to load precreated dataset (%s) sent in upload form' % id )
                    continue
                if trans.user is None and trans.galaxy_session.current_history != data.history:
                    log.error( 'Got a precreated dataset (%s) but it does not belong to anonymous user\'s current session (%s)'
                        % ( data.id, trans.galaxy_session.id ) )
                elif data.history.user != trans.user:
                    log.error( 'Got a precreated dataset (%s) but it does not belong to current user (%s)'
                        % ( data.id, trans.user.id ) )
                else:
                    data.state = data.states.ERROR
                    data.info = 'Upload of this dataset was interrupted.  Please try uploading again or'
                    self.sa_session.add( data )
                    self.sa_session.flush()
        # It's unlikely the user will ever see this.
        return 'message.mako', dict( status='error',
            message='Your upload was interrupted. If this was uninentional, please retry it.',
            refresh_frames=[], cont=None )

    def populate_state( self, trans, inputs, state, incoming, history=None, source="html", prefix="", context=None ):
        errors = dict()
        # Push this level onto the context stack
        context = ExpressionContext( state, context )
        for input in inputs.itervalues():
            key = prefix + input.name
            if isinstance( input, Repeat ):
                group_state = state[input.name]
                # Create list of empty errors for each previously existing state
                group_errors = [ ]
                any_group_errors = False
                rep_index = 0
                del group_state[:]  # Clear prepopulated defaults if repeat.min set.
                while True:
                    rep_name = "%s_%d" % ( key, rep_index )
                    if not any( [ incoming_key.startswith(rep_name) for incoming_key in incoming.keys() ] ):
                        break
                    if rep_index < input.max:
                        new_state = {}
                        new_state['__index__'] = rep_index
                        self.fill_in_new_state( trans, input.inputs, new_state, context, history=history )
                        group_state.append( new_state )
                        group_errors.append( {} )
                        rep_errors = self.populate_state( trans,
                                                    input.inputs,
                                                    new_state,
                                                    incoming,
                                                    history,
                                                    source,
                                                    prefix=rep_name + "|",
                                                    context=context )
                        if rep_errors:
                            any_group_errors = True
                            group_errors[rep_index].update( rep_errors )

                    else:
                        group_errors[-1] = { '__index__': 'Cannot add repeat (max size=%i).' % input.max }
                        any_group_errors = True
                    rep_index += 1
            elif isinstance( input, Conditional ):
                group_state = state[input.name]
                group_prefix = "%s|" % ( key )
                # Deal with the 'test' element and see if its value changed
                if input.value_ref and not input.value_ref_in_group:
                    # We are referencing an existent parameter, which is not
                    # part of this group
                    test_param_key = prefix + input.test_param.name
                else:
                    test_param_key = group_prefix + input.test_param.name
                # Get value of test param and determine current case
                value, test_param_error = check_param_from_incoming( trans,
                                                                     group_state,
                                                                     input.test_param,
                                                                     incoming,
                                                                     test_param_key,
                                                                     context,
                                                                     source )

                if test_param_error:
                    errors[ input.name ] = [ test_param_error ]
                    # Store the value of the test element
                    group_state[ input.test_param.name ] = value
                else:
                    current_case = input.get_current_case( value, trans )
                    # Current case has changed, throw away old state
                    group_state = state[input.name] = {}
                    # TODO: we should try to preserve values if we can
                    self.fill_in_new_state( trans, input.cases[current_case].inputs, group_state, context, history=history )
                    group_errors = self.populate_state( trans,
                                                        input.cases[current_case].inputs,
                                                        group_state,
                                                        incoming,
                                                        history,
                                                        source,
                                                        prefix=group_prefix,
                                                        context=context,
                    )
                    if group_errors:
                        errors[ input.name ] = group_errors
                    # Store the current case in a special value
                    group_state['__current_case__'] = current_case
                    # Store the value of the test element
                    group_state[ input.test_param.name ] = value
            elif isinstance( input, UploadDataset ):
                group_state = state[input.name]
                group_errors = []
                any_group_errors = False
                d_type = input.get_datatype( trans, context )
                writable_files = d_type.writable_files
                #remove extra files
                while len( group_state ) > len( writable_files ):
                    del group_state[-1]

                # Add new fileupload as needed
                while len( writable_files ) > len( group_state ):
                    new_state = {}
                    new_state['__index__'] = len( group_state )
                    self.fill_in_new_state( trans, input.inputs, new_state, context )
                    group_state.append( new_state )
                    if any_group_errors:
                        group_errors.append( {} )

                # Update state
                for i, rep_state in enumerate( group_state ):
                    rep_index = rep_state['__index__']
                    rep_prefix = "%s_%d|" % ( key, rep_index )
                    rep_errors = self.populate_state( trans,
                                                    input.inputs,
                                                    rep_state,
                                                    incoming,
                                                    history,
                                                    source,
                                                    prefix=rep_prefix,
                                                    context=context)
                    if rep_errors:
                        any_group_errors = True
                        group_errors.append( rep_errors )
                    else:
                        group_errors.append( {} )
                # Were there *any* errors for any repetition?
                if any_group_errors:
                    errors[input.name] = group_errors
            else:
                value, error = check_param_from_incoming( trans, state, input, incoming, key, context, source )
                if error:
                    errors[ input.name ] = error
                state[ input.name ] = value
        return errors

    def update_state( self, trans, inputs, state, incoming, source='html', prefix="", context=None,
                      update_only=False, old_errors={}, item_callback=None ):
        """
        Update the tool state in `state` using the user input in `incoming`.
        This is designed to be called recursively: `inputs` contains the
        set of inputs being processed, and `prefix` specifies a prefix to
        add to the name of each input to extract its value from `incoming`.

        If `update_only` is True, values that are not in `incoming` will
        not be modified. In this case `old_errors` can be provided, and any
        errors for parameters which were *not* updated will be preserved.
        """
        errors = dict()
        # Push this level onto the context stack
        context = ExpressionContext( state, context )
        # Iterate inputs and update (recursively)
        for input in inputs.itervalues():
            key = prefix + input.name
            if isinstance( input, Repeat ):
                group_state = state[input.name]
                # Create list of empty errors for each previously existing state
                group_errors = [ {} for i in range( len( group_state ) ) ]
                group_old_errors = old_errors.get( input.name, None )
                any_group_errors = False
                # Check any removals before updating state -- only one
                # removal can be performed, others will be ignored
                for i, rep_state in enumerate( group_state ):
                    rep_index = rep_state['__index__']
                    if key + "_" + str(rep_index) + "_remove" in incoming:
                        if len( group_state ) > input.min:
                            del group_state[i]
                            del group_errors[i]
                            if group_old_errors:
                                del group_old_errors[i]
                            break
                        else:
                            group_errors[i] = { '__index__': 'Cannot remove repeat (min size=%i).' % input.min }
                            any_group_errors = True
                            # Only need to find one that can't be removed due to size, since only
                            # one removal is processed at # a time anyway
                            break
                    elif group_old_errors and group_old_errors[i]:
                        group_errors[i] = group_old_errors[i]
                        any_group_errors = True
                # Update state
                max_index = -1
                for i, rep_state in enumerate( group_state ):
                    rep_index = rep_state['__index__']
                    max_index = max( max_index, rep_index )
                    rep_prefix = "%s_%d|" % ( key, rep_index )
                    if group_old_errors:
                        rep_old_errors = group_old_errors[i]
                    else:
                        rep_old_errors = {}
                    rep_errors = self.update_state( trans,
                                                    input.inputs,
                                                    rep_state,
                                                    incoming,
                                                    source=source,
                                                    prefix=rep_prefix,
                                                    context=context,
                                                    update_only=update_only,
                                                    old_errors=rep_old_errors,
                                                    item_callback=item_callback )
                    if rep_errors:
                        any_group_errors = True
                        group_errors[i].update( rep_errors )
                # Check for addition
                if key + "_add" in incoming:
                    if len( group_state ) < input.max:
                        new_state = {}
                        new_state['__index__'] = max_index + 1
                        self.fill_in_new_state( trans, input.inputs, new_state, context )
                        group_state.append( new_state )
                        group_errors.append( {} )
                    else:
                        group_errors[-1] = { '__index__': 'Cannot add repeat (max size=%i).' % input.max }
                        any_group_errors = True
                # Were there *any* errors for any repetition?
                if any_group_errors:
                    errors[input.name] = group_errors
            elif isinstance( input, Conditional ):
                group_state = state[input.name]
                group_old_errors = old_errors.get( input.name, {} )
                old_current_case = group_state['__current_case__']
                group_prefix = "%s|" % ( key )
                # Deal with the 'test' element and see if its value changed
                if input.value_ref and not input.value_ref_in_group:
                    # We are referencing an existent parameter, which is not
                    # part of this group
                    test_param_key = prefix + input.test_param.name
                else:
                    test_param_key = group_prefix + input.test_param.name
                test_param_error = None
                test_incoming = get_incoming_value( incoming, test_param_key, None )
                if test_param_key not in incoming \
                   and "__force_update__" + test_param_key not in incoming \
                   and update_only:
                    # Update only, keep previous value and state, but still
                    # recurse in case there are nested changes
                    value = group_state[ input.test_param.name ]
                    current_case = old_current_case
                    if input.test_param.name in old_errors:
                        errors[ input.test_param.name ] = old_errors[ input.test_param.name ]
                else:
                    # Get value of test param and determine current case
                    value, test_param_error = \
                        check_param( trans, input.test_param, test_incoming, context, source=source )
                    try:
                        current_case = input.get_current_case( value, trans )
                    except ValueError, e:
                        if input.is_job_resource_conditional:
                            # Unless explicitly given job resource parameters
                            # (e.g. from the run tool form) don't populate the
                            # state. Along with other hacks prevents workflow
                            # saving from populating resource defaults - which
                            # are meant to be much more transient than the rest
                            # of tool state.
                            continue
                        #load default initial value
                        if not test_param_error:
                            test_param_error = str( e )
                        if trans is not None:
                            history = trans.get_history()
                        else:
                            history = None
                        value = input.test_param.get_initial_value( trans, context, history=history )
                        current_case = input.get_current_case( value, trans )
                case_changed = current_case != old_current_case
                if case_changed:
                    # Current case has changed, throw away old state
                    group_state = state[input.name] = {}
                    # TODO: we should try to preserve values if we can
                    self.fill_in_new_state( trans, input.cases[current_case].inputs, group_state, context )
                    group_errors = dict()
                    group_old_errors = dict()

                # If we didn't just change the current case and are coming from HTML - the values
                # in incoming represent the old values and should not be replaced. If being updated
                # from the API (json) instead of HTML - form values below the current case
                # may also be supplied and incoming should be preferred to case defaults.
                if (not case_changed) or (source != "html"):
                    # Current case has not changed, update children
                    group_errors = self.update_state( trans,
                                                      input.cases[current_case].inputs,
                                                      group_state,
                                                      incoming,
                                                      prefix=group_prefix,
                                                      context=context,
                                                      source=source,
                                                      update_only=update_only,
                                                      old_errors=group_old_errors,
                                                      item_callback=item_callback )
                    if input.test_param.name in group_old_errors and not test_param_error:
                        test_param_error = group_old_errors[ input.test_param.name ]
                if test_param_error:
                    group_errors[ input.test_param.name ] = test_param_error
                if group_errors:
                    errors[ input.name ] = group_errors
                # Store the current case in a special value
                group_state['__current_case__'] = current_case
                # Store the value of the test element
                group_state[ input.test_param.name ] = value
            elif isinstance( input, UploadDataset ):
                group_state = state[input.name]
                group_errors = []
                group_old_errors = old_errors.get( input.name, None )
                any_group_errors = False
                d_type = input.get_datatype( trans, context )
                writable_files = d_type.writable_files
                #remove extra files
                while len( group_state ) > len( writable_files ):
                    del group_state[-1]
                    if group_old_errors:
                        del group_old_errors[-1]
                # Update state
                max_index = -1
                for i, rep_state in enumerate( group_state ):
                    rep_index = rep_state['__index__']
                    max_index = max( max_index, rep_index )
                    rep_prefix = "%s_%d|" % ( key, rep_index )
                    if group_old_errors:
                        rep_old_errors = group_old_errors[i]
                    else:
                        rep_old_errors = {}
                    rep_errors = self.update_state( trans,
                                                    input.inputs,
                                                    rep_state,
                                                    incoming,
                                                    prefix=rep_prefix,
                                                    context=context,
                                                    source=source,
                                                    update_only=update_only,
                                                    old_errors=rep_old_errors,
                                                    item_callback=item_callback )
                    if rep_errors:
                        any_group_errors = True
                        group_errors.append( rep_errors )
                    else:
                        group_errors.append( {} )
                # Add new fileupload as needed
                offset = 1
                while len( writable_files ) > len( group_state ):
                    new_state = {}
                    new_state['__index__'] = max_index + offset
                    offset += 1
                    self.fill_in_new_state( trans, input.inputs, new_state, context )
                    group_state.append( new_state )
                    if any_group_errors:
                        group_errors.append( {} )
                # Were there *any* errors for any repetition?
                if any_group_errors:
                    errors[input.name] = group_errors
            else:
                if key not in incoming \
                   and "__force_update__" + key not in incoming \
                   and update_only:
                    # No new value provided, and we are only updating, so keep
                    # the old value (which should already be in the state) and
                    # preserve the old error message.
                    if input.name in old_errors:
                        errors[ input.name ] = old_errors[ input.name ]
                else:
                    incoming_value = get_incoming_value( incoming, key, None )
                    value, error = check_param( trans, input, incoming_value, context, source=source )
                    # If a callback was provided, allow it to process the value
                    input_name = input.name
                    if item_callback:
                        old_value = state.get( input_name, None )
                        value, error = item_callback( trans, key, input, value, error, old_value, context )
                    if error:
                        errors[ input_name ] = error

                    state[ input_name ] = value
                    meta_properties = self.__meta_properties_for_state( key, incoming, incoming_value, value, input_name )
                    state.update( meta_properties )
        return errors

    def __remove_meta_properties( self, incoming ):
        result = incoming.copy()
        meta_property_suffixes = [
            "__multirun__",
            "__collection_multirun__",
        ]
        for key, value in incoming.iteritems():
            if any( map( lambda s: key.endswith(s), meta_property_suffixes ) ):
                del result[ key ]
        return result

    def __meta_properties_for_state( self, key, incoming, incoming_val, state_val, input_name ):
        meta_properties = {}
        meta_property_suffixes = [
            "__multirun__",
            "__collection_multirun__",
        ]
        for meta_property_suffix in meta_property_suffixes:
            multirun_key = "%s|%s" % ( key, meta_property_suffix )
            if multirun_key in incoming:
                multi_value = incoming[ multirun_key ]
                meta_properties[ "%s|%s" % ( input_name, meta_property_suffix ) ] = multi_value
        return meta_properties

    @property
    def params_with_missing_data_table_entry( self ):
        """
        Return all parameters that are dynamically generated select lists whose
        options require an entry not currently in the tool_data_table_conf.xml file.
        """
        params = []
        for input_param in self.input_params:
            if isinstance( input_param, SelectToolParameter ) and input_param.is_dynamic:
                options = input_param.options
                if options and options.missing_tool_data_table_name and input_param not in params:
                    params.append( input_param )
        return params

    @property
    def params_with_missing_index_file( self ):
        """
        Return all parameters that are dynamically generated
        select lists whose options refer to a  missing .loc file.
        """
        params = []
        for input_param in self.input_params:
            if isinstance( input_param, SelectToolParameter ) and input_param.is_dynamic:
                options = input_param.options
                if options and options.missing_index_file and input_param not in params:
                    params.append( input_param )
        return params

    def get_static_param_values( self, trans ):
        """
        Returns a map of parameter names and values if the tool does not
        require any user input. Will raise an exception if any parameter
        does require input.
        """
        args = dict()
        for key, param in self.inputs.iteritems():
            if isinstance( param, HiddenToolParameter ):
                args[key] = model.User.expand_user_properties( trans.user, param.value )
            elif isinstance( param, BaseURLToolParameter ):
                args[key] = param.get_value( trans )
            else:
                raise Exception( "Unexpected parameter type" )
        return args

    def execute( self, trans, incoming={}, set_output_hid=True, history=None, **kwargs ):
        """
        Execute the tool using parameter values in `incoming`. This just
        dispatches to the `ToolAction` instance specified by
        `self.tool_action`. In general this will create a `Job` that
        when run will build the tool's outputs, e.g. `DefaultToolAction`.
        """
        return self.tool_action.execute( self, trans, incoming=incoming, set_output_hid=set_output_hid, history=history, **kwargs )

    def params_to_strings( self, params, app ):
        return params_to_strings( self.inputs, params, app )

    def params_from_strings( self, params, app, ignore_errors=False ):
        return params_from_strings( self.inputs, params, app, ignore_errors )

    def check_and_update_param_values( self, values, trans, update_values=True, allow_workflow_parameters=False ):
        """
        Check that all parameters have values, and fill in with default
        values where necessary. This could be called after loading values
        from a database in case new parameters have been added.
        """
        messages = {}
        self.check_and_update_param_values_helper( self.inputs, values, trans, messages, update_values=update_values, allow_workflow_parameters=allow_workflow_parameters )
        return messages

    def check_and_update_param_values_helper( self, inputs, values, trans, messages, context=None, prefix="", update_values=True, allow_workflow_parameters=False ):
        """
        Recursive helper for `check_and_update_param_values_helper`
        """
        context = ExpressionContext( values, context )
        for input in inputs.itervalues():
            # No value, insert the default
            if input.name not in values:
                if isinstance( input, Conditional ):
                    cond_messages = {}
                    if not input.is_job_resource_conditional:
                        cond_messages = { input.test_param.name: "No value found for '%s%s', used default" % ( prefix, input.label ) }
                        messages[ input.name ] = cond_messages
                    test_value = input.test_param.get_initial_value( trans, context )
                    current_case = input.get_current_case( test_value, trans )
                    self.check_and_update_param_values_helper( input.cases[ current_case ].inputs, {}, trans, cond_messages, context, prefix, allow_workflow_parameters=allow_workflow_parameters )
                elif isinstance( input, Repeat ):
                    if input.min:
                        messages[ input.name ] = []
                        for i in range( input.min ):
                            rep_prefix = prefix + "%s %d > " % ( input.title, i + 1 )
                            rep_dict = dict()
                            messages[ input.name ].append( rep_dict )
                            self.check_and_update_param_values_helper( input.inputs, {}, trans, rep_dict, context, rep_prefix, allow_workflow_parameters=allow_workflow_parameters )
                else:
                    messages[ input.name ] = "No value found for '%s%s', used default" % ( prefix, input.label )
                values[ input.name ] = input.get_initial_value( trans, context )
            # Value, visit recursively as usual
            else:
                if isinstance( input, Repeat ):
                    for i, d in enumerate( values[ input.name ] ):
                        rep_prefix = prefix + "%s %d > " % ( input.title, i + 1 )
                        self.check_and_update_param_values_helper( input.inputs, d, trans, messages, context, rep_prefix, allow_workflow_parameters=allow_workflow_parameters )
                elif isinstance( input, Conditional ):
                    group_values = values[ input.name ]
                    use_initial_value = False
                    if '__current_case__' in group_values:
                        if int( group_values['__current_case__'] ) >= len( input.cases ):
                            use_initial_value = True
                    else:
                        use_initial_value = True
                    if input.test_param.name not in group_values or use_initial_value:
                        # No test param invalidates the whole conditional
                        values[ input.name ] = group_values = input.get_initial_value( trans, context )
                        messages[ input.test_param.name ] = "No value found for '%s%s', used default" % ( prefix, input.test_param.label )
                        current_case = group_values['__current_case__']
                        for child_input in input.cases[current_case].inputs.itervalues():
                            messages[ child_input.name ] = "Value no longer valid for '%s%s', replaced with default" % ( prefix, child_input.label )
                    else:
                        current = group_values["__current_case__"]
                        self.check_and_update_param_values_helper( input.cases[current].inputs, group_values, trans, messages, context, prefix, allow_workflow_parameters=allow_workflow_parameters )
                else:
                    # Regular tool parameter, no recursion needed
                    try:
                        ck_param = True
                        if allow_workflow_parameters and isinstance( values[ input.name ], basestring ):
                            if WORKFLOW_PARAMETER_REGULAR_EXPRESSION.search( values[ input.name ] ):
                                ck_param = False
                        #this will fail when a parameter's type has changed to a non-compatible one: e.g. conditional group changed to dataset input
                        if ck_param:
                            input.value_from_basic( input.value_to_basic( values[ input.name ], trans.app ), trans.app, ignore_errors=False )
                    except:
                        messages[ input.name ] = "Value no longer valid for '%s%s', replaced with default" % ( prefix, input.label )
                        if update_values:
                            values[ input.name ] = input.get_initial_value( trans, context )

    def handle_unvalidated_param_values( self, input_values, app ):
        """
        Find any instances of `UnvalidatedValue` within input_values and
        validate them (by calling `ToolParameter.from_html` and
        `ToolParameter.validate`).
        """
        # No validation is done when check_values is False
        if not self.check_values:
            return
        self.handle_unvalidated_param_values_helper( self.inputs, input_values, app )

    def handle_unvalidated_param_values_helper( self, inputs, input_values, app, context=None, prefix="" ):
        """
        Recursive helper for `handle_unvalidated_param_values`
        """
        context = ExpressionContext( input_values, context )
        for input in inputs.itervalues():
            if isinstance( input, Repeat ):
                for i, d in enumerate( input_values[ input.name ] ):
                    rep_prefix = prefix + "%s %d > " % ( input.title, i + 1 )
                    self.handle_unvalidated_param_values_helper( input.inputs, d, app, context, rep_prefix )
            elif isinstance( input, Conditional ):
                values = input_values[ input.name ]
                current = values["__current_case__"]
                # NOTE: The test param doesn't need to be checked since
                #       there would be no way to tell what case to use at
                #       workflow build time. However I'm not sure if we are
                #       actually preventing such a case explicately.
                self.handle_unvalidated_param_values_helper( input.cases[current].inputs, values, app, context, prefix )
            else:
                # Regular tool parameter
                value = input_values[ input.name ]
                if isinstance( value, UnvalidatedValue ):
                    try:
                        # Convert from html representation
                        if value.value is None:
                            # If value.value is None, it could not have been
                            # submited via html form and therefore .from_html
                            # can't be guaranteed to work
                            value = None
                        else:
                            value = input.from_html( value.value, None, context )
                        # Do any further validation on the value
                        input.validate( value, None )
                    except Exception, e:
                        # Wrap an re-raise any generated error so we can
                        # generate a more informative message
                        message = "Failed runtime validation of %s%s (%s)" \
                            % ( prefix, input.label, e )
                        raise LateValidationError( message )
                    input_values[ input.name ] = value

    def handle_job_failure_exception( self, e ):
        """
        Called by job.fail when an exception is generated to allow generation
        of a better error message (returning None yields the default behavior)
        """
        message = None
        # If the exception was generated by late validation, use its error
        # message (contains the parameter name and value)
        if isinstance( e, LateValidationError ):
            message = e.message
        return message

    def build_dependency_shell_commands( self ):
        """Return a list of commands to be run to populate the current environment to include this tools requirements."""
        return self.app.toolbox.dependency_manager.dependency_shell_commands(
            self.requirements,
            installed_tool_dependencies=self.installed_tool_dependencies
        )

    @property
    def installed_tool_dependencies(self):
        if self.tool_shed_repository:
            installed_tool_dependencies = self.tool_shed_repository.tool_dependencies_installed_or_in_error
        else:
            installed_tool_dependencies = None
        return installed_tool_dependencies

    def build_redirect_url_params( self, param_dict ):
        """
        Substitute parameter values into self.redirect_url_params
        """
        if not self.redirect_url_params:
            return
        redirect_url_params = None
        # Substituting parameter values into the url params
        redirect_url_params = fill_template( self.redirect_url_params, context=param_dict )
        # Remove newlines
        redirect_url_params = redirect_url_params.replace( "\n", " " ).replace( "\r", " " )
        return redirect_url_params

    def parse_redirect_url( self, data, param_dict ):
        """
        Parse the REDIRECT_URL tool param. Tools that send data to an external
        application via a redirect must include the following 3 tool params:

        1) REDIRECT_URL - the url to which the data is being sent

        2) DATA_URL - the url to which the receiving application will send an
           http post to retrieve the Galaxy data

        3) GALAXY_URL - the url to which the external application may post
           data as a response
        """
        redirect_url = param_dict.get( 'REDIRECT_URL' )
        redirect_url_params = self.build_redirect_url_params( param_dict )
        # Add the parameters to the redirect url.  We're splitting the param
        # string on '**^**' because the self.parse() method replaced white
        # space with that separator.
        params = redirect_url_params.split( '**^**' )
        rup_dict = {}
        for param in params:
            p_list = param.split( '=' )
            p_name = p_list[0]
            p_val = p_list[1]
            rup_dict[ p_name ] = p_val
        DATA_URL = param_dict.get( 'DATA_URL', None )
        assert DATA_URL is not None, "DATA_URL parameter missing in tool config."
        DATA_URL += "/%s/display" % str( data.id )
        redirect_url += "?DATA_URL=%s" % DATA_URL
        # Add the redirect_url_params to redirect_url
        for p_name in rup_dict:
            redirect_url += "&%s=%s" % ( p_name, rup_dict[ p_name ] )
        # Add the current user email to redirect_url
        if data.history.user:
            USERNAME = str( data.history.user.email )
        else:
            USERNAME = 'Anonymous'
        redirect_url += "&USERNAME=%s" % USERNAME
        return redirect_url

    def call_hook( self, hook_name, *args, **kwargs ):
        """
        Call the custom code hook function identified by 'hook_name' if any,
        and return the results
        """
        try:
            code = self.get_hook( hook_name )
            if code:
                return code( *args, **kwargs )
        except Exception, e:
            original_message = ''
            if len( e.args ):
                original_message = e.args[0]
            e.args = ( "Error in '%s' hook '%s', original message: %s" % ( self.name, hook_name, original_message ), )
            raise

    def exec_before_job( self, app, inp_data, out_data, param_dict={} ):
        pass

    def exec_after_process( self, app, inp_data, out_data, param_dict, job=None ):
        pass

    def job_failed( self, job_wrapper, message, exception=False ):
        """
        Called when a job has failed
        """
        pass

    def collect_associated_files( self, output, job_working_directory ):
        """
        Find extra files in the job working directory and move them into
        the appropriate dataset's files directory
        """
        for name, hda in output.items():
            temp_file_path = os.path.join( job_working_directory, "dataset_%s_files" % ( hda.dataset.id ) )
            extra_dir = None
            try:
                # This skips creation of directories - object store
                # automatically creates them.  However, empty directories will
                # not be created in the object store at all, which might be a
                # problem.
                for root, dirs, files in os.walk( temp_file_path ):
                    extra_dir = root.replace(job_working_directory, '', 1).lstrip(os.path.sep)
                    for f in files:
                        self.app.object_store.update_from_file(hda.dataset,
                            extra_dir=extra_dir,
                            alt_name=f,
                            file_name=os.path.join(root, f),
                            create=True,
                            preserve_symlinks=True
                        )
                # Clean up after being handled by object store.
                # FIXME: If the object (e.g., S3) becomes async, this will
                # cause issues so add it to the object store functionality?
                if extra_dir is not None:
                    # there was an extra_files_path dir, attempt to remove it
                    shutil.rmtree(temp_file_path)
            except Exception, e:
                log.debug( "Error in collect_associated_files: %s" % ( e ) )
                continue

    def collect_child_datasets( self, output, job_working_directory ):
        """
        Look for child dataset files, create HDA and attach to parent.
        """
        children = {}
        # Loop through output file names, looking for generated children in
        # form of 'child_parentId_designation_visibility_extension'
        for name, outdata in output.items():
            filenames = []
            if 'new_file_path' in self.app.config.collect_outputs_from:
                filenames.extend( glob.glob(os.path.join(self.app.config.new_file_path, "child_%i_*" % outdata.id) ) )
            if 'job_working_directory' in self.app.config.collect_outputs_from:
                filenames.extend( glob.glob(os.path.join(job_working_directory, "child_%i_*" % outdata.id) ) )
            for filename in filenames:
                if not name in children:
                    children[name] = {}
                fields = os.path.basename(filename).split("_")
                fields.pop(0)
                parent_id = int(fields.pop(0))
                designation = fields.pop(0)
                visible = fields.pop(0).lower()
                if visible == "visible":
                    visible = True
                else:
                    visible = False
                ext = fields.pop(0).lower()
                child_dataset = self.app.model.HistoryDatasetAssociation( extension=ext,
                                                                          parent_id=outdata.id,
                                                                          designation=designation,
                                                                          visible=visible,
                                                                          dbkey=outdata.dbkey,
                                                                          create_dataset=True,
                                                                          sa_session=self.sa_session )
                self.app.security_agent.copy_dataset_permissions( outdata.dataset, child_dataset.dataset )
                # Move data from temp location to dataset location
                self.app.object_store.update_from_file(child_dataset.dataset, file_name=filename, create=True)
                self.sa_session.add( child_dataset )
                self.sa_session.flush()
                child_dataset.set_size()
                child_dataset.name = "Secondary Dataset (%s)" % ( designation )
                child_dataset.init_meta()
                child_dataset.set_meta()
                child_dataset.set_peek()
                # Associate new dataset with job
                job = None
                for assoc in outdata.creating_job_associations:
                    job = assoc.job
                    break
                if job:
                    assoc = self.app.model.JobToOutputDatasetAssociation( '__new_child_file_%s|%s__' % ( name, designation ), child_dataset )
                    assoc.job = job
                    self.sa_session.add( assoc )
                    self.sa_session.flush()
                child_dataset.state = outdata.state
                self.sa_session.add( child_dataset )
                self.sa_session.flush()
                # Add child to return dict
                children[name][designation] = child_dataset
                # Need to update all associated output hdas, i.e. history was
                # shared with job running
                for dataset in outdata.dataset.history_associations:
                    if outdata == dataset:
                        continue
                    # Create new child dataset
                    child_data = child_dataset.copy( parent_id=dataset.id )
                    self.sa_session.add( child_data )
                    self.sa_session.flush()
        return children

    def collect_primary_datasets( self, output, job_working_directory, input_ext ):
        """
        Find any additional datasets generated by a tool and attach (for
        cases where number of outputs is not known in advance).
        """
        return output_collect.collect_primary_datasets( self, output, job_working_directory, input_ext )

    def to_dict( self, trans, link_details=False, io_details=False ):
        """ Returns dict of tool. """

        # Basic information
        tool_dict = super( Tool, self ).to_dict()

        # Add link details.
        if link_details:
            # Add details for creating a hyperlink to the tool.
            if not isinstance( self, DataSourceTool ):
                link = url_for( controller='tool_runner', tool_id=self.id )
            else:
                link = url_for( controller='tool_runner', action='data_source_redirect', tool_id=self.id )

            # Basic information
            tool_dict.update( { 'link': link,
                                'min_width': self.uihints.get( 'minwidth', -1 ),
                                'target': self.target } )

        # Add input and output details.
        if io_details:
            tool_dict[ 'inputs' ] = [ input.to_dict( trans ) for input in self.inputs.values() ]
            tool_dict[ 'outputs' ] = [ output.to_dict() for output in self.outputs.values() ]

        tool_dict[ 'panel_section_id' ], tool_dict[ 'panel_section_name' ] = self.get_panel_section()

        return tool_dict

    def get_default_history_by_trans( self, trans, create=False ):
        return trans.get_history( create=create )

    @classmethod
    def get_externally_referenced_paths( self, path ):
        """ Return relative paths to externally referenced files by the tool
        described by file at `path`. External components should not assume things
        about the structure of tool xml files (this is the tool's responsibility).
        """
        tree = raw_tool_xml_tree(path)
        root = tree.getroot()
        external_paths = []
        for code_elem in root.findall( 'code' ):
            external_path = code_elem.get( 'file' )
            if external_path:
                external_paths.append( external_path )
        external_paths.extend( imported_macro_paths( root ) )
        # May also need to load external citation files as well at some point.
        return external_paths


class OutputParameterJSONTool( Tool ):
    """
    Alternate implementation of Tool that provides parameters and other values
    JSONified within the contents of an output dataset
    """
    tool_type = 'output_parameter_json'

    def _prepare_json_list( self, param_list ):
        rval = []
        for value in param_list:
            if isinstance( value, dict ):
                rval.append( self._prepare_json_param_dict( value ) )
            elif isinstance( value, list ):
                rval.append( self._prepare_json_list( value ) )
            else:
                rval.append( str( value ) )
        return rval

    def _prepare_json_param_dict( self, param_dict ):
        rval = {}
        for key, value in param_dict.iteritems():
            if isinstance( value, dict ):
                rval[ key ] = self._prepare_json_param_dict( value )
            elif isinstance( value, list ):
                rval[ key ] = self._prepare_json_list( value )
            else:
                rval[ key ] = str( value )
        return rval

    def exec_before_job( self, app, inp_data, out_data, param_dict=None ):
        if param_dict is None:
            param_dict = {}
        json_params = {}
        json_params[ 'param_dict' ] = self._prepare_json_param_dict( param_dict )  # it would probably be better to store the original incoming parameters here, instead of the Galaxy modified ones?
        json_params[ 'output_data' ] = []
        json_params[ 'job_config' ] = dict( GALAXY_DATATYPES_CONF_FILE=param_dict.get( 'GALAXY_DATATYPES_CONF_FILE' ), GALAXY_ROOT_DIR=param_dict.get( 'GALAXY_ROOT_DIR' ), TOOL_PROVIDED_JOB_METADATA_FILE=jobs.TOOL_PROVIDED_JOB_METADATA_FILE )
        json_filename = None
        for i, ( out_name, data ) in enumerate( out_data.iteritems() ):
            #use wrapped dataset to access certain values
            wrapped_data = param_dict.get( out_name )
            #allow multiple files to be created
            file_name = str( wrapped_data )
            extra_files_path = str( wrapped_data.files_path )
            data_dict = dict( out_data_name=out_name,
                              ext=data.ext,
                              dataset_id=data.dataset.id,
                              hda_id=data.id,
                              file_name=file_name,
                              extra_files_path=extra_files_path )
            json_params[ 'output_data' ].append( data_dict )
            if json_filename is None:
                json_filename = file_name
        out = open( json_filename, 'w' )
        out.write( json.dumps( json_params ) )
        out.close()


class DataSourceTool( OutputParameterJSONTool ):
    """
    Alternate implementation of Tool for data_source tools -- those that
    allow the user to query and extract data from another web site.
    """
    tool_type = 'data_source'
    default_tool_action = DataSourceToolAction

    def _build_GALAXY_URL_parameter( self ):
        return ToolParameter.build( self, ElementTree.XML( '<param name="GALAXY_URL" type="baseurl" value="/tool_runner?tool_id=%s" />' % self.id ) )

    def parse_inputs( self, tool_source ):
        super( DataSourceTool, self ).parse_inputs( tool_source )
        if 'GALAXY_URL' not in self.inputs:
            self.inputs[ 'GALAXY_URL' ] = self._build_GALAXY_URL_parameter()
            self.inputs_by_page[0][ 'GALAXY_URL' ] = self.inputs[ 'GALAXY_URL' ]

    def exec_before_job( self, app, inp_data, out_data, param_dict=None ):
        if param_dict is None:
            param_dict = {}
        dbkey = param_dict.get( 'dbkey' )
        info = param_dict.get( 'info' )
        data_type = param_dict.get( 'data_type' )
        name = param_dict.get( 'name' )

        json_params = {}
        json_params[ 'param_dict' ] = self._prepare_json_param_dict( param_dict )  # it would probably be better to store the original incoming parameters here, instead of the Galaxy modified ones?
        json_params[ 'output_data' ] = []
        json_params[ 'job_config' ] = dict( GALAXY_DATATYPES_CONF_FILE=param_dict.get( 'GALAXY_DATATYPES_CONF_FILE' ), GALAXY_ROOT_DIR=param_dict.get( 'GALAXY_ROOT_DIR' ), TOOL_PROVIDED_JOB_METADATA_FILE=jobs.TOOL_PROVIDED_JOB_METADATA_FILE )
        json_filename = None
        for i, ( out_name, data ) in enumerate( out_data.iteritems() ):
            #use wrapped dataset to access certain values
            wrapped_data = param_dict.get( out_name )
            #allow multiple files to be created
            cur_base_param_name = 'GALAXY|%s|' % out_name
            cur_name = param_dict.get( cur_base_param_name + 'name', name )
            cur_dbkey = param_dict.get( cur_base_param_name + 'dkey', dbkey )
            cur_info = param_dict.get( cur_base_param_name + 'info', info )
            cur_data_type = param_dict.get( cur_base_param_name + 'data_type', data_type )
            if cur_name:
                data.name = cur_name
            if not data.info and cur_info:
                data.info = cur_info
            if cur_dbkey:
                data.dbkey = cur_dbkey
            if cur_data_type:
                data.extension = cur_data_type
            file_name = str( wrapped_data )
            extra_files_path = str( wrapped_data.files_path )
            data_dict = dict( out_data_name=out_name,
                              ext=data.ext,
                              dataset_id=data.dataset.id,
                              hda_id=data.id,
                              file_name=file_name,
                              extra_files_path=extra_files_path )
            json_params[ 'output_data' ].append( data_dict )
            if json_filename is None:
                json_filename = file_name
        out = open( json_filename, 'w' )
        out.write( json.dumps( json_params ) )
        out.close()


class AsyncDataSourceTool( DataSourceTool ):
    tool_type = 'data_source_async'

    def _build_GALAXY_URL_parameter( self ):
        return ToolParameter.build( self, ElementTree.XML( '<param name="GALAXY_URL" type="baseurl" value="/async/%s" />' % self.id ) )


class DataDestinationTool( Tool ):
    tool_type = 'data_destination'


class SetMetadataTool( Tool ):
    """
    Tool implementation for special tool that sets metadata on an existing
    dataset.
    """
    tool_type = 'set_metadata'
    requires_setting_metadata = False

    def exec_after_process( self, app, inp_data, out_data, param_dict, job=None ):
        for name, dataset in inp_data.iteritems():
            external_metadata = JobExternalOutputMetadataWrapper( job )
            if external_metadata.external_metadata_set_successfully( dataset, app.model.context ):
                dataset.metadata.from_JSON_dict( external_metadata.get_output_filenames_by_dataset( dataset, app.model.context ).filename_out )
            else:
                dataset._state = model.Dataset.states.FAILED_METADATA
                self.sa_session.add( dataset )
                self.sa_session.flush()
                return
            # If setting external metadata has failed, how can we inform the
            # user? For now, we'll leave the default metadata and set the state
            # back to its original.
            dataset.datatype.after_setting_metadata( dataset )
            if job and job.tool_id == '1.0.0':
                dataset.state = param_dict.get( '__ORIGINAL_DATASET_STATE__' )
            else:
                # Revert dataset.state to fall back to dataset.dataset.state
                dataset._state = None
            # Need to reset the peek, which may rely on metadata
            dataset.set_peek()
            self.sa_session.add( dataset )
            self.sa_session.flush()

    def job_failed( self, job_wrapper, message, exception=False ):
        job = job_wrapper.sa_session.query( model.Job ).get( job_wrapper.job_id )
        if job:
            inp_data = {}
            for dataset_assoc in job.input_datasets:
                inp_data[dataset_assoc.name] = dataset_assoc.dataset
            return self.exec_after_process( job_wrapper.app, inp_data, {}, job_wrapper.get_param_dict(), job=job )


class ExportHistoryTool( Tool ):
    tool_type = 'export_history'


class ImportHistoryTool( Tool ):
    tool_type = 'import_history'


class GenomeIndexTool( Tool ):
    tool_type = 'index_genome'


class DataManagerTool( OutputParameterJSONTool ):
    tool_type = 'manage_data'
    default_tool_action = DataManagerToolAction

    def __init__( self, config_file, root, app, guid=None, data_manager_id=None, **kwds ):
        self.data_manager_id = data_manager_id
        super( DataManagerTool, self ).__init__( config_file, root, app, guid=guid, **kwds )
        if self.data_manager_id is None:
            self.data_manager_id = self.id

    def exec_after_process( self, app, inp_data, out_data, param_dict, job=None, **kwds ):
        #run original exec_after_process
        super( DataManagerTool, self ).exec_after_process( app, inp_data, out_data, param_dict, job=job, **kwds )
        #process results of tool
        if job and job.state == job.states.ERROR:
            return
        #Job state may now be 'running' instead of previous 'error', but datasets are still set to e.g. error
        for dataset in out_data.itervalues():
            if dataset.state != dataset.states.OK:
                return
        data_manager_id = job.data_manager_association.data_manager_id
        data_manager = self.app.data_managers.get_manager( data_manager_id, None )
        assert data_manager is not None, "Invalid data manager (%s) requested. It may have been removed before the job completed." % ( data_manager_id )
        data_manager.process_result( out_data )

    def get_default_history_by_trans( self, trans, create=False ):
        def _create_data_manager_history( user ):
            history = trans.app.model.History( name='Data Manager History (automatically created)', user=user )
            data_manager_association = trans.app.model.DataManagerHistoryAssociation( user=user, history=history )
            trans.sa_session.add_all( ( history, data_manager_association ) )
            trans.sa_session.flush()
            return history
        user = trans.user
        assert user, 'You must be logged in to use this tool.'
        history = user.data_manager_histories
        if not history:
            #create
            if create:
                history = _create_data_manager_history( user )
            else:
                history = None
        else:
            for history in reversed( history ):
                history = history.history
                if not history.deleted:
                    break
            if history.deleted:
                if create:
                    history = _create_data_manager_history( user )
                else:
                    history = None
        return history


# Populate tool_type to ToolClass mappings
tool_types = {}
for tool_class in [ Tool, SetMetadataTool, OutputParameterJSONTool,
                    DataManagerTool, DataSourceTool, AsyncDataSourceTool,
                    DataDestinationTool ]:
    tool_types[ tool_class.tool_type ] = tool_class


# ---- Utility classes to be factored out -----------------------------------
class TracksterConfig:
    """ Trackster configuration encapsulation. """

    def __init__( self, actions ):
        self.actions = actions

    @staticmethod
    def parse( root ):
        actions = []
        for action_elt in root.findall( "action" ):
            actions.append( SetParamAction.parse( action_elt ) )
        return TracksterConfig( actions )


class SetParamAction:
    """ Set parameter action. """

    def __init__( self, name, output_name ):
        self.name = name
        self.output_name = output_name

    @staticmethod
    def parse( elt ):
        """ Parse action from element. """
        return SetParamAction( elt.get( "name" ), elt.get( "output_name" ) )


class BadValue( object ):
    def __init__( self, value ):
        self.value = value


class ToolStdioRegex( object ):
    """
    This is a container for the <stdio> element's regex subelement.
    The regex subelement has a "match" attribute, a "sources"
    attribute that contains "output" and/or "error", and a "level"
    attribute that contains "warning" or "fatal".
    """
    def __init__( self ):
        self.match = ""
        self.stdout_match = False
        self.stderr_match = False
        # TODO: Define a common class or constant for error level:
        self.error_level = "fatal"
        self.desc = ""


class ToolStdioExitCode( object ):
    """
    This is a container for the <stdio> element's <exit_code> subelement.
    The exit_code element has a range of exit codes and the error level.
    """
    def __init__( self ):
        self.range_start = float( "-inf" )
        self.range_end = float( "inf" )
        # TODO: Define a common class or constant for error level:
        self.error_level = "fatal"
        self.desc = ""


class TestCollectionDef( object ):

    def __init__( self, elem, parse_param_elem ):
        self.elements = []
        attrib = dict( elem.attrib )
        self.collection_type = attrib[ "type" ]
        self.name = attrib.get( "name", "Unnamed Collection" )
        for element in elem.findall( "element" ):
            element_attrib = dict( element.attrib )
            element_identifier = element_attrib[ "name" ]
            nested_collection_elem = element.find( "collection" )
            if nested_collection_elem:
                self.elements.append( ( element_identifier, TestCollectionDef( nested_collection_elem, parse_param_elem ) ) )
            else:
                self.elements.append( ( element_identifier, parse_param_elem( element ) ) )

    def collect_inputs( self ):
        inputs = []
        for element in self.elements:
            value = element[ 1 ]
            if isinstance( value, TestCollectionDef ):
                inputs.extend( value.collect_inputs() )
            else:
                inputs.append( value )
        return inputs


def json_fix( val ):
    if isinstance( val, list ):
        return [ json_fix( v ) for v in val ]
    elif isinstance( val, dict ):
        return dict( [ ( json_fix( k ), json_fix( v ) ) for ( k, v ) in val.iteritems() ] )
    elif isinstance( val, unicode ):
        return val.encode( "utf8" )
    else:
        return val


def check_param_from_incoming( trans, state, input, incoming, key, context, source ):
    """
    Unlike "update" state, this preserves default if no incoming value found.
    This lets API user specify just a subset of params and allow defaults to be
    used when available.
    """
    default_input_value = state.get( input.name, None )
    incoming_value = get_incoming_value( incoming, key, default_input_value )
    value, error = check_param( trans, input, incoming_value, context, source=source )
    return value, error


def get_incoming_value( incoming, key, default ):
    """
    Fetch value from incoming dict directly or check special nginx upload
    created variants of this key.
    """
    if "__" + key + "__is_composite" in incoming:
        composite_keys = incoming["__" + key + "__keys"].split()
        value = dict()
        for composite_key in composite_keys:
            value[composite_key] = incoming[key + "_" + composite_key]
        return value
    else:
        return incoming.get( key, default )


class InterruptedUpload( Exception ):
    pass
