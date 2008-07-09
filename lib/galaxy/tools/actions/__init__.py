from galaxy.util.bunch import Bunch
from galaxy.tools.parameters import *
from galaxy.util.template import fill_template
from galaxy.util.none_like import NoneDataset

import logging
log = logging.getLogger( __name__ )

class ToolAction( object ):
    """
    The actions to be taken when a tool is run (after parameters have
    been converted and validated).
    """
    def execute( self, tool, trans, incoming={} ):
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
            def process_dataset( data ):
                if data and not isinstance( data.datatype, input.formats ):
                    for target_ext in input.extensions:
                        if target_ext in data.get_converter_types():
                            data.refresh() #need to refresh incase this conversion just took place, i.e. input above in tool performed the same conversion
                            datasets = data.get_converted_files_by_type( target_ext )
                            if datasets: data = datasets[0]
                            elif input.converter_safe( param_values, trans ):
                                #run converter here
                                assoc = trans.app.model.ImplicitlyConvertedDatasetAssociation( parent = data, file_type = target_ext, metadata_safe = False )
                                new_data = data.datatype.convert_dataset( trans, data, target_ext, return_output = True, visible = False ).values()[0]
                                new_data.hid = data.hid
                                new_data.name = data.name
                                new_data.flush()
                                assoc.dataset = new_data
                                assoc.flush()
                                data = new_data
                            break
                return data
            if isinstance( input, DataToolParameter ):
                if isinstance( value, list ):
                    # If there are multiple inputs with the same name, they
                    # are stored as name1, name2, ...
                    for i, v in enumerate( value ):
                        input_datasets[ prefix + input.name + str( i + 1 ) ] = process_dataset( v )
                        if parent:
                            parent[input.name] = input_datasets[ prefix + input.name + str( i + 1 ) ]
                        else:
                            param_values[input.name][i] = input_datasets[ prefix + input.name + str( i + 1 ) ]
                else:
                    input_datasets[ prefix + input.name ] = process_dataset( value )
                    if parent:
                        parent[input.name] = input_datasets[ prefix + input.name ]
                    else:
                        param_values[input.name] = input_datasets[ prefix + input.name ]
        tool.visit_inputs( param_values, visitor )
        return input_datasets
    
    def execute(self, tool, trans, incoming={}, set_output_hid = True ):
        out_data   = {}
        
        # Collect any input datasets from the incoming parameters
        inp_data = self.collect_input_datasets( tool, incoming, trans )
        
        # Deal with input metadata, 'dbkey', names, and types
        
        # FIXME: does this need to modify 'incoming' or should this be 
        #        moved into 'build_param_dict'? Is this just about getting the
        #        metadata into the command line?
        # NEED TO FIX THIS SOON.
        input_names = []
        input_ext = 'data'
        input_dbkey = incoming.get( "dbkey", "?" )
        input_meta = Bunch()
        for name, data in inp_data.items():
            if data:
                input_names.append( 'data %s' % data.hid )
                input_ext = data.ext
            else:
                data = NoneDataset( datatypes_registry = trans.app.datatypes_registry )
            if data.dbkey not in [None, '?']:
                input_dbkey = data.dbkey
            for meta_key, meta_value in data.metadata.items():
                if meta_value is not None:
                    meta_value = str(data.datatype.metadata_spec[meta_key].wrap(meta_value, data))
                    meta_key = '%s_%s' % (name, meta_key)
                    incoming[meta_key] = meta_value
                else:
                    incoming_key = '%s_%s' % (name, meta_key)
                    incoming[incoming_key] = data.datatype.metadata_spec[meta_key].no_value

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
        
        # Keep track of parent / child relationships, we'll create all the 
        # datasets first, then create the associations
        parent_to_child_pairs = []
        child_dataset_names = set()
        
        for name, output in tool.outputs.items():
            if output.parent:
                parent_to_child_pairs.append( ( output.parent, name ) )
                child_dataset_names.add( name )
            ## What is the following hack for? Need to document under what 
            ## conditions can the following occur? (james@bx.psu.edu)
            # HACK: the output data has already been created
            #      this happens i.e. as a result of the async controller
            if name in incoming:
                dataid = incoming[name]
                data = trans.app.model.HistoryDatasetAssociation.get( dataid )
                assert data != None
                out_data[name] = data
            else:
                # the type should match the input
                ext = output.format
                if ext == "input":
                    ext = input_ext
                data = trans.app.model.HistoryDatasetAssociation( extension=ext, create_dataset=True )
                # Commit the dataset immediately so it gets database assigned unique id
                data.flush()
            # Create an empty file immediately
            open( data.file_name, "w" ).close()
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
                params = dict( incoming )
                params['tool'] = tool
                params['on_string'] = on_text
                data.name = fill_template( output.label, context=params )
            else:
                data.name = tool.name 
                if on_text:
                    data.name += ( " on " + on_text )
            # Store output 
            out_data[ name ] = data
            # Store all changes to database
            trans.app.model.flush()
            
        # Add all the top-level (non-child) datasets to the history
        for name in out_data.keys():
            if name not in child_dataset_names and name not in incoming: #don't add children; or already existing datasets, i.e. async created
                data = out_data[ name ]
                trans.history.add_dataset( data, set_hid = set_output_hid )
                data.flush()
                
        # Add all the children to their parents
        for parent_name, child_name in parent_to_child_pairs:
            parent_dataset = out_data[ parent_name ]
            child_dataset = out_data[ child_name ]
            parent_dataset.children.append( child_dataset )
            
        # Store data after custom code runs 
        trans.app.model.flush()
        
        # Create the job object
        job = trans.app.model.Job()
        job.session_id = trans.get_galaxy_session( create=True ).id
        if trans.get_history() is not None:
            job.history_id = trans.get_history().id
        job.tool_id = tool.id
        try:
            # For backward compatability, some tools may not have versions yet.
            job.tool_version = tool.version
        except:
            job.tool_version = "1.0.0"
        ## job.command_line = command_line
        ## job.param_filename = param_filename
        # FIXME: Don't need all of incoming here, just the defined parameters
        #        from the tool. We need to deal with tools that pass all post
        #        parameters to the command as a special case.
        for name, value in tool.params_to_strings( incoming, trans.app ).iteritems():
            job.add_parameter( name, value )
        for name, dataset in inp_data.iteritems():
            if dataset:
                job.add_input_dataset( name, dataset )
            else:
                job.add_input_dataset( name, None )
        for name, dataset in out_data.iteritems():
            job.add_output_dataset( name, dataset )
        trans.app.model.flush()
        
        # Queue the job for execution
        trans.app.job_queue.put( job.id, tool )
        # IMPORTANT: keep the following event as is - we parse it for our session activity reports
        trans.log_event( "Added job to the job queue, id: %s" % str(job.id), tool_id=job.tool_id )
        return out_data
