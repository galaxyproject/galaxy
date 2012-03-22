from galaxy.model import LibraryDatasetDatasetAssociation
from galaxy.util.bunch import Bunch
from galaxy.util.odict import odict
from galaxy.util.json import to_json_string
from galaxy.tools.parameters import *
from galaxy.tools.parameters.grouping import *
from galaxy.util.template import fill_template
from galaxy.util.none_like import NoneDataset
from galaxy.web import url_for
from galaxy.exceptions import ObjectInvalid
import galaxy.tools
from types import *

import logging
log = logging.getLogger( __name__ )

class ToolAction( object ):
    """
    The actions to be taken when a tool is run (after parameters have
    been converted and validated).
    """
    def execute( self, tool, trans, incoming={}, set_output_hid=True ):
        raise TypeError("Abstract method")
    
class DefaultToolAction( object ):
    """Default tool action is to run an external command"""
    
    def collect_input_datasets( self, tool, param_values, trans ):
        """
        Collect any dataset inputs from incoming. Returns a mapping from 
        parameter name to Dataset instance for each tool parameter that is
        of the DataToolParameter type.
        """
        input_datasets = dict()
        def visitor( prefix, input, value, parent = None ):
            def process_dataset( data, formats = None ):
                if formats is None:
                    formats = input.formats
                if data and not isinstance( data.datatype, formats ):
                    # Need to refresh in case this conversion just took place, i.e. input above in tool performed the same conversion
                    trans.sa_session.refresh( data )
                    target_ext, converted_dataset = data.find_conversion_destination( formats )
                    if target_ext:
                        if converted_dataset:
                            data = converted_dataset
                        else:
                            #run converter here
                            new_data = data.datatype.convert_dataset( trans, data, target_ext, return_output = True, visible = False ).values()[0]
                            new_data.hid = data.hid
                            new_data.name = data.name
                            trans.sa_session.add( new_data )
                            assoc = trans.app.model.ImplicitlyConvertedDatasetAssociation( parent = data, file_type = target_ext, dataset = new_data, metadata_safe = False )
                            trans.sa_session.add( assoc )
                            trans.sa_session.flush()
                            data = new_data
                current_user_roles = trans.get_current_user_roles()
                if data and not trans.app.security_agent.can_access_dataset( current_user_roles, data.dataset ):
                    raise "User does not have permission to use a dataset (%s) provided for input." % data.id
                return data
            if isinstance( input, DataToolParameter ):
                if isinstance( value, list ):
                    # If there are multiple inputs with the same name, they
                    # are stored as name1, name2, ...
                    for i, v in enumerate( value ):
                        input_datasets[ prefix + input.name + str( i + 1 ) ] = process_dataset( v )
                        conversions = []
                        for conversion_name, conversion_extensions, conversion_datatypes in input.conversions:
                            new_data = process_dataset( input_datasets[ prefix + input.name + str( i + 1 ) ], conversion_datatypes )
                            if not new_data or isinstance( new_data.datatype, conversion_datatypes ):
                                input_datasets[ prefix + conversion_name + str( i + 1 ) ] = new_data
                                conversions.append( ( conversion_name, new_data ) )
                            else:
                                raise Exception, 'A path for explicit datatype conversion has not been found: %s --/--> %s' % ( input_datasets[ prefix + input.name + str( i + 1 ) ].extension, conversion_extensions )
                        if parent:
                            parent[input.name] = input_datasets[ prefix + input.name + str( i + 1 ) ]
                            for conversion_name, conversion_data in conversions:
                                #allow explicit conversion to be stored in job_parameter table
                                parent[ conversion_name ] = conversion_data.id #a more robust way to determine JSONable value is desired
                        else:
                            param_values[input.name][i] = input_datasets[ prefix + input.name + str( i + 1 ) ]
                            for conversion_name, conversion_data in conversions:
                                #allow explicit conversion to be stored in job_parameter table
                                param_values[ conversion_name ][i] = conversion_data.id #a more robust way to determine JSONable value is desired
                else:
                    input_datasets[ prefix + input.name ] = process_dataset( value )
                    conversions = []
                    for conversion_name, conversion_extensions, conversion_datatypes in input.conversions:
                        new_data = process_dataset( input_datasets[ prefix + input.name ], conversion_datatypes )
                        if not new_data or isinstance( new_data.datatype, conversion_datatypes ):
                            input_datasets[ prefix + conversion_name ] = new_data
                            conversions.append( ( conversion_name, new_data ) )
                        else:
                            raise Exception, 'A path for explicit datatype conversion has not been found: %s --/--> %s' % ( input_datasets[ prefix + input.name ].extension, conversion_extensions )
                    target_dict = parent
                    if not target_dict:
                        target_dict = param_values
                    target_dict[ input.name ] = input_datasets[ prefix + input.name ]
                    for conversion_name, conversion_data in conversions:
                        #allow explicit conversion to be stored in job_parameter table
                        target_dict[ conversion_name ] = conversion_data.id #a more robust way to determine JSONable value is desired
        tool.visit_inputs( param_values, visitor )
        return input_datasets

    def execute(self, tool, trans, incoming={}, return_job=False, set_output_hid=True, set_output_history=True, history=None, job_params=None ):
        """
        Executes a tool, creating job and tool outputs, associating them, and
        submitting the job to the job queue. If history is not specified, use
        trans.history as destination for tool's output datasets.
        """
        def make_dict_copy( from_dict ):
            """
            Makes a copy of input dictionary from_dict such that all values that are dictionaries
            result in creation of a new dictionary ( a sort of deepcopy ).  We may need to handle 
            other complex types ( e.g., lists, etc ), but not sure... 
            Yes, we need to handle lists (and now are)... 
            """
            copy_from_dict = {}
            for key, value in from_dict.items():
                if type( value ).__name__ == 'dict':
                    copy_from_dict[ key ] = make_dict_copy( value )
                elif isinstance( value, list ):
                    copy_from_dict[ key ] = make_list_copy( value )
                else:
                    copy_from_dict[ key ] = value
            return copy_from_dict
        def make_list_copy( from_list ):
            new_list = []
            for value in from_list:
                if isinstance( value, dict ):
                    new_list.append( make_dict_copy( value ) )
                elif isinstance( value, list ):
                    new_list.append( make_list_copy( value ) )
                else:
                    new_list.append( value )
            return new_list
        def wrap_values( inputs, input_values, skip_missing_values = False ):
            # Wrap tool inputs as necessary
            for input in inputs.itervalues():
                if input.name not in input_values and skip_missing_values:
                    continue
                if isinstance( input, Repeat ):
                    for d in input_values[ input.name ]:
                        wrap_values( input.inputs, d, skip_missing_values = skip_missing_values )
                elif isinstance( input, Conditional ):
                    values = input_values[ input.name ]
                    current = values[ "__current_case__" ]
                    wrap_values( input.cases[current].inputs, values, skip_missing_values = skip_missing_values )
                elif isinstance( input, DataToolParameter ):
                    input_values[ input.name ] = \
                        galaxy.tools.DatasetFilenameWrapper( input_values[ input.name ],
                                                             datatypes_registry = trans.app.datatypes_registry,
                                                             tool = tool,
                                                             name = input.name )
                elif isinstance( input, SelectToolParameter ):
                    input_values[ input.name ] = galaxy.tools.SelectToolParameterWrapper( input, input_values[ input.name ], tool.app, other_values = incoming )
                else:
                    input_values[ input.name ] = galaxy.tools.InputValueWrapper( input, input_values[ input.name ], incoming )
        
        # Set history.
        if not history:
            history = trans.history
        
        out_data = odict()
        # Collect any input datasets from the incoming parameters
        inp_data = self.collect_input_datasets( tool, incoming, trans )

        # Deal with input dataset names, 'dbkey' and types
        input_names = []
        input_ext = 'data'
        input_dbkey = incoming.get( "dbkey", "?" )
        for name, data in inp_data.items():
            if not data:
                data = NoneDataset( datatypes_registry = trans.app.datatypes_registry )
                continue
                
            # Convert LDDA to an HDA.
            if isinstance(data, LibraryDatasetDatasetAssociation):
                data = data.to_history_dataset_association( None )
                inp_data[name] = data
            
            else: # HDA
                if data.hid:
                    input_names.append( 'data %s' % data.hid )
            input_ext = data.ext
            
            if data.dbkey not in [None, '?']:
                input_dbkey = data.dbkey

        # Collect chromInfo dataset and add as parameters to incoming
        db_datasets = {}
        db_dataset = trans.db_dataset_for( input_dbkey )
        if db_dataset:
            db_datasets[ "chromInfo" ] = db_dataset
            incoming[ "chromInfo" ] = db_dataset.file_name
        else:
            # For custom builds, chrom info resides in converted dataset; for built-in builds, chrom info resides in tool-data/shared.
            chrom_info = None
            if trans.user and ( 'dbkeys' in trans.user.preferences ) and ( input_dbkey in from_json_string( trans.user.preferences[ 'dbkeys' ] ) ):
                # Custom build.
                custom_build_dict = from_json_string( trans.user.preferences[ 'dbkeys' ] )[ input_dbkey ]
                if 'fasta' in custom_build_dict:
                    build_fasta_dataset = trans.app.model.HistoryDatasetAssociation.get( custom_build_dict[ 'fasta' ] )
                    chrom_info = build_fasta_dataset.get_converted_dataset( trans, 'len' ).file_name
            
            if not chrom_info:
                # Default to built-in build.
                chrom_info = os.path.join( trans.app.config.tool_data_path, 'shared','ucsc','chrom', "%s.len" % input_dbkey )
            incoming[ "chromInfo" ] = chrom_info
        inp_data.update( db_datasets )
        
        # Determine output dataset permission/roles list
        existing_datasets = [ inp for inp in inp_data.values() if inp ]
        if existing_datasets:
            output_permissions = trans.app.security_agent.guess_derived_permissions_for_datasets( existing_datasets )
        else:
            # No valid inputs, we will use history defaults
            output_permissions = trans.app.security_agent.history_get_default_permissions( history )
        # Build name for output datasets based on tool name and input names
        if len( input_names ) == 1:
            on_text = input_names[0]
        elif len( input_names ) == 2:
            on_text = '%s and %s' % tuple(input_names[0:2])
        elif len( input_names ) == 3:
            on_text = '%s, %s, and %s' % tuple(input_names[0:3])
        elif len( input_names ) > 3:
            on_text = '%s, %s, and others' % tuple(input_names[0:2])
        else:
            on_text = ""
        # Add the dbkey to the incoming parameters
        incoming[ "dbkey" ] = input_dbkey
        params = None #wrapped params are used by change_format action and by output.label; only perform this wrapping once, as needed
        # Keep track of parent / child relationships, we'll create all the 
        # datasets first, then create the associations
        parent_to_child_pairs = []
        child_dataset_names = set()
        object_store_id = None
        for name, output in tool.outputs.items():
            for filter in output.filters:
                try:
                    if not eval( filter.text.strip(), globals(), incoming ):
                        break #do not create this dataset
                except Exception, e:
                    log.debug( 'Dataset output filter failed: %s' % e )
            else: #all filters passed
                if output.parent:
                    parent_to_child_pairs.append( ( output.parent, name ) )
                    child_dataset_names.add( name )
                ## What is the following hack for? Need to document under what 
                ## conditions can the following occur? (james@bx.psu.edu)
                # HACK: the output data has already been created
                #      this happens i.e. as a result of the async controller
                if name in incoming:
                    dataid = incoming[name]
                    data = trans.sa_session.query( trans.app.model.HistoryDatasetAssociation ).get( dataid )
                    assert data != None
                    out_data[name] = data
                else:
                    # the type should match the input
                    ext = output.format
                    if ext == "input":
                        ext = input_ext
                    if output.format_source is not None and output.format_source in inp_data:
                        try:
                            ext = inp_data[output.format_source].ext
                        except Exception, e:
                            pass
                    
                    #process change_format tags
                    if output.change_format:
                        if params is None:
                            params = make_dict_copy( incoming )
                            wrap_values( tool.inputs, params, skip_missing_values = not tool.check_values )
                        for change_elem in output.change_format:
                            for when_elem in change_elem.findall( 'when' ):
                                check = when_elem.get( 'input', None )
                                if check is not None:
                                    try:
                                        if '$' not in check:
                                            #allow a simple name or more complex specifications
                                            check = '${%s}' % check
                                        if str( fill_template( check, context = params ) ) == when_elem.get( 'value', None ):
                                            ext = when_elem.get( 'format', ext )
                                    except: #bad tag input value; possibly referencing a param within a different conditional when block or other nonexistent grouping construct
                                        continue
                                else:
                                    check = when_elem.get( 'input_dataset', None )
                                    if check is not None:
                                        check = inp_data.get( check, None )
                                        if check is not None:
                                            if str( getattr( check, when_elem.get( 'attribute' ) ) ) == when_elem.get( 'value', None ):
                                                ext = when_elem.get( 'format', ext )
                    data = trans.app.model.HistoryDatasetAssociation( extension=ext, create_dataset=True, sa_session=trans.sa_session )
                    if output.hidden:
                        data.visible = False
                    # Commit the dataset immediately so it gets database assigned unique id
                    trans.sa_session.add( data )
                    trans.sa_session.flush()
                    trans.app.security_agent.set_all_dataset_permissions( data.dataset, output_permissions )
                # Create an empty file immediately.  The first dataset will be
                # created in the "default" store, all others will be created in
                # the same store as the first.
                data.dataset.object_store_id = object_store_id
                try:
                    trans.app.object_store.create( data.dataset )
                except ObjectInvalid:
                    raise Exception('Unable to create output dataset: object store is full')
                object_store_id = data.dataset.object_store_id      # these will be the same thing after the first output
                # This may not be neccesary with the new parent/child associations
                data.designation = name
                # Copy metadata from one of the inputs if requested. 
                if output.metadata_source:
                    data.init_meta( copy_from=inp_data[output.metadata_source] )
                else:
                    data.init_meta()
                # Take dbkey from LAST input
                data.dbkey = str(input_dbkey)
                # Set state 
                # FIXME: shouldn't this be NEW until the job runner changes it?
                data.state = data.states.QUEUED
                data.blurb = "queued"
                # Set output label
                if output.label:
                    if params is None:
                        params = make_dict_copy( incoming )
                        # wrapping the params allows the tool config to contain things like
                        # <outputs>
                        #     <data format="input" name="output" label="Blat on ${<input_param>.name}" />
                        # </outputs>
                        wrap_values( tool.inputs, params, skip_missing_values = not tool.check_values )
                    #tool (only needing to be set once) and on_string (set differently for each label) are overwritten for each output dataset label being determined
                    params['tool'] = tool
                    params['on_string'] = on_text
                    data.name = fill_template( output.label, context=params )
                else:
                    data.name = tool.name 
                    if on_text:
                        data.name += ( " on " + on_text )
                # Store output 
                out_data[ name ] = data
                if output.actions:
                    #Apply pre-job tool-output-dataset actions; e.g. setting metadata, changing format
                    output_action_params = dict( out_data )
                    output_action_params.update( incoming )
                    output.actions.apply_action( data, output_action_params )
                # Store all changes to database
                trans.sa_session.flush()
        # Add all the top-level (non-child) datasets to the history unless otherwise specified
        for name in out_data.keys():
            if name not in child_dataset_names and name not in incoming: #don't add children; or already existing datasets, i.e. async created
                data = out_data[ name ]
                if set_output_history:
                    history.add_dataset( data, set_hid = set_output_hid )
                trans.sa_session.add( data )
                trans.sa_session.flush()
        # Add all the children to their parents
        for parent_name, child_name in parent_to_child_pairs:
            parent_dataset = out_data[ parent_name ]
            child_dataset = out_data[ child_name ]
            parent_dataset.children.append( child_dataset )
        # Store data after custom code runs 
        trans.sa_session.flush()
        # Create the job object
        job = trans.app.model.Job()
        galaxy_session = trans.get_galaxy_session()
        # If we're submitting from the API, there won't be a session.
        if type( galaxy_session ) == trans.model.GalaxySession:
            job.session_id = galaxy_session.id
        if trans.user is not None:
            job.user_id = trans.user.id
        job.history_id = history.id
        job.tool_id = tool.id
        try:
            # For backward compatibility, some tools may not have versions yet.
            job.tool_version = tool.version
        except:
            job.tool_version = "1.0.0"
        # FIXME: Don't need all of incoming here, just the defined parameters
        #        from the tool. We need to deal with tools that pass all post
        #        parameters to the command as a special case.
        for name, value in tool.params_to_strings( incoming, trans.app ).iteritems():
            job.add_parameter( name, value )
        current_user_roles = trans.get_current_user_roles()
        for name, dataset in inp_data.iteritems():
            if dataset:
                if not trans.app.security_agent.can_access_dataset( current_user_roles, dataset.dataset ):
                    raise "User does not have permission to use a dataset (%s) provided for input." % data.id
                job.add_input_dataset( name, dataset )
            else:
                job.add_input_dataset( name, None )
        for name, dataset in out_data.iteritems():
            job.add_output_dataset( name, dataset )
        job.object_store_id = object_store_id
        if job_params:
            job.params = to_json_string( job_params )
        trans.sa_session.add( job )
        trans.sa_session.flush()
        # Some tools are not really executable, but jobs are still created for them ( for record keeping ).
        # Examples include tools that redirect to other applications ( epigraph ).  These special tools must
        # include something that can be retrieved from the params ( e.g., REDIRECT_URL ) to keep the job
        # from being queued.
        if 'REDIRECT_URL' in incoming:
            # Get the dataset - there should only be 1
            for name in inp_data.keys():
                dataset = inp_data[ name ]
            redirect_url = tool.parse_redirect_url( dataset, incoming )
            # GALAXY_URL should be include in the tool params to enable the external application 
            # to send back to the current Galaxy instance
            GALAXY_URL = incoming.get( 'GALAXY_URL', None )
            assert GALAXY_URL is not None, "GALAXY_URL parameter missing in tool config."
            redirect_url += "&GALAXY_URL=%s" % GALAXY_URL
            # Job should not be queued, so set state to ok
            job.state = trans.app.model.Job.states.OK
            job.info = "Redirected to: %s" % redirect_url
            trans.sa_session.add( job )
            trans.sa_session.flush()
            trans.response.send_redirect( url_for( controller='tool_runner', action='redirect', redirect_url=redirect_url ) )
        else:
            # Queue the job for execution
            trans.app.job_queue.put( job.id, tool )
            trans.log_event( "Added job to the job queue, id: %s" % str(job.id), tool_id=job.tool_id )
            return job, out_data
