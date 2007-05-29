"""
Classes encapsulating galaxy tools and tool configuration.
"""

import pkg_resources; 
pkg_resources.require( "Cheetah" )
pkg_resources.require( "simplejson" )

import logging, os, string, sys, tempfile
import thread
import simplejson

from UserDict import DictMixin
from Cheetah.Template import Template
from cookbook.odict import odict
from cookbook.patterns import Bunch
from galaxy import util, jobs, model
from elementtree import ElementTree
from parameters import *
from grouping import *
from galaxy.util.expressions import ExpressionContext
from galaxy.tools.test import ToolTestBuilder
from galaxy.tools.actions import DefaultToolAction
from copy import copy

log = logging.getLogger( __name__ )

class ToolNotFoundException( Exception ):
    pass

class ToolBox( object ):
    """
    Container for a collection of tools
    """

    def __init__( self, config_filename, tool_root_dir ):
        """
        Create a toolbox from the config file names by `config_filename`,
        using `tool_root_directory` as the base directory for finding 
        individual tool config files.
        """
        self.tools_by_id = {}
        self.tools_and_sections_by_id = {}
        self.sections = []
        self.tool_root_dir = tool_root_dir
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
                    log.debug( "Loaded tool: %s", tool.id )
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
        return ToolClass( config_file, root )
        
    def reload( self, tool_id ):
        """
        Attempt to reload the tool identified by 'tool_id', if successfull 
        replace the old tool.
        """
        if tool_id not in self.tools_and_sections_by_id:
            raise ToolNotFoundException( "No tool with id %s" % tool_id )
        old_tool, section = self.tools_and_sections_by_id[ tool_id ]
        new_tool = self.load_tool( old_tool.config_file )
        log.debug( "Reloaded tool %s", old_tool.id )
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
        Convert the data to a pickleable form
        """
        rval = tool.params_to_strings( self.inputs, app )
        rval["__page__"] = self.page  
        return rval      
    def decode( self, values, tool, app ):
        """
        Restore the state from pickleable form
        """
        self.page = values.pop( "__page__" )
        self.inputs = tool.params_from_strings( values, app, ignore_errors=True )

class Tool:
    """
    Represents a computational tool that can be executed through Galaxy. 
    """
    def __init__( self, config_file, root ):
        """
        Load a tool from the config named by `config_file`
        """
        # Determine the full path of the directory where the tool config is
        self.config_file = config_file
        self.tool_dir = os.path.dirname( config_file )
        # Parse XML element containing configuration
        self.parse( root )
        
    def parse( self, root ):
        """
        Read tool configuration from the element `root` and fill in `self`.
        """
        # Get the (user visible) name of the tool
        self.name = root.get("name")
        if not self.name: raise Exception, "Missing tool 'name'"
        # Get the UNIQUE id for the tool 
        # TODO: can this be generated automatically?
        self.id = root.get("id")
        if not self.id: raise Exception, "Missing tool 'id'" 
        # Command line (template). Optional for tools that do not invoke a 
        # local program  
        command = root.find("command")
        if command is not None and command.text is not None:
            self.command = command.text.lstrip() # get rid of leading whitespace
            interpreter  = command.get("interpreter")
            if interpreter:
                self.command = interpreter + " " + os.path.join(self.tool_dir, self.command)
        else:
            self.command = ''
        # Short description of the tool
        self.description = util.xml_text(root, "description")
        # Is this a 'hidden' tool (hidden in tool menu)
        self.hidden = util.xml_text(root, "hidden")
        if self.hidden: self.hidden = util.string_as_bool(self.hidden)
        # Load any tool specific code (optional) Edit: INS 5/29/2007,
        # allow code files to have access to the individual tool's
        # "module" if it has one.  Allows us to reuse code files, etc.
        lock = thread.allocate_lock()
        lock.acquire(True)
        oldpath = copy(sys.path)
        sys.path.append( self.tool_dir )
        self.code_namespace = dict()
        for code_elem in root.findall("code"):
            file_name = code_elem.get("file")
            code_path = os.path.join( self.tool_dir, file_name )
            execfile( code_path, self.code_namespace )
        # Restore old sys.path
        sys.path = oldpath
        lock.release()
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
        # FIXME: This is not used anywhere, what does it do?
        # url redirection to ougoings
        self.redir_url  = root.find("url")
        # Description of outputs produced by an invocation of the tool
        self.outputs = {}
        out_elem = root.find("outputs")
        if out_elem:
            for data_elem in out_elem.findall("data"):
                name = data_elem.get("name")
                format = data_elem.get("format", "data")
                metadata_source = data_elem.get("metadata_source", "")
                parent = data_elem.get("parent", None)
                self.outputs[name] = (format, metadata_source, parent)
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
        # Tests
        tests_elem = root.find( "tests" )
        if tests_elem:
            try:
                self.parse_tests( tests_elem )
            except:
                log.exception( "Failed to parse tool tests" )
        else:
            self.tests = None
            
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
        
    def parse_input_elem( self, parent_elem, enctypes ):
        """
        Parse a parent element whose children are inputs -- these could be 
        groups (repeat, conditional) or param elements. Groups will be parsed
        recursively.
        """
        rval = odict()
        for elem in parent_elem:
            # Repeat group
            if elem.tag == "repeat":
                group = Repeat()
                group.name = elem.get( "name" )
                group.title = elem.get( "title" ) 
                group.inputs = self.parse_input_elem( elem, enctypes )  
                rval[group.name] = group
            elif elem.tag == "conditional":
                group = Conditional()
                group.name = elem.get( "name" )
                # Should have one child "input" which determines the case
                input_elem = elem.find( "param" )
                assert input_elem is not None, "<conditional> must have a child <param>"
                group.test_param = self.parse_param_elem( input_elem, enctypes )
                # And a set of possible cases
                for case_elem in elem.findall( "when" ):
                    case = ConditionalWhen()
                    case.value = case_elem.get( "value" )
                    case.inputs = self.parse_input_elem( case_elem, enctypes )
                    group.cases.append( case )
                rval[group.name] = group
            elif elem.tag == "param":
                param = self.parse_param_elem( elem, enctypes )
                rval[param.name] = param
        return rval

    def parse_param_elem( self, input_elem, enctypes ):
        """
        Parse a single "<param>" element and return a ToolParameter instance. 
        Also, if the parameter has a 'required_enctype' add it to the set
        enctypes.
        """
        param = ToolParameter.build( self, input_elem )
        param_enctype = param.get_required_enctype()
        if param_enctype:
            enctypes.add( param_enctype )
        return param

    def new_state( self, trans ):
        """
        Create a new `DefaultToolState` for this tool. It will be initialized
        based on `self.inputs` with appropriate default values.
        """
        state = DefaultToolState()
        state.inputs = {}
        self.fill_in_new_state( trans, self.inputs_by_page[ 0 ], state.inputs )
        return state

    def fill_in_new_state( self, trans, inputs, state ):
        """
        Fill in a state dictionary with default values taken from input.
        Grouping elements are filled in recursively. 
        """
        for input in inputs.itervalues():
            if isinstance( input, Repeat ):  
                state[ input.name ] = []
            elif isinstance( input, Conditional ):
                s = state[ input.name ] = {}
                test_value = input.test_param.get_initial_value( trans, state )
                current_case = input.get_current_case( test_value, trans )
                self.fill_in_new_state( trans, input.cases[current_case].inputs, s )
                # Store the current case in a special value
                s['__current_case__'] = current_case
                # Store the value of the test element
                s[ input.test_param.name ] = test_value
            else:
                value = input.get_initial_value( trans, state )
                state[ input.name ] = value

    def get_param_html_map( self, trans, page=0, other_values={} ):
        """
        Return a dictionary containing the HTML representation of each 
        parameter. This is used for rendering display elements. It is 
        currently not compatible with grouping constructs.
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
        if self.code_namespace and name in self.code_namespace:
            return self.code_namespace[name]
        return None
        
    def visit_inputs( self, value, callback ):
        # HACK: Yet another hack around check_values
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
            # This feels a bit like a hack
            if "runtool_btn" not in incoming and "URL" not in incoming:
                return "tool_form.tmpl", dict( errors={}, tool_state=state, param_values={}, incoming={} )
        # Fill in everything we can in the state and keep track of errors
        # Now process new parameters for the current page
        if self.check_values:
            errors = self.update_state( trans, self.inputs_by_page[state.page], state.inputs, incoming )
            # Any tool specific validation
            validate_input = self.get_hook( 'validate_input' )
            if validate_input:
                validate_input( trans, errors, state.inputs, self.inputs_by_page[state.page] )
            params = state.inputs
        else:
            errors = {}
            params = incoming
        # Did the user actually click next / execute or is this just
        # a refresh?
        if 'runtool_btn' in incoming or 'URL' in incoming:
            # If there were errors, we stay on the same page and display 
            # error messages
            if errors:
                error_message = "One or more errors were found in the input you provided. The specific errors are marked below."    
                return "tool_form.tmpl", dict( errors=errors, tool_state=state, incoming=incoming, error_message=error_message )
            # If we've completed the last page we can execute the tool
            elif state.page == self.last_page:
                out_data = self.execute( trans, params )
                return 'tool_executed.tmpl', dict( out_data=out_data )
            # Otherwise move on to the next page
            else:
                state.page += 1
                # Fill in the default values for the next page
                self.fill_in_new_state( trans, self.inputs_by_page[ state.page ], state.inputs )
                return 'tool_form.tmpl', dict( errors=errors, tool_state=state )
        else:
            return 'tool_form.tmpl', dict( errors=errors, tool_state=state )
      
    def update_state( self, trans, inputs, state, incoming, prefix = "", context=None ):
        """
        Update the tool state in `state` using the user input in `incoming`. 
        This is designed to be called recursively: `inputs` contains the
        set of inputs being processed, and `prefix` specifies a prefix to
        add to the name of each input to extract it's value from `incoming`.
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
                any_group_errors = False
                # Check any removals before updating state
                for i in range( len( group_state ) ):                    
                    if input.name + "_" + str(i) + "_remove" in incoming:
                        del group_state[i]
                # Update state
                for i in range( len( group_state ) ):
                    prefix = "%s_%d|" % ( key, i )
                    rep_errors = self.update_state( trans,
                                                    input.inputs, 
                                                    group_state[i], 
                                                    incoming, 
                                                    prefix,
                                                    context )
                    if rep_errors:
                        any_group_errors = True
                        group_errors.append( rep_errors )
                    else:
                        group_errors.append( {} )
                # Check for addition
                if input.name + "_add" in incoming:
                    new_state = {}
                    self.fill_in_new_state( trans, input.inputs, new_state )
                    group_state.append( new_state )
                    if any_group_errors:
                        group_errors.append( {} )
                # Were there *any* errors for any repetition?
                if any_group_errors:
                    errors[input.name] = group_errors
            elif isinstance( input, Conditional ):
                group_state = state[input.name]
                old_current_case = group_state['__current_case__']
                prefix = "%s|" % ( key )
                # Deal with the 'test' element and see if it's value changed
                test_incoming = incoming.get( prefix + input.test_param.name, None )
                value, test_param_error = \
                    self.check_param( trans, input.test_param, test_incoming, group_state )
                current_case = input.get_current_case( value, trans )
                if current_case != old_current_case:
                    # Current case has changed, throw away old state
                    group_state = state[input.name] = {}
                    # TODO: we should try to preserve values if we can
                    self.fill_in_new_state( trans, input.cases[current_case].inputs, group_state )
                    group_errors = dict()
                else:
                    # Current case has not changed, update children
                    group_errors = self.update_state( trans, 
                                                      input.cases[current_case].inputs, 
                                                      group_state,
                                                      incoming, 
                                                      prefix )
                if test_param_error:
                    group_errors[ input.test_param.name ] = test_param_error
                if group_errors:
                    errors[ input.name ] = group_errors
                # Store the current case in a special value
                group_state['__current_case__'] = current_case
                # Store the value of the test element
                group_state[ input.test_param.name ] = value
            else:
                incoming_value = incoming.get( key, None )
                value, error = self.check_param( trans, input, incoming_value, state )
                if error:
                    errors[ input.name ] = error
                state[input.name] = value
        return errors
            
    def check_param( self, trans, param, incoming_value, param_values ):
        """
        Check the value of a single parameter `param`. The value in 
        `incoming_value` is converted from its HTML encoding and validated.
        The `param_values` argument contains the processed values of 
        previous parameters (this may actually be an ExpressionContext 
        when dealing with grouping scenarios).
        """
        value = incoming_value
        error = None
        try:
            if param.name == 'file_data':
                pass
            elif value is not None or isinstance(param, DataToolParameter):
                # Convert value from HTML representation
                value = param.from_html( value, trans, param_values )
                # Allow the value to be converted if neccesary
                filtered_value = param.filter_value( value, trans, param_values )
                # Then do any further validation on the value
                param.validate( filtered_value, trans.history )
        except ValueError, e:
            error = str( e )
        return value, error
            
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
            
    def execute( self, trans, incoming={} ):
        """
        Execute the tool using parameter values in `incoming`. This just
        dispatches to the `ToolAction` instance specified by 
        `self.tool_action`. In general this will create a `Job` that 
        when run will build the tool's outputs, e.g. `DefaultToolAction`.
        """
        return self.tool_action.execute( self, trans, incoming )
        
    def params_to_strings( self, params, app ):
        """
        Convert a dictionary of parameter values to a dictionary of strings
        suitable for persisting. The `value_to_basic` method of each parameter
        is called to convert its value to basic types, the result of which
        is then json encoded (this allowing complex nested parameters and 
        such).
        """
        rval = dict()
        for key, value in params.iteritems():
            if key in self.inputs:
                basic = self.inputs[ key ].value_to_basic( value, app )
                rval[ key ] = simplejson.dumps( basic )
            else:
                rval[ key ] = value
        return rval
        
    def params_from_strings( self, params, app, ignore_errors=False ):
        """
        Convert a dictionary of strings as produced by `params_to_strings`
        back into parameter values (decode the json representation and then
        allow each parameter to convert the basic types into the parameters
        preferred form).
        """
        rval = dict()
        for key, value in params.iteritems():
            if key in self.inputs:
                basic = simplejson.loads( value )
                rval[ key ] = self.inputs[key].value_from_basic( basic, app, ignore_errors )
            else:
                rval[ key ] = value 
        return rval
        
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
                else:
                    input_values[ input.name ] = \
                        InputValueWrapper( input, input_values[ input.name ] )
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
            param_dict[name] = DatasetFilenameWrapper( data )
            for child_association in data.children:
                child = child_association.child
                key = "_CHILD___%s___%s" % ( name, child.designation ) 
                param_dict[ key ] = DatasetFilenameWrapper( child )
        for name, data in output_datasets.items():
            param_dict[name] = DatasetFilenameWrapper( data )
            for child_association in data.children:
                child = child_association.child
                key = "_CHILD___%s___%s" % ( name, child.designation ) 
                param_dict[ key ] = DatasetFilenameWrapper( child )
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
            template = Template( source=template_text, searchList=[param_dict] )
            f.write( str( template ) )
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
            template = Template( source=self.command, searchList=[param_dict] )
            command_line = str( template )  
            # Remove newlines from command line
            command_line = command_line.replace( "\n", " " ).replace( "\r", " " )
        except Exception, e:
            # Modify exception message to be more clear
            #e.args = ( 'Error substituting into command line. Params: %r, Command: %s' % ( param_dict, self.command ) )
            raise
        return command_line
        
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
        
# ---- Utility classes to be factored out -----------------------------------
        
class BadValue( object ):
    def __init__( self, value ):
        self.value = value
        
class InputValueWrapper( object ):
    """
    Wraps an input so that __str__ gives the "param_dict" representation.
    """
    def __init__( self, input, value ):
        self.input = input
        self.value = value
    def __str__( self ):
        return self.input.to_param_dict_string( self.value )
    def __getattr__( self, key ):
        return getattr( self.value, key )
        
class DatasetFilenameWrapper( object ):
    """
    Wraps a dataset so that __str__ returns the filename, but all other
    attributes are accessible.
    """
    def __init__( self, dataset ):
        self.dataset = dataset
    def __str__( self ):
        return self.dataset.file_name
    def __getattr__( self, key ):
        return getattr( self.dataset, key )
