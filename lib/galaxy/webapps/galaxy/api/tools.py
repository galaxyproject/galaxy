import urllib

from galaxy import exceptions
from galaxy import web, util
from galaxy.web import _future_expose_api_anonymous
from galaxy.web.base.controller import BaseAPIController
from galaxy.web.base.controller import UsesVisualizationMixin
from galaxy.web.base.controller import UsesHistoryMixin
from galaxy.visualization.genomes import GenomeRegion
from galaxy.util.json import dumps
from galaxy.visualization.data_providers.genome import *

from galaxy.managers.collections_util import dictify_dataset_collection_instance

import logging
log = logging.getLogger( __name__ )


class ToolsController( BaseAPIController, UsesVisualizationMixin, UsesHistoryMixin ):
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
        try:
            return self.app.toolbox.to_dict( trans, in_panel=in_panel, trackster=trackster)
        except Exception, exc:
            log.error( 'could not convert toolbox to dictionary: %s', str( exc ), exc_info=True )
            trans.response.status = 500
            return { 'error': str( exc ) }

    @_future_expose_api_anonymous
    def show( self, trans, id, **kwd ):
        """
        GET /api/tools/{tool_id}
        Returns tool information, including parameters and inputs.
        """
        io_details = util.string_as_bool( kwd.get( 'io_details', False ) )
        link_details = util.string_as_bool( kwd.get( 'link_details', False ) )
        tool = self._get_tool( id )
        return tool.to_dict( trans, io_details=io_details, link_details=link_details )

    @_future_expose_api_anonymous
    def citations( self, trans, id, **kwds ):
        tool = self._get_tool( id )
        rval = []
        for citation in tool.citations:
            rval.append( citation.to_dict( 'bibtex' ) )
        return rval

    @web.expose_api_anonymous
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
        tool = trans.app.toolbox.get_tool( payload[ 'tool_id' ] ) if 'tool_id' in payload else None
        if not tool:
            trans.response.status = 404
            return { "message": { "type": "error", "text" : trans.app.model.Dataset.conversion_messages.NO_TOOL } }

        # Set running history from payload parameters.
        # History not set correctly as part of this API call for
        # dataset upload.
        history_id = payload.get("history_id", None)
        if history_id:
            target_history = self.get_history( trans, history_id )
        else:
            target_history = None

        # Set up inputs.
        inputs = payload.get( 'inputs', {} )
        # Find files coming in as multipart file data and add to inputs.
        for k, v in payload.iteritems():
            if k.startswith("files_") or k.startswith("__files_"):
                inputs[k] = v

        #for inputs that are coming from the Library, copy them into the history
        input_patch = {}
        for k, v in inputs.iteritems():
            if  isinstance(v, dict) and v.get('src', '') == 'ldda' and 'id' in v:
                ldda = trans.sa_session.query( trans.app.model.LibraryDatasetDatasetAssociation ).get( trans.security.decode_id(v['id']) )
                if trans.user_is_admin() or trans.app.security_agent.can_access_dataset( trans.get_current_user_roles(), ldda.dataset ):
                    input_patch[k] = ldda.to_history_dataset_association(target_history, add_to_history=True)

        for k, v in input_patch.iteritems():
            inputs[k] = v

        # HACK: add run button so that tool.handle_input will run tool.
        inputs['runtool_btn'] = 'Execute'
        # TODO: encode data ids and decode ids.
        # TODO: handle dbkeys
        params = util.Params( inputs, sanitize=False )
        # process_state will be 'populate' or 'update'. When no tool
        # state is specified in input - it will be 'populate', and
        # tool will fully expand repeat and conditionals when building
        # up state. If tool state is found in input
        # parameters,process_state will be 'update' and complex
        # submissions (with repeats and conditionals) must be built up
        # over several iterative calls to the API - mimicing behavior
        # of web controller (though frankly API never returns
        # tool_state so this "legacy" behavior is probably impossible
        # through API currently).
        incoming = params.__dict__
        process_state = "update" if "tool_state" in incoming else "populate"
        template, vars = tool.handle_input( trans, incoming, history=target_history, process_state=process_state, source="json" )
        if 'errors' in vars:
            trans.response.status = 400
            return { "message": { "type": "error", "data" : vars[ 'errors' ] } }

        # TODO: check for errors and ensure that output dataset(s) are available.
        output_datasets = vars.get( 'out_data', [] )
        rval = {
            "outputs": [],
            "jobs": [],
            "implicit_collections": [],
        }

        job_errors = vars.get( 'job_errors', [] )
        if job_errors:
            # If we are here - some jobs were successfully executed but some failed.
            rval[ "errors" ] = job_errors

        outputs = rval[ "outputs" ]
        #TODO:?? poss. only return ids?
        for output_name, output in output_datasets:
            output_dict = output.to_dict()
            #add the output name back into the output data structure
            #so it's possible to figure out which newly created elements
            #correspond with which tool file outputs
            output_dict[ 'output_name' ] = output_name
            outputs.append( trans.security.encode_dict_ids( output_dict ) )

        for job in vars.get('jobs', []):
            rval[ 'jobs' ].append( self.encode_all_ids( trans, job.to_dict( view='collection' ), recursive=True ) )

        for output_name, collection_instance in vars.get( 'implicit_collections', {} ).iteritems():
            history = target_history or trans.history
            output_dict = dictify_dataset_collection_instance( collection_instance, security=trans.security, parent=history )
            output_dict[ 'output_name' ] = output_name
            rval[ 'implicit_collections' ].append( output_dict )

        return rval

    #
    # -- Helper methods --
    #
    def _get_tool( self, id ):
        id = urllib.unquote_plus( id )
        tool = self.app.toolbox.get_tool( id )
        if not tool:
            raise exceptions.ObjectNotFound("Could not find tool with id '%s'" % id)
        return tool

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
                    regions = sorted(regions, key=lambda r: (r.chrom.lower(), r.start))

                    # Merge overlapping regions so that regions do not overlap
                    # and hence data is not included multiple times.
                    prev = regions[0]
                    cur = regions[1]
                    index = 1
                    while True:
                        if cur.chrom == prev.chrom and cur.start <= prev.end:
                            # Found overlapping regions, so join them into prev.
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
            return msg

        #
        # Set tool parameters--except non-hidden dataset parameters--using combination of
        # job's previous parameters and incoming parameters. Incoming parameters
        # have priority.
        #
        original_job = self.get_hda_job( original_dataset )
        tool = trans.app.toolbox.get_tool( original_job.tool_id )
        if not tool:
            return trans.app.model.Dataset.conversion_messages.NO_TOOL
        tool_params = dict( [ ( p.name, p.value ) for p in original_job.parameters ] )

        # TODO: rather than set new inputs using dict of json'ed value, unpack parameters and set using set_param_value below.
        # TODO: need to handle updates to conditional parameters; conditional
        # params are stored in dicts (and dicts within dicts).
        new_inputs = payload[ 'inputs' ]
        tool_params.update( dict( [ ( key, dumps( value ) ) for key, value in new_inputs.items() if key in tool.inputs and new_inputs[ key ] is not None ] ) )
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
                if data_provider and ( not data_provider.converted_dataset
                                       or data_provider.converted_dataset.state != trans.app.model.Dataset.states.OK ):
                    # Can convert but no converted dataset yet, so return message about why.
                    data_sources = input_dataset.datatype.data_sources
                    msg = input_dataset.convert_dataset( trans, data_sources[ 'data' ] )
                    if msg is not None:
                        messages_list.append( msg )

        # Return any messages generated during conversions.
        return_message = self._get_highest_priority_msg( messages_list )
        if return_message:
            return return_message

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
                    for value in param_dict.values():
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
            if input_dataset is None:  # optional dataset and dataset wasn't selected
                tool_params[ jida.name ] = None
            elif run_on_regions and 'data' in input_dataset.datatype.data_sources:
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
                    data_source = input_dataset.datatype.data_sources[ 'data' ]
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
                    trans.app.datatypes_registry.set_external_metadata_tool.tool_action.execute( trans.app.datatypes_registry.set_external_metadata_tool,
                                                                                                 trans, incoming={ 'input1': new_dataset },
                                                                                                 overwrite=False, job_params={ "source" : "trackster" } )
                    # Add HDA subset association.
                    subset_association = trans.app.model.HistoryDatasetAssociationSubset( hda=input_dataset, subset=new_dataset, location=regions_str )
                    trans.sa_session.add( subset_association )

                    subset_dataset = new_dataset

                trans.sa_session.flush()

                # Add dataset to tool's parameters.
                if not set_param_value( tool_params, jida.name, subset_dataset ):
                    return { "error" : True, "message" : "error setting parameter %s" % jida.name }

        #
        # Execute tool and handle outputs.
        #
        try:
            subset_job, subset_job_outputs = tool.execute( trans, incoming=tool_params,
                                                           history=target_history,
                                                           job_params={ "source" : "trackster" } )
        except Exception, e:
            # Lots of things can go wrong when trying to execute tool.
            return { "error" : True, "message" : e.__class__.__name__ + ": " + str(e) }
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

        dataset_dict = output_dataset.to_dict()
        dataset_dict[ 'id' ] = trans.security.encode_id( dataset_dict[ 'id' ] )
        dataset_dict[ 'track_config' ] = self.get_new_track_config( trans, output_dataset )
        return dataset_dict
