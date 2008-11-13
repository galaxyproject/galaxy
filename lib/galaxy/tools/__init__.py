"""
Classes encapsulating galaxy tools and tool configuration.
"""

import pkg_resources; 

pkg_resources.require( "simplejson" )

import logging, os, string, sys, tempfile, glob, shutil
import simplejson
import sha, hmac, binascii

from UserDict import DictMixin
from galaxy.util.odict import odict
from galaxy.util.bunch import Bunch
from galaxy.util.template import fill_template
from galaxy import util, jobs, model
from elementtree import ElementTree
from parameters import *
from parameters.grouping import *
from galaxy.util.expressions import ExpressionContext
from galaxy.tools.test import ToolTestBuilder
from galaxy.tools.actions import DefaultToolAction
from galaxy.model import directory_hash_id
from galaxy.util.none_like import NoneDataset
from galaxy.datatypes import sniff

log = logging.getLogger( __name__ )

class ToolNotFoundException( Exception ):
    pass

class ToolBox( object ):
    """
    Container for a collection of tools
    """

    def __init__( self, config_filename, tool_root_dir, app ):
        """
        Create a toolbox from the config file names by `config_filename`,
        using `tool_root_directory` as the base directory for finding 
        individual tool config files.
        """
        self.tools_by_id = {}
        self.tools_and_sections_by_id = {}
        self.sections = []
        self.tool_root_dir = tool_root_dir
        self.app = app
        try:
            self.init_tools( config_filename )
        except:
            log.exception( "ToolBox error reading %s", config_filename )

    def init_tools( self, config_filename ):
        """
        Read the configuration file and load each tool.
        """
        log.info("parsing the tool configuration")
        tree = util.parse_xml( config_filename )
        root = tree.getroot()
        for elem in root.findall("section"):
            section = ToolSection(elem)
            log.debug( "Loading tools in section: %s" % section.name )
            for tool in elem.findall("tool"):
                try:
                    path = tool.get("file")
                    tool = self.load_tool( os.path.join( self.tool_root_dir, path ) )
                    log.debug( "Loaded tool: %s %s" %( tool.id, tool.version ) )
                    self.tools_by_id[tool.id] = tool
                    self.tools_and_sections_by_id[tool.id] = tool, section
                    section.tools.append(tool)
                except Exception, exc:
                    log.exception( "error reading tool from path: %s" % path )
            self.sections.append(section)
        
    def load_tool( self, config_file ):
        """
        Load a single tool from the file named by `config_file` and return 
        an instance of `Tool`.
        """
        # Parse XML configuration file and get the root element
        tree = util.parse_xml( config_file )
        root = tree.getroot()
        # Allow specifying a different tool subclass to instantiate
        if root.find( "type" ):
            type_elem = root.find( "type" )
            module = type_elem.get( 'module', 'galaxy.tools' )
            cls = type_elem.get( 'class' )
            mod = __import__( module, globals(), locals(), [cls])
            ToolClass = getattr( mod, cls )
        else:
            ToolClass = Tool
        return ToolClass( config_file, root, self.app )
        
    def reload( self, tool_id ):
        """
        Attempt to reload the tool identified by 'tool_id', if successfull 
        replace the old tool.
        """
        if tool_id not in self.tools_and_sections_by_id:
            raise ToolNotFoundException( "No tool with id %s" % tool_id )
        old_tool, section = self.tools_and_sections_by_id[ tool_id ]
        new_tool = self.load_tool( old_tool.config_file )
        log.debug( "Reloaded tool %s %s" %( old_tool.id, old_tool.version ) )
        # Is there a potential sync problem here? This should be roughly 
        # atomic. Too many indexes for tools...
        section.tools[ section.tools.index( old_tool ) ] = new_tool
        self.tools_by_id[ tool_id ] = new_tool
        self.tools_and_sections_by_id[ tool_id ] = new_tool, section
        
    def itertools( self ):
        """
        Iterate over all the tools in the toolbox (ordered by section but
        without grouping).
        """
        for section in self.sections:
            for tool in section.tools:
                yield tool

class ToolSection( object ):
    """
    A group of tools with similar type/purpose that will be displayed as a
    group in the user interface.
    """
    def __init__( self, elem ):
        self.name = elem.get( "name" )
        self.id = elem.get( "id" )
        self.version = elem.get( "version" )
        self.tools = []

class DefaultToolState( object ):
    """
    Keeps track of the state of a users interaction with a tool between 
    requests. The default tool state keeps track of the current page (for 
    multipage "wizard" tools) and the values of all parameters.
    """
    def __init__( self ):
        self.page = 0
        self.inputs = None
    def encode( self, tool, app ):
        """
        Convert the data to a string
        """
        # Convert parameters to a dictionary of strings, and save curent
        # page in that dict
        value = params_to_strings( tool.inputs, self.inputs, app )
        value["__page__"] = self.page
        value = simplejson.dumps( value )
        # Make it secure
        a = hmac.new( app.config.tool_secret, value, sha ).hexdigest()
        b = binascii.hexlify( value )
        return "%s:%s" % ( a, b )      
    def decode( self, value, tool, app ):
        """
        Restore the state from a string
        """
        # Extract and verify hash
        a, b = value.split( ":" )
        value = binascii.unhexlify( b )
        test = hmac.new( app.config.tool_secret, value, sha ).hexdigest()
        assert a == test
        # Restore from string
        values = json_fix( simplejson.loads( value ) )
        self.page = values.pop( "__page__" )
        self.inputs = params_from_strings( tool.inputs, values, app, ignore_errors=True )

class ToolOutput( object ):
    """
    Represents an output datasets produced by a tool. For backward
    compatibility this behaves as if it were the tuple:
      (format, metadata_source, parent)  
    """
    def __init__( self, name, format=None, metadata_source=None, 
                  parent=None, label=None ):
        self.name = name
        self.format = format
        self.metadata_source = metadata_source
        self.parent = parent
        self.label = label

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

class Tool:
    """
    Represents a computational tool that can be executed through Galaxy. 
    """
    def __init__( self, config_file, root, app ):
        """
        Load a tool from the config named by `config_file`
        """
        # Determine the full path of the directory where the tool config is
        self.config_file = config_file
        self.tool_dir = os.path.dirname( config_file )
        self.app = app
        # Parse XML element containing configuration
        self.parse( root )
        
    def parse( self, root ):
        """
        Read tool configuration from the element `root` and fill in `self`.
        """
        # Get the (user visible) name of the tool
        self.name = root.get( "name" )
        if not self.name: 
            raise Exception, "Missing tool 'name'"
        # Get the UNIQUE id for the tool 
        # TODO: can this be generated automatically?
        self.id = root.get( "id" )
        if not self.id: 
            raise Exception, "Missing tool 'id'" 
        self.version = root.get( "version" )
        if not self.version: 
            # For backward compatibility, some tools may not have versions yet.
            self.version = "1.0.0"
        # Type of tool
        self.tool_type = root.get( "tool_type", None )
        # data_source tool
        if self.tool_type == "data_source":
            self.URL_method = root.get( "URL_method", "get" ) # get is the default
            # TODO: Biomart hack - eliminate when they encode URL - they'll let us know when...
            self.add_to_URL = root.get( "add_to_URL", None )
            self.param_trans_dict = {}
            req_param_trans = root.find( "request_param_translation" )
            if req_param_trans is not None:
                for req_param in req_param_trans.findall( "request_param" ):
                    # req_param tags must look like <request_param galaxy_name="dbkey" remote_name="GENOME" missing="" />
                    trans_list = []
                    remote_name = req_param.get( "remote_name" )
                    trans_list.append( req_param.get( "galaxy_name" ) )
                    trans_list.append( req_param.get( "missing" ) )
                    if req_param.get( "galaxy_name" ) == "data_type":
                        # The req_param tag for data_type is special in that it can contain another tag set like
                        # <data_type_translation>
                        #    <format galaxy_format="tabular" remote_format="selectedFields" />
                        # </data_type_translation>
                        format_trans = req_param.find( "data_type_translation" )
                        if format_trans is not None:
                            format_trans_dict = {}
                            for format in format_trans.findall( "format" ):
                                remote_format = format.get( "remote_format" )
                                galaxy_format = format.get( "galaxy_format" )                        
                                format_trans_dict[ remote_format ] = galaxy_format
                            trans_list.append( format_trans_dict )
                    self.param_trans_dict[ remote_name ] = trans_list
        # Command line (template). Optional for tools that do not invoke a local program  
        command = root.find("command")
        if command is not None and command.text is not None:
            self.command = command.text.lstrip() # get rid of leading whitespace
            interpreter  = command.get("interpreter")
            if interpreter:
                # TODO: path munging for cluster/dataset server relocatability
                executable = self.command.split()[0]
                abs_executable = os.path.abspath(os.path.join(self.tool_dir, executable))
                self.command = self.command.replace(executable, abs_executable, 1)
                self.command = interpreter + " " + self.command
        else:
            self.command = ''
        # Parameters used to build URL for redirection to external app
        redirect_url_params = root.find( "redirect_url_params" )
        if redirect_url_params is not None and redirect_url_params.text is not None:
            # get rid of leading / trailing white space
            redirect_url_params = redirect_url_params.text.strip()
            # Replace remaining white space with something we can safely split on later
            # when we are building the params
            self.redirect_url_params = redirect_url_params.replace( ' ', '**^**' )
        else:
            self.redirect_url_params = ''
        # Short description of the tool
        self.description = util.xml_text(root, "description")
        # Job runner
        if self.app.config.start_job_runners is None:
            # Jobs are always local regardless of tool config if no additional
            # runners are started
            self.job_runner = "local:///"
        else:
            # Set job runner to the cluster default
            self.job_runner = self.app.config.default_cluster_job_runner
            for tup in self.app.config.tool_runners:
                if tup[0] == self.id.lower():
                    self.job_runner = tup[1]
                    break
        # Is this a 'hidden' tool (hidden in tool menu)
        self.hidden = util.xml_text(root, "hidden")
        if self.hidden: self.hidden = util.string_as_bool(self.hidden)
        # Load any tool specific code (optional) Edit: INS 5/29/2007,
        # allow code files to have access to the individual tool's
        # "module" if it has one.  Allows us to reuse code files, etc.
        self.code_namespace = dict()
        self.hook_map = {}
        for code_elem in root.findall("code"):
            for hook_elem in code_elem.findall("hook"):
                for key, value in hook_elem.items():
                    # map hook to function
                    self.hook_map[key]=value
            file_name = code_elem.get("file")
            code_path = os.path.join( self.tool_dir, file_name )
            execfile( code_path, self.code_namespace )
        # Load any tool specific options (optional)
        self.options = dict( sanitize=True, refresh=False )
        for option_elem in root.findall("options"):
            for option, value in self.options.copy().items():
                if isinstance(value, type(False)):
                    self.options[option] = util.string_as_bool(option_elem.get(option, str(value)))
                else:
                    self.options[option] = option_elem.get(option, str(value))
        self.options = Bunch(** self.options)
        # Parse tool inputs (if there are any required)
        self.parse_inputs( root )
        # Parse tool help
        self.parse_help( root )
        # Description of outputs produced by an invocation of the tool
        self.outputs = {}
        out_elem = root.find("outputs")
        if out_elem:
            for data_elem in out_elem.findall("data"):
                output = ToolOutput( data_elem.get("name") )
                output.format = data_elem.get("format", "data")
                output.change_format = data_elem.findall("change_format")
                output.metadata_source = data_elem.get("metadata_source", "")
                output.parent = data_elem.get("parent", None)
                output.label = util.xml_text( data_elem, "label" )
                self.outputs[ output.name ] = output
        # Any extra generated config files for the tool
        self.config_files = []
        conf_parent_elem = root.find("configfiles")
        if conf_parent_elem:
            for conf_elem in conf_parent_elem.findall( "configfile" ):
                name = conf_elem.get( "name" )
                filename = conf_elem.get( "filename", None )
                text = conf_elem.text
                self.config_files.append( ( name, filename, text ) )
        # Action
        action_elem = root.find( "action" )
        if action_elem is None:
            self.tool_action = DefaultToolAction()
        else:
            module = action_elem.get( 'module' )
            cls = action_elem.get( 'class' )
            mod = __import__( module, globals(), locals(), [cls])
            self.tool_action = getattr( mod, cls )()
        # User interface hints
        self.uihints = {}
        uihints_elem = root.find( "uihints" )
        if uihints_elem is not None:
            for key, value in uihints_elem.attrib.iteritems():
                self.uihints[ key ] = value
        # Tests
        tests_elem = root.find( "tests" )
        if tests_elem:
            try:
                self.parse_tests( tests_elem )
            except:
                log.exception( "Failed to parse tool tests" )
        else:
            self.tests = None
        # Determine if this tool can be used in workflows
        self.is_workflow_compatible = self.check_workflow_compatible()
        
            
    def parse_inputs( self, root ):
        """
        Parse the "<inputs>" element and create appropriate `ToolParameter`s.
        This implementation supports multiple pages and grouping constructs.
        """
        # Load parameters (optional)
        input_elem = root.find("inputs")
        if input_elem:
            # Handle properties of the input form
            self.check_values = util.string_as_bool( input_elem.get("check_values", "true") )
            self.action = input_elem.get( "action", "/tool_runner/index")
            self.target = input_elem.get( "target", "galaxy_main" )
            self.method = input_elem.get( "method", "post" )
            # Parse the actual parameters
            self.inputs = odict()
            self.inputs_by_page = list()
            self.display_by_page = list()
            enctypes = set()
            # Handle multiple page case
            pages = input_elem.findall( "page" )
            for page in ( pages or [ input_elem ] ):
                display, inputs = self.parse_input_page( page, enctypes )
                self.inputs_by_page.append( inputs )
                self.inputs.update( inputs )
                self.display_by_page.append( display )
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
                raise Exception, "Conflicting required enctypes: %s" % str( enctypes )
        # Check if the tool either has no parameters or only hidden (and
        # thus hardcoded) parameters. FIXME: hidden parameters aren't
        # parameters at all really, and should be passed in a different
        # way, making this check easier.
        self.input_required = False
        for param in self.inputs.values():
            if not isinstance( param, ( HiddenToolParameter, BaseURLToolParameter ) ):
                self.input_required = True
                break
                
    def parse_help( self, root ):
        """
        Parse the help text for the tool. Formatted in reStructuredText.
        This implementation supports multiple pages.
        """
        # TODO: Allow raw HTML or an external link.
        self.help = root.find("help")
        self.help_by_page = list()
        help_header = ""
        help_footer = ""
        if self.help is not None:
            help_pages = self.help.findall( "page" )
            help_header = self.help.text
            try:
                self.help = util.rst_to_html(self.help.text)
            except:
                log.exception( "error in help for tool %s" % self.name )
            # Multiple help page case
            if help_pages:
                for help_page in help_pages:
                    self.help_by_page.append( help_page.text )
                    help_footer = help_footer + help_page.tail
        # Each page has to rendered all-together because of backreferences allowed by rst
        try:
            self.help_by_page = [ util.rst_to_html( help_header + x + help_footer )
                                  for x in self.help_by_page ]
        except:
            log.exception( "error in multi-page help for tool %s" % self.name )
        # Pad out help pages to match npages ... could this be done better?
        while len( self.help_by_page ) < self.npages: 
            self.help_by_page.append( self.help )
            
    def parse_tests( self, tests_elem ):
        """
        Parse any "<test>" elements, create a `ToolTestBuilder` for each and
        store in `self.tests`.
        """
        self.tests = []
        for i, test_elem in enumerate( tests_elem.findall( 'test' ) ):
            name = test_elem.get( 'name', 'Test-%d' % (i+1) )
            test = ToolTestBuilder( self, name )
            try:
                for param_elem in test_elem.findall( "param" ):
                    attrib = dict( param_elem.attrib )
                    if 'values' in attrib:
                        value = attrib[ 'values' ].split( ',' )
                    elif 'value' in attrib:
                        value = attrib['value']
                    else:
                        value = None
                    test.add_param( attrib.pop( 'name' ), value, attrib )
                for output_elem in test_elem.findall( "output" ):
                    attrib = dict( output_elem.attrib )
                    name = attrib.pop( 'name', None )
                    if name is None:
                        raise Exception( "Test output does not have a 'name'" )
                    file = attrib.pop( 'file', None )
                    if file is None:
                        raise Exception( "Test output does not have a 'file'")
                    test.add_output( name, file )
            except Exception, e:
                test.error = True
                test.exception = e
            self.tests.append( test )
            
    def parse_input_page( self, input_elem, enctypes ):
        """
        Parse a page of inputs. This basically just calls 'parse_input_elem',
        but it also deals with possible 'display' elements which are supported
        only at the top/page level (not in groups).
        """
        inputs = self.parse_input_elem( input_elem, enctypes )
        # Display
        display_elem = input_elem.find("display")
        if display_elem is not None:
            display = util.xml_to_string(display_elem)
        else:
            display = None
        return display, inputs
        
    def parse_input_elem( self, parent_elem, enctypes, context=None ):
        """
        Parse a parent element whose children are inputs -- these could be 
        groups (repeat, conditional) or param elements. Groups will be parsed
        recursively.
        """
        rval = odict()
        context = ExpressionContext( rval, context )
        for elem in parent_elem:
            # Repeat group
            if elem.tag == "repeat":
                group = Repeat()
                group.name = elem.get( "name" )
                group.title = elem.get( "title" ) 
                group.inputs = self.parse_input_elem( elem, enctypes, context )  
                rval[group.name] = group
            elif elem.tag == "conditional":
                group = Conditional()
                group.name = elem.get( "name" )
                # Should have one child "input" which determines the case
                input_elem = elem.find( "param" )
                assert input_elem is not None, "<conditional> must have a child <param>"
                group.test_param = self.parse_param_elem( input_elem, enctypes, context )
                # Must refresh when test_param changes
                group.test_param.refresh_on_change = True
                # And a set of possible cases
                for case_elem in elem.findall( "when" ):
                    case = ConditionalWhen()
                    case.value = case_elem.get( "value" )
                    case.inputs = self.parse_input_elem( case_elem, enctypes, context )
                    group.cases.append( case )
                rval[group.name] = group
            elif elem.tag == "param":
                param = self.parse_param_elem( elem, enctypes, context )
                rval[param.name] = param
        return rval

    def parse_param_elem( self, input_elem, enctypes, context ):
        """
        Parse a single "<param>" element and return a ToolParameter instance. 
        Also, if the parameter has a 'required_enctype' add it to the set
        enctypes.
        """
        param = ToolParameter.build( self, input_elem )
        param_enctype = param.get_required_enctype()
        if param_enctype:
            enctypes.add( param_enctype )
        # If parameter depends on any other paramters, we must refresh the
        # form when it changes
        for name in param.get_dependencies():
            context[ name ].refresh_on_change = True
            context[ name ].dependent_params.append( param.name )
        return param
    
    def check_workflow_compatible( self ):
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
        if self.action != "/tool_runner/index":
            return False
        # HACK: upload is (as always) a special case becuase file parameters
        #       can't be persisted.
        if self.id == "upload1":
            return False
        # TODO: Anyway to capture tools that dynamically change their own
        #       outputs?
        return True

    def new_state( self, trans, all_pages=False ):
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
        self.fill_in_new_state( trans, inputs, state.inputs )
        return state

    def fill_in_new_state( self, trans, inputs, state, context=None ):
        """
        Fill in a tool state dictionary with default values for all parameters
        in the dictionary `inputs`. Grouping elements are filled in recursively. 
        """
        context = ExpressionContext( state, context )
        for input in inputs.itervalues():
            if isinstance( input, Repeat ):
                # Repeat elements are always initialized to have 0 units.
                state[ input.name ] = []
            elif isinstance( input, Conditional ):
                # State for a conditional is a plain dictionary. 
                s = state[ input.name ] = {}
                # Get the default value for the 'test element' and use it
                # to determine the current case
                test_value = input.test_param.get_initial_value( trans, context )
                current_case = input.get_current_case( test_value, trans )
                # Recursively fill in state for selected case
                self.fill_in_new_state( trans, input.cases[current_case].inputs, s, context )
                # Store the current case in a special value
                s['__current_case__'] = current_case
                # Store the value of the test element
                s[ input.test_param.name ] = test_value
            else:
                # `input` is just a plain parameter, get its default value
                state[ input.name ] = input.get_initial_value( trans, context )

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
        each nested set of parameters. The callback method is then called as:
        
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

    def handle_input( self, trans, incoming ):
        """
        Process incoming parameters for this tool from the dict `incoming`,
        update the tool state (or create if none existed), and either return
        to the form or execute the tool (only if 'execute' was clicked and
        there were no errors).
        """
        # Get the state or create if not found
        if "tool_state" in incoming:
            encoded_state = util.string_to_object( incoming["tool_state"] )
            state = DefaultToolState()
            state.decode( encoded_state, self, trans.app )
        else:
            state = self.new_state( trans )
            # This feels a bit like a hack. It allows forcing full processing
            # of inputs even when there is no state in the incoming dictionary
            # by providing either 'runtool_btn' (the name of the submit button
            # on the standard run form) or "URL" (a parameter provided by
            # external data source tools). 
            if "runtool_btn" not in incoming and "URL" not in incoming:
                return "tool_form.mako", dict( errors={}, tool_state=state, param_values={}, incoming={} )
        # Process incoming data
        if not( self.check_values ):
            # If `self.check_values` is false we don't do any checking or
            # processing on input parameters. This is used to pass raw values
            # through to/from external sites. FIXME: This should be handled
            # more cleanly, there is no reason why external sites need to
            # post back to the same URL that the tool interface uses.
            errors = {}
            params = incoming
        else:
            # Update state for all inputs on the current page taking new
            # values from `incoming`.
            errors = self.update_state( trans, self.inputs_by_page[state.page], state.inputs, incoming, changed_dependencies={} )
            # If the tool provides a `validate_input` hook, call it. 
            validate_input = self.get_hook( 'validate_input' )
            if validate_input:
                validate_input( trans, errors, state.inputs, self.inputs_by_page[state.page] )
            params = state.inputs
        # Did the user actually click next / execute or is this just
        # a refresh?
        if 'runtool_btn' in incoming or 'URL' in incoming:
            # If there were errors, we stay on the same page and display 
            # error messages
            if errors:
                error_message = "One or more errors were found in the input you provided. The specific errors are marked below."    
                return "tool_form.mako", dict( errors=errors, tool_state=state, incoming=incoming, error_message=error_message )
            # If we've completed the last page we can execute the tool
            elif state.page == self.last_page:
                out_data = self.execute( trans, incoming=params )
                return 'tool_executed.mako', dict( out_data=out_data )
            # Otherwise move on to the next page
            else:
                state.page += 1
                # Fill in the default values for the next page
                self.fill_in_new_state( trans, self.inputs_by_page[ state.page ], state.inputs )
                return 'tool_form.mako', dict( errors=errors, tool_state=state )
        else:
            # Just a refresh, render the form with updated state and errors.
            return 'tool_form.mako', dict( errors=errors, tool_state=state )
      
    def update_state( self, trans, inputs, state, incoming, prefix="", context=None,
                      update_only=False, old_errors={}, changed_dependencies={} ):
        """
        Update the tool state in `state` using the user input in `incoming`. 
        This is designed to be called recursively: `inputs` contains the
        set of inputs being processed, and `prefix` specifies a prefix to
        add to the name of each input to extract it's value from `incoming`.
        
        If `update_only` is True, values that are not in `incoming` will
        not be modified. In this case `old_errors` can be provided, and any
        errors for parameters which were *not* updated will be preserved.
        
        Parameters in incoming that are 'dependency parameters' are those
        whose value is used by a dependent parameter to dynamically generate
        it's options list.  When the value of these dependency parameters changes,
        the new value is stored in changed_dependencies.
        """
        errors = dict()     
        # Push this level onto the context stack
        context = ExpressionContext( state, context )
        # Iterate inputs and update (recursively)
        for input in inputs.itervalues():
            key = prefix + input.name
            if isinstance( input, Repeat ):
                group_state = state[input.name]
                group_errors = []
                group_old_errors = old_errors.get( input.name, None )
                any_group_errors = False
                # Check any removals before updating state -- only one
                # removal can be performed, others will be ignored
                for i, rep_state in enumerate( group_state ):
                    rep_index = rep_state['__index__']
                    if key + "_" + str(rep_index) + "_remove" in incoming:
                        del group_state[i]
                        if group_old_errors:
                            del group_old_errors[i]
                        break
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
                                                    update_only=update_only,
                                                    old_errors=rep_old_errors,
                                                    changed_dependencies=changed_dependencies )
                    if rep_errors:
                        any_group_errors = True
                        group_errors.append( rep_errors )
                    else:
                        group_errors.append( {} )
                # Check for addition
                if key + "_add" in incoming:
                    new_state = {}
                    new_state['__index__'] = max_index + 1
                    self.fill_in_new_state( trans, input.inputs, new_state, context )
                    group_state.append( new_state )
                    if any_group_errors:
                        group_errors.append( {} )
                # Were there *any* errors for any repetition?
                if any_group_errors:
                    errors[input.name] = group_errors
            elif isinstance( input, Conditional ):
                group_state = state[input.name]
                group_old_errors = old_errors.get( input.name, {} )
                old_current_case = group_state['__current_case__']
                group_prefix = "%s|" % ( key )
                # Deal with the 'test' element and see if it's value changed
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
                        check_param( trans, input.test_param, test_incoming, context )
                    current_case = input.get_current_case( value, trans )
                if current_case != old_current_case:
                    # Current case has changed, throw away old state
                    group_state = state[input.name] = {}
                    # TODO: we should try to preserve values if we can
                    self.fill_in_new_state( trans, input.cases[current_case].inputs, group_state, context )
                    group_errors = dict()
                    group_old_errors = dict()
                else:
                    # Current case has not changed, update children
                    group_errors = self.update_state( trans, 
                                                      input.cases[current_case].inputs, 
                                                      group_state,
                                                      incoming, 
                                                      prefix=group_prefix,
                                                      context=context,
                                                      update_only=update_only,
                                                      old_errors=group_old_errors,
                                                      changed_dependencies=changed_dependencies )
                if test_param_error:
                    group_errors[ input.test_param.name ] = test_param_error
                if group_errors:
                    errors[ input.name ] = group_errors
                # Store the current case in a special value
                group_state['__current_case__'] = current_case
                # Store the value of the test element
                group_state[ input.test_param.name ] = value
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
                    # SelectToolParameters and DataToolParameters whose options are dynamically
                    # generated based on the current value of a dependency parameter require special
                    # handling.  When the dependency parameter's value is changed, the form is
                    # submitted ( due to the refresh_on_change behavior ).  When this occurs, the 
                    # "dependent" parameter's value has not been reset ( dynamically generated based 
                    # on the new value of its dependency ) prior to reaching this point, so we need 
                    # to regenerate it before it is validated in check_param().
                    incoming_value_generated = False
                    if not( 'runtool_btn' in incoming or 'URL' in incoming ):
                        # Form must have been refreshed, probably due to a refresh_on_change
                        try:
                            if input.is_dynamic:
                                dependencies = input.get_dependencies()
                                for dependency_name in dependencies:
                                    dependency_value = changed_dependencies.get( dependency_name, None )
                                    if dependency_value:
                                        # We need to dynamically generate the current input based on 
                                        # the changed dependency parameter
                                        changed_params = {}
                                        changed_params[dependency_name] = dependency_value
                                        changed_params[input.name] = input
                                        incoming_value = input.get_initial_value( trans, changed_params )
                                        incoming_value_generated = True
                                        # Delete the dependency_param from chagned_dependencies since its
                                        # dependent param has been generated based its new value.
                                        del changed_dependencies[dependency_name]
                                        break
                        except:
                            pass
                    if not incoming_value_generated:
                        incoming_value = get_incoming_value( incoming, key, None )
                    value, error = check_param( trans, input, incoming_value, context )
                    if input.dependent_params and state[ input.name ] != value:
                        # We need to keep track of changed dependency parametrs ( parameters
                        # that have dependent parameters whose options are dynamically generated )
                        changed_dependencies[ input.name ] = value
                    if error:
                        errors[ input.name ] = error
                    state[ input.name ] = value
        return errors
            
    def get_static_param_values( self, trans ):
        """
        Returns a map of parameter names and values if the tool does not 
        require any user input. Will raise an exception if any parameter
        does require input.
        """
        args = dict()
        for key, param in self.inputs.iteritems():
            if isinstance( param, HiddenToolParameter ):
                args[key] = param.value
            elif isinstance( param, BaseURLToolParameter ):
                args[key] = param.get_value( trans )
            else:
                raise Exception( "Unexpected parameter type" )
        return args
            
    def execute( self, trans, incoming={}, set_output_hid=True ):
        """
        Execute the tool using parameter values in `incoming`. This just
        dispatches to the `ToolAction` instance specified by 
        `self.tool_action`. In general this will create a `Job` that 
        when run will build the tool's outputs, e.g. `DefaultToolAction`.
        """
        return self.tool_action.execute( self, trans, incoming=incoming, set_output_hid=set_output_hid )
        
    def params_to_strings( self, params, app ):
        return params_to_strings( self.inputs, params, app )
        
    def params_from_strings( self, params, app, ignore_errors=False ):
        return params_from_strings( self.inputs, params, app, ignore_errors )
    
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

    def handle_unvalidated_param_values_helper( self, inputs, input_values, app, context=None ):
        """
        Recursive helper for `handle_unvalidated_param_values`
        """
        context = ExpressionContext( input_values, context )
        for input in inputs.itervalues():
            if isinstance( input, Repeat ):  
                for d in input_values[ input.name ]:
                    self.handle_unvalidated_param_values_helper( input.inputs, d, app, context )
            elif isinstance( input, Conditional ):
                values = input_values[ input.name ]
                current = values["__current_case__"]
                self.handle_unvalidated_param_values_helper( input.cases[current].inputs, values, app, context )
            else:
                # Regular tool parameter
                value = input_values[ input.name ]
                if isinstance( value, UnvalidatedValue ):
                    if value.value is None: #if value.value is None, it could not have been submited via html form and therefore .from_html can't be guaranteed to work
                        value = None
                    else:
                        value = input.from_html( value.value, None, context )
                    # Then do any further validation on the value
                    input.validate( value, None )
                    input_values[ input.name ] = value
    
    def build_param_dict( self, incoming, input_datasets, output_datasets ):
        """
        Build the dictionary of parameters for substituting into the command
        line. Each value is wrapped in a `InputValueWrapper`, which allows
        all the attributes of the value to be used in the template, *but* 
        when the __str__ method is called it actually calls the 
        `to_param_dict_value` method of the associated input.
        """
        param_dict = dict()
        # All parameters go into the param_dict
        param_dict.update( incoming )
        # Wrap parameters as neccesary
        def wrap_values( inputs, input_values ):
            for input in inputs.itervalues():
                if isinstance( input, Repeat ):  
                    for d in input_values[ input.name ]:
                        wrap_values( input.inputs, d )
                elif isinstance( input, Conditional ):
                    values = input_values[ input.name ]
                    current = values["__current_case__"]
                    wrap_values( input.cases[current].inputs, values )
                elif isinstance( input, DataToolParameter ):
                    input_values[ input.name ] = \
                        DatasetFilenameWrapper( input_values[ input.name ], datatypes_registry = self.app.datatypes_registry, tool = self, name = input.name )
                else:
                    input_values[ input.name ] = \
                        InputValueWrapper( input, input_values[ input.name ], param_dict )
        # HACK: only wrap if check_values is false, this deals with external
        #       tools where the inputs don't even get passed through. These
        #       tools (e.g. UCSC) should really be handled in a special way.
        if self.check_values:
            wrap_values( self.inputs, param_dict )
        # Additionally, datasets go in the param dict. We wrap them such that
        # if the bare variable name is used it returns the filename (for
        # backwards compatibility). We also add any child datasets to the
        # the param dict encoded as:
        #   "_CHILD___{dataset_name}___{child_designation}",
        # but this should be considered DEPRECATED, instead use:
        #   $dataset.get_child( 'name' ).filename
        for name, data in input_datasets.items():
            param_dict[name] = DatasetFilenameWrapper( data, datatypes_registry = self.app.datatypes_registry, tool = self, name = name )
            if data:
                for child in data.children:
                    param_dict[ "_CHILD___%s___%s" % ( name, child.designation ) ] = DatasetFilenameWrapper( child )
        for name, data in output_datasets.items():
            param_dict[name] = DatasetFilenameWrapper( data )
            # Provide access to a path to store additional files
            # TODO: path munging for cluster/dataset server relocatability
            param_dict[name].files_path = os.path.abspath(os.path.join(self.app.config.new_file_path, "dataset_%s_files" % (data.id) ))
            for child in data.children:
                param_dict[ "_CHILD___%s___%s" % ( name, child.designation ) ] = DatasetFilenameWrapper( child )
        # We add access to app here, this allows access to app.config, etc
        param_dict['__app__'] = RawObjectWrapper( self.app )
        # More convienent access to app.config.new_file_path; we don't need to wrap a string
        # But this method of generating additional datasets should be considered DEPRECATED
        # TODO: path munging for cluster/dataset server relocatability
        param_dict['__new_file_path__'] = os.path.abspath(self.app.config.new_file_path)
        # The following points to location (xxx.loc) files which are pointers to locally cached data
        param_dict['GALAXY_DATA_INDEX_DIR'] = self.app.config.tool_data_path
        # Return the dictionary of parameters
        return param_dict
    
    def build_param_file( self, param_dict, directory=None ):
        """
        Build temporary file for file based parameter transfer if needed
        """
        if self.command and "$param_file" in self.command:
            fd, param_filename = tempfile.mkstemp( dir=directory )
            os.close( fd )
            f = open( param_filename, "wt" )
            for key, value in param_dict.items():
                # parameters can be strings or lists of strings, coerce to list
                if type(value) != type([]):
                    value = [ value ]
                for elem in value:
                    f.write( '%s=%s\n' % (key, elem) ) 
            f.close()
            param_dict['param_file'] = param_filename
            return param_filename
        else:
            return None
            
    def build_config_files( self, param_dict, directory=None ):
        """
        Build temporary file for file based parameter transfer if needed
        """
        config_filenames = []
        for name, filename, template_text in self.config_files:
            # If a particular filename was forced by the config use it
            if filename is not None:
                if directory is None:
                    raise Exception( "Config files with fixed filenames require a working directory" )
                config_filename = os.path.join( directory, filename )
            else:
                fd, config_filename = tempfile.mkstemp( dir=directory )
                os.close( fd )
            f = open( config_filename, "wt" )
            f.write( fill_template( template_text, context=param_dict ) )
            f.close()
            param_dict[name] = config_filename
            config_filenames.append( config_filename )
        return config_filenames
        
    def build_command_line( self, param_dict ):
        """
        Build command line to invoke this tool given a populated param_dict
        """
        command_line = None
        if not self.command:
            return
        try:                
            # Substituting parameters into the command
            command_line = fill_template( self.command, context=param_dict )
            # Remove newlines from command line
            command_line = command_line.replace( "\n", " " ).replace( "\r", " " )
        except Exception, e:
            # Modify exception message to be more clear
            #e.args = ( 'Error substituting into command line. Params: %r, Command: %s' % ( param_dict, self.command ) )
            raise
        return command_line

    def build_redirect_url_params( self, param_dict ):
        """Substitute parameter values into self.redirect_url_params"""
        if not self.redirect_url_params:
            return
        redirect_url_params = None            
        # Substituting parameter values into the url params
        redirect_url_params = fill_template( self.redirect_url_params, context=param_dict )
        # Remove newlines
        redirect_url_params = redirect_url_params.replace( "\n", " " ).replace( "\r", " " )
        return redirect_url_params

    def parse_redirect_url( self, data, param_dict ):
        """Parse the REDIRECT_URL tool param"""
        # Tools that send data to an external application via a redirect must include the following 3 tool params:
        # REDIRECT_URL - the url to which the data is being sent
        # DATA_URL - the url to which the receiving application will send an http post to retrieve the Galaxy data
        # GALAXY_URL - the url to which the external application may post data as a response
        redirect_url = param_dict.get( 'REDIRECT_URL' )
        redirect_url_params = self.build_redirect_url_params( param_dict )
        # Add the parameters to the redirect url.  We're splitting the param string on '**^**'
        # because the self.parse() method replaced white space with that separator.
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
            e.args = ( "Error in '%s' hook '%s', original message: %s" % ( self.name, hook_name, e.args[0] ) )
            raise

    def exec_before_job( self, app, inp_data, out_data, param_dict={} ):
        if self.tool_type == 'data_source':
            # List for converting UCSC to Galaxy exts, if not in following dictionary, use provided datatype
            data_type_to_ext = { 'wigdata':'wig', 'tab':'interval', 'hyperlinks':'html', 'sequence':'fasta' }
            dbkey = param_dict.get( 'dbkey' )
            organism = param_dict.get( 'organism' )
            table = param_dict.get( 'table' )
            description = param_dict.get( 'description' )
            info = param_dict.get( 'info' )
            if description == 'range':
                description = param_dict.get( 'position', '' )
                if not description:
                    description = 'unknown position'
            data_type = param_dict.get( 'data_type' )
            items = out_data.items()
            for name, data in items:
                if organism and table and description:
                    data.name  = '%s on %s: %s (%s)' % ( data.name, organism, table, description )
                data.info = info
                data.dbkey = dbkey
                try:
                    data_type = data_type_to_ext[ data_type ]
                except: 
                    pass
                if data_type not in app.datatypes_registry.datatypes_by_extension: 
                    data_type = 'interval'
                data = app.datatypes_registry.change_datatype( data, data_type )
                # Store external data source's request parameters temporarily in output file
                out = open( data.file_name, 'w' )
                for key, value in param_dict.items():
                    print >> out, '%s\t%s' % ( key, value )
                out.close()
                out_data[ name ] = data
            return out_data

    def exec_after_process( self, app, inp_data, out_data, param_dict ):
        # TODO: for data_source tools at least, this code can probably be handled more optimally by adding a new
        # tag set in the tool config.
        if self.tool_type == 'data_source':
            name, data = out_data.items()[0]
            if data.state == data.states.OK:
                data.name = param_dict.get( 'name', data.name )
                data.info = param_dict.get( 'info', data.name )
                data.dbkey = param_dict.get( 'dbkey', data.dbkey )
                data.extension = param_dict.get( 'data_type', data.extension )
            if data.extension == 'txt':
                data_type = sniff.guess_ext( data.file_name, sniff_order=app.datatypes_registry.sniff_order )
                data = app.datatypes_registry.change_datatype( data, data_type )
            elif not isinstance( data.datatype, datatypes.interval.Bed ) and isinstance( data.datatype, datatypes.interval.Interval ):
                data.set_meta()
                if data.missing_meta(): 
                    data = app.datatypes_registry.change_datatype( data, 'tabular' )
            data.set_peek()
            data.set_size()
            data.flush()

    def collect_associated_files( self, output ):
        for name, outdata in output.items():
            temp_file_path = os.path.join( self.app.config.new_file_path, "dataset_%s_files" % ( outdata.id ) )
            try:
                if len( os.listdir( temp_file_path ) ) > 0:
                    store_file_path = os.path.join( os.path.join( self.app.config.file_path, *directory_hash_id( outdata.id ) ), "dataset_%d_files" % outdata.id )
                    shutil.move( temp_file_path, store_file_path )
            except:
                continue
    
    def collect_child_datasets( self, output):
        children = {}
        #Loop through output file names, looking for generated children in form of 'child_parentId_designation_visibility_extension'
        for name, outdata in output.items():
            for filename in glob.glob(os.path.join(self.app.config.new_file_path,"child_%i_*" % outdata.id) ):
                if not name in children:
                    children[name] = {}
                fields = os.path.basename(filename).split("_")
                fields.pop(0)
                parent_id = int(fields.pop(0))
                designation = fields.pop(0)
                visible = fields.pop(0).lower()
                if visible == "visible": visible = True
                else: visible = False
                ext = fields.pop(0).lower()
                child_dataset = self.app.model.HistoryDatasetAssociation( extension=ext, parent_id=outdata.id, designation=designation, visible=visible, dbkey=outdata.dbkey, create_dataset=True )
                self.app.security_agent.copy_dataset_permissions( outdata.dataset, child_dataset.dataset )
                # Move data from temp location to dataset location
                shutil.move( filename, child_dataset.file_name )
                child_dataset.flush()
                child_dataset.name = "Secondary Dataset (%s)" % ( designation )
                child_dataset.state = child_dataset.states.OK
                child_dataset.init_meta()
                child_dataset.set_meta()
                child_dataset.set_peek()
                child_dataset.set_size()
                child_dataset.flush()
                # Add child to return dict 
                children[name][designation] = child_dataset
                for dataset in outdata.dataset.history_associations: #need to update all associated output hdas, i.e. history was shared with job running
                    if outdata == dataset: continue
                    # Create new child dataset
                    child_data = child_dataset.copy( parent_id = dataset.id )
                    child_data.flush()
        return children
        
    def collect_primary_datasets( self, output):
        primary_datasets = {}
        #Loop through output file names, looking for generated primary datasets in form of 'primary_associatedWithDatasetID_designation_visibility_extension'
        for name, outdata in output.items():
            for filename in glob.glob(os.path.join(self.app.config.new_file_path,"primary_%i_*" % outdata.id) ):
                if not name in primary_datasets:
                    primary_datasets[name] = {}
                fields = os.path.basename(filename).split("_")
                fields.pop(0)
                parent_id = int(fields.pop(0))
                designation = fields.pop(0)
                visible = fields.pop(0).lower()
                if visible == "visible": visible = True
                else: visible = False
                ext = fields.pop(0).lower()
                # Create new primary dataset
                primary_data = self.app.model.HistoryDatasetAssociation( extension=ext, designation=designation, visible=visible, dbkey=outdata.dbkey, create_dataset=True )
                self.app.security_agent.copy_dataset_permissions( outdata.dataset, primary_data.dataset )
                primary_data.flush()
                # Move data from temp location to dataset location
                shutil.move( filename, primary_data.file_name )
                primary_data.name = dataset.name
                primary_data.info = dataset.info
                primary_data.state = primary_data.states.OK
                primary_data.init_meta( copy_from=dataset )
                primary_data.set_meta()
                primary_data.set_peek()
                primary_data.set_size()
                primary_data.flush()
                outdata.history.add_dataset( primary_data )
                # Add dataset to return dict 
                primary_datasets[name][designation] = primary_data
                for dataset in outdata.dataset.history_associations: #need to update all associated output hdas, i.e. history was shared with job running
                    if outdata == dataset: continue
                    new_data = primary_data.copy()
                    dataset.history.add( new_data )
                    new_data.flush()
        return primary_datasets

        
# ---- Utility classes to be factored out -----------------------------------
        
class BadValue( object ):
    def __init__( self, value ):
        self.value = value

class RawObjectWrapper( object ):
    """
    Wraps an object so that __str__ returns module_name:class_name.
    """
    def __init__( self, obj ):
        self.obj = obj
    def __str__( self ):
        return "%s:%s" % (self.obj.__module__, self.obj.__class__.__name__)
    def __getattr__( self, key ):
        return getattr( self.obj, key )

class InputValueWrapper( object ):
    """
    Wraps an input so that __str__ gives the "param_dict" representation.
    """
    def __init__( self, input, value, other_values={} ):
        self.input = input
        self.value = value
        self._other_values = other_values
    def __str__( self ):
        return self.input.to_param_dict_string( self.value, self._other_values )
    def __getattr__( self, key ):
        return getattr( self.value, key )
        
class DatasetFilenameWrapper( object ):
    """
    Wraps a dataset so that __str__ returns the filename, but all other
    attributes are accessible.
    """
    
    class MetadataWrapper:
        """
        Wraps a Metadata Collection to return MetadataParameters wrapped according to the metadata spec.
        Methods implemented to match behavior of a Metadata Collection.
        """
        def __init__( self, metadata ):
            self.metadata = metadata
        def __getattr__( self, name ):
            rval = self.metadata.get( name, None )
            if name in self.metadata.spec:
                if rval is None:
                    rval = self.metadata.spec[name].no_value
                rval = self.metadata.spec[name].param.to_string( rval )
                setattr( self, name, rval ) #lets store this value, so we don't need to recalculate if needed again
            return rval
        def __nonzero__( self ):
            return self.metadata.__nonzero__()
        def __iter__( self ):
            return self.metadata.__iter__()
        def get( self, key, default=None ):
            try:
                return getattr( self, key )
            except:
                return default
        def items( self ):
            return iter( [ ( k, self.get( k ) ) for k, v in self.metadata.items() ] )
    
    def __init__( self, dataset, datatypes_registry = None, tool = None, name = None ):
        if not dataset:
            try:
                #TODO: allow this to work when working with grouping
                ext = tool.inputs[name].extensions[0]
            except:
                ext = 'data'
            self.dataset = NoneDataset( datatypes_registry = datatypes_registry, ext = ext )
        else:
            self.dataset = dataset
            self.metadata = self.MetadataWrapper( dataset.metadata )
    def __str__( self ):
        return self.dataset.file_name
    def __getattr__( self, key ):
        return getattr( self.dataset, key )
        
def json_fix( val ):
    if isinstance( val, list ):
        return [ json_fix( v ) for v in val ]
    elif isinstance( val, dict ):
        return dict( [ ( json_fix( k ), json_fix( v ) ) for ( k, v ) in val.iteritems() ] )
    elif isinstance( val, unicode ):
        return val.encode( "utf8" )
    else:
        return val
    
def get_incoming_value( incoming, key, default ):
    if "__" + key + "__is_composite" in incoming:
        composite_keys = incoming["__" + key + "__keys"].split()
        value = dict()
        for composite_key in composite_keys:
            value[composite_key] = incoming[key + "_" + composite_key]
        return value
    else:
        return incoming.get( key, default )