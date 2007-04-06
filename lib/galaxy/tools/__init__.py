"""
Classes encapsulating galaxy tools and tool configuration.
"""

import logging, os, string, sys, tempfile
from cookbook.odict import odict
from cookbook.patterns import Bunch
from galaxy import util, jobs
from elementtree import ElementTree
from parameters import *
from galaxy.tools.test import ToolTestBuilder

log = logging.getLogger( __name__ )

class ToolNotFoundException( Exception ):
    pass

class ToolBox( object ):
    """
    Container for a collection of tools
    """

    def __init__( self, config_filename, tool_root_dir ):
        """Create a toolbox from config in 'fname'"""
        self.tools_by_id = {}
        self.tools_and_sections_by_id = {}
        self.sections = []
        self.tool_root_dir = tool_root_dir
        try:
            self.init_tools( config_filename )
        except:
            log.exception( "ToolBox error reading %s", config_filename )

    def init_tools( self, config_filename ):
        """Reads the individual tool configurations paths from the main configuration file"""
        log.info("parsing the tool configuration")
        tree = util.parse_xml( config_filename )
        root = tree.getroot()
        for elem in root.findall("section"):
            section = ToolSection(elem)
            log.debug( "Loading tools in section: %s" % section.name )
            for tool in elem.findall("tool"):
                try:
                    path = tool.get("file")
                    tool = Tool( os.path.join( self.tool_root_dir, path ) )
                    log.debug( "Loaded tool: %s", tool.id )
                    self.tools_by_id[tool.id] = tool
                    self.tools_and_sections_by_id[tool.id] = tool, section
                    section.tools.append(tool)
                except Exception, exc:
                    log.exception( "error reading tool from path: %s" % path )
            self.sections.append(section)
        
    def reload( self, tool_id ):
        """
        Attempt to reload the tool identified by 'tool_id', if successfull 
        replace the old tool.
        """
        if tool_id not in self.tools_and_sections_by_id:
            raise ToolNotFoundException( "No tool with id %s" % tool_id )
        old_tool, section = self.tools_and_sections_by_id[ tool_id ]
        new_tool = Tool( old_tool.config_file )
        log.debug( "Reloaded tool %s", old_tool.id )
        # Is there a potential sync problem here? This should be roughly 
        # atomic. Too many indexes for tools...
        section.tools[ section.tools.index( old_tool ) ] = new_tool
        self.tools_by_id[ tool_id ] = new_tool
        self.tools_and_sections_by_id[ tool_id ] = new_tool, section
        
    def itertools( self ):
        """Return any tests associated with tools"""
        for section in self.sections:
            for tool in section.tools:
                yield tool

    def __str__(self):
        return "%s: %s" % (self.__class__.__name__, self.tools_by_id)

class ToolSection( object ):
    """A group of tools with similar type/purpose"""

    def __init__( self, elem):
        """Creates a tool section"""
        self.name = elem.get("name")
        self.id   = elem.get("id")
        self.tools = []

    def __str__( self ):
        return "%s: %s (%s)" % (self.__class__.__name__ , self.name, self.id) 

class DefaultToolState( object ):
    def __init__( self ):
        self.page = 0
        self.params = {}

class Tool:
    """
    Creates a tool class from a tool specification
    """
    def __init__( self, config_file ):
        """
        Load a tool from 'config file'
        """
        # Determine the full path of the directory where the tool config is
        self.config_file = config_file
        self.tool_dir = os.path.dirname( config_file )
        # Parse XML configuration file and get the root element
        tree  = util.parse_xml( self.config_file )
        root  = tree.getroot()
        # Get the (user visible) name of the tool
        self.name = root.get("name")
        if not self.name: raise Exception, "Missing tool 'name'"
        # Get the UNIQUE id for the tool 
        # TODO: can this be generated automatically?
        self.id   = root.get("id")
        if not self.id: raise Exception, "Missing tool 'id'" 
        # Command line (template). Optional for tools that do not invoke a 
        # local program  
        command = root.find("command")
        if command is not None:
            self.command = util.xml_text(root, "command") # get rid of whitespace
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
        # Load any tool specific code (optional)
        self.code_namespace = dict()
        for code_elem in root.findall("code"):
            file_name = code_elem.get("file")
            code_path = os.path.join( self.tool_dir, file_name )
            execfile( code_path, self.code_namespace )
        # Load any tool specific options (optional)
        self.options = {'sanitize':True, 'refresh':False}
        for option_elem in root.findall("options"):
            for option, value in self.options.copy().items():
                if isinstance(value, type(False)):
                    self.options[option] = util.string_as_bool(option_elem.get(option, str(value)))
                else:
                    self.options[option] = option_elem.get(option, str(value))
        self.options = Bunch(** self.options)
        # Load parameters (optional)
        input_elem = root.find("inputs")
        if input_elem:
            # Handle properties of the input form
            self.check_values = util.string_as_bool( input_elem.get("check_values", "true") )
            self.action = input_elem.get( "action", "/tool_runner/index")
            self.target = input_elem.get( "target", "galaxy_main" )
            self.method = input_elem.get( "method", "post" )
            # Parse the actual parameters
            self.param_map = odict()
            self.param_map_by_page = list()
            self.display_by_page = list()
            enctypes = set()
            # Handle multiple page case
            pages = input_elem.findall( "page" )
            for page in ( pages or [ input_elem ] ):
                display, param_map = self.parse_page( page, enctypes )
                self.param_map_by_page.append( param_map )
                self.param_map.update( param_map )
                self.display_by_page.append( display )
            self.display = self.display_by_page[0]
            self.npages = len( self.param_map_by_page )
            self.last_page = len( self.param_map_by_page ) - 1
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
        for param in self.param_map.values():
            if not isinstance( param, ( HiddenToolParameter, BaseURLToolParameter ) ):
                self.input_required = True
                break
        # Longer help text for the tool. Formatted in RST
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
            self.help_by_page = [ \
                util.rst_to_html(help_header + x + help_footer) for x in self.help_by_page \
                ]
        except:
            log.exception( "error in multi-page help for tool %s" % self.name )
        # Pad out help pages to match npages ... could this be done better?
        while len(self.help_by_page) < self.npages: self.help_by_page.append( self.help )
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
            
    def parse_tests( self, tests_elem ):
        """Parse any 'test' elements and save"""
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
            
    def parse_page( self, input_elem, enctypes ):
        param_map = odict()
        for param_elem in input_elem.findall("param"):
            param = ToolParameter.build( self, param_elem )
            param_map[param.name] = param
            param_enctype = param.get_required_enctype()
            if param_enctype:
                enctypes.add( param_enctype )
        display_elem = input_elem.find("display")
        if display_elem is not None:
            display = util.xml_to_string(display_elem)
        else:
            display = None
        return display, param_map

    def get_param_html_map( self, trans, page=0 ):
        """Map containing HTML representation of each parameter"""
        return dict( ( key, param.get_html( trans ) ) for key, param in self.param_map_by_page[page].iteritems() )

    def get_param(self, key):
        """Returns a parameter by name"""
        return self.param_map.get(key, None)

    def __str__(self):
        return "%s: %s (%s)" % (self.__class__.__name__ , self.name, self.id)

    def get_hook(self, name):
        """Returns an externally loaded object from the namespace"""
        if self.code_namespace and name in self.code_namespace:
            return self.code_namespace[name]
        return None

    def handle_input( self, trans, incoming ):
        """Process incoming parameters for this tool"""
        # Get the state or create if not found
        if "tool_state" in incoming:
            state = util.string_to_object( incoming["tool_state"] )
        else:
            state = DefaultToolState()
            # This feels a bit like a hack
            if "runtool_btn" not in incoming and "URL" not in incoming:
                return "tool_form.tmpl", dict( errors={}, tool_state=state, param_values={}, incoming={} )
        # Check that values from previous page are all there
        params = dict()
        for p in range( state.page ):
            for param in self.param_map_by_page[p].values():
                if param.name in state.params:
                    params[param.name] = param.filter_value( state.params[ param.name ], trans, params )
                else:
                    raise Exception( "Value from previous page is not stored!" )
        # Now process new parameters for the current page
        error_map = dict()
        if self.check_values:
            # Validate each parameter
            for param in self.param_map_by_page[state.page].values():
                try:
                    value = orig_value = incoming.get( param.name, None )
                    if param.name == 'file_data':
                        value = orig_value
                    elif orig_value is not None or isinstance(param, DataToolParameter):
                        # Allow the value to be converted if neccesary
                        value = param.filter_value( orig_value, trans, params )
                        # Then do any further validation on the value
                        param.validate( value, trans.history )
                    # All okay, stuff it back into the parameter map
                    state.params[param.name] = orig_value
                    params[param.name] = value
                except ValueError, e:
                    error_map[param.name] = str( e )
            # Any tool specific validation
            validate_input = self.get_hook( 'validate_input' )
            if validate_input:
                validate_input( trans, error_map, params, self.param_map_by_page[state.page] )
        else:
            params = incoming
        
        #Add Tool Parameters to tool's namespace.
        self.code_namespace['GALAXY_TOOL_PARAMS']=Bunch(** params)
        
        # If there were errors, we stay on the same page and display 
        # error messages
        if error_map:
            error_message = "One or more errors were found in the input you provided. The specific errors are marked below."    
            return "tool_form.tmpl", dict( errors=error_map, tool_state=state, param_values=params, incoming=incoming, error_message=error_message )
        # If we've completed the last page we can execute the tool
        elif state.page == self.last_page:
            out_data = self.execute( trans, params )
            return 'tool_executed.tmpl', dict( out_data=out_data )
        # Otherwise move on to the next page
        else:
            state.page += 1
            return 'tool_form.tmpl', dict( errors={}, tool_state=state, param_values=params, incoming=incoming )
            
    def get_static_param_values( self, trans ):
        """
        Returns a map of parameter names and values if the tool does
        not require any user input. Will raise an exception if a
        parameter that does require input exists.
        """
        args = dict()
        for key, param in self.param_map.iteritems():
            if isinstance( param, HiddenToolParameter ):
                args[key] = param.value
            elif isinstance( param, BaseURLToolParameter ):
                args[key] = trans.request.base + param.value
            else:
                raise Exception( "Unexpected parameter type" )
        return args
            
    def execute( self, trans, incoming={} ):
        return self.tool_action.execute( self, trans, incoming )
        
    def params_to_strings( self, params, app ):
        rval = dict()
        for key, value in params.iteritems():
            if key in self.param_map:
                rval[ key ] = self.param_map[key].to_string( value, app )
            else:
                rval[ key ] = str( value )
        return rval
        
    def params_to_python( self, params, app ):
        rval = dict()
        for key, value in params.iteritems():
            if key in self.param_map:
                rval[ key ] = self.param_map[key].to_python( value, app )
            else:
                rval[ key ] = value
        return rval
        
    def build_param_dict( self, incoming, input_datasets, output_datasets ):
        """
        Build the dictionary of parameters for substituting into the command
        line.
        """
        param_dict = dict()
        # All converted posted parameters go int the param dict
        param_dict.update( incoming )
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
    
    def build_param_file( self, param_dict ):
        """
        Build temporary file for file based parameter transfer if needed
        """
        if self.command and "$param_file" in self.command:
            fd, param_filename = tempfile.mkstemp()
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
        
    def build_command_line( self, param_dict ):
        """
        Build command line to invoke this tool given a populated param_dict
        """
        command_line = None
        if self.command:
            try:                
                # Substituting parameters into the command
                # TODO: replace with a real template (Cheetah)
                command_line = string.Template( self.command ).substitute( param_dict )
            except Exception, e:
                # Modify exception message to be more clear
                e.args = ( 'Error substituting into command line. Params: %r, Command: %s' % ( param_dict, self.command ) )
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
            raise Exception, "Error in '%s' hook: %s" % ( hook_name, e )

class ToolAction( object ):
    """
    The actions to be taken when a tool is run (after parameters have
    been converted and validated).
    """
    def execute( self, tool, trans, incoming={} ):
        raise TypeError("Abstract method")
    
class DefaultToolAction( object ):
    """
    Default tool action is to run an external command
    """
    
    def collect_input_datasets( self, tool, incoming ):
        """
        Collect any dataset inputs from incoming. Returns a mapping from 
        parameter name to Dataset instance for each tool parameter that is
        of the DataToolParameter type.
        """
        input_datasets = dict()
        for name, value in incoming.iteritems():
            param = tool.get_param( name )
            if param and isinstance( param, DataToolParameter ):
                if isinstance( value, list ):
                    # If there are multiple inputs with the same name, they
                    # are stored as name1, name2, ...
                    for i, v in enumerate( value ):
                        input_datasets[ name + str( i + 1 ) ] = v
                else:
                    input_datasets[ name ] = value
        return input_datasets
    
    def execute(self, tool, trans, incoming={} ):
        out_data   = {}
        
        # Collect any input datasets from the incoming parameters
        inp_data = self.collect_input_datasets( tool, incoming )
        
        # Deal with input metadata, 'dbkey', names, and types
        
        # FIXME: does this need to modify 'incoming' or should this be 
        #        moved into 'build_param_dict'? Is this just about getting the
        #        metadata into the command line? 
        input_names = []
        input_ext = 'data'
        input_dbkey = incoming.get( "dbkey", "?" )
        input_meta = Bunch()
        for name, data in inp_data.items():
            # Hack for fake incoming data
            if data == None:
                data = trans.app.model.Dataset()
                data.state = data.states.FAKE
            input_names.append( 'data %s' % data.hid )
            input_ext = data.ext
            if data.dbkey not in [None, '?']:
                input_dbkey = data.dbkey
            for meta_key, meta_value in data.metadata.items():
                if meta_value is not None:
                    meta_key = '%s_%s' % (name, meta_key)
                    incoming[meta_key] = meta_value

        # Build name for output datasets based on tool name and input names
        output_base_name = tool.name
        if input_names:
            output_base_name += ' on ' + ', '.join( input_names )
        
        # Add the dbkey to the incoming parameters
        incoming[ "dbkey" ] = input_dbkey
        
        # Keep track of parent / child relationships, we'll create all the 
        # datasets first, then create the associations
        parent_to_child_pairs = []
        child_dataset_names = set()
        
        for name, elems in tool.outputs.items():
            ( ext, metadata_source, parent ) = elems
            if parent:
                parent_to_child_pairs.append( ( parent, name ) )
                child_dataset_names.add( name )
            ## What is the following hack for? Need to document under what 
            ## conditions can the following occur? (james@bx.psu.edu)
            # HACK: the output data has already been created
            if name in incoming:
                dataid = incoming[name]
                data = trans.app.model.Dataset.get( dataid )
                assert data != None
                out_data[name] = data
                continue 
            # the type should match the input
            if ext == "input":
                ext = input_ext
            # FIXME: What does this flush?
            trans.app.model.flush()
            data = trans.app.model.Dataset()
            # Commit the dataset immediately so it gets database assigned 
            # unique id
            data.flush()
            # Create an empty file immediately
            open( data.file_name, "w" ).close()
            # FIXME: What does this flush?
            trans.app.model.flush()
            # This may not be neccesary with the new parent/child associations
            data.designation = name
            # Set the extension / datatype
            # FIXME: Datatypes -- this propertype has a lot of hidden logic
            data.extension = ext
            # Copy metadata from one of the inputs if requested. 
            # FIXME: init_meta should take a dataset to copy from as an 
            # argument
            if metadata_source:
                data.metadata = Bunch( ** inp_data[metadata_source].metadata.__dict__ )
            else:
                data.init_meta()
            # Take dbkey from LAST input
            data.dbkey = input_dbkey
            # Default attributes
            data.state = data.states.QUEUED
            data.blurb = "queued"
            data.name  = output_base_name
            out_data[ name ] = data
            # Store all changes to database
            trans.app.model.flush()
                        
        # Add all the top-level (non-child) datasets to the history
        for name in out_data.keys():
            if name not in child_dataset_names:
                data = out_data[ name ]
                trans.history.add_dataset( data )
                data.flush()
                
        # Add all the children to their parents
        for parent_name, child_name in parent_to_child_pairs:
            parent_dataset = out_data[ parent_name ]
            child_dataset = out_data[ child_name ]
            assoc = trans.app.model.DatasetChildAssociation()
            assoc.child = child_dataset
            assoc.designation = child_dataset.designation
            parent_dataset.children.append( assoc )
            # FIXME: Child dataset hid
            
        # Store data after custom code runs 
        trans.app.model.flush()

        # Build params, done before hook so hook can use
        param_dict = tool.build_param_dict( incoming, inp_data, out_data )

        # Run the before queue ("exec_before_job") hook
        # FIXME: this hook should probably be called exec_before_job_queued
        tool.call_hook( 'exec_before_job', trans, inp_data=inp_data, 
                        out_data=out_data, tool=tool, param_dict=param_dict )

        # Build the job's command line, moved to after the hook so the hook can alter params
        param_filename = tool.build_param_file( param_dict )
        command_line = tool.build_command_line( param_dict )
        
        # Create the job object
        job = trans.app.model.Job()
        job.session_id = trans.get_galaxy_session( create=True ).id
        if trans.get_history() is not None:
            job.history_id = trans.get_history().id
        job.tool_id = tool.id
        job.command_line = command_line
        job.param_filename = param_filename
        # FIXME: Don't need all of incoming here, just the defined parameters
        #        from the tool. We need to deal with tools that pass all post
        #        parameters to the command as a special case.
        for name, value in tool.params_to_strings( incoming, trans.app ).iteritems():
            job.add_parameter( name, value )
        for name, dataset in inp_data.iteritems():
            job.add_input_dataset( name, dataset )
        for name, dataset in out_data.iteritems():
            job.add_output_dataset( name, dataset )
        trans.app.model.flush()
        
        # Queue the job for execution
        trans.app.job_queue.put( job.id, tool )
        # IMPORTANT: keep the following event as is - we parse it for our session activity reports
        trans.log_event( "Added job to the job queue, id: %s" % str(job.id), tool_id=job.tool_id )
        return out_data
        
# ---- Utility classes to be factored out -----------------------------------

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
