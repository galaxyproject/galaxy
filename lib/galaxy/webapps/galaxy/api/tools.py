import logging
import urllib
from json import dumps

import galaxy.queue_worker
from galaxy import exceptions, managers, util, web
from galaxy.managers.collections_util import dictify_dataset_collection_instance
from galaxy.visualization.genomes import GenomeRegion
from galaxy.web import _future_expose_api as expose_api
from galaxy.web import _future_expose_api_anonymous as expose_api_anonymous
from galaxy.web import _future_expose_api_anonymous_and_sessionless as expose_api_anonymous_and_sessionless
from galaxy.web.base.controller import BaseAPIController
from galaxy.web.base.controller import UsesVisualizationMixin

log = logging.getLogger( __name__ )


class ToolsController( BaseAPIController, UsesVisualizationMixin ):
    """
    RESTful controller for interactions with tools.
    """

    def __init__( self, app ):
        super( ToolsController, self ).__init__( app )
        self.history_manager = managers.histories.HistoryManager( app )
        self.hda_manager = managers.hdas.HDAManager( app )

    @expose_api_anonymous_and_sessionless
    def index( self, trans, **kwds ):
        """
        GET /api/tools: returns a list of tools defined by parameters::

            parameters:

                in_panel  - if true, tools are returned in panel structure,
                            including sections and labels
                trackster - if true, only tools that are compatible with
                            Trackster are returned
                q         - if present search on the given query will be performed
                tool_id   - if present the given tool_id will be searched for
                            all installed versions
        """

        # Read params.
        in_panel = util.string_as_bool( kwds.get( 'in_panel', 'True' ) )
        trackster = util.string_as_bool( kwds.get( 'trackster', 'False' ) )
        q = kwds.get( 'q', '' )
        tool_id = kwds.get( 'tool_id', '' )

        # Find whether to search.
        if q:
            hits = self._search( q )
            results = []
            if hits:
                for hit in hits:
                    try:
                        tool = self._get_tool( hit, user=trans.user )
                        if tool:
                            results.append( tool.id )
                    except exceptions.AuthenticationFailed:
                        pass
                    except exceptions.ObjectNotFound:
                        pass
            return results

        # Find whether to detect.
        if tool_id:
            detected_versions = self._detect( trans, tool_id )
            return detected_versions

        # Return everything.
        try:
            return self.app.toolbox.to_dict( trans, in_panel=in_panel, trackster=trackster)
        except Exception:
            raise exceptions.InternalServerError( "Error: Could not convert toolbox to dictionary" )

    @expose_api_anonymous_and_sessionless
    def show( self, trans, id, **kwd ):
        """
        GET /api/tools/{tool_id}
        Returns tool information, including parameters and inputs.
        """
        io_details = util.string_as_bool( kwd.get( 'io_details', False ) )
        link_details = util.string_as_bool( kwd.get( 'link_details', False ) )
        tool = self._get_tool( id, user=trans.user )
        return tool.to_dict( trans, io_details=io_details, link_details=link_details )

    @expose_api_anonymous
    def build( self, trans, id, **kwd ):
        """
        GET /api/tools/{tool_id}/build
        Returns a tool model including dynamic parameters and updated values, repeats block etc.
        """
        if 'payload' in kwd:
            kwd = kwd.get('payload')
        tool_version = kwd.get( 'tool_version', None )
        tool = self._get_tool( id, tool_version=tool_version, user=trans.user )
        return tool.to_json(trans, kwd.get('inputs', kwd))

    @expose_api
    @web.require_admin
    def reload( self, trans, id, **kwd ):
        """
        GET /api/tools/{tool_id}/reload
        Reload specified tool.
        """
        galaxy.queue_worker.send_control_task( trans.app, 'reload_tool', noop_self=True, kwargs={ 'tool_id': id } )
        message, status = trans.app.toolbox.reload_tool_by_id( id )
        return { status: message }

    @expose_api
    @web.require_admin
    def all_requirements(self, trans, **kwds):
        """
        GET /api/tools/all_requirements
        Return list of unique requirements for all tools.
        """

        return trans.app.toolbox.all_requirements

    @expose_api
    @web.require_admin
    def requirements(self, trans, id, **kwds):
        """
        GET /api/tools/{tool_id}/requirements
        Return the resolver status for a specific tool id.
        [{"status": "installed", "name": "hisat2", "versionless": false, "resolver_type": "conda", "version": "2.0.3", "type": "package"}]
        """
        tool = self._get_tool(id)
        return tool.tool_requirements_status

    @expose_api
    @web.require_admin
    def install_dependencies(self, trans, id, **kwds):
        """
        POST /api/tools/{tool_id}/install_dependencies
        Attempts to install requirements via the dependency resolver

        parameters:
            build_dependency_cache:  If true, attempts to cache dependencies for this tool
            force_rebuild:           If true and chache dir exists, attempts to delete cache dir
        """
        tool = self._get_tool(id)
        tool._view.install_dependencies(tool.requirements)
        if kwds.get('build_dependency_cache'):
            tool.build_dependency_cache(**kwds)
        # TODO: rework resolver install system to log and report what has been done.
        # _view.install_dependencies should return a dict with stdout, stderr and success status
        return tool.tool_requirements_status

    @expose_api
    @web.require_admin
    def build_dependency_cache(self, trans, id, **kwds):
        """
        POST /api/tools/{tool_id}/build_dependency_cache
        Attempts to cache installed dependencies.

        parameters:
            force_rebuild:           If true and chache dir exists, attempts to delete cache dir
        """
        tool = self._get_tool(id)
        tool.build_dependency_cache(**kwds)
        # TODO: Should also have a more meaningful return.
        return tool.tool_requirements_status

    @expose_api
    @web.require_admin
    def diagnostics( self, trans, id, **kwd ):
        """
        GET /api/tools/{tool_id}/diagnostics
        Return diagnostic information to help debug panel
        and dependency related problems.
        """
        # TODO: Move this into tool.
        def to_dict(x):
            return x.to_dict()

        tool = self._get_tool( id, user=trans.user )
        if hasattr( tool, 'lineage' ):
            lineage_dict = tool.lineage.to_dict()
        else:
            lineage_dict = None
        tool_shed_dependencies = tool.installed_tool_dependencies
        if tool_shed_dependencies:
            tool_shed_dependencies_dict = map(to_dict, tool_shed_dependencies)
        else:
            tool_shed_dependencies_dict = None
        return {
            "tool_id": tool.id,
            "tool_version": tool.version,
            "dependency_shell_commands": tool.build_dependency_shell_commands(),
            "lineage": lineage_dict,
            "requirements": map(to_dict, tool.requirements),
            "installed_tool_shed_dependencies": tool_shed_dependencies_dict,
            "tool_dir": tool.tool_dir,
            "tool_shed": tool.tool_shed,
            "repository_name": tool.repository_name,
            "repository_owner": tool.repository_owner,
            "installed_changeset_revision": None,
            "guid": tool.guid,
        }

    def _detect( self, trans, tool_id ):
        """
        Detect whether the tool with the given id is installed.

        :param tool_id: exact id of the tool
        :type tool_id:  str

        :return:      list with available versions
        "return type: list
        """
        tools = self.app.toolbox.get_tool( tool_id, get_all_versions=True )
        detected_versions = []
        if tools:
            for tool in tools:
                if tool and tool.allow_user_access( trans.user ):
                    detected_versions.append( tool.version )
        return detected_versions

    def _search( self, q ):
        """
        Perform the search on the given query.
        Boosts and numer of results are configurable in galaxy.ini file.

        :param q: the query to search with
        :type  q: str

        :return:      Dictionary containing the tools' ids of the best hits.
        :return type: dict
        """
        tool_name_boost = self.app.config.get( 'tool_name_boost', 9 )
        tool_section_boost = self.app.config.get( 'tool_section_boost', 3 )
        tool_description_boost = self.app.config.get( 'tool_description_boost', 2 )
        tool_label_boost = self.app.config.get( 'tool_label_boost', 1 )
        tool_stub_boost = self.app.config.get( 'tool_stub_boost', 5 )
        tool_help_boost = self.app.config.get( 'tool_help_boost', 0.5 )
        tool_search_limit = self.app.config.get( 'tool_search_limit', 20 )
        tool_enable_ngram_search = self.app.config.get( 'tool_enable_ngram_search', False )
        tool_ngram_minsize = self.app.config.get( 'tool_ngram_minsize', 3 )
        tool_ngram_maxsize = self.app.config.get( 'tool_ngram_maxsize', 4 )

        results = self.app.toolbox_search.search( q=q,
                                                  tool_name_boost=tool_name_boost,
                                                  tool_section_boost=tool_section_boost,
                                                  tool_description_boost=tool_description_boost,
                                                  tool_label_boost=tool_label_boost,
                                                  tool_stub_boost=tool_stub_boost,
                                                  tool_help_boost=tool_help_boost,
                                                  tool_search_limit=tool_search_limit,
                                                  tool_enable_ngram_search=tool_enable_ngram_search,
                                                  tool_ngram_minsize=tool_ngram_minsize,
                                                  tool_ngram_maxsize=tool_ngram_maxsize )
        return results

    @expose_api_anonymous_and_sessionless
    def citations( self, trans, id, **kwds ):
        tool = self._get_tool( id, user=trans.user )
        rval = []
        for citation in tool.citations:
            rval.append( citation.to_dict( 'bibtex' ) )
        return rval

    @web.expose_api_raw
    @web.require_admin
    def download( self, trans, id, **kwds ):
        tool_tarball = trans.app.toolbox.package_tool(trans, id)
        trans.response.set_content_type('application/x-gzip')
        download_file = open(tool_tarball, "rb")
        trans.response.headers[ "Content-Disposition" ] = 'attachment; filename="%s.tgz"' % (id)
        return download_file

    @expose_api_anonymous
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
        tool = trans.app.toolbox.get_tool( payload[ 'tool_id' ], tool_version ) if 'tool_id' in payload else None
        if not tool or not tool.allow_user_access( trans.user ):
            raise exceptions.MessageException( 'Tool not found or not accessible.' )
        if trans.app.config.user_activation_on:
            if not trans.user:
                log.warning( "Anonymous user attempts to execute tool, but account activation is turned on." )
            elif not trans.user.active:
                log.warning( "User \"%s\" attempts to execute tool, but account activation is turned on and user account is not active." % trans.user.email )

        # Set running history from payload parameters.
        # History not set correctly as part of this API call for
        # dataset upload.
        history_id = payload.get('history_id', None)
        if history_id:
            decoded_id = self.decode_id( history_id )
            target_history = self.history_manager.get_owned( decoded_id, trans.user, current_history=trans.history )
        else:
            target_history = None

        # Set up inputs.
        inputs = payload.get( 'inputs', {} )
        # Find files coming in as multipart file data and add to inputs.
        for k, v in payload.iteritems():
            if k.startswith('files_') or k.startswith('__files_'):
                inputs[k] = v

        # for inputs that are coming from the Library, copy them into the history
        input_patch = {}
        for k, v in inputs.iteritems():
            if isinstance(v, dict) and v.get('src', '') == 'ldda' and 'id' in v:
                ldda = trans.sa_session.query( trans.app.model.LibraryDatasetDatasetAssociation ).get( self.decode_id(v['id']) )
                if trans.user_is_admin() or trans.app.security_agent.can_access_dataset( trans.get_current_user_roles(), ldda.dataset ):
                    input_patch[k] = ldda.to_history_dataset_association(target_history, add_to_history=True)

        for k, v in input_patch.iteritems():
            inputs[k] = v

        # TODO: encode data ids and decode ids.
        # TODO: handle dbkeys
        params = util.Params( inputs, sanitize=False )
        incoming = params.__dict__
        vars = tool.handle_input( trans, incoming, history=target_history )

        # TODO: check for errors and ensure that output dataset(s) are available.
        output_datasets = vars.get( 'out_data', [] )
        rval = { 'outputs': [], 'output_collections': [], 'jobs': [], 'implicit_collections': [] }

        job_errors = vars.get( 'job_errors', [] )
        if job_errors:
            # If we are here - some jobs were successfully executed but some failed.
            rval[ 'errors' ] = job_errors

        outputs = rval[ 'outputs' ]
        # TODO:?? poss. only return ids?
        for output_name, output in output_datasets:
            output_dict = output.to_dict()
            # add the output name back into the output data structure
            # so it's possible to figure out which newly created elements
            # correspond with which tool file outputs
            output_dict[ 'output_name' ] = output_name
            outputs.append( trans.security.encode_dict_ids( output_dict, skip_startswith="metadata_" ) )

        for job in vars.get('jobs', []):
            rval[ 'jobs' ].append( self.encode_all_ids( trans, job.to_dict( view='collection' ), recursive=True ) )

        for output_name, collection_instance in vars.get('output_collections', []):
            history = target_history or trans.history
            output_dict = dictify_dataset_collection_instance( collection_instance, security=trans.security, parent=history )
            output_dict[ 'output_name' ] = output_name
            rval[ 'output_collections' ].append( output_dict )

        for output_name, collection_instance in vars.get( 'implicit_collections', {} ).iteritems():
            history = target_history or trans.history
            output_dict = dictify_dataset_collection_instance( collection_instance, security=trans.security, parent=history )
            output_dict[ 'output_name' ] = output_name
            rval[ 'implicit_collections' ].append( output_dict )

        return rval

    #
    # -- Helper methods --
    #
    def _get_tool( self, id, tool_version=None, user=None ):
        id = urllib.unquote_plus( id )
        tool = self.app.toolbox.get_tool( id, tool_version )
        if not tool:
            raise exceptions.ObjectNotFound( "Could not find tool with id '%s'." % id )
        if not tool.allow_user_access( user ):
            raise exceptions.AuthenticationFailed( "Access denied, please login for tool with id '%s'." % id )
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
        decoded_dataset_id = self.decode_id( payload.get( 'target_dataset_id' ) )
        original_dataset = self.hda_manager.get_accessible( decoded_dataset_id, user=trans.user )
        original_dataset = self.hda_manager.error_if_uploading( original_dataset )
        msg = self.hda_manager.data_conversion_status( original_dataset )
        if msg:
            return msg

        # Set tool parameters--except non-hidden dataset parameters--using combination of
        # job's previous parameters and incoming parameters. Incoming parameters
        # have priority.
        #
        original_job = self.hda_manager.creating_job( original_dataset )
        tool = trans.app.toolbox.get_tool( original_job.tool_id )
        if not tool or not tool.allow_user_access( trans.user ):
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
                if data_provider and ( not data_provider.converted_dataset or
                                       data_provider.converted_dataset.state != trans.app.model.Dataset.states.OK ):
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
                    input_dataset.get_converted_dataset( trans, data_source )
                    input_dataset.get_converted_dataset_deps( trans, data_source )

                    # Create new HDA for input dataset's subset.
                    new_dataset = trans.app.model.HistoryDatasetAssociation( extension=input_dataset.ext,
                                                                             dbkey=input_dataset.dbkey,
                                                                             create_dataset=True,
                                                                             sa_session=trans.sa_session,
                                                                             name="Subset [%s] of data %i" %
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
                                                                                                 overwrite=False, job_params={ "source": "trackster" } )
                    # Add HDA subset association.
                    subset_association = trans.app.model.HistoryDatasetAssociationSubset( hda=input_dataset, subset=new_dataset, location=regions_str )
                    trans.sa_session.add( subset_association )

                    subset_dataset = new_dataset

                trans.sa_session.flush()

                # Add dataset to tool's parameters.
                if not set_param_value( tool_params, jida.name, subset_dataset ):
                    return { "error": True, "message": "error setting parameter %s" % jida.name }

        #
        # Execute tool and handle outputs.
        #
        try:
            subset_job, subset_job_outputs = tool.execute( trans, incoming=tool_params,
                                                           history=target_history,
                                                           job_params={ "source": "trackster" } )
        except Exception as e:
            # Lots of things can go wrong when trying to execute tool.
            return { "error": True, "message": e.__class__.__name__ + ": " + str(e) }
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
