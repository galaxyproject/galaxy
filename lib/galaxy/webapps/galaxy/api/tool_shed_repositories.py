import json
import logging
import re
from time import strftime

from paste.httpexceptions import HTTPBadRequest, HTTPForbidden

import tool_shed.util.shed_util_common as suc
from galaxy import util
from galaxy import web
from galaxy import exceptions
from galaxy.web import _future_expose_api as expose_api
from galaxy.web.base.controller import BaseAPIController

from tool_shed.galaxy_install.install_manager import InstallRepositoryManager
from tool_shed.galaxy_install.metadata.installed_repository_metadata_manager import InstalledRepositoryMetadataManager
from tool_shed.galaxy_install.repair_repository_manager import RepairRepositoryManager
from tool_shed.util import common_util
from tool_shed.util import encoding_util
from tool_shed.util import hg_util
from tool_shed.util import workflow_util
from tool_shed.util import tool_util
from tool_shed.util import repository_util

from sqlalchemy import and_

log = logging.getLogger( __name__ )


def get_message_for_no_shed_tool_config():
    # This Galaxy instance is not configured with a shed-related tool panel configuration file.
    message = 'The tool_config_file setting in galaxy.ini must include at least one shed tool configuration file name with a <toolbox> '
    message += 'tag that includes a tool_path attribute value which is a directory relative to the Galaxy installation directory in order to '
    message += 'automatically install tools from a tool shed into Galaxy (e.g., the file name shed_tool_conf.xml whose <toolbox> tag is '
    message += '<toolbox tool_path="../shed_tools">).  For details, see the "Installation of Galaxy tool shed repository tools into a local '
    message += 'Galaxy instance" section of the Galaxy tool shed wiki at http://wiki.galaxyproject.org/InstallingRepositoriesToGalaxy#'
    message += 'Installing_Galaxy_tool_shed_repository_tools_into_a_local_Galaxy_instance.'
    return message


class ToolShedRepositoriesController( BaseAPIController ):
    """RESTful controller for interactions with tool shed repositories."""

    def __ensure_can_install_repos( self, trans ):
        # Make sure this Galaxy instance is configured with a shed-related tool panel configuration file.
        if not suc.have_shed_tool_conf_for_install( self.app ):
            message = get_message_for_no_shed_tool_config()
            log.debug( message )
            return dict( status='error', error=message )
        # Make sure the current user's API key proves he is an admin user in this Galaxy instance.
        if not trans.user_is_admin():
            raise exceptions.AdminRequiredException( 'You are not authorized to request the latest installable revision for a repository in this Galaxy instance.' )

    def __flatten_repository_dependency_list( self, trans, tool_shed_repository ):
        '''
        Return a recursive exclusive flattened list of all tool_shed_repository's dependencies.
        '''
        dependencies = []
        for dependency in tool_shed_repository.repository_dependencies:
            if len( dependency.repository_dependencies ) > 0:
                sub_dependencies = self.__flatten_repository_dependency_list( trans, dependency )
                for sub_dependency in sub_dependencies:
                    if sub_dependency not in dependencies:
                        dependencies.append( sub_dependency )
            if dependency not in dependencies:
                dependencies.append( dependency.as_dict( value_mapper=self.__get_value_mapper( trans, tool_shed_repository ) ) )
        return dependencies

    def __get_repo_info_dict( self, trans, repositories, tool_shed_url ):
        repo_ids = []
        changesets = []
        for repository_id, changeset in repositories:
            repo_ids.append( repository_id )
            changesets.append( changeset )
        params = dict( repository_ids=str( ','.join( repo_ids ) ), changeset_revisions=str( ','.join( changesets ) ) )
        pathspec = [ 'repository', 'get_repository_information' ]
        raw_text = util.url_get( tool_shed_url, password_mgr=self.app.tool_shed_registry.url_auth( tool_shed_url ), pathspec=pathspec, params=params )
        return json.loads( raw_text )

    def __get_value_mapper( self, trans, tool_shed_repository ):
        value_mapper = { 'id': trans.security.encode_id( tool_shed_repository.id ),
                         'error_message': tool_shed_repository.error_message or '' }
        return value_mapper

    def __get_tool_dependencies( self, metadata, tool_dependencies=None ):
        if tool_dependencies is None:
            tool_dependencies = []
        for key, dependency_dict in metadata[ 'tool_dependencies' ].items():
            if 'readme' in dependency_dict:
                del( dependency_dict[ 'readme' ] )
            if dependency_dict not in tool_dependencies:
                tool_dependencies.append( dependency_dict )
        if metadata[ 'has_repository_dependencies' ]:
            for dependency in metadata[ 'repository_dependencies' ]:
                tool_dependencies = self.__get_tool_dependencies( dependency, tool_dependencies )
        return tool_dependencies

    def __get_tools( self, metadata, tools=None ):
        if tools is None:
            tools = []
        if metadata[ 'includes_tools_for_display_in_tool_panel' ]:
            for key, tool_dict in metadata[ 'tools' ]:
                tool_info = dict( clean=re.sub( '[^a-zA-Z0-9]+', '_', tool_dict[ 'name' ] ).lower(),
                                  name=tool_dict[ 'name' ],
                                  version=tool_dict[ 'version' ],
                                  description=tool_dict[ 'description' ] )
                if tool_info not in tools:
                    tools.append( tool_info )
        if metadata[ 'has_repository_dependencies' ]:
            for dependency in metadata[ 'repository_dependencies' ]:
                tools = self.__get_tools( dependency, tools )
        return tools

    @expose_api
    def check_for_updates( self, trans, **kwd ):
        '''
        GET /api/tool_shed_repositories/check_for_updates
        Check for updates to the specified repository, or all installed repositories.

        :param key: the current Galaxy admin user's API key
        :param id: the galaxy-side encoded repository ID
        '''
        repository_id = kwd.get( 'id', None )
        message, status = repository_util.check_for_updates( self.app, trans.install_model, repository_id )
        return { 'status': status, 'message': message }

    @expose_api
    def exported_workflows( self, trans, id, **kwd ):
        """
        GET /api/tool_shed_repositories/{encoded_tool_shed_repository_id}/exported_workflows

        Display a list of dictionaries containing information about this tool shed repository's exported workflows.

        :param id: the encoded id of the ToolShedRepository object
        """
        # Example URL: http://localhost:8763/api/tool_shed_repositories/f2db41e1fa331b3e/exported_workflows
        # Since exported workflows are dictionaries with very few attributes that differentiate them from each
        # other, we'll build the list based on the following dictionary of those few attributes.
        exported_workflows = []
        repository = repository_util.get_tool_shed_repository_by_id( self.app, id )
        metadata = repository.metadata
        if metadata:
            exported_workflow_tups = metadata.get( 'workflows', [] )
        else:
            exported_workflow_tups = []
        for index, exported_workflow_tup in enumerate( exported_workflow_tups ):
            # The exported_workflow_tup looks like ( relative_path, exported_workflow_dict ), where the value of
            # relative_path is the location on disk (relative to the root of the installed repository) where the
            # exported_workflow_dict file (.ga file) is located.
            exported_workflow_dict = exported_workflow_tup[ 1 ]
            annotation = exported_workflow_dict.get( 'annotation', '' )
            format_version = exported_workflow_dict.get( 'format-version', '' )
            workflow_name = exported_workflow_dict.get( 'name', '' )
            # Since we don't have an in-memory object with an id, we'll identify the exported workflow via its
            # location (i.e., index) in the list.
            display_dict = dict( index=index, annotation=annotation, format_version=format_version, workflow_name=workflow_name )
            exported_workflows.append( display_dict )
        return exported_workflows

    @expose_api
    def get_latest_installable_revision( self, trans, payload, **kwd ):
        """
        POST /api/tool_shed_repositories/get_latest_installable_revision
        Get the latest installable revision of a specified repository from a specified Tool Shed.

        :param key: the current Galaxy admin user's API key

        The following parameters are included in the payload.
        :param tool_shed_url (required): the base URL of the Tool Shed from which to retrieve the Repository revision.
        :param name (required): the name of the Repository
        :param owner (required): the owner of the Repository
        """
        # Get the information about the repository to be installed from the payload.
        tool_shed_url, name, owner = self.__parse_repository_from_payload( payload )
        # Make sure the current user's API key proves he is an admin user in this Galaxy instance.
        if not trans.user_is_admin():
            raise exceptions.AdminRequiredException( 'You are not authorized to request the latest installable revision for a repository in this Galaxy instance.' )
        params = dict( name=name, owner=owner )
        pathspec = [ 'api', 'repositories', 'get_ordered_installable_revisions' ]
        try:
            raw_text = util.url_get( tool_shed_url, password_mgr=self.app.tool_shed_registry.url_auth( tool_shed_url ), pathspec=pathspec, params=params )
        except Exception as e:
            message = "Error attempting to retrieve the latest installable revision from tool shed %s for repository %s owned by %s: %s" % \
                ( str( tool_shed_url ), str( name ), str( owner ), str( e ) )
            log.debug( message )
            return dict( status='error', error=message )
        if raw_text:
            # If successful, the response from get_ordered_installable_revisions will be a list of
            # changeset_revision hash strings.
            changeset_revisions = json.loads( raw_text )
            if len( changeset_revisions ) >= 1:
                return changeset_revisions[ -1 ]
        return hg_util.INITIAL_CHANGELOG_HASH

    @expose_api
    @web.require_admin
    def shed_categories( self, trans, **kwd ):
        """
        GET /api/tool_shed_repositories/shed_categories

        Display a list of categories in the selected toolshed.

        :param tool_shed_url: the url of the toolshed to get categories from
        """
        tool_shed_url = kwd.get( 'tool_shed_url', '' )
        tool_shed_url = common_util.get_tool_shed_url_from_tool_shed_registry( trans.app, tool_shed_url )
        url = util.build_url( tool_shed_url, pathspec=[ 'api', 'categories' ] )
        categories = json.loads( util.url_get( url ) )
        repositories = []
        url = util.build_url( tool_shed_url, pathspec=[ 'api', 'repositories' ] )
        for repo in json.loads( util.url_get( url ) ):
            repositories.append( dict( value=repo[ 'id' ], label='%s/%s' % ( repo[ 'owner' ], repo[ 'name' ] ) ) )
        return { 'categories': categories, 'repositories': repositories }

    @expose_api
    @web.require_admin
    def shed_category( self, trans, **kwd ):
        """
        GET /api/tool_shed_repositories/shed_category

        Display a list of repositories in the selected category.

        :param tool_shed_url: the url of the toolshed to get repositories from
        :param category_id: the category to get repositories from
        """
        tool_shed_url = kwd.get( 'tool_shed_url', '' )
        category_id = kwd.get( 'category_id', '' )
        tool_shed_url = common_util.get_tool_shed_url_from_tool_shed_registry( trans.app, tool_shed_url )
        url = util.build_url( tool_shed_url, pathspec=[ 'api', 'categories', category_id, 'repositories' ] )
        category = json.loads( util.url_get( url ) )
        return category

    @expose_api
    @web.require_admin
    def shed_repository( self, trans, **kwd ):
        """
        GET /api/tool_shed_repositories/shed_repository

        Get details about the specified repository from its shed.

        :param tsr_id: the tool_shed_repository_id
        """
        tool_dependencies = dict()
        tools = dict()
        tool_shed_url = kwd.get( 'tool_shed_url', '' )
        tsr_id = kwd.get( 'tsr_id', '' )
        tool_panel_section_select_field = tool_util.build_tool_panel_section_select_field( trans.app )
        tool_panel_section_dict = { 'name': tool_panel_section_select_field.name,
                                    'id': tool_panel_section_select_field.field_id,
                                    'sections': [] }
        for name, id, _ in tool_panel_section_select_field.options:
            tool_panel_section_dict['sections'].append( dict( id=id, name=name ) )
        repository_data = dict()
        repository_data[ 'repository' ] = json.loads( util.url_get( tool_shed_url, pathspec=[ 'api', 'repositories', tsr_id ] ) )
        repository_data[ 'repository' ][ 'metadata' ] = json.loads( util.url_get( tool_shed_url, pathspec=[ 'api', 'repositories', tsr_id, 'metadata' ] ) )
        repository_data[ 'shed_conf' ] = tool_util.build_shed_tool_conf_select_field( trans.app ).get_html().replace('\n', '')
        repository_data[ 'panel_section_html' ] = tool_panel_section_select_field.get_html( extra_attr={ 'style': 'width: 30em;' } ).replace( '\n', '' )
        repository_data[ 'panel_section_dict' ] = tool_panel_section_dict
        for changeset, metadata in repository_data[ 'repository' ][ 'metadata' ].items():
            if changeset not in tool_dependencies:
                tool_dependencies[ changeset ] = []
            if metadata[ 'includes_tools_for_display_in_tool_panel' ]:
                if changeset not in tools:
                    tools[ changeset ] = []
                for tool_dict in metadata[ 'tools' ]:
                    tool_info = dict( clean=re.sub( '[^a-zA-Z0-9]+', '_', tool_dict[ 'name' ] ).lower(),
                                      guid=tool_dict[ 'guid' ],
                                      name=tool_dict[ 'name' ],
                                      version=tool_dict[ 'version' ],
                                      description=tool_dict[ 'description' ] )
                    if tool_info not in tools[ changeset ]:
                        tools[ changeset ].append( tool_info )
                if metadata[ 'has_repository_dependencies' ]:
                    for repository_dependency in metadata[ 'repository_dependencies' ]:
                        tools[ changeset ] = self.__get_tools( repository_dependency, tools[ changeset ] )
                repository_data[ 'tools' ] = tools
            for key, dependency_dict in metadata[ 'tool_dependencies' ].items():
                if 'readme' in dependency_dict:
                    del( dependency_dict[ 'readme' ] )
                if dependency_dict not in tool_dependencies[ changeset ]:
                    tool_dependencies[ changeset ].append( dependency_dict )
                    # log.debug(tool_dependencies)
            if metadata[ 'has_repository_dependencies' ]:
                for repository_dependency in metadata[ 'repository_dependencies' ]:
                    tool_dependencies[ changeset ] = self.__get_tool_dependencies( repository_dependency, tool_dependencies[ changeset ] )
        repository_data[ 'tool_dependencies' ] = tool_dependencies
        return repository_data

    @expose_api
    def import_workflow( self, trans, payload, **kwd ):
        """
        POST /api/tool_shed_repositories/import_workflow

        Import the specified exported workflow contained in the specified installed tool shed repository into Galaxy.

        :param key: the API key of the Galaxy user with which the imported workflow will be associated.
        :param id: the encoded id of the ToolShedRepository object

        The following parameters are included in the payload.
        :param index: the index location of the workflow tuple in the list of exported workflows stored in the metadata for the specified repository
        """
        api_key = kwd.get( 'key', None )
        if api_key is None:
            raise HTTPBadRequest( detail="Missing required parameter 'key' whose value is the API key for the Galaxy user importing the specified workflow." )
        tool_shed_repository_id = kwd.get( 'id', '' )
        if not tool_shed_repository_id:
            raise HTTPBadRequest( detail="Missing required parameter 'id'." )
        index = payload.get( 'index', None )
        if index is None:
            raise HTTPBadRequest( detail="Missing required parameter 'index'." )
        repository = repository_util.get_tool_shed_repository_by_id( self.app, tool_shed_repository_id )
        exported_workflows = json.loads( self.exported_workflows( trans, tool_shed_repository_id ) )
        # Since we don't have an in-memory object with an id, we'll identify the exported workflow via its location (i.e., index) in the list.
        exported_workflow = exported_workflows[ int( index ) ]
        workflow_name = exported_workflow[ 'workflow_name' ]
        workflow, status, error_message = workflow_util.import_workflow( trans, repository, workflow_name )
        if status == 'error':
            log.debug( error_message )
            return {}
        return workflow.to_dict( view='element' )

    @expose_api
    def import_workflows( self, trans, **kwd ):
        """
        POST /api/tool_shed_repositories/import_workflows

        Import all of the exported workflows contained in the specified installed tool shed repository into Galaxy.

        :param key: the API key of the Galaxy user with which the imported workflows will be associated.
        :param id: the encoded id of the ToolShedRepository object
        """
        api_key = kwd.get( 'key', None )
        if api_key is None:
            raise HTTPBadRequest( detail="Missing required parameter 'key' whose value is the API key for the Galaxy user importing the specified workflow." )
        tool_shed_repository_id = kwd.get( 'id', '' )
        if not tool_shed_repository_id:
            raise HTTPBadRequest( detail="Missing required parameter 'id'." )
        repository = repository_util.get_tool_shed_repository_by_id( self.app, tool_shed_repository_id )
        exported_workflows = json.loads( self.exported_workflows( trans, tool_shed_repository_id ) )
        imported_workflow_dicts = []
        for exported_workflow_dict in exported_workflows:
            workflow_name = exported_workflow_dict[ 'workflow_name' ]
            workflow, status, error_message = workflow_util.import_workflow( trans, repository, workflow_name )
            if status == 'error':
                log.debug( error_message )
            else:
                imported_workflow_dicts.append( workflow.to_dict( view='element' ) )
        return imported_workflow_dicts

    @expose_api
    def index( self, trans, **kwd ):
        """
        GET /api/tool_shed_repositories
        Display a list of dictionaries containing information about installed tool shed repositories.
        """
        # Example URL: http://localhost:8763/api/tool_shed_repositories
        clause_list = []
        if 'name' in kwd:
            clause_list.append( self.app.install_model.ToolShedRepository.table.c.name == kwd.get( 'name', None ) )
        if 'owner' in kwd:
            clause_list.append( self.app.install_model.ToolShedRepository.table.c.owner == kwd.get( 'owner', None ) )
        if 'changeset' in kwd:
            clause_list.append( self.app.install_model.ToolShedRepository.table.c.changeset_revision == kwd.get( 'changeset', None ) )
        tool_shed_repository_dicts = []
        query = trans.install_model.context.query( self.app.install_model.ToolShedRepository ) \
                                           .order_by( self.app.install_model.ToolShedRepository.table.c.name )
        if len( clause_list ) > 0:
            query = query.filter( and_( *clause_list ) )
        for tool_shed_repository in query.all():
            tool_shed_repository_dict = \
                tool_shed_repository.to_dict( value_mapper=self.__get_value_mapper( trans, tool_shed_repository ) )
            tool_shed_repository_dict[ 'url' ] = web.url_for( controller='tool_shed_repositories',
                                                              action='show',
                                                              id=trans.security.encode_id( tool_shed_repository.id ) )
            tool_shed_repository_dicts.append( tool_shed_repository_dict )
        return tool_shed_repository_dicts

    @expose_api
    @web.require_admin
    def install( self, trans, **kwd ):
        """
        POST /api/tool_shed_repositories/install
        Initiate the installation of a repository.

        :param install_resolver_dependencies: True to install resolvable dependencies.
        :param install_tool_dependencies: True to install tool dependencies.
        :param install_repository_dependencies: True to install repository dependencies.
        :param tool_panel_section_id: The unique identifier for an existing tool panel section
        :param new_tool_panel_section_label: Create a new tool panel section with this label
        :param shed_tool_conf: The shed tool config file to use for this installation
        :param tool_shed_url: The URL for the toolshed whence this repository is being installed
        :param changeset: The changeset to update to after cloning the repository
        """
        irm = InstallRepositoryManager( self.app )
        tool_shed_url = kwd.get( 'tool_shed_url', None )
        repositories = json.loads( kwd.get( 'repositories', '[]' ) )
        repo_info_dict = self.__get_repo_info_dict( trans, repositories, tool_shed_url )
        includes_tools = False
        includes_tools_for_display_in_tool_panel = False
        has_repository_dependencies = False
        includes_tool_dependencies = False
        install_resolver_dependencies = util.asbool( kwd.get( 'install_resolver_dependencies', False ) )
        for encoded_repo_info_dict in repo_info_dict.get( 'repo_info_dicts', [] ):
            decoded_repo_info_dict = encoding_util.tool_shed_decode( encoded_repo_info_dict )
            if not includes_tools:
                includes_tools = util.string_as_bool( decoded_repo_info_dict.get( 'includes_tools', False ) )
            if not includes_tools_for_display_in_tool_panel:
                includes_tools_for_display_in_tool_panel = \
                    util.string_as_bool( decoded_repo_info_dict.get( 'includes_tools_for_display_in_tool_panel', False ) )
            if not has_repository_dependencies:
                has_repository_dependencies = util.string_as_bool( repo_info_dict.get( 'has_repository_dependencies', False ) )
            if not includes_tool_dependencies:
                includes_tool_dependencies = util.string_as_bool( repo_info_dict.get( 'includes_tool_dependencies', False ) )
        encoded_repo_info_dicts = util.listify( repo_info_dict.get( 'repo_info_dicts', [] ) )
        repo_info_dicts = [ encoding_util.tool_shed_decode( encoded_repo_info_dict ) for encoded_repo_info_dict in encoded_repo_info_dicts ]
        tool_panel_section_id = kwd.get( 'tool_panel_section_id', None )
        new_tool_panel_section_label = kwd.get( 'new_tool_panel_section', None )
        tool_panel_section_mapping = json.loads( kwd.get( 'tool_panel_section', '{}' ) )
        install_tool_dependencies = util.asbool( kwd.get( 'install_tool_dependencies', False ) )
        install_repository_dependencies = util.asbool( kwd.get( 'install_repository_dependencies', False ) )
        shed_tool_conf = kwd.get( 'shed_tool_conf', None )
        tool_path = suc.get_tool_path_by_shed_tool_conf_filename( self.app, shed_tool_conf )
        installation_dict = dict( install_repository_dependencies=install_repository_dependencies,
                                  new_tool_panel_section_label=new_tool_panel_section_label,
                                  no_changes_checked=False,
                                  repo_info_dicts=repo_info_dicts,
                                  tool_panel_section_id=tool_panel_section_id,
                                  tool_path=tool_path,
                                  tool_shed_url=tool_shed_url )
        new_repositories, tool_panel_keys, repo_info_dicts, filtered_repos = irm.handle_tool_shed_repositories( installation_dict )
        if new_repositories:
            installation_dict = dict( created_or_updated_tool_shed_repositories=new_repositories,
                                      filtered_repo_info_dicts=filtered_repos,
                                      has_repository_dependencies=has_repository_dependencies,
                                      includes_tool_dependencies=includes_tool_dependencies,
                                      includes_tools=includes_tools,
                                      includes_tools_for_display_in_tool_panel=includes_tools_for_display_in_tool_panel,
                                      install_repository_dependencies=install_repository_dependencies,
                                      install_tool_dependencies=install_tool_dependencies,
                                      message='',
                                      new_tool_panel_section_label=new_tool_panel_section_label,
                                      tool_panel_section_mapping=tool_panel_section_mapping,
                                      install_resolver_dependencies=install_resolver_dependencies,
                                      shed_tool_conf=shed_tool_conf,
                                      status='ok',
                                      tool_panel_section_id=tool_panel_section_id,
                                      tool_panel_section_keys=tool_panel_keys,
                                      tool_path=tool_path,
                                      tool_shed_url=tool_shed_url )
            encoded_kwd, query, tool_shed_repositories, encoded_repository_ids = \
                irm.initiate_repository_installation( installation_dict )
            return json.dumps( dict( operation='install',
                                     api=True,
                                     install_resolver_dependencies=install_resolver_dependencies,
                                     install_tool_dependencies=install_tool_dependencies,
                                     encoded_kwd=encoded_kwd,
                                     reinstalling=False,
                                     tool_shed_repository_ids=json.dumps( [ repo[0] for repo in repositories ] ),
                                     repositories=[ trans.security.encode_id( repo.id ) for repo in new_repositories ] ) )

    @expose_api
    def install_repository_revision( self, trans, payload, **kwd ):
        """
        POST /api/tool_shed_repositories/install_repository_revision
        Install a specified repository revision from a specified tool shed into Galaxy.

        :param key: the current Galaxy admin user's API key

        The following parameters are included in the payload.
        :param tool_shed_url (required): the base URL of the Tool Shed from which to install the Repository
        :param name (required): the name of the Repository
        :param owner (required): the owner of the Repository
        :param changeset_revision (required): the changeset_revision of the RepositoryMetadata object associated with the Repository
        :param new_tool_panel_section_label (optional): label of a new section to be added to the Galaxy tool panel in which to load
                                                        tools contained in the Repository.  Either this parameter must be an empty string or
                                                        the tool_panel_section_id parameter must be an empty string or both must be an empty
                                                        string (both cannot be used simultaneously).
        :param tool_panel_section_id (optional): id of the Galaxy tool panel section in which to load tools contained in the Repository.
                                                 If this parameter is an empty string and the above new_tool_panel_section_label parameter is an
                                                 empty string, tools will be loaded outside of any sections in the tool panel.  Either this
                                                 parameter must be an empty string or the tool_panel_section_id parameter must be an empty string
                                                 of both must be an empty string (both cannot be used simultaneously).
        :param install_repository_dependencies (optional): Set to True if you want to install repository dependencies defined for the specified
                                                           repository being installed.  The default setting is False.
        :param install_tool_dependencies (optional): Set to True if you want to install tool dependencies defined for the specified repository being
                                                     installed.  The default setting is False.
        :param shed_tool_conf (optional): The shed-related tool panel configuration file configured in the "tool_config_file" setting in the Galaxy config file
                                          (e.g., galaxy.ini).  At least one shed-related tool panel config file is required to be configured. Setting
                                          this parameter to a specific file enables you to choose where the specified repository will be installed because
                                          the tool_path attribute of the <toolbox> from the specified file is used as the installation location
                                          (e.g., <toolbox tool_path="../shed_tools">).  If this parameter is not set, a shed-related tool panel configuration
                                          file will be selected automatically.
        """
        # Get the information about the repository to be installed from the payload.
        tool_shed_url, name, owner, changeset_revision = self.__parse_repository_from_payload( payload, include_changeset=True )
        self.__ensure_can_install_repos( trans )
        irm = InstallRepositoryManager( self.app )
        installed_tool_shed_repositories = irm.install( tool_shed_url,
                                                        name,
                                                        owner,
                                                        changeset_revision,
                                                        payload )

        def to_dict( tool_shed_repository ):
            tool_shed_repository_dict = tool_shed_repository.as_dict( value_mapper=self.__get_value_mapper( trans, tool_shed_repository ) )
            tool_shed_repository_dict[ 'url' ] = web.url_for( controller='tool_shed_repositories',
                                                              action='show',
                                                              id=trans.security.encode_id( tool_shed_repository.id ) )
            return tool_shed_repository_dict
        if installed_tool_shed_repositories:
            return map( to_dict, installed_tool_shed_repositories )
        message = "No repositories were installed, possibly because the selected repository has already been installed."
        return dict( status="ok", message=message )

    @expose_api
    def install_repository_revisions( self, trans, payload, **kwd ):
        """
        POST /api/tool_shed_repositories/install_repository_revisions
        Install one or more specified repository revisions from one or more specified tool sheds into Galaxy.  The received parameters
        must be ordered lists so that positional values in tool_shed_urls, names, owners and changeset_revisions are associated.

        It's questionable whether this method is needed as the above method for installing a single repository can probably cover all
        desired scenarios.  We'll keep this one around just in case...

        :param key: the current Galaxy admin user's API key

        The following parameters are included in the payload.
        :param tool_shed_urls: the base URLs of the Tool Sheds from which to install a specified Repository
        :param names: the names of the Repositories to be installed
        :param owners: the owners of the Repositories to be installed
        :param changeset_revisions: the changeset_revisions of each RepositoryMetadata object associated with each Repository to be installed
        :param new_tool_panel_section_label: optional label of a new section to be added to the Galaxy tool panel in which to load
                                             tools contained in the Repository.  Either this parameter must be an empty string or
                                             the tool_panel_section_id parameter must be an empty string, as both cannot be used.
        :param tool_panel_section_id: optional id of the Galaxy tool panel section in which to load tools contained in the Repository.
                                      If not set, tools will be loaded outside of any sections in the tool panel.  Either this
                                      parameter must be an empty string or the tool_panel_section_id parameter must be an empty string,
                                      as both cannot be used.
        :param install_repository_dependencies (optional): Set to True if you want to install repository dependencies defined for the specified
                                                           repository being installed.  The default setting is False.
        :param install_tool_dependencies (optional): Set to True if you want to install tool dependencies defined for the specified repository being
                                                     installed.  The default setting is False.
        :param shed_tool_conf (optional): The shed-related tool panel configuration file configured in the "tool_config_file" setting in the Galaxy config file
                                          (e.g., galaxy.ini).  At least one shed-related tool panel config file is required to be configured. Setting
                                          this parameter to a specific file enables you to choose where the specified repository will be installed because
                                          the tool_path attribute of the <toolbox> from the specified file is used as the installation location
                                          (e.g., <toolbox tool_path="../shed_tools">).  If this parameter is not set, a shed-related tool panel configuration
                                          file will be selected automatically.
        """
        self.__ensure_can_install_repos( trans )
        # Get the information about all of the repositories to be installed.
        tool_shed_urls = util.listify( payload.get( 'tool_shed_urls', '' ) )
        names = util.listify( payload.get( 'names', '' ) )
        owners = util.listify( payload.get( 'owners', '' ) )
        changeset_revisions = util.listify( payload.get( 'changeset_revisions', '' ) )
        num_specified_repositories = len( tool_shed_urls )
        if len( names ) != num_specified_repositories or \
                len( owners ) != num_specified_repositories or \
                len( changeset_revisions ) != num_specified_repositories:
            message = 'Error in tool_shed_repositories API in install_repository_revisions: the received parameters must be ordered '
            message += 'lists so that positional values in tool_shed_urls, names, owners and changeset_revisions are associated.'
            log.debug( message )
            return dict( status='error', error=message )
        # Get the information about the Galaxy components (e.g., tool pane section, tool config file, etc) that will contain information
        # about each of the repositories being installed.
        # TODO: we may want to enhance this method to allow for each of the following to be associated with each repository instead of
        # forcing all repositories to use the same settings.
        install_repository_dependencies = payload.get( 'install_repository_dependencies', False )
        install_resolver_dependencies = payload.get( 'install_resolver_dependencies', False )
        install_tool_dependencies = payload.get( 'install_tool_dependencies', False )
        new_tool_panel_section_label = payload.get( 'new_tool_panel_section_label', '' )
        shed_tool_conf = payload.get( 'shed_tool_conf', None )
        tool_panel_section_id = payload.get( 'tool_panel_section_id', '' )
        all_installed_tool_shed_repositories = []
        for tool_shed_url, name, owner, changeset_revision in zip( tool_shed_urls, names, owners, changeset_revisions ):
            current_payload = dict( tool_shed_url=tool_shed_url,
                                    name=name,
                                    owner=owner,
                                    changeset_revision=changeset_revision,
                                    new_tool_panel_section_label=new_tool_panel_section_label,
                                    tool_panel_section_id=tool_panel_section_id,
                                    install_repository_dependencies=install_repository_dependencies,
                                    install_resolver_dependencies=install_resolver_dependencies,
                                    install_tool_dependencies=install_tool_dependencies,
                                    shed_tool_conf=shed_tool_conf )
            installed_tool_shed_repositories = self.install_repository_revision( trans, **current_payload )
            if isinstance( installed_tool_shed_repositories, dict ):
                # We encountered an error.
                return installed_tool_shed_repositories
            elif isinstance( installed_tool_shed_repositories, list ):
                all_installed_tool_shed_repositories.extend( installed_tool_shed_repositories )
        return all_installed_tool_shed_repositories

    @expose_api
    def repair_repository_revision( self, trans, payload, **kwd ):
        """
        POST /api/tool_shed_repositories/repair_repository_revision
        Repair a specified repository revision previously installed into Galaxy.

        :param key: the current Galaxy admin user's API key

        The following parameters are included in the payload.
        :param tool_shed_url (required): the base URL of the Tool Shed from which the Repository was installed
        :param name (required): the name of the Repository
        :param owner (required): the owner of the Repository
        :param changeset_revision (required): the changeset_revision of the RepositoryMetadata object associated with the Repository
        """
        # Get the information about the repository to be installed from the payload.
        tool_shed_url, name, owner, changeset_revision = self.__parse_repository_from_payload( payload, include_changeset=True )
        tool_shed_repositories = []
        tool_shed_repository = repository_util.get_installed_repository( self.app,
                                                                         tool_shed=tool_shed_url,
                                                                         name=name,
                                                                         owner=owner,
                                                                         changeset_revision=changeset_revision )
        rrm = RepairRepositoryManager( self.app )
        repair_dict = rrm.get_repair_dict( tool_shed_repository )
        ordered_tsr_ids = repair_dict.get( 'ordered_tsr_ids', [] )
        ordered_repo_info_dicts = repair_dict.get( 'ordered_repo_info_dicts', [] )
        if ordered_tsr_ids and ordered_repo_info_dicts:
            for index, tsr_id in enumerate( ordered_tsr_ids ):
                repository = trans.install_model.context.query( trans.install_model.ToolShedRepository ).get( trans.security.decode_id( tsr_id ) )
                repo_info_dict = ordered_repo_info_dicts[ index ]
                # TODO: handle errors in repair_dict.
                repair_dict = rrm.repair_tool_shed_repository( repository,
                                                               encoding_util.tool_shed_encode( repo_info_dict ) )
                repository_dict = repository.to_dict( value_mapper=self.__get_value_mapper( trans, repository ) )
                repository_dict[ 'url' ] = web.url_for( controller='tool_shed_repositories',
                                                        action='show',
                                                        id=trans.security.encode_id( repository.id ) )
                if repair_dict:
                    errors = repair_dict.get( repository.name, [] )
                    repository_dict[ 'errors_attempting_repair' ] = '  '.join( errors )
                tool_shed_repositories.append( repository_dict )
        # Display the list of repaired repositories.
        return tool_shed_repositories

    def __parse_repository_from_payload( self, payload, include_changeset=False ):
        # Get the information about the repository to be installed from the payload.
        tool_shed_url = payload.get( 'tool_shed_url', '' )
        if not tool_shed_url:
            raise exceptions.RequestParameterMissingException( "Missing required parameter 'tool_shed_url'." )
        name = payload.get( 'name', '' )
        if not name:
            raise exceptions.RequestParameterMissingException( "Missing required parameter 'name'." )
        owner = payload.get( 'owner', '' )
        if not owner:
            raise exceptions.RequestParameterMissingException( "Missing required parameter 'owner'." )
        if not include_changeset:
            return tool_shed_url, name, owner

        changeset_revision = payload.get( 'changeset_revision', '' )
        if not changeset_revision:
            raise HTTPBadRequest( detail="Missing required parameter 'changeset_revision'." )

        return tool_shed_url, name, owner, changeset_revision

    @expose_api
    def reset_metadata_on_installed_repositories( self, trans, payload, **kwd ):
        """
        PUT /api/tool_shed_repositories/reset_metadata_on_installed_repositories

        Resets all metadata on all repositories installed into Galaxy in an "orderly fashion".

        :param key: the API key of the Galaxy admin user.
        """
        start_time = strftime( "%Y-%m-%d %H:%M:%S" )
        results = dict( start_time=start_time,
                        successful_count=0,
                        unsuccessful_count=0,
                        repository_status=[] )
        # Make sure the current user's API key proves he is an admin user in this Galaxy instance.
        if not trans.user_is_admin():
            raise HTTPForbidden( detail='You are not authorized to reset metadata on repositories installed into this Galaxy instance.' )
        irmm = InstalledRepositoryMetadataManager( self.app )
        query = irmm.get_query_for_setting_metadata_on_repositories( order=False )
        # Now reset metadata on all remaining repositories.
        for repository in query:
            try:
                irmm.set_repository( repository )
                irmm.reset_all_metadata_on_installed_repository()
                irmm_invalid_file_tups = irmm.get_invalid_file_tups()
                if irmm_invalid_file_tups:
                    message = tool_util.generate_message_for_invalid_tools( self.app,
                                                                            irmm_invalid_file_tups,
                                                                            repository,
                                                                            None,
                                                                            as_html=False )
                    results[ 'unsuccessful_count' ] += 1
                else:
                    message = "Successfully reset metadata on repository %s owned by %s" % \
                        ( str( repository.name ), str( repository.owner ) )
                    results[ 'successful_count' ] += 1
            except Exception as e:
                message = "Error resetting metadata on repository %s owned by %s: %s" % \
                    ( str( repository.name ), str( repository.owner ), str( e ) )
                results[ 'unsuccessful_count' ] += 1
            results[ 'repository_status' ].append( message )
        stop_time = strftime( "%Y-%m-%d %H:%M:%S" )
        results[ 'stop_time' ] = stop_time
        return json.dumps( results, sort_keys=True, indent=4 )

    @expose_api
    def show( self, trans, id, **kwd ):
        """
        GET /api/tool_shed_repositories/{encoded_tool_shed_repsository_id}
        Display a dictionary containing information about a specified tool_shed_repository.

        :param id: the encoded id of the ToolShedRepository object
        """
        # Example URL: http://localhost:8763/api/tool_shed_repositories/df7a1f0c02a5b08e
        tool_shed_repository = repository_util.get_tool_shed_repository_by_id( self.app, id )
        if tool_shed_repository is None:
            log.debug( "Unable to locate tool_shed_repository record for id %s." % ( str( id ) ) )
            return {}
        tool_shed_repository_dict = tool_shed_repository.as_dict( value_mapper=self.__get_value_mapper( trans, tool_shed_repository ) )
        tool_shed_repository_dict[ 'url' ] = web.url_for( controller='tool_shed_repositories',
                                                          action='show',
                                                          id=trans.security.encode_id( tool_shed_repository.id ) )
        return tool_shed_repository_dict

    @expose_api
    @web.require_admin
    def status( self, trans, id, **kwd ):
        """
        GET /api/tool_shed_repositories/{id}/status
        Display a dictionary containing information about a specified repository's installation
        status and a list of its dependencies and the status of each.

        :param id: the repository's encoded id
        """
        tool_shed_repository = repository_util.get_tool_shed_repository_by_id( self.app, id )
        if tool_shed_repository is None:
            log.debug( "Unable to locate tool_shed_repository record for id %s." % ( str( id ) ) )
            return {}
        tool_shed_repository_dict = tool_shed_repository.as_dict( value_mapper=self.__get_value_mapper( trans, tool_shed_repository ) )
        tool_shed_repository_dict[ 'url' ] = web.url_for( controller='tool_shed_repositories',
                                                          action='show',
                                                          id=trans.security.encode_id( tool_shed_repository.id ) )
        tool_shed_repository_dict[ 'repository_dependencies' ] = self.__flatten_repository_dependency_list( trans, tool_shed_repository )
        return tool_shed_repository_dict
