from cookbook.patterns import Bunch
from galaxy.tools.parameters import *

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
    
    def collect_input_datasets( self, tool, param_values ):
        """
        Collect any dataset inputs from incoming. Returns a mapping from 
        parameter name to Dataset instance for each tool parameter that is
        of the DataToolParameter type.
        """
        input_datasets = dict()
        def visitor( prefix, input, value ):
            if isinstance( input, DataToolParameter ):
                if isinstance( value, list ):
                    # If there are multiple inputs with the same name, they
                    # are stored as name1, name2, ...
                    for i, v in enumerate( value ):
                        input_datasets[ prefix + input.name + str( i + 1 ) ] = v
                else:
                    input_datasets[ prefix + input.name ] = value
        tool.visit_inputs( param_values, visitor )
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
                else:
                    incoming_key = '%s_%s' % (name, meta_key)
                    incoming[incoming_key] = data.datatype.metadata_spec[meta_key].no_value

        # Build name for output datasets based on tool name and input names
        output_base_name = tool.name
        if len( input_names ) == 1:
            output_base_name += ' on ' + input_names[0]
        elif len( input_names ) == 2:
            output_base_name += ' on %s and %s' % tuple(input_names[0:2])
        elif len( input_names ) == 3:
            output_base_name += ' on %s, %s, and %s' % tuple(input_names[0:3])
        elif len( input_names ) > 3:
            output_base_name += ' on %s, %s, and others' % tuple(input_names[0:2])
        
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
            data = trans.app.model.Dataset(extension=ext)
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
            #data.extension = ext
            # Copy metadata from one of the inputs if requested. 
            if metadata_source:
                data.init_meta( copy_from=inp_data[metadata_source] )
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
        
        # Create the job object
        job = trans.app.model.Job()
        job.session_id = trans.get_galaxy_session( create=True ).id
        if trans.get_history() is not None:
            job.history_id = trans.get_history().id
        job.tool_id = tool.id
        ## job.command_line = command_line
        ## job.param_filename = param_filename
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
