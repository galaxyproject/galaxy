import urllib

from galaxy import exceptions
from galaxy import web, util
from galaxy import managers
from galaxy.web import _future_expose_api_anonymous
from galaxy.web import _future_expose_api
from galaxy.web.base.controller import BaseAPIController
from galaxy.web.base.controller import UsesVisualizationMixin
from galaxy.visualization.genomes import GenomeRegion
from galaxy.util.json import dumps
from galaxy.visualization.data_providers.genome import *
from galaxy.tools.parameters import params_to_incoming, check_param
from galaxy.tools.parameters import visit_input_values
from galaxy.tools.parameters.meta import expand_meta_parameters
from galaxy.managers.collections_util import dictify_dataset_collection_instance
from galaxy.model import HistoryDatasetAssociation
from galaxy.util.expressions import ExpressionContext
from collections import Iterable

import galaxy.queue_worker

import logging
log = logging.getLogger( __name__ )


class ToolsController( BaseAPIController, UsesVisualizationMixin ):
    """
    RESTful controller for interactions with tools.
    """

    def __init__( self, app ):
        super( ToolsController, self ).__init__( app )
        self.mgrs = util.bunch.Bunch(
            histories=managers.histories.HistoryManager( app )
        )

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
    def build( self, trans, id, **kwd ):
        """
        GET /api/tools/{tool_id}/build
        Returns a tool model including dynamic parameters and updated values, repeats block etc.
        """
        tool_id = urllib.unquote_plus( id )
        tool_version = kwd.get( 'tool_version', None )
        tool = self.app.toolbox.get_tool( tool_id, tool_version )
        if not tool:
            trans.response.status = 500
            return { 'error': 'Could not find tool with id \'%s\'' % tool_id }
        return self._build_dict(trans, tool, kwd)
    
    @_future_expose_api
    @web.require_admin
    def reload( self, trans, tool_id, **kwd ):
        """
        GET /api/tools/{tool_id}/reload
        Reload specified tool.
        """
        toolbox = trans.app.toolbox
        galaxy.queue_worker.send_control_task( trans, 'reload_tool', noop_self=True, kwargs={ 'tool_id': tool_id } )
        message, status = trans.app.toolbox.reload_tool_by_id( tool_id )
        return { status: message }

    @_future_expose_api_anonymous
    def citations( self, trans, id, **kwds ):
        tool = self._get_tool( id )
        rval = []
        for citation in tool.citations:
            rval.append( citation.to_dict( 'bibtex' ) )
        return rval

    @web.expose_api_raw
    @web.require_admin
    def download( self, trans, id, **kwds ):
        tool_tarball, success, message = trans.app.toolbox.package_tool( trans, id )
        if success:
            trans.response.set_content_type( 'application/x-gzip' )
            download_file = open( tool_tarball )
            os.unlink( tool_tarball )
            tarball_path, filename = os.path.split( tool_tarball )
            trans.response.headers[ "Content-Disposition" ] = 'attachment; filename="%s.tgz"' % ( id )
            return download_file

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
        tool_version = payload.get( 'tool_version', None )
        tool = trans.app.toolbox.get_tool( payload[ 'tool_id' ] , tool_version ) if 'tool_id' in payload else None
        if not tool:
            trans.response.status = 404
            return { "message": { "type": "error", "text" : trans.app.model.Dataset.conversion_messages.NO_TOOL } }

        # Set running history from payload parameters.
        # History not set correctly as part of this API call for
        # dataset upload.
        history_id = payload.get("history_id", None)
        if history_id:
            decoded_id = trans.security.decode_id( history_id )
            target_history = self.mgrs.histories.owned_by_id( trans, decoded_id, trans.user )
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
    def _get_tool( self, id, tool_version=None ):
        id = urllib.unquote_plus( id )
        tool = self.app.toolbox.get_tool( id, tool_version )
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

    def _build_dict(self, trans, tool, kwd={}):
        """
        Recursively creates a tool dictionary containing repeats, dynamic options and updated states.
        """
        job_id = kwd.get('job_id', None)
        dataset_id = kwd.get('dataset_id', None)
        
        # load job details if provided
        job = None
        if job_id:
            try:
                job_id = trans.security.decode_id( job_id )
                job = trans.sa_session.query( trans.app.model.Job ).get( job_id )
            except Exception, exception:
                trans.response.status = 500
                return { 'error': 'Failed to retrieve job.' }
        elif dataset_id:
            try:
                dataset_id = trans.security.decode_id( dataset_id )
                data = trans.sa_session.query( trans.app.model.HistoryDatasetAssociation ).get( dataset_id )
                if not ( trans.user_is_admin() or trans.app.security_agent.can_access_dataset( trans.get_current_user_roles(), data.dataset ) ):
                    trans.response.status = 500
                    return { 'error': 'User has no access to dataset.' }
                job = data.creating_job
                if not job:
                    trans.response.status = 500
                    return { 'error': 'Creating job not found.' }
            except Exception, exception:
                trans.response.status = 500
                return { 'error': 'Failed to get job information.' }
        
        # load job parameters into incoming
        tool_message = ''
        if job:
            try:
                job_params = job.get_param_values( trans.app, ignore_errors = True )
                job_messages = tool.check_and_update_param_values( job_params, trans, update_values=False )
                tool_message = self._compare_tool_version(trans, tool, job)
                params_to_incoming( kwd, tool.inputs, job_params, trans.app )
            except Exception, exception:
                trans.response.status = 500
                return { 'error': str( exception ) }
                
        # create parameter object
        params = galaxy.util.Params( kwd, sanitize = False )
        
        # convert value to jsonifiable value
        def convert(v):
            # check if value is numeric
            isnumber = False
            try:
                float(v)
                isnumber = True
            except Exception:
                pass

            # fix hda parsing
            if isinstance(v, HistoryDatasetAssociation):
                return {
                    'id'  : trans.security.encode_id(v.id),
                    'src' : 'hda'
                }
            elif isinstance(v, bool):
                if v is True:
                    return 'true'
                else:
                    return 'false'
            elif isinstance(v, basestring) or isnumber:
                return v
            else:
                return None

        # ensures that input dictionary is jsonifiable
        def sanitize(dict):
            # get current value
            value = dict['value'] if 'value' in dict else None

            # identify lists
            if dict['type'] in ['data']:
                if isinstance(value, list):
                    value = [ convert(v) for v in value ]
                else:
                    value = [ convert(value) ]
                value = {
                    'batch'     : dict['multiple'],
                    'values'    : value
                }
            elif isinstance(value, list):
                value = [ convert(v) for v in value ]
            else:
                value = convert(value)

            # update and return
            dict['value'] = value
            return dict
        
        # initialize state using default parameters
        def initialize_state(trans, inputs, state, context=None):
            context = ExpressionContext(state, context)
            for input in inputs.itervalues():
                state[input.name] = input.get_initial_value(trans, context)
    
        # check the current state of a value and update it if necessary
        def check_state(trans, input, default_value, context):
            value = default_value
            error = 'State validation failed.'
            try:
                # resolves the inconsistent definition of boolean parameters (see base.py) without modifying shared code
                if input.type == 'boolean' and isinstance(default_value, basestring):
                    value, error = [util.string_as_bool(default_value), None]
                else:
                    value, error = check_param(trans, input, default_value, context)
            except Exception:
                log.error('Checking parameter %s failed.', input.name)
                pass
            return [value, error]
    
        # populates state with incoming url parameters
        def populate_state(trans, inputs, state, errors, incoming, prefix="", context=None ):
            context = ExpressionContext(state, context)
            for input in inputs.itervalues():
                key = prefix + input.name
                if input.type == 'repeat':
                    group_state = state[input.name]
                    rep_index = 0
                    del group_state[:]
                    while True:
                        rep_name = "%s_%d" % (key, rep_index)
                        if not any([incoming_key.startswith(rep_name) for incoming_key in incoming.keys()]):
                            break
                        if rep_index < input.max:
                            new_state = {}
                            new_state['__index__'] = rep_index
                            initialize_state(trans, input.inputs, new_state, context)
                            group_state.append(new_state)
                            populate_state(trans, input.inputs, new_state, errors, incoming, prefix=rep_name + "|", context=context)
                        rep_index += 1
                elif input.type == 'conditional':
                    group_state = state[input.name]
                    group_prefix = "%s|" % ( key )
                    test_param_key = group_prefix + input.test_param.name
                    default_value = incoming.get(test_param_key, group_state.get(input.test_param.name, None))
                    value, error = check_state(trans, input.test_param, default_value, context)
                    if error:
                        errors[test_param_key] = error
                    else:
                        current_case = input.get_current_case(value, trans)
                        group_state = state[input.name] = {}
                        initialize_state(trans, input.cases[current_case].inputs, group_state, context)
                        populate_state( trans, input.cases[current_case].inputs, group_state, errors, incoming, prefix=group_prefix, context=context)
                        group_state['__current_case__'] = current_case
                    group_state[input.test_param.name] = value
                else:
                    default_value = incoming.get(key, state.get(input.name, None))
                    value, error = check_state(trans, input, default_value, context)
                    if error:
                        errors[key] = error
                    state[input.name] = value
        
        # builds tool model including all attributes
        def iterate(group_inputs, inputs, tool_state, other_values=None):
            other_values = ExpressionContext( tool_state, other_values )
            for input_index, input in enumerate( inputs.itervalues() ):
                # create model dictionary
                group_inputs[input_index] = input.to_dict(trans)
                if group_inputs[input_index] is None:
                    continue

                # identify stat for subsection/group
                group_state = tool_state[input.name]

                # iterate and update values
                if input.type == 'repeat':
                    group_cache = group_inputs[input_index]['cache'] = {}
                    for i in range( len( group_state ) ):
                        group_cache[i] = {}
                        iterate( group_cache[i], input.inputs, group_state[i], other_values )
                elif input.type == 'conditional':
                    try:
                        test_param = group_inputs[input_index]['test_param']
                        test_param['value'] = convert(group_state[test_param['name']])
                    except Exception:
                        pass
                    i = group_state['__current_case__']
                    iterate(group_inputs[input_index]['cases'][i]['inputs'], input.cases[i].inputs, group_state, other_values)
                else:
                    # create input dictionary, try to pass other_values if to_dict function supports it e.g. dynamic options
                    try:
                        group_inputs[input_index] = input.to_dict(trans, other_values=other_values)
                    except Exception:
                        pass

                    # update input value from tool state
                    try:
                        group_inputs[input_index]['value'] = tool_state[group_inputs[input_index]['name']]
                    except Exception:
                        pass

                    # sanitize if value exists
                    if group_inputs[input_index]['value']:
                        group_inputs[input_index] = sanitize(group_inputs[input_index])

        # do param translation here, used by datasource tools
        if tool.input_translator:
            tool.input_translator.translate( params )
        
        # create tool state
        state_inputs = {}
        state_errors = {}
        initialize_state(trans, tool.inputs, state_inputs)
        populate_state(trans, tool.inputs, state_inputs, state_errors, params.__dict__)

        # create basic tool model
        tool_model = tool.to_dict(trans)
        tool_model['inputs'] = {}

        # build tool model
        iterate(tool_model['inputs'], tool.inputs, state_inputs, '')

        # load tool help
        tool_help = ''
        if tool.help:
            tool_help = tool.help
            tool_help = tool_help.render( static_path=web.url_for( '/static' ), host_url=web.url_for('/', qualified=True) )
            if type( tool_help ) is not unicode:
                tool_help = unicode( tool_help, 'utf-8')
        
        # check if citations exist
        tool_citations = False
        if tool.citations:
            tool_citations = True
    
        # get tool versions
        tool_versions = []
        tools = self.app.toolbox.get_loaded_tools_by_lineage(tool.id)
        for t in tools:
            tool_versions.append(t.version)
        
        ## add information with underlying requirements and their versions
        tool_requirements = []
        if tool.requirements:
            for requirement in tool.requirements:
                tool_requirements.append({
                    'name'      : requirement.name,
                    'version'   : requirement.version
                })

        # add additional properties
        tool_model.update({
            'help'          : tool_help,
            'citations'     : tool_citations,
            'biostar_url'   : trans.app.config.biostar_url,
            'message'       : tool_message,
            'versions'      : tool_versions,
            'requirements'  : tool_requirements,
            'errors'        : state_errors
        })

        # check for errors
        if 'error' in tool_message:
            return tool_message

        # return enriched tool model
        return tool_model

    def _compare_tool_version( self, trans, tool, job ):
        """
        Compares a tool version with the tool version from a job (from ToolRunner).
        """
        tool_id = job.tool_id
        tool_version = job.tool_version
        message = ''
        try:
            select_field, tools, tool = self.app.toolbox.get_tool_components( tool_id, tool_version=tool_version, get_loaded_tools_by_lineage=False, set_selected=True )
            if tool is None:
                trans.response.status = 500
                return { 'error': 'This dataset was created by an obsolete tool (%s). Can\'t re-run.' % tool_id }
            if ( tool.id != tool_id and tool.old_id != tool_id ) or tool.version != tool_version:
                if tool.id == tool_id:
                    if tool_version == None:
                        # for some reason jobs don't always keep track of the tool version.
                        message = ''
                    else:
                        message = 'This job was initially run with tool version "%s", which is currently not available.  ' % tool_version
                        if len( tools ) > 1:
                            message += 'You can re-run the job with the selected tool or choose another derivation of the tool.'
                        else:
                            message += 'You can re-run the job with this tool version, which is a derivation of the original tool.'
                else:
                    if len( tools ) > 1:
                        message = 'This job was initially run with tool version "%s", which is currently not available.  ' % tool_version
                        message += 'You can re-run the job with the selected tool or choose another derivation of the tool.'
                    else:
                        message = 'This job was initially run with tool id "%s", version "%s", which is ' % ( tool_id, tool_version )
                        message += 'currently not available.  You can re-run the job with this tool, which is a derivation of the original tool.'
        except Exception, error:
            trans.response.status = 500
            return { 'error': str (error) }
                
        # can't rerun upload, external data sources, et cetera. workflow compatible will proxy this for now
        if not tool.is_workflow_compatible:
            trans.response.status = 500
            return { 'error': 'The \'%s\' tool does currently not support re-running.' % tool.name }
        return message
