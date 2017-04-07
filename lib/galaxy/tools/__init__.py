"""
Classes encapsulating galaxy tools and tool configuration.
"""
import glob
import json
import logging
import os
import re
import tarfile
import tempfile
import threading
from cgi import FieldStorage
from datetime import datetime
from distutils.version import LooseVersion
from xml.etree import ElementTree

from mako.template import Template
from paste import httpexceptions
from six import string_types
from six.moves.urllib.parse import unquote_plus

import galaxy.jobs
import tool_shed.util.repository_util as repository_util
import tool_shed.util.shed_util_common

from galaxy import (
    exceptions,
    model
)
from galaxy.datatypes.metadata import JobExternalOutputMetadataWrapper
from galaxy.managers import histories
from galaxy.queue_worker import send_control_task
from galaxy.tools.actions import DefaultToolAction
from galaxy.tools.actions.data_manager import DataManagerToolAction
from galaxy.tools.actions.data_source import DataSourceToolAction
from galaxy.tools.actions.model_operations import ModelOperationToolAction
from galaxy.tools.actions.upload import UploadToolAction
from galaxy.tools.deps import (
    CachedDependencyManager,
    views
)
from galaxy.tools.fetcher import ToolLocationFetcher
from galaxy.tools.parameters import (
    check_param,
    params_from_strings,
    params_to_incoming,
    params_to_strings,
    populate_state,
    visit_input_values
)
from galaxy.tools.parameters import output_collect
from galaxy.tools.parameters.basic import (
    BaseURLToolParameter,
    DataCollectionToolParameter,
    DataToolParameter,
    HiddenToolParameter,
    SelectToolParameter,
    ToolParameter
)
from galaxy.tools.parameters.grouping import Conditional, ConditionalWhen, Repeat, Section, UploadDataset
from galaxy.tools.parameters.input_translation import ToolInputTranslator
from galaxy.tools.parameters.meta import expand_meta_parameters
from galaxy.tools.parser import (
    get_tool_source,
    ToolOutputCollectionPart
)
from galaxy.tools.parser.xml import XmlPageSource
from galaxy.tools.test import parse_tests
from galaxy.tools.toolbox import BaseGalaxyToolBox
from galaxy.util import (
    ExecutionTimer,
    listify,
    rst_to_html,
    string_as_bool,
    unicodify
)
from galaxy.util.bunch import Bunch
from galaxy.util.dictifiable import Dictifiable
from galaxy.util.expressions import ExpressionContext
from galaxy.util.json import json_fix
from galaxy.util.json import safe_loads
from galaxy.util.odict import odict
from galaxy.util.template import fill_template
from galaxy.version import VERSION_MAJOR
from galaxy.web import url_for
from galaxy.web.form_builder import SelectField
from galaxy.work.context import WorkRequestContext
from tool_shed.util import common_util

from .execute import execute as execute_job
from .loader import (
    imported_macro_paths,
    raw_tool_xml_tree,
    template_macro_params
)

log = logging.getLogger( __name__ )

HELP_UNINITIALIZED = threading.Lock()
MODEL_TOOLS_PATH = os.path.abspath(os.path.dirname(__file__))
# Tools that require Galaxy's Python environment to be preserved.
GALAXY_LIB_TOOLS_UNVERSIONED = [
    "upload1",
    # Legacy tools bundled with Galaxy.
    "vcf_to_maf_customtrack1",
    "laj_1",
    "meme_fimo",
    "secure_hash_message_digest",
    "join1",
    "gff2bed1",
    "gff_filter_by_feature_count",
    "Extract genomic DNA 1",
    "aggregate_scores_in_intervals2",
    "Interval_Maf_Merged_Fasta2",
    "maf_stats1",
    "Interval2Maf1",
    "MAF_To_Interval1",
    "MAF_filter",
    "MAF_To_Fasta1",
    "MAF_Reverse_Complement_1",
    "MAF_split_blocks_by_species1",
    "maf_limit_size1",
    "maf_by_block_number1",
    "wiggle2simple1",
    # Converters
    "CONVERTER_bed_to_fli_0",
    "CONVERTER_fastq_to_fqtoc0",
    "CONVERTER_gff_to_fli_0",
    "CONVERTER_gff_to_interval_index_0",
    "CONVERTER_maf_to_fasta_0",
    "CONVERTER_maf_to_interval_0",
    "CONVERTER_wiggle_to_interval_0",
    # Tools improperly migrated to the tool shed (devteam)
    "lastz_wrapper_2",
    "qualityFilter",
    "winSplitter",
    "pileup_interval",
    "count_gff_features",
    "Convert characters1",
    "lastz_paired_reads_wrapper",
    "subRate1",
    "substitutions1",
    "sam_pileup",
    "find_diag_hits",
    "cufflinks",
    # Tools improperly migrated to the tool shed (iuc)
    "tabular_to_dbnsfp",
]
# Tools that needed galaxy on the PATH in the past but no longer do along
# with the version at which they were fixed.
GALAXY_LIB_TOOLS_VERSIONED = {
    "sam_to_bam": LooseVersion("1.1.3"),
}


class ToolErrorLog:
    def __init__(self):
        self.error_stack = []
        self.max_errors = 100

    def add_error(self, file, phase, exception):
        self.error_stack.insert(0, {
            "file": file,
            "time": str(datetime.now()),
            "phase": phase,
            "error": str(exception)
        } )
        if len(self.error_stack) > self.max_errors:
            self.error_stack.pop()


global_tool_errors = ToolErrorLog()


class ToolInputsNotReadyException( Exception ):
    pass


class ToolNotFoundException( Exception ):
    pass


class ToolBox( BaseGalaxyToolBox ):
    """ A derivative of AbstractToolBox with knowledge about Tool internals -
    how to construct them, action types, dependency management, etc....
    """

    def __init__( self, config_filenames, tool_root_dir, app, tool_conf_watcher=None ):
        self._reload_count = 0
        self.tool_location_fetcher = ToolLocationFetcher()
        super( ToolBox, self ).__init__(
            config_filenames=config_filenames,
            tool_root_dir=tool_root_dir,
            app=app,
        )

    def handle_panel_update(self, section_dict):
        """
        Sends a panel update to all threads/processes.
        """
        send_control_task(self.app, 'create_panel_section', kwargs=section_dict)
        # The following local call to self.create_section should be unnecessary
        # but occasionally the local ToolPanelElements instance appears to not
        # get updated.
        self.create_section(section_dict)

    def has_reloaded(self, other_toolbox):
        return self._reload_count != other_toolbox._reload_count

    @property
    def all_requirements(self):
        reqs = set([req for _, tool in self.tools() for req in tool.tool_requirements])
        return [r.to_dict() for r in reqs]

    @property
    def tools_by_id( self ):
        # Deprecated method, TODO - eliminate calls to this in test/.
        return self._tools_by_id

    def create_tool( self, config_file, repository_id=None, guid=None, **kwds ):
        try:
            tool_source = get_tool_source(
                config_file,
                enable_beta_formats=getattr( self.app.config, "enable_beta_tool_formats", False ),
                tool_location_fetcher=self.tool_location_fetcher,
            )
        except Exception as e:
            # capture and log parsing errors
            global_tool_errors.add_error(config_file, "Tool XML parsing", e)
            raise e
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
            # Normal tool
            root = getattr( tool_source, 'root', None )
            ToolClass = Tool
        tool = ToolClass( config_file, tool_source, self.app, guid=guid, repository_id=repository_id, **kwds )
        return tool

    def handle_datatypes_changed( self ):
        """ Refresh upload tools when new datatypes are added. """
        for tool_id in self._tools_by_id:
            tool = self._tools_by_id[ tool_id ]
            if isinstance( tool.tool_action, UploadToolAction ):
                self.reload_tool_by_id( tool_id )

    def get_tool_components( self, tool_id, tool_version=None, get_loaded_tools_by_lineage=False, set_selected=False ):
        """
        Retrieve all loaded versions of a tool from the toolbox and return a select list enabling
        selection of a different version, the list of the tool's loaded versions, and the specified tool.
        """
        toolbox = self
        tool_version_select_field = None
        tools = []
        tool = None
        # Backwards compatibility for datasource tools that have default tool_id configured, but which
        # are now using only GALAXY_URL.
        tool_ids = listify( tool_id )
        for tool_id in tool_ids:
            if get_loaded_tools_by_lineage:
                tools = toolbox.get_loaded_tools_by_lineage( tool_id )
            else:
                tools = toolbox.get_tool( tool_id, tool_version=tool_version, get_all_versions=True )
            if tools:
                tool = toolbox.get_tool( tool_id, tool_version=tool_version, get_all_versions=False )
                if len( tools ) > 1:
                    tool_version_select_field = self.__build_tool_version_select_field( tools, tool.id, set_selected )
                break
        return tool_version_select_field, tools, tool

    def _path_template_kwds( self ):
        return {
            "model_tools_path": MODEL_TOOLS_PATH,
        }

    def _get_tool_shed_repository( self, tool_shed, name, owner, installed_changeset_revision ):
        # Abstract toolbox doesn't have a dependency on the the database, so
        # override _get_tool_shed_repository here to provide this information.

        return repository_util.get_installed_repository(
            self.app,
            tool_shed=tool_shed,
            name=name,
            owner=owner,
            installed_changeset_revision=installed_changeset_revision
        )

    def __build_tool_version_select_field( self, tools, tool_id, set_selected ):
        """Build a SelectField whose options are the ids for the received list of tools."""
        options = []
        refresh_on_change_values = []
        for tool in tools:
            options.insert( 0, ( tool.version, tool.id ) )
            refresh_on_change_values.append( tool.id )
        select_field = SelectField( name='tool_id', refresh_on_change=True, refresh_on_change_values=refresh_on_change_values )
        for option_tup in options:
            selected = set_selected and option_tup[ 1 ] == tool_id
            if selected:
                select_field.add_option( 'version %s' % option_tup[ 0 ], option_tup[ 1 ], selected=True )
            else:
                select_field.add_option( 'version %s' % option_tup[ 0 ], option_tup[ 1 ] )
        return select_field


class DefaultToolState( object ):
    """
    Keeps track of the state of a users interaction with a tool between
    requests.
    """
    def __init__( self ):
        self.page = 0
        self.rerun_remap_job_id = None
        self.inputs = {}

    def initialize( self, trans, tool ):
        """
        Create a new `DefaultToolState` for this tool. It will be initialized
        with default values for inputs. Grouping elements are filled in recursively.
        """
        self.inputs = {}
        context = ExpressionContext( self.inputs )
        for input in tool.inputs.itervalues():
            self.inputs[ input.name ] = input.get_initial_value( trans, context )

    def encode( self, tool, app, nested=False ):
        """
        Convert the data to a string
        """
        value = params_to_strings( tool.inputs, self.inputs, app, nested=nested )
        value["__page__"] = self.page
        value["__rerun_remap_job_id__"] = self.rerun_remap_job_id
        return value

    def decode( self, values, tool, app ):
        """
        Restore the state from a string
        """
        values = json_fix( safe_loads( values ) ) or {}
        self.page = values.pop( "__page__" ) if "__page__" in values else None
        self.rerun_remap_job_id = values.pop( "__rerun_remap_job_id__" ) if "__rerun_remap_job_id__" in values else None
        self.inputs = params_from_strings( tool.inputs, values, app, ignore_errors=True )

    def copy( self ):
        """
        Shallow copy of the state
        """
        new_state = DefaultToolState()
        new_state.page = self.page
        new_state.rerun_remap_job_id = self.rerun_remap_job_id
        new_state.inputs = self.inputs
        return new_state


class Tool( object, Dictifiable ):
    """
    Represents a computational tool that can be executed through Galaxy.
    """

    tool_type = 'default'
    requires_setting_metadata = True
    default_tool_action = DefaultToolAction
    dict_collection_visible_keys = ( 'id', 'name', 'version', 'description', 'labels' )

    def __init__( self, config_file, tool_source, app, guid=None, repository_id=None, allow_code_files=True ):
        """Load a tool from the config named by `config_file`"""
        # Determine the full path of the directory where the tool config is
        self.config_file = config_file
        self.tool_dir = os.path.dirname( config_file )
        self.app = app
        self.repository_id = repository_id
        self._allow_code_files = allow_code_files
        # setup initial attribute values
        self.inputs = odict()
        self.stdio_exit_codes = list()
        self.stdio_regexes = list()
        self.inputs_by_page = list()
        self.display_by_page = list()
        self.action = '/tool_runner/index'
        self.target = 'galaxy_main'
        self.method = 'post'
        self.labels = []
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
        self.changeset_revision = None
        self.installed_changeset_revision = None
        # The tool.id value will be the value of guid, but we'll keep the
        # guid attribute since it is useful to have.
        self.guid = guid
        self.old_id = None
        self.version = None
        self.dependencies = []
        # Enable easy access to this tool's version lineage.
        self.lineage_ids = []
        # populate toolshed repository info, if available
        self.populate_tool_shed_info()
        # add tool resource parameters
        self.populate_resource_parameters( tool_source )
        # Parse XML element containing configuration
        try:
            self.parse( tool_source, guid=guid )
        except Exception as e:
            global_tool_errors.add_error(config_file, "Tool Loading", e)
            raise e
        self.history_manager = histories.HistoryManager( app )
        self._view = views.DependencyResolversView(app)

    @property
    def version_object(self):
        return LooseVersion(self.version)

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
            return repository_util.get_installed_repository( self.app,
                                                             tool_shed=self.tool_shed,
                                                             name=self.repository_name,
                                                             owner=self.repository_owner,
                                                             installed_changeset_revision=self.installed_changeset_revision )
        return None

    @property
    def produces_collections_of_unknown_type( self ):

        def output_is_dynamic_collection(output):
            if not output.collection:
                return False
            if output.structure.collection_type:
                return False
            return True

        return any( map( output_is_dynamic_collection, self.outputs.values() ) )

    @property
    def produces_collections_with_unknown_structure( self ):

        def output_is_dynamic(output):
            if not output.collection:
                return False
            return output.dynamic_structure

        return any( map( output_is_dynamic, self.outputs.values() ) )

    @property
    def valid_input_states( self ):
        return model.Dataset.valid_input_states

    @property
    def requires_galaxy_python_environment(self):
        """Indicates this tool's runtime requires Galaxy's Python environment."""
        # All special tool types (data source, history import/export, etc...)
        # seem to require Galaxy's Python.
        if self.tool_type != "default":
            return True

        config = self.app.config
        preserve_python_environment = config.preserve_python_environment
        if preserve_python_environment == "always":
            return True
        elif preserve_python_environment == "legacy_and_local" and self.repository_id is None:
            return True
        else:
            unversioned_legacy_tool = self.old_id in GALAXY_LIB_TOOLS_UNVERSIONED
            versioned_legacy_tool = self.old_id in GALAXY_LIB_TOOLS_VERSIONED
            legacy_tool = unversioned_legacy_tool or \
                (versioned_legacy_tool and self.version_object < GALAXY_LIB_TOOLS_VERSIONED[self.old_id])
            return legacy_tool

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
                        if param not in job_tool_config.params or job_tool_config.params[param] != value:
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

    def allow_user_access( self, user, attempting_access=True ):
        """
        :returns: bool -- Whether the user is allowed to access the tool.
        """
        if self.require_login and user is None:
            return False
        return True

    def parse( self, tool_source, guid=None ):
        """
        Read tool configuration from the element `root` and fill in `self`.
        """
        self.profile = float( tool_source.parse_profile() )
        # Get the UNIQUE id for the tool
        self.old_id = tool_source.parse_id()
        if guid is None:
            self.id = self.old_id
        else:
            self.id = guid
        if not self.id:
            raise Exception( "Missing tool 'id' for tool at '%s'" % tool_source )

        if self.profile >= 16.04 and VERSION_MAJOR < self.profile:
            template = "The tool %s targets version %s of Galaxy, you should upgrade Galaxy to ensure proper functioning of this tool."
            message = template % (self.id, self.profile)
            log.warning(message)

        # Get the (user visible) name of the tool
        self.name = tool_source.parse_name()
        if not self.name:
            raise Exception( "Missing tool 'name' for tool with id '%s' at '%s'" % (self.id, tool_source) )

        self.version = tool_source.parse_version()
        if not self.version:
            if self.profile < 16.04:
                # For backward compatibility, some tools may not have versions yet.
                self.version = "1.0.0"
            else:
                raise Exception( "Missing tool 'version' for tool with id '%s' at '%s'" % (self.id, tool_source) )

        self.edam_operations = tool_source.parse_edam_operations()
        self.edam_topics = tool_source.parse_edam_topics()

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

        self.parse_command( tool_source )
        self.environment_variables = self.parse_environment_variables( tool_source )

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
        if hasattr( self.app, 'job_config' ):
            self.job_tool_configurations = self.app.job_config.get_job_tool_configurations(self_ids)

        # Is this a 'hidden' tool (hidden in tool menu)
        self.hidden = tool_source.parse_hidden()

        self.__parse_legacy_features(tool_source)

        # Load any tool specific options (optional)
        self.options = dict(
            sanitize=tool_source.parse_sanitize(),
            refresh=tool_source.parse_refresh(),
        )
        self.options = Bunch(** self.options)

        # Parse tool inputs (if there are any required)
        self.parse_inputs( tool_source )

        # Parse tool help
        self.parse_help( tool_source )

        # Description of outputs produced by an invocation of the tool
        self.parse_outputs( tool_source )

        # Parse result handling for tool exit codes and stdout/stderr messages:
        self.parse_stdio( tool_source )

        self.strict_shell = tool_source.parse_strict_shell()

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
        if self._allow_code_files:
            for code_elem in root.findall("code"):
                for hook_elem in code_elem.findall("hook"):
                    for key, value in hook_elem.items():
                        # map hook to function
                        self.hook_map[key] = value
                file_name = code_elem.get("file")
                code_path = os.path.join( self.tool_dir, file_name )
                with open(code_path) as f:
                    exec(compile(f.read(), code_path, 'exec'), self.code_namespace)

        # User interface hints
        uihints_elem = root.find( "uihints" )
        if uihints_elem is not None:
            for key, value in uihints_elem.attrib.items():
                self.uihints[ key ] = value

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
            inputs_elem = conf_parent_elem.find( "inputs" )
            if inputs_elem is not None:
                name = inputs_elem.get( "name" )
                filename = inputs_elem.get( "filename", None )
                format = inputs_elem.get("format", "json")
                content = dict(format=format)
                self.config_files.append( ( name, filename, content ) )
            for conf_elem in conf_parent_elem.findall( "configfile" ):
                name = conf_elem.get( "name" )
                filename = conf_elem.get( "filename", None )
                content = conf_elem.text
                self.config_files.append( ( name, filename, content ) )

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

    def parse_command( self, tool_source ):
        """
        """
        # Command line (template). Optional for tools that do not invoke a local program
        command = tool_source.parse_command()
        if command is not None:
            self.command = command.lstrip()  # get rid of leading whitespace
            # Must pre-pend this AFTER processing the cheetah command template
            self.interpreter = tool_source.parse_interpreter()
        else:
            self.command = ''
            self.interpreter = None

    def parse_environment_variables( self, tool_source ):
        return tool_source.parse_environment_variables()

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
                    if '?' in unquote_plus( self.action ):
                        raise Exception( 'URL parameters in a non-default tool action can not be used '
                                         'in conjunction with nginx upload.  Please convert them to '
                                         'hidden POST parameters' )
                    self.action = (self.app.config.nginx_upload_path + '?nginx_redir=',
                                   unquote_plus(self.action))
                self.target = input_elem.get( "target", self.target )
                self.method = input_elem.get( "method", self.method )
                # Parse the actual parameters
                # Handle multiple page case
            for page_source in pages.page_sources:
                inputs = self.parse_input_elem( page_source, enctypes )
                display = page_source.parse_display()
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
        self.outputs, self.output_collections = tool_source.parse_outputs(self)

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
                    for case_value, case_inputs in group.value_from( context, group, self ).items():
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
                    if group.test_param.optional:
                        log.warning("Tool with id %s declares a conditional test parameter as optional, this is invalid and will be ignored." % self.id)
                        group.test_param.optional = False
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
            elif input_type == "section":
                group = Section()
                group.name = input_source.get( "name" )
                group.title = input_source.get( "title" )
                group.help = input_source.get( "help", None )
                group.expanded = input_source.get_bool( "expanded", False )
                page_source = input_source.parse_nested_inputs_source()
                group.inputs = self.parse_input_elem( page_source, enctypes, context )
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
            # Let it throw exception, but give some hint what the problem might be
            if name not in context:
                log.error("Could not find dependency '%s' of parameter '%s' in tool %s" % (name, param.name, self.name) )
            context[ name ].refresh_on_change = True
        return param

    def populate_resource_parameters( self, tool_source ):
        root = getattr( tool_source, 'root', None )
        if root is not None and hasattr( self.app, 'job_config' ) and hasattr( self.app.job_config, 'get_tool_resource_xml' ):
            resource_xml = self.app.job_config.get_tool_resource_xml( root.get( 'id' ), self.tool_type )
            if resource_xml is not None:
                inputs = root.find( 'inputs' )
                if inputs is None:
                    inputs = ElementTree.fromstring( '<inputs/>' )
                    root.append( inputs )
                inputs.append( resource_xml )

    def populate_tool_shed_info( self ):
        if self.repository_id is not None and self.app.name == 'galaxy':
            repository_id = self.app.security.decode_id( self.repository_id )
            tool_shed_repository = self.app.install_model.context.query( self.app.install_model.ToolShedRepository ).get( repository_id )
            if tool_shed_repository:
                self.tool_shed = tool_shed_repository.tool_shed
                self.repository_name = tool_shed_repository.name
                self.repository_owner = tool_shed_repository.owner
                self.changeset_revision = tool_shed_repository.changeset_revision
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
                    help_text = tool_shed.util.shed_util_common.set_image_paths( self.app, self.repository_id, help_text )
                except Exception as e:
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

    def find_output_def( self, name ):
        # name is JobToOutputDatasetAssociation name.
        # TODO: to defensive, just throw IndexError and catch somewhere
        # up that stack.
        if ToolOutputCollectionPart.is_named_collection_part_name( name ):
            collection_name, part = ToolOutputCollectionPart.split_output_name( name )
            collection_def = self.output_collections.get( collection_name, None )
            if not collection_def:
                return None
            return collection_def.outputs.get( part, None )
        else:
            return self.outputs.get( name, None )

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

        if self.produces_collections_of_unknown_type:
            # Getting there...
            return False

        if hasattr( tool_source, "root"):
            root = tool_source.root
            if not string_as_bool( root.get( "workflow_compatible", "True" ) ):
                return False

        # TODO: Anyway to capture tools that dynamically change their own
        #       outputs?
        return True

    def new_state( self, trans ):
        """
        Create a new `DefaultToolState` for this tool. It will be initialized
        with default values for inputs. Grouping elements are filled in recursively.
        """
        state = DefaultToolState()
        state.initialize( trans, self )
        return state

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

    def visit_inputs( self, values, callback ):
        """
        Call the function `callback` on each parameter of this tool. Visits
        grouping parameters recursively and constructs unique prefixes for
        each nested set of  The callback method is then called as:

        `callback( level_prefix, parameter, parameter_value )`
        """
        # HACK: Yet another hack around check_values -- WHY HERE?
        if self.check_values:
            visit_input_values( self.inputs, values, callback )

    def handle_input( self, trans, incoming, history=None ):
        """
        Process incoming parameters for this tool from the dict `incoming`,
        update the tool state (or create if none existed), and either return
        to the form or execute the tool (only if 'execute' was clicked and
        there were no errors).
        """
        request_context = WorkRequestContext( app=trans.app, user=trans.user, history=history or trans.history )
        rerun_remap_job_id = None
        if 'rerun_remap_job_id' in incoming:
            try:
                rerun_remap_job_id = trans.app.security.decode_id( incoming[ 'rerun_remap_job_id' ] )
            except Exception as exception:
                log.error( str( exception ) )
                raise exceptions.MessageException( 'Failure executing tool (attempting to rerun invalid job).' )

        # Fixed set of input parameters may correspond to any number of jobs.
        # Expand these out to individual parameters for given jobs (tool executions).
        expanded_incomings, collection_info = expand_meta_parameters( trans, self, incoming )
        if not expanded_incomings:
            raise exceptions.MessageException( 'Tool execution failed, trying to run a tool over an empty collection.' )

        # Remapping a single job to many jobs doesn't make sense, so disable
        # remap if multi-runs of tools are being used.
        if rerun_remap_job_id and len( expanded_incomings ) > 1:
            raise exceptions.MessageException( 'Failure executing tool (cannot create multiple jobs when remapping existing job).' )

        # Process incoming data
        validation_timer = ExecutionTimer()
        all_errors = []
        all_params = []
        for expanded_incoming in expanded_incomings:
            params = {}
            errors = {}
            if self.input_translator:
                self.input_translator.translate( expanded_incoming )
            if not self.check_values:
                # If `self.check_values` is false we don't do any checking or
                # processing on input  This is used to pass raw values
                # through to/from external sites.
                params = expanded_incoming
            else:
                # Update state for all inputs on the current page taking new
                # values from `incoming`.
                populate_state( request_context, self.inputs, expanded_incoming, params, errors )

                # If the tool provides a `validate_input` hook, call it.
                validate_input = self.get_hook( 'validate_input' )
                if validate_input:
                    validate_input( request_context, errors, params, self.inputs )
            all_errors.append( errors )
            all_params.append( params )
        log.debug( 'Validated and populated state for tool request %s' % validation_timer )
        # If there were errors, we stay on the same page and display them
        if any( all_errors ):
            err_data = { key: value for d in all_errors for ( key, value ) in d.items() }
            raise exceptions.MessageException( ', '.join( msg for msg in err_data.values() ), err_data=err_data )
        else:
            execution_tracker = execute_job( trans, self, all_params, history=request_context.history, rerun_remap_job_id=rerun_remap_job_id, collection_info=collection_info )
            if execution_tracker.successful_jobs:
                return dict( out_data=execution_tracker.output_datasets,
                             num_jobs=len( execution_tracker.successful_jobs ),
                             job_errors=execution_tracker.execution_errors,
                             jobs=execution_tracker.successful_jobs,
                             output_collections=execution_tracker.output_collections,
                             implicit_collections=execution_tracker.implicit_collections )
            else:
                raise exceptions.MessageException( execution_tracker.execution_errors[ 0 ] )

    def handle_single_execution( self, trans, rerun_remap_job_id, params, history, mapping_over_collection, execution_cache=None ):
        """
        Return a pair with whether execution is successful as well as either
        resulting output data or an error message indicating the problem.
        """
        try:
            job, out_data = self.execute( trans, incoming=params, history=history, rerun_remap_job_id=rerun_remap_job_id, mapping_over_collection=mapping_over_collection, execution_cache=execution_cache )
        except httpexceptions.HTTPFound as e:
            # if it's a paste redirect exception, pass it up the stack
            raise e
        except ToolInputsNotReadyException as e:
            return False, e
        except Exception as e:
            log.exception('Exception caught while attempting tool execution:')
            message = 'Error executing tool: %s' % str(e)
            return False, message
        if isinstance( out_data, odict ):
            return job, list(out_data.items())
        else:
            if isinstance( out_data, string_types ):
                message = out_data
            else:
                message = 'Failure executing tool (invalid data returned from tool execution)'
            return False, message

    def find_fieldstorage( self, x ):
        if isinstance( x, FieldStorage ):
            raise InterruptedUpload( None )
        elif isinstance(x, dict):
            [ self.find_fieldstorage( y ) for y in x.values() ]
        elif isinstance(x, list):
            [ self.find_fieldstorage( y ) for y in x ]

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
        for key, param in self.inputs.items():
            # BaseURLToolParameter is now a subclass of HiddenToolParameter, so
            # we must check if param is a BaseURLToolParameter first
            if isinstance( param, BaseURLToolParameter ):
                args[key] = param.get_initial_value( trans, None )
            elif isinstance( param, HiddenToolParameter ):
                args[key] = model.User.expand_user_properties( trans.user, param.value )
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

    def check_and_update_param_values( self, values, trans, update_values=True, workflow_building_mode=False ):
        """
        Check that all parameters have values, and fill in with default
        values where necessary. This could be called after loading values
        from a database in case new parameters have been added.
        """
        messages = {}
        request_context = WorkRequestContext( app=trans.app, user=trans.user, history=trans.history, workflow_building_mode=workflow_building_mode )

        def validate_inputs( input, value, error, parent, context, prefixed_name, prefixed_label, **kwargs ):
            if not error:
                value, error = check_param( request_context, input, value, context )
            if error:
                if update_values:
                    try:
                        previous_value = value
                        value = input.get_initial_value( request_context, context )
                        if not prefixed_name.startswith( '__' ):
                            messages[ prefixed_name ] = error if previous_value == value else '%s Using default: \'%s\'.' % ( error, value )
                        parent[ input.name ] = value
                    except:
                        messages[ prefixed_name ] = 'Attempt to replace invalid value for \'%s\' failed.' % ( prefixed_label )
                else:
                    messages[ prefixed_name ] = error

        visit_input_values( self.inputs, values, validate_inputs )
        return messages

    def build_dependency_cache(self, **kwds):
        if isinstance(self.app.toolbox.dependency_manager, CachedDependencyManager):
            self.app.toolbox.dependency_manager.build_cache(
                requirements=self.requirements,
                installed_tool_dependencies=self.installed_tool_dependencies,
                tool_dir=self.tool_dir,
                job_directory=None,
                metadata=False,
                tool_instance=self,
                **kwds
            )

    def build_dependency_shell_commands( self, job_directory=None, metadata=False ):
        """
        Return a list of commands to be run to populate the current environment to include this tools requirements.
        """
        return self.app.toolbox.dependency_manager.dependency_shell_commands(
            requirements=self.requirements,
            installed_tool_dependencies=self.installed_tool_dependencies,
            tool_dir=self.tool_dir,
            job_directory=job_directory,
            preserve_python_environment=self.requires_galaxy_python_environment,
            metadata=metadata,
            tool_instance=self
        )

    @property
    def installed_tool_dependencies(self):
        if self.tool_shed_repository:
            installed_tool_dependencies = self.tool_shed_repository.tool_dependencies_installed_or_in_error
        else:
            installed_tool_dependencies = None
        return installed_tool_dependencies

    @property
    def tool_requirements(self):
        """
        Return all requiremens of type package
        """
        return self.requirements.packages

    @property
    def tool_requirements_status(self):
        """
        Return a list of dictionaries for all tool dependencies with their associated status
        """
        return self._view.get_requirements_status({self.id: self.tool_requirements}, self.installed_tool_dependencies)

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
        except Exception as e:
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
                if name not in children:
                    children[name] = {}
                fields = os.path.basename(filename).split("_")
                designation = fields[2]
                visible = fields[3].lower()
                if visible == "visible":
                    visible = True
                else:
                    visible = False
                ext = fields[4].lower()
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

    def collect_primary_datasets( self, output, job_working_directory, input_ext, input_dbkey="?" ):
        """
        Find any additional datasets generated by a tool and attach (for
        cases where number of outputs is not known in advance).
        """
        return output_collect.collect_primary_datasets( self, output, job_working_directory, input_ext, input_dbkey=input_dbkey )

    def collect_dynamic_collections( self, output, **kwds ):
        """ Find files corresponding to dynamically structured collections.
        """
        return output_collect.collect_dynamic_collections( self, output, **kwds )

    def to_archive(self):
        tool = self
        tarball_files = []
        temp_files = []
        tool_xml = open( os.path.abspath( tool.config_file ), 'r' ).read()
        # Retrieve tool help images and rewrite the tool's xml into a temporary file with the path
        # modified to be relative to the repository root.
        image_found = False
        if tool.help is not None:
            tool_help = tool.help._source
            # Check each line of the rendered tool help for an image tag that points to a location under static/
            for help_line in tool_help.split( '\n' ):
                image_regex = re.compile( 'img alt="[^"]+" src="\${static_path}/([^"]+)"' )
                matches = re.search( image_regex, help_line )
                if matches is not None:
                    tool_help_image = matches.group(1)
                    tarball_path = tool_help_image
                    filesystem_path = os.path.abspath( os.path.join( self.app.config.root, 'static', tool_help_image ) )
                    if os.path.exists( filesystem_path ):
                        tarball_files.append( ( filesystem_path, tarball_path ) )
                        image_found = True
                        tool_xml = tool_xml.replace( '${static_path}/%s' % tarball_path, tarball_path )
        # If one or more tool help images were found, add the modified tool XML to the tarball instead of the original.
        if image_found:
            fd, new_tool_config = tempfile.mkstemp( suffix='.xml' )
            os.close( fd )
            open( new_tool_config, 'w' ).write( tool_xml )
            tool_tup = ( os.path.abspath( new_tool_config ), os.path.split( tool.config_file )[-1]  )
            temp_files.append( os.path.abspath( new_tool_config ) )
        else:
            tool_tup = ( os.path.abspath( tool.config_file ), os.path.split( tool.config_file )[-1]  )
        tarball_files.append( tool_tup )
        # TODO: This feels hacky.
        tool_command = tool.command.strip().split()[0]
        tool_path = os.path.dirname( os.path.abspath( tool.config_file ) )
        # Add the tool XML to the tuple that will be used to populate the tarball.
        if os.path.exists( os.path.join( tool_path, tool_command ) ):
            tarball_files.append( ( os.path.join( tool_path, tool_command ), tool_command ) )
        # Find and add macros and code files.
        for external_file in tool.get_externally_referenced_paths( os.path.abspath( tool.config_file ) ):
            external_file_abspath = os.path.abspath( os.path.join( tool_path, external_file ) )
            tarball_files.append( ( external_file_abspath, external_file ) )
        if os.path.exists( os.path.join( tool_path, "Dockerfile" ) ):
            tarball_files.append( ( os.path.join( tool_path, "Dockerfile" ), "Dockerfile" ) )
        # Find tests, and check them for test data.
        tests = tool.tests
        if tests is not None:
            for test in tests:
                # Add input file tuples to the list.
                for input in test.inputs:
                    for input_value in test.inputs[ input ]:
                        input_filename = str( input_value )
                        input_path = os.path.abspath( os.path.join( 'test-data', input_filename ) )
                        if os.path.exists( input_path ):
                            td_tup = ( input_path, os.path.join( 'test-data', input_filename ) )
                            tarball_files.append( td_tup )
                # And add output file tuples to the list.
                for label, filename, _ in test.outputs:
                    output_filepath = os.path.abspath( os.path.join( 'test-data', filename ) )
                    if os.path.exists( output_filepath ):
                        td_tup = ( output_filepath, os.path.join( 'test-data', filename ) )
                        tarball_files.append( td_tup )
        for param in tool.input_params:
            # Check for tool data table definitions.
            if hasattr( param, 'options' ):
                if hasattr( param.options, 'tool_data_table' ):
                    data_table = param.options.tool_data_table
                    if hasattr( data_table, 'filenames' ):
                        data_table_definitions = []
                        for data_table_filename in data_table.filenames:
                            # FIXME: from_shed_config seems to always be False.
                            if not data_table.filenames[ data_table_filename ][ 'from_shed_config' ]:
                                tar_file = data_table.filenames[ data_table_filename ][ 'filename' ] + '.sample'
                                sample_file = os.path.join( data_table.filenames[ data_table_filename ][ 'tool_data_path' ],
                                                            tar_file )
                                # Use the .sample file, if one exists. If not, skip this data table.
                                if os.path.exists( sample_file ):
                                    tarfile_path, tarfile_name = os.path.split( tar_file )
                                    tarfile_path = os.path.join( 'tool-data', tarfile_name )
                                    tarball_files.append( ( sample_file, tarfile_path ) )
                                data_table_definitions.append( data_table.xml_string )
                        if len( data_table_definitions ) > 0:
                            # Put the data table definition XML in a temporary file.
                            table_definition = '<?xml version="1.0" encoding="utf-8"?>\n<tables>\n    %s</tables>'
                            table_definition = table_definition % '\n'.join( data_table_definitions )
                            fd, table_conf = tempfile.mkstemp()
                            os.close( fd )
                            open( table_conf, 'w' ).write( table_definition )
                            tarball_files.append( ( table_conf, os.path.join( 'tool-data', 'tool_data_table_conf.xml.sample' ) ) )
                            temp_files.append( table_conf )
        # Create the tarball.
        fd, tarball_archive = tempfile.mkstemp( suffix='.tgz' )
        os.close( fd )
        tarball = tarfile.open( name=tarball_archive, mode='w:gz' )
        # Add the files from the previously generated list.
        for fspath, tarpath in tarball_files:
            tarball.add( fspath, arcname=tarpath )
        tarball.close()
        # Delete any temporary files that were generated.
        for temp_file in temp_files:
            os.remove( temp_file )
        return tarball_archive

    def to_dict( self, trans, link_details=False, io_details=False ):
        """ Returns dict of tool. """

        # Basic information
        tool_dict = super( Tool, self ).to_dict()

        tool_dict["edam_operations"] = self.edam_operations
        tool_dict["edam_topics"] = self.edam_topics

        # Fill in ToolShedRepository info
        if hasattr(self, 'tool_shed') and self.tool_shed:
            tool_dict['tool_shed_repository'] = {
                'name': self.repository_name,
                'owner': self.repository_owner,
                'changeset_revision': self.changeset_revision,
                'tool_shed': self.tool_shed
            }

        # If an admin user, expose the path to the actual tool config XML file.
        if trans.user_is_admin():
            tool_dict[ 'config_file' ] = os.path.abspath( self.config_file )

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
            tool_dict[ 'outputs' ] = [ output.to_dict( app=self.app ) for output in self.outputs.values() ]

        tool_dict[ 'panel_section_id' ], tool_dict[ 'panel_section_name' ] = self.get_panel_section()

        tool_class = self.__class__
        regular_form = tool_class == Tool or isinstance(self, DatabaseOperationTool)
        tool_dict["form_style"] = "regular" if regular_form else "special"

        return tool_dict

    def to_json( self, trans, kwd={}, job=None, workflow_building_mode=False ):
        """
        Recursively creates a tool dictionary containing repeats, dynamic options and updated states.
        """
        history_id = kwd.get( 'history_id', None )
        history = None
        try:
            if history_id is not None:
                history = self.history_manager.get_owned( trans.security.decode_id( history_id ), trans.user, current_history=trans.history )
            else:
                history = trans.get_history()
            if history is None and job is not None:
                history = self.history_manager.get_owned( job.history.id, trans.user, current_history=trans.history )
            if history is None:
                raise exceptions.MessageException( 'History unavailable. Please specify a valid history id' )
        except Exception as e:
            raise exceptions.MessageException( '[history_id=%s] Failed to retrieve history. %s.' % ( history_id, str( e ) ) )

        # build request context
        request_context = WorkRequestContext( app=trans.app, user=trans.user, history=history, workflow_building_mode=workflow_building_mode )

        # load job parameters into incoming
        tool_message = ''
        tool_warnings = ''
        if job:
            try:
                job_params = job.get_param_values( self.app, ignore_errors=True )
                tool_warnings = self.check_and_update_param_values( job_params, request_context, update_values=False )
                self._map_source_to_history( request_context, self.inputs, job_params )
                tool_message = self._compare_tool_version( job )
                params_to_incoming( kwd, self.inputs, job_params, self.app )
            except Exception as e:
                raise exceptions.MessageException( str( e ) )

        # create parameter object
        params = galaxy.util.Params( kwd, sanitize=False )

        # populates model from state
        def populate_model( inputs, state_inputs, group_inputs, other_values=None ):
            other_values = ExpressionContext( state_inputs, other_values )
            for input_index, input in enumerate( inputs.values() ):
                tool_dict = None
                group_state = state_inputs.get( input.name, {} )
                if input.type == 'repeat':
                    tool_dict = input.to_dict( request_context )
                    group_cache = tool_dict[ 'cache' ] = {}
                    for i in range( len( group_state ) ):
                        group_cache[ i ] = []
                        populate_model( input.inputs, group_state[ i ], group_cache[ i ], other_values )
                elif input.type == 'conditional':
                    tool_dict = input.to_dict( request_context )
                    if 'test_param' in tool_dict:
                        test_param = tool_dict[ 'test_param' ]
                        test_param[ 'value' ] = input.test_param.value_to_basic( group_state.get( test_param[ 'name' ], input.test_param.get_initial_value( request_context, other_values ) ), self.app )
                        test_param[ 'text_value' ] = input.test_param.value_to_display_text( test_param[ 'value' ], self.app )
                        for i in range( len( tool_dict['cases'] ) ):
                            current_state = {}
                            if i == group_state.get( '__current_case__' ):
                                current_state = group_state
                            populate_model( input.cases[ i ].inputs, current_state, tool_dict[ 'cases' ][ i ][ 'inputs' ], other_values )
                elif input.type == 'section':
                    tool_dict = input.to_dict( request_context )
                    populate_model( input.inputs, group_state, tool_dict[ 'inputs' ], other_values )
                else:
                    try:
                        tool_dict = input.to_dict( request_context, other_values=other_values )
                        tool_dict[ 'value' ] = input.value_to_basic( state_inputs.get( input.name, input.get_initial_value( request_context, other_values ) ), self.app, use_security=True )
                        tool_dict[ 'text_value' ] = input.value_to_display_text( tool_dict[ 'value' ], self.app )
                    except Exception as e:
                        tool_dict = input.to_dict( request_context )
                        log.exception('tools::to_json() - Skipping parameter expansion \'%s\': %s.' % ( input.name, e ) )
                        pass
                if input_index >= len( group_inputs ):
                    group_inputs.append( tool_dict )
                else:
                    group_inputs[ input_index ] = tool_dict

        # expand incoming parameters (parameters might trigger multiple tool executions,
        # here we select the first execution only in order to resolve dynamic parameters)
        expanded_incomings, _ = expand_meta_parameters( trans, self, params.__dict__ )
        if expanded_incomings:
            params.__dict__ = expanded_incomings[ 0 ]

        # do param translation here, used by datasource tools
        if self.input_translator:
            self.input_translator.translate( params )

        # create tool state
        state_inputs = {}
        state_errors = {}
        populate_state( request_context, self.inputs, params.__dict__, state_inputs, state_errors )

        # create tool model
        tool_model = self.to_dict( request_context )
        tool_model[ 'inputs' ] = []
        populate_model( self.inputs, state_inputs, tool_model[ 'inputs' ] )

        # create tool help
        tool_help = ''
        if self.help:
            tool_help = self.help.render( static_path=url_for( '/static' ), host_url=url_for( '/', qualified=True ) )
            tool_help = unicodify( tool_help, 'utf-8' )

        # create tool versions
        tool_versions = []
        tools = self.app.toolbox.get_loaded_tools_by_lineage( self.id )
        for t in tools:
            if t.version not in tool_versions:
                tool_versions.append( t.version )

        # update tool model
        tool_model.update({
            'id'            : self.id,
            'help'          : tool_help,
            'citations'     : bool( self.citations ),
            'biostar_url'   : self.app.config.biostar_url,
            'sharable_url'  : self.tool_shed_repository.get_sharable_url( self.app ) if self.tool_shed_repository else None,
            'message'       : tool_message,
            'warnings'      : tool_warnings,
            'versions'      : tool_versions,
            'requirements'  : [ { 'name' : r.name, 'version' : r.version } for r in self.requirements ],
            'errors'        : state_errors,
            'state_inputs'  : params_to_strings( self.inputs, state_inputs, self.app ),
            'job_id'        : trans.security.encode_id( job.id ) if job else None,
            'job_remap'     : self._get_job_remap( job ),
            'history_id'    : trans.security.encode_id( history.id ),
            'display'       : self.display_interface,
            'action'        : url_for( self.action ),
            'method'        : self.method,
            'enctype'       : self.enctype
        })
        return tool_model

    def _get_job_remap( self, job):
        if job:
            if job.state == job.states.ERROR:
                try:
                    if [ hda.dependent_jobs for hda in [ jtod.dataset for jtod in job.output_datasets ] if hda.dependent_jobs ]:
                        return True
                except Exception as exception:
                    log.error( str( exception ) )
                    pass
        return False

    def _map_source_to_history( self, trans, tool_inputs, params ):
        # Need to remap dataset parameters. Job parameters point to original
        # dataset used; parameter should be the analygous dataset in the
        # current history.
        history = trans.history

        # Create index for hdas.
        hda_source_dict = {}
        for hda in history.datasets:
            key = '%s_%s' % ( hda.hid, hda.dataset.id )
            hda_source_dict[ hda.dataset.id ] = hda_source_dict[ key ] = hda

        # Ditto for dataset collections.
        hdca_source_dict = {}
        for hdca in history.dataset_collections:
            key = '%s_%s' % ( hdca.hid, hdca.collection.id )
            hdca_source_dict[ hdca.collection.id ] = hdca_source_dict[ key ] = hdca

        # Map dataset or collection to current history
        def map_to_history( value ):
            id = None
            source = None
            if isinstance( value, self.app.model.HistoryDatasetAssociation ):
                id = value.dataset.id
                source = hda_source_dict
            elif isinstance( value, self.app.model.HistoryDatasetCollectionAssociation ):
                id = value.collection.id
                source = hdca_source_dict
            else:
                return None
            key = '%s_%s' % ( value.hid, id )
            if key in source:
                return source[ key ]
            elif id in source:
                return source[ id ]
            else:
                return None

        def mapping_callback( input, value, **kwargs ):
            if isinstance( input, DataToolParameter ):
                if isinstance(value, list):
                    values = []
                    for val in value:
                        new_val = map_to_history( val )
                        if new_val:
                            values.append( new_val )
                        else:
                            values.append( val )
                    return values
                else:
                    return map_to_history( value )
            elif isinstance( input, DataCollectionToolParameter ):
                return map_to_history( value )
        visit_input_values( tool_inputs, params, mapping_callback )

    def _compare_tool_version( self, job ):
        """
        Compares a tool version with the tool version from a job (from ToolRunner).
        """
        tool_id = job.tool_id
        tool_version = job.tool_version
        message = ''
        try:
            select_field, tools, tool = self.app.toolbox.get_tool_components( tool_id, tool_version=tool_version, get_loaded_tools_by_lineage=False, set_selected=True )
            if tool is None:
                raise exceptions.MessageException( 'This dataset was created by an obsolete tool (%s). Can\'t re-run.' % tool_id )
            if ( self.id != tool_id and self.old_id != tool_id ) or self.version != tool_version:
                if self.id == tool_id:
                    if tool_version is None:
                        # for some reason jobs don't always keep track of the tool version.
                        message = ''
                    else:
                        message = 'This job was run with tool version "%s", which is not available.  ' % tool_version
                        if len( tools ) > 1:
                            message += 'You can re-run the job with the selected tool or choose another version of the tool.'
                        else:
                            message += 'You can re-run the job with this tool version, which is a different version of the original tool.'
                else:
                    new_tool_shed_url = '%s/%s/' % ( tool.tool_shed_repository.get_sharable_url( tool.app ), tool.tool_shed_repository.changeset_revision )
                    old_tool_shed_url = common_util.get_tool_shed_url_from_tool_shed_registry( self.app, tool_id.split( '/repos/' )[ 0 ] )
                    old_tool_shed_url = '%s/view/%s/%s/' % ( old_tool_shed_url, tool.repository_owner, tool.repository_name )
                    message = 'This job was run with <a href=\"%s\" target=\"_blank\">tool id \"%s\"</a>, version "%s", which is not available.  ' % ( old_tool_shed_url, tool_id, tool_version )
                    if len( tools ) > 1:
                        message += 'You can re-run the job with the selected <a href=\"%s\" target=\"_blank\">tool id \"%s\"</a> or choose another derivation of the tool.' % ( new_tool_shed_url, self.id )
                    else:
                        message += 'You can re-run the job with <a href=\"%s\" target=\"_blank\">tool id \"%s\"</a>, which is a derivation of the original tool.' % ( new_tool_shed_url, self.id )
        except Exception as e:
            raise exceptions.MessageException( str( e ) )
        return message

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
        for key, value in param_dict.items():
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
        json_params[ 'job_config' ] = dict( GALAXY_DATATYPES_CONF_FILE=param_dict.get( 'GALAXY_DATATYPES_CONF_FILE' ), GALAXY_ROOT_DIR=param_dict.get( 'GALAXY_ROOT_DIR' ), TOOL_PROVIDED_JOB_METADATA_FILE=galaxy.jobs.TOOL_PROVIDED_JOB_METADATA_FILE )
        json_filename = None
        for i, ( out_name, data ) in enumerate( out_data.items() ):
            # use wrapped dataset to access certain values
            wrapped_data = param_dict.get( out_name )
            # allow multiple files to be created
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
        # Open all data_source tools in _top.
        self.target = '_top'
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
        json_params[ 'job_config' ] = dict( GALAXY_DATATYPES_CONF_FILE=param_dict.get( 'GALAXY_DATATYPES_CONF_FILE' ), GALAXY_ROOT_DIR=param_dict.get( 'GALAXY_ROOT_DIR' ), TOOL_PROVIDED_JOB_METADATA_FILE=galaxy.jobs.TOOL_PROVIDED_JOB_METADATA_FILE )
        json_filename = None
        for i, ( out_name, data ) in enumerate( out_data.items() ):
            # use wrapped dataset to access certain values
            wrapped_data = param_dict.get( out_name )
            # allow multiple files to be created
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
        for name, dataset in inp_data.items():
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


class DataManagerTool( OutputParameterJSONTool ):
    tool_type = 'manage_data'
    default_tool_action = DataManagerToolAction

    def __init__( self, config_file, root, app, guid=None, data_manager_id=None, **kwds ):
        self.data_manager_id = data_manager_id
        super( DataManagerTool, self ).__init__( config_file, root, app, guid=guid, **kwds )
        if self.data_manager_id is None:
            self.data_manager_id = self.id

    def exec_after_process( self, app, inp_data, out_data, param_dict, job=None, **kwds ):
        assert self.allow_user_access( job.user ), "You must be an admin to access this tool."
        # run original exec_after_process
        super( DataManagerTool, self ).exec_after_process( app, inp_data, out_data, param_dict, job=job, **kwds )
        # process results of tool
        if job and job.state == job.states.ERROR:
            return
        # Job state may now be 'running' instead of previous 'error', but datasets are still set to e.g. error
        for dataset in out_data.values():
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
        assert self.allow_user_access( user ), "You must be an admin to access this tool."
        history = user.data_manager_histories
        if not history:
            # create
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

    def allow_user_access( self, user, attempting_access=True ):
        """
        :param user: model object representing user.
        :type user: galaxy.model.User
        :param attempting_access: is the user attempting to do something with the
                               the tool (set false for incidental checks like toolbox
                               listing)
        :type attempting_access:  bool

        :returns: bool -- Whether the user is allowed to access the tool.
        Data Manager tools are only accessible to admins.
        """
        if super( DataManagerTool, self ).allow_user_access( user ) and self.app.config.is_admin_user( user ):
            return True
        # If this is just an incidental check - do not log the scary message
        # about users attempting to do something problematic.
        if attempting_access:
            if user:
                user = user.id
            log.debug( "User (%s) attempted to access a data manager tool (%s), but is not an admin.", user, self.id )
        return False


class DatabaseOperationTool( Tool ):
    default_tool_action = ModelOperationToolAction
    require_dataset_ok = True

    @property
    def valid_input_states( self ):
        if self.require_dataset_ok:
            return (model.Dataset.states.OK,)
        else:
            return model.Dataset.terminal_states

    @property
    def allow_errored_inputs( self ):
        return not self.require_dataset_ok

    def check_inputs_ready( self, input_datasets, input_dataset_collections ):
        def check_dataset_instance( input_dataset ):
            if input_dataset.is_pending:
                raise ToolInputsNotReadyException()

            if self.require_dataset_ok:
                if input_dataset.state != input_dataset.dataset.states.OK:
                    raise ValueError("Tool requires inputs to be in valid state.")

        for input_dataset in input_datasets.values():
            check_dataset_instance( input_dataset )

        for input_dataset_collection in input_dataset_collections.values():
            if not input_dataset_collection.collection.populated:
                raise ToolInputsNotReadyException()

            map( check_dataset_instance, input_dataset_collection.dataset_instances )

    def produce_outputs( self, trans, out_data, output_collections, incoming, history ):
        return self._outputs_dict()

    def _outputs_dict( self ):
        return odict()


class UnzipCollectionTool( DatabaseOperationTool ):
    tool_type = 'unzip_collection'

    def produce_outputs( self, trans, out_data, output_collections, incoming, history ):
        has_collection = incoming[ "input" ]
        if hasattr(has_collection, "element_type"):
            # It is a DCE
            collection = has_collection.element_object
        else:
            # It is an HDCA
            collection = has_collection.collection

        assert collection.collection_type == "paired"
        forward_o, reverse_o = collection.dataset_instances
        forward, reverse = forward_o.copy(), reverse_o.copy()
        # TODO: rename...
        history.add_dataset( forward, set_hid=True )
        history.add_dataset( reverse, set_hid=True )
        out_data["forward"] = forward
        out_data["reverse"] = reverse


class ZipCollectionTool( DatabaseOperationTool ):
    tool_type = 'zip_collection'

    def produce_outputs( self, trans, out_data, output_collections, incoming, history ):
        forward_o = incoming[ "input_forward" ]
        reverse_o = incoming[ "input_reverse" ]

        forward, reverse = forward_o.copy(), reverse_o.copy()
        new_elements = odict()
        new_elements["forward"] = forward
        new_elements["reverse"] = reverse
        history.add_dataset( forward, set_hid=False )
        history.add_dataset( reverse, set_hid=False )

        output_collections.create_collection(
            next(iter(self.outputs.values())), "output", elements=new_elements
        )


class MergeCollectionTool( DatabaseOperationTool ):
    tool_type = 'merge_collection'

    def produce_outputs( self, trans, out_data, output_collections, incoming, history ):
        input_lists = []

        for incoming_repeat in incoming[ "inputs" ]:
            input_lists.append(incoming_repeat["input"])

        advanced = incoming.get("advanced", None)
        dupl_actions = "keep_first"
        suffix_pattern = None
        if advanced is not None:
            dupl_actions = advanced["conflict"]['duplicate_options']

            if dupl_actions in ['suffix_conflict', 'suffix_every', 'suffix_conflict_rest']:
                suffix_pattern = advanced['conflict']['suffix_pattern']

        new_element_structure = odict()

        # Which inputs does the identifier appear in.
        identifiers_map = {}
        for input_num, input_list in enumerate(input_lists):
            for dce in input_list.collection.elements:
                    element_identifier = dce.element_identifier
                    if element_identifier not in identifiers_map:
                        identifiers_map[element_identifier] = []
                    elif dupl_actions == "fail":
                        raise Exception("Duplicate collection element identifiers found for [%s]" % element_identifier)
                    identifiers_map[element_identifier].append(input_num)

        for copy, input_list in enumerate(input_lists):
            for dce in input_list.collection.elements:
                element = dce.element_object
                valid = False

                # dealing with a single element
                if hasattr(element, "is_ok"):
                    if element.is_ok:
                        valid = True
                elif hasattr(element, "dataset_instances"):
                    # we are probably a list:paired dataset, both need to be in non error state
                    forward_o, reverse_o = element.dataset_instances
                    if forward_o.is_ok and reverse_o.is_ok:
                        valid = True

                if valid:
                    element_identifier = dce.element_identifier
                    identifier_seen = element_identifier in new_element_structure
                    appearances = identifiers_map[element_identifier]
                    add_suffix = False
                    if dupl_actions == "suffix_every":
                        add_suffix = True
                    elif dupl_actions == "suffix_conflict" and len(appearances) > 1:
                        add_suffix = True
                    elif dupl_actions == "suffix_conflict_rest" and len(appearances) > 1 and appearances[0] != copy:
                        add_suffix = True

                    if dupl_actions == "keep_first" and identifier_seen:
                        continue

                    if add_suffix:
                        suffix = suffix_pattern.replace("#", str(copy + 1))
                        effective_identifer = "%s%s" % (element_identifier, suffix)
                    else:
                        effective_identifer = element_identifier

                    new_element_structure[effective_identifer] = element

        # Don't copy until we know everything is fine and we have the structure of the list ready to go.
        new_elements = odict()
        for key, value in new_element_structure.items():
            copied_value = value.copy()
            if getattr(copied_value, "history_content_type", None) == "dataset":
                history.add_dataset(copied_value, set_hid=False)
            new_elements[key] = copied_value

        output_collections.create_collection(
            next(iter(self.outputs.values())), "output", elements=new_elements
        )


class FilterFailedDatasetsTool( DatabaseOperationTool ):
    tool_type = 'filter_failed_datasets_collection'
    require_dataset_ok = False

    def produce_outputs( self, trans, out_data, output_collections, incoming, history ):
        hdca = incoming[ "input" ]

        assert hdca.collection.collection_type == "list" or hdca.collection.collection_type == 'list:paired'

        new_elements = odict()

        for dce in hdca.collection.elements:
            element = dce.element_object

            valid = False

            # dealing with a single element
            if hasattr(element, "is_ok"):
                if element.is_ok:
                    valid = True
            elif hasattr(element, "dataset_instances"):
                # we are probably a list:paired dataset, both need to be in non error state
                forward_o, reverse_o = element.dataset_instances
                if forward_o.is_ok and reverse_o.is_ok:
                    valid = True

            if valid:
                element_identifier = dce.element_identifier
                copied_value = element.copy()
                if getattr(copied_value, "history_content_type", None) == "dataset":
                    history.add_dataset(copied_value, set_hid=False)
                new_elements[element_identifier] = copied_value

        output_collections.create_collection(
            next(iter(self.outputs.values())), "output", elements=new_elements
        )


class FlattenTool( DatabaseOperationTool ):
    tool_type = 'flatten_collection'

    def produce_outputs( self, trans, out_data, output_collections, incoming, history ):
        hdca = incoming[ "input" ]
        join_identifier = incoming["join_identifier"]
        new_elements = odict()

        def add_elements(collection, prefix=""):
            for dce in collection.elements:
                dce_object = dce.element_object
                dce_identifier = dce.element_identifier
                identifier = "%s%s%s" % (prefix, join_identifier, dce_identifier) if prefix else dce_identifier
                if dce.is_collection:
                    add_elements(dce_object, prefix=identifier)
                else:
                    copied_dataset = dce_object.copy()
                    history.add_dataset(copied_dataset, set_hid=False)
                    new_elements[identifier] = copied_dataset
        add_elements(hdca.collection)
        output_collections.create_collection(
            next(iter(self.outputs.values())), "output", elements=new_elements
        )


# Populate tool_type to ToolClass mappings
tool_types = {}
for tool_class in [ Tool, SetMetadataTool, OutputParameterJSONTool,
                    DataManagerTool, DataSourceTool, AsyncDataSourceTool,
                    UnzipCollectionTool, ZipCollectionTool, MergeCollectionTool,
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


class InterruptedUpload( Exception ):
    pass
