from galaxy import web, util
from galaxy.web.base.controller import BaseAPIController, UsesHistoryDatasetAssociationMixin, UsesVisualizationMixin
from galaxy.visualization.genome.visual_analytics import get_dataset_job
from galaxy.visualization.genomes import GenomeRegion
from galaxy.util.json import to_json_string, from_json_string
from galaxy.visualization.data_providers.genome import *

class ToolsController( BaseAPIController, UsesVisualizationMixin ):
    """
    RESTful controller for interactions with tools.
    """
    
    @web.expose_api
    def index( self, trans, **kwds ):
        """
        GET /api/tools: returns a list of tools defined by parameters::

            parameters:

                in_panel  - if true, tools are returned in panel structure, 
                            including sections and labels
                trackster - if true, only tools that are compatible with 
                            Trackster are returned

        """
        
        # Read params.
        in_panel = util.string_as_bool( kwds.get( 'in_panel', 'True' ) )
        trackster = util.string_as_bool( kwds.get( 'trackster', 'False' ) )
        
        # Create return value.
        return self.app.toolbox.to_dict( trans, in_panel=in_panel, trackster=trackster )

    @web.expose_api
    def show( self, trans, id, **kwd ):
        """
        GET /api/tools/{tool_id}
        Returns tool information, including parameters and inputs.
        """
        return self.app.toolbox.tools_by_id[ id ].to_dict( trans, for_display=True )
        
    @web.expose_api
    def create( self, trans, payload, **kwd ):
        """
        POST /api/tools
        Executes tool using specified inputs and returns tool's outputs.
        """
        
        # HACK: for now, if action is rerun, rerun tool.
        action = payload.get( 'action', None )
        if action == 'rerun':
            return self._rerun_tool( trans, payload, **kwd )
        
        # -- Execute tool. --
        
        # Get tool.
        tool_id = payload[ 'tool_id' ]
        tool = trans.app.toolbox.get_tool( tool_id )
        if not tool:
            return { "message": { "type": "error", "text" : trans.app.model.Dataset.conversion_messages.NO_TOOL } }

        # Set running history from payload parameters.
        # History not set correctly as part of this API call for
        # dataset upload.
        history_id = payload.get("history_id", None)
        if history_id:
            target_history = trans.sa_session.query(trans.app.model.History).get(
                trans.security.decode_id(history_id))
            trans.galaxy_session.current_history = target_history
        else:
            target_history = None
        
        # Set up inputs.
        inputs = payload[ 'inputs' ]
        # HACK: add run button so that tool.handle_input will run tool.
        inputs['runtool_btn'] = 'Execute'
        # TODO: encode data ids and decode ids.
        params = util.Params( inputs, sanitize = False )
        template, vars = tool.handle_input( trans, params.__dict__, history=target_history)

        # TODO: check for errors and ensure that output dataset(s) are available.
        output_datasets = vars.get('out_data', {}).values()
        rval = {
            "outputs": []
        }
        outputs = rval[ "outputs" ]
        for output in output_datasets:
            outputs.append( output.get_api_value() )
        return rval
        
    #
    # -- Helper methods --
    #
    
    def _run_tool( self, trans, tool_id, target_dataset_id, **kwargs ):
        """
        Run a tool. This method serves as a general purpose way to run tools asynchronously.
        """

        #
        # Set target history (the history that tool will use for outputs) using
        # target dataset. If user owns dataset, put new data in original 
        # dataset's history; if user does not own dataset (and hence is accessing
        # dataset via sharing), put new data in user's current history.
        #
        target_dataset = self.get_dataset( trans, target_dataset_id, check_ownership=False, check_accessible=True )
        if target_dataset.history.user == trans.user:
            target_history = target_dataset.history
        else:
            target_history = trans.get_history( create=True )

        # HACK: tools require unencoded parameters but kwargs are typically 
        # encoded, so try decoding all parameter values.
        for key, value in kwargs.items():
            try:
                value = trans.security.decode_id( value )
                kwargs[ key ] = value
            except:
                pass

        #        
        # Execute tool.
        #
        tool = trans.app.toolbox.get_tool( tool_id )
        if not tool:
            return trans.app.model.Dataset.conversion_messages.NO_TOOL

        # HACK: add run button so that tool.handle_input will run tool.
        kwargs['runtool_btn'] = 'Execute'
        params = util.Params( kwargs, sanitize = False )
        template, vars = tool.handle_input( trans, params.__dict__, history=target_history )

        # TODO: check for errors and ensure that output dataset is available.
        output_datasets = vars[ 'out_data' ].values()
        return self.add_track_async( trans, output_datasets[0].id )

    
    def _rerun_tool( self, trans, payload, **kwargs ):
        """
        Rerun a tool to produce a new output dataset that corresponds to a 
        dataset that a user is currently viewing.
        """

        #
        # TODO: refactor to use same code as run_tool.
        #        

        # Run tool on region if region is specificied.
        run_on_regions = False
        regions = payload.get( 'regions', None )
        if regions:
            if isinstance( regions, dict ):
                # Regions is a single region.
                regions = [ GenomeRegion.from_dict( regions ) ]
            elif isinstance( regions, list ):
                # There is a list of regions.
                regions = [ GenomeRegion.from_dict( r ) for r in regions ]

                if len( regions ) > 1:
                    # Sort by chrom name, start so that data is not fetched out of order.
                    regions.sort( key=lambda r: r.chrom )
                    regions.sort( key=lambda r: r.start )

                    # Merge overlapping regions so that regions do not overlap 
                    # and hence data is not included multiple times.
                    prev = regions[0]
                    cur = regions[1]
                    index = 1
                    while True:
                        if cur.start <= prev.end:
                            # Found overlapping regions, so join them.
                            prev.end = cur.end
                            del regions[ index ]
                        else:
                            # No overlap, move to next region.
                            prev = cur
                            index += 1

                        # Get next region or exit.    
                        if index == len( regions ):
                            # Done.
                            break
                        else:
                            cur = regions[ index ]
            
            run_on_regions = True
            
        # Dataset check.
        original_dataset = self.get_dataset( trans, payload[ 'target_dataset_id' ], check_ownership=False, check_accessible=True )
        msg = self.check_dataset_state( trans, original_dataset )
        if msg:
            return to_json_string( msg )

        #
        # Set tool parameters--except non-hidden dataset parameters--using combination of
        # job's previous parameters and incoming parameters. Incoming parameters
        # have priority.
        #
        original_job = get_dataset_job( original_dataset )
        tool = trans.app.toolbox.get_tool( original_job.tool_id )
        if not tool:
            return trans.app.model.Dataset.conversion_messages.NO_TOOL
        tool_params = dict( [ ( p.name, p.value ) for p in original_job.parameters ] )
        
        # TODO: rather than set new inputs using dict of json'ed value, unpack parameters and set using set_param_value below.
        # TODO: need to handle updates to conditional parameters; conditional 
        # params are stored in dicts (and dicts within dicts).
        new_inputs = payload[ 'inputs' ]
        tool_params.update( dict( [ ( key, to_json_string( value ) ) for key, value in new_inputs.items() if key in tool.inputs and new_inputs[ key ] is not None ] ) )
        tool_params = tool.params_from_strings( tool_params, self.app )

        #
        # If running tool on region, convert input datasets (create indices) so
        # that can regions of data can be quickly extracted.
        # 
        data_provider_registry = trans.app.data_provider_registry
        messages_list = []
        if run_on_regions:
            for jida in original_job.input_datasets:
                input_dataset = jida.dataset
                data_provider = data_provider_registry.get_data_provider( trans, original_dataset=input_dataset, source='data' )
                if data_provider:
                    if not data_provider.converted_dataset:
                        msg = self.convert_dataset( trans, input_dataset, data_source )
                        if msg is not None:
                            messages_list.append( msg )

        # Return any messages generated during conversions.
        return_message = self._get_highest_priority_msg( messages_list )
        if return_message:
            return to_json_string( return_message )

        #
        # Set target history (the history that tool will use for inputs/outputs).
        # If user owns dataset, put new data in original dataset's history; if 
        # user does not own dataset (and hence is accessing dataset via sharing), 
        # put new data in user's current history.
        #
        if original_dataset.history.user == trans.user:
            target_history = original_dataset.history
        else:
            target_history = trans.get_history( create=True )
        hda_permissions = trans.app.security_agent.history_get_default_permissions( target_history )

        def set_param_value( param_dict, param_name, param_value ):
            """
            Set new parameter value in a tool's parameter dictionary.
            """

            # Recursive function to set param value.
            def set_value( param_dict, group_name, group_index, param_name, param_value ):
                if group_name in param_dict:
                    param_dict[ group_name ][ group_index ][ param_name ] = param_value
                    return True
                elif param_name in param_dict:
                    param_dict[ param_name ] = param_value
                    return True
                else:
                    # Recursive search.
                    return_val = False
                    for name, value in param_dict.items():
                        if isinstance( value, dict ):
                            return_val = set_value( value, group_name, group_index, param_name, param_value)
                            if return_val:
                                return return_val
                    return False

            # Parse parameter name if necessary.
            if param_name.find( "|" ) == -1:
                # Non-grouping parameter.
                group_name = group_index = None
            else:
                # Grouping parameter.
                group, param_name = param_name.split( "|" )
                index = group.rfind( "_" )
                group_name = group[ :index ]
                group_index = int( group[ index + 1: ] )

            return set_value( param_dict, group_name, group_index, param_name, param_value )

        # Set parameters based tool's trackster config.
        params_set = {}
        for action in tool.trackster_conf.actions:
            success = False
            for joda in original_job.output_datasets:
                if joda.name == action.output_name:
                    set_param_value( tool_params, action.name, joda.dataset )
                    params_set[ action.name ] = True
                    success = True
                    break

            if not success:
                return trans.app.model.Dataset.conversion_messages.ERROR

        #
        # Set input datasets for tool. If running on regions, extract and use subset
        # when possible.
        #
        if run_on_regions:
            regions_str = ",".join( [ str( r ) for r in regions ] )
        for jida in original_job.input_datasets:
            # If param set previously by config actions, do nothing.
            if jida.name in params_set:
                continue

            input_dataset = jida.dataset
            if input_dataset is None: #optional dataset and dataset wasn't selected
                tool_params[ jida.name ] = None
            elif run_on_regions and hasattr( input_dataset.datatype, 'get_track_type' ):
                # Dataset is indexed and hence a subset can be extracted and used
                # as input.

                # Look for subset.
                subset_dataset_association = trans.sa_session.query( trans.app.model.HistoryDatasetAssociationSubset ) \
                                                             .filter_by( hda=input_dataset, location=regions_str ) \
                                                             .first()
                if subset_dataset_association:
                    # Data subset exists.
                    subset_dataset = subset_dataset_association.subset
                else:
                    # Need to create subset.
                    track_type, data_sources = input_dataset.datatype.get_track_type()
                    data_source = data_sources[ 'data' ]
                    converted_dataset = input_dataset.get_converted_dataset( trans, data_source )
                    deps = input_dataset.get_converted_dataset_deps( trans, data_source )

                    # Create new HDA for input dataset's subset.
                    new_dataset = trans.app.model.HistoryDatasetAssociation( extension=input_dataset.ext, \
                                                                             dbkey=input_dataset.dbkey, \
                                                                             create_dataset=True, \
                                                                             sa_session=trans.sa_session,
                                                                             name="Subset [%s] of data %i" % \
                                                                                 ( regions_str, input_dataset.hid ),
                                                                             visible=False )
                    target_history.add_dataset( new_dataset )
                    trans.sa_session.add( new_dataset )
                    trans.app.security_agent.set_all_dataset_permissions( new_dataset.dataset, hda_permissions )

                    # Write subset of data to new dataset
                    data_provider = data_provider_registry.get_data_provider( trans, original_dataset=input_dataset, source='data' )
                    trans.app.object_store.create( new_dataset.dataset )
                    data_provider.write_data_to_file( regions, new_dataset.file_name )

                    # TODO: (a) size not working; (b) need to set peek.
                    new_dataset.set_size()
                    new_dataset.info = "Data subset for trackster"
                    new_dataset.set_dataset_state( trans.app.model.Dataset.states.OK )

                    # Set metadata.
                    # TODO: set meta internally if dataset is small enough?
                    if trans.app.config.set_metadata_externally:
                        trans.app.datatypes_registry.set_external_metadata_tool.tool_action.execute( trans.app.datatypes_registry.set_external_metadata_tool, 
                                                                                                     trans, incoming = { 'input1':new_dataset }, 
                                                                                                     overwrite=False, job_params={ "source" : "trackster" } )
                    else:
                        message = 'Attributes updated'
                        new_dataset.set_meta()
                        new_dataset.datatype.after_setting_metadata( new_dataset )

                    # Add HDA subset association.
                    subset_association = trans.app.model.HistoryDatasetAssociationSubset( hda=input_dataset, subset=new_dataset, location=regions_str )
                    trans.sa_session.add( subset_association )

                    subset_dataset = new_dataset

                trans.sa_session.flush()

                # Add dataset to tool's parameters.
                if not set_param_value( tool_params, jida.name, subset_dataset ):
                    return to_json_string( { "error" : True, "message" : "error setting parameter %s" % jida.name } )

        #        
        # Execute tool and handle outputs.
        #
        try:
            subset_job, subset_job_outputs = tool.execute( trans, incoming=tool_params, 
                                                           history=target_history, 
                                                           job_params={ "source" : "trackster" } )
        except Exception, e:
            # Lots of things can go wrong when trying to execute tool.
            return to_json_string( { "error" : True, "message" : e.__class__.__name__ + ": " + str(e) } )
        if run_on_regions:
            for output in subset_job_outputs.values():
                output.visible = False
            trans.sa_session.flush()

        #    
        # Return new track that corresponds to the original dataset.
        #
        output_name = None
        for joda in original_job.output_datasets:
            if joda.dataset == original_dataset:
                output_name = joda.name
                break
        for joda in subset_job.output_datasets:
            if joda.name == output_name:
                output_dataset = joda.dataset
        
        dataset_dict = output_dataset.get_api_value()
        dataset_dict[ 'id' ] = trans.security.encode_id( dataset_dict[ 'id' ] )
        dataset_dict[ 'track_config' ] = self.get_new_track_config( trans, output_dataset );
        return dataset_dict
