import logging
import urllib2
from galaxy.util import json
from galaxy import util
from galaxy import web
from galaxy.web.base.controller import BaseAPIController
from tool_shed.galaxy_install import repository_util
import tool_shed.util.shed_util_common as suc

log = logging.getLogger( __name__ )

def default_tool_shed_repository_value_mapper( trans, tool_shed_repository ):
    value_mapper={ 'id' : trans.security.encode_id( tool_shed_repository.id ),
                   'error_message' : tool_shed_repository.error_message or '' }
    return value_mapper

def get_message_for_no_shed_tool_config():
    # This Galaxy instance is not configured with a shed-related tool panel configuration file.
    message = 'The tool_config_file setting in universe_wsgi.ini must include at least one shed tool configuration file name with a <toolbox> '
    message += 'tag that includes a tool_path attribute value which is a directory relative to the Galaxy installation directory in order to '
    message += 'automatically install tools from a tool shed into Galaxy (e.g., the file name shed_tool_conf.xml whose <toolbox> tag is '
    message += '<toolbox tool_path="../shed_tools">).  For details, see the "Installation of Galaxy tool shed repository tools into a local '
    message += 'Galaxy instance" section of the Galaxy tool shed wiki at http://wiki.galaxyproject.org/InstallingRepositoriesToGalaxy#'
    message += 'Installing_Galaxy_tool_shed_repository_tools_into_a_local_Galaxy_instance.'
    return message

class ToolShedRepositoriesController( BaseAPIController ):
    """RESTful controller for interactions with tool shed repositories."""

    @web.expose_api
    def index( self, trans, **kwd ):
        """
        GET /api/tool_shed_repositories
        Display a list of dictionaries containing information about installed tool shed repositories.
        """
        # Example URL: http://localhost:8763/api/tool_shed_repositories
        tool_shed_repository_dicts = []
        try:
            query = trans.sa_session.query( trans.app.model.ToolShedRepository ) \
                                    .order_by( trans.app.model.ToolShedRepository.table.c.name ) \
                                    .all()
            for tool_shed_repository in query:
                tool_shed_repository_dict = tool_shed_repository.get_api_value( value_mapper=default_tool_shed_repository_value_mapper( trans, tool_shed_repository ) )
                tool_shed_repository_dict[ 'url' ] = web.url_for( controller='tool_shed_repositories',
                                                                  action='show',
                                                                  id=trans.security.encode_id( tool_shed_repository.id ) )
                tool_shed_repository_dicts.append( tool_shed_repository_dict )
            return tool_shed_repository_dicts
        except Exception, e:
            message = "Error in the tool_shed_repositories API in index: %s" % str( e )
            log.error( message, exc_info=True )
            trans.response.status = 500
            return message

    @web.expose_api
    def show( self, trans, id, **kwd ):
        """
        GET /api/tool_shed_repositories/{encoded_tool_shed_repsository_id}
        Display a dictionary containing information about a specified tool_shed_repository.

        :param id: the encoded id of the ToolShedRepository object
        """
        # Example URL: http://localhost:8763/api/tool_shed_repositories/df7a1f0c02a5b08e
        try:
            tool_shed_repository = suc.get_tool_shed_repository_by_id( trans, id )
            tool_shed_repository_dict = tool_shed_repository.as_dict( value_mapper=default_tool_shed_repository_value_mapper( trans, tool_shed_repository ) )
            tool_shed_repository_dict[ 'url' ] = web.url_for( controller='tool_shed_repositories',
                                                              action='show',
                                                              id=trans.security.encode_id( tool_shed_repository.id ) )
            return tool_shed_repository_dict
        except Exception, e:
            message = "Error in tool_shed_repositories API in index: " + str( e )
            log.error( message, exc_info=True )
            trans.response.status = 500
            return message

    @web.expose_api
    def install_repository_revision( self, trans, payload, **kwd ):
        """
        POST /api/tool_shed_repositories/install_repository_revision
        Install a specified repository revision from a specified tool shed into Galaxy.
        
        :param key: the current Galaxy admin user's API key
        
        The following parameters are included in the payload.
        :param tool_shed_url (required): the base URL of the Tool Shed from which to install the Repository
        :param name (required): the name of the Repository
        :param owner (required): the owner of the Repository
        :param changset_revision (required): the changset_revision of the RepositoryMetadata object associated with the Repository
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
                                          (e.g., universe_wsgi.ini).  At least one shed-related tool panel config file is required to be configured. Setting
                                          this parameter to a specific file enables you to choose where the specified repository will be installed because
                                          the tool_path attribute of the <toolbox> from the specified file is used as the installation location
                                          (e.g., <toolbox tool_path="../shed_tools">).  If this parameter is not set, a shed-related tool panel configuration
                                          file will be selected automatically.
        """
        # Get the information about the repository to be installed from the payload.
        tool_shed_url = payload.get( 'tool_shed_url', '' )
        if not tool_shed_url:
            raise HTTPBadRequest( detail="Missing required parameter 'tool_shed_url'." )
        name = payload.get( 'name', '' )
        if not name:
            raise HTTPBadRequest( detail="Missing required parameter 'name'." )
        owner = payload.get( 'owner', '' )
        if not owner:
            raise HTTPBadRequest( detail="Missing required parameter 'owner'." )
        changeset_revision = payload.get( 'changeset_revision', '' )
        if not changeset_revision:
            raise HTTPBadRequest( detail="Missing required parameter 'changeset_revision'." )
        # Make sure this Galaxy instance is configured with a shed-related tool panel configuration file.
        if not suc.have_shed_tool_conf_for_install( trans ):
            message = get_message_for_no_shed_tool_config()
            log.error( message, exc_info=True )
            trans.response.status = 500
            return dict( status='error', error=message )
        # Make sure the current user's API key proves he is an admin user in this Galaxy instance.
        if not trans.user_is_admin():
            raise HTTPForbidden( detail='You are not authorized to install a tool shed repository into this Galaxy instance.' )
        # Keep track of all repositories that are installed - there may be more than one if repository dependencies are installed.
        installed_tool_shed_repositories = []
        # Get all of the information necessary for installing the repository from the specified tool shed.
        url = suc.url_join( tool_shed_url,
                            'api/repositories/get_repository_revision_install_info?name=%s&owner=%s&changeset_revision=%s' % \
                            ( name, owner, changeset_revision ) )
        try:
            response = urllib2.urlopen( url )
            raw_text = response.read()
            response.close()
        except Exception, e:
            message = "Error attempting to retrieve installation information from tool shed %s for revision %s of repository %s owned by %s: %s" % \
                ( str( tool_shed_url ), str( changeset_revision ), str( name ), str( owner ), str( e ) )
            log.error( message, exc_info=True )
            trans.response.status = 500
            return dict( status='error', error=message )
        if raw_text:
            items = json.from_json_string( raw_text )
            repository_dict = items[ 0 ]
            repository_revision_dict = items[ 1 ]
            repo_info_dict = items[ 2 ]
        else:
            message = "Unable to retrieve installation information from tool shed %s for revision %s of repository %s owned by %s: %s" % \
                ( str( tool_shed_url ), str( changeset_revision ), str( name ), str( owner ), str( e ) )
            log.error( message, exc_info=True )
            trans.response.status = 500
            return dict( status='error', error=message )
        repo_info_dicts = [ repo_info_dict ]
        # Make sure the tool shed returned everything we need for installing the repository.
        try:
            has_repository_dependencies = repository_revision_dict[ 'has_repository_dependencies' ]
        except:
            raise HTTPBadRequest( detail="Missing required parameter 'has_repository_dependencies'." )
        try:
            includes_tools = repository_revision_dict[ 'includes_tools' ]
        except:
            raise HTTPBadRequest( detail="Missing required parameter 'includes_tools'." )
        try:
            includes_tool_dependencies = repository_revision_dict[ 'includes_tool_dependencies' ]
        except:
            raise HTTPBadRequest( detail="Missing required parameter 'includes_tool_dependencies'." )
        try:
            includes_tools_for_display_in_tool_panel = repository_revision_dict[ 'includes_tools_for_display_in_tool_panel' ]
        except:
            raise HTTPBadRequest( detail="Missing required parameter 'includes_tools_for_display_in_tool_panel'." )
        # Get the information about the Galaxy components (e.g., tool pane section, tool config file, etc) that will contain the repository information.
        install_repository_dependencies = payload.get( 'install_repository_dependencies', False )
        install_tool_dependencies = payload.get( 'install_tool_dependencies', False )
        new_tool_panel_section = payload.get( 'new_tool_panel_section_label', '' )
        shed_tool_conf = payload.get( 'shed_tool_conf', None )
        if shed_tool_conf:
            # Get the tool_path setting.
            index, shed_conf_dict = suc.get_shed_tool_conf_dict( trans.app, shed_tool_conf )
            tool_path = shed_config_dict[ 'tool_path' ]
        else:
            # Pick a semi-random shed-related tool panel configuration file and get the tool_path setting.
            for shed_config_dict in trans.app.toolbox.shed_tool_confs:
                # Don't use migrated_tools_conf.xml.
                if shed_config_dict[ 'config_filename' ] != trans.app.config.migrated_tools_config:
                    break
            shed_tool_conf = shed_config_dict[ 'config_filename' ]
            tool_path = shed_config_dict[ 'tool_path' ]
        if not shed_tool_conf:
            raise HTTPBadRequest( detail="Missing required parameter 'shed_tool_conf'." )
        tool_panel_section_id = payload.get( 'tool_panel_section_id', '' )
        if tool_panel_section_id not in [ None, '' ]:
            tool_panel_section = trans.app.toolbox.tool_panel[ tool_panel_section_id ]
        else:
            tool_panel_section = ''
        # Build the dictionary of information necessary for creating tool_shed_repository database records for each repository being installed.
        installation_dict = dict( install_repository_dependencies=install_repository_dependencies,
                                  new_tool_panel_section=new_tool_panel_section,
                                  no_changes_checked=False,
                                  reinstalling=False,
                                  repo_info_dicts=repo_info_dicts,
                                  tool_panel_section=tool_panel_section,
                                  tool_path=tool_path,
                                  tool_shed_url=tool_shed_url )
        # Create the tool_shed_repository database records and gather additional information for repository installation.
        created_or_updated_tool_shed_repositories, tool_panel_section_keys, repo_info_dicts, filtered_repo_info_dicts, message = \
            repository_util.handle_tool_shed_repositories( trans, installation_dict, using_api=True )
        if message and len( repo_info_dicts ) == 1:
            # We're attempting to install a single repository that has already been installed into this Galaxy instance.
            log.error( message, exc_info=True )
            trans.response.status = 500
            return dict( status='error', error=message )
        if created_or_updated_tool_shed_repositories:
            # Build the dictionary of information necessary for installing the repositories.
            installation_dict = dict( created_or_updated_tool_shed_repositories=created_or_updated_tool_shed_repositories,
                                      filtered_repo_info_dicts=filtered_repo_info_dicts,
                                      has_repository_dependencies=has_repository_dependencies,
                                      includes_tool_dependencies=includes_tool_dependencies,
                                      includes_tools=includes_tools,
                                      includes_tools_for_display_in_tool_panel=includes_tools_for_display_in_tool_panel,
                                      install_repository_dependencies=install_repository_dependencies,
                                      install_tool_dependencies=install_tool_dependencies,
                                      message='',
                                      new_tool_panel_section=new_tool_panel_section,
                                      shed_tool_conf=shed_tool_conf,
                                      status='done',
                                      tool_panel_section=tool_panel_section,
                                      tool_panel_section_keys=tool_panel_section_keys,
                                      tool_path=tool_path,
                                      tool_shed_url=tool_shed_url )
            # Prepare the repositories for installation.  Even though this method receives a single combination of tool_shed_url, name, owner and
            # changeset_revision, there may be multiple repositories for installation at this point because repository dependencies may have added
            # additional repositories for installation along with the single specified repository.
            encoded_kwd, query, tool_shed_repositories, encoded_repository_ids = repository_util.initiate_repository_installation( trans, installation_dict )
            # Install the repositories, keeping track of each one for later display.
            for index, tool_shed_repository in enumerate( tool_shed_repositories ):
                repo_info_dict = repo_info_dicts[ index ]
                tool_panel_section_key = tool_panel_section_keys[ index ]
                repository_util.install_tool_shed_repository( trans,
                                                              tool_shed_repository,
                                                              repo_info_dict,
                                                              tool_panel_section_key,
                                                              shed_tool_conf,
                                                              tool_path,
                                                              install_tool_dependencies,
                                                              reinstalling=False )
                tool_shed_repository_dict = tool_shed_repository.as_dict( value_mapper=default_tool_shed_repository_value_mapper( trans, tool_shed_repository ) )
                tool_shed_repository_dict[ 'url' ] = web.url_for( controller='tool_shed_repositories',
                                                                  action='show',
                                                                  id=trans.security.encode_id( tool_shed_repository.id ) )
                installed_tool_shed_repositories.append( tool_shed_repository_dict )
        else:
            log.error( message, exc_info=True )
            trans.response.status = 500
            return dict( status='error', error=message )
        # Display the list of installed repositories.
        return installed_tool_shed_repositories

    @web.expose_api
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
        :param changset_revisions: the changset_revisions of each RepositoryMetadata object associated with each Repository to be installed
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
                                          (e.g., universe_wsgi.ini).  At least one shed-related tool panel config file is required to be configured. Setting
                                          this parameter to a specific file enables you to choose where the specified repository will be installed because
                                          the tool_path attribute of the <toolbox> from the specified file is used as the installation location
                                          (e.g., <toolbox tool_path="../shed_tools">).  If this parameter is not set, a shed-related tool panel configuration
                                          file will be selected automatically.
        """
        if not suc.have_shed_tool_conf_for_install( trans ):
            # This Galaxy instance is not configured with a shed-related tool panel configuration file.
            message = get_message_for_no_shed_tool_config()
            log.error( message, exc_info=True )
            trans.response.status = 500
            return dict( status='error', error=message )
        if not trans.user_is_admin():
            raise HTTPForbidden( detail='You are not authorized to install a tool shed repository into this Galaxy instance.' )
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
            log.error( message, exc_info=True )
            trans.response.status = 500
            return dict( status='error', error=message )
        # Get the information about the Galaxy components (e.g., tool pane section, tool config file, etc) that will contain information
        # about each of the repositories being installed.
        # TODO: we may want to enhance this method to allow for each of the following to be associated with each repository instead of
        # forcing all repositories to use the same settings.
        install_repository_dependencies = payload.get( 'install_repository_dependencies', False )
        install_tool_dependencies = payload.get( 'install_tool_dependencies', False )
        new_tool_panel_section_label = payload.get( 'new_tool_panel_section_label', '' )
        shed_tool_conf = payload.get( 'shed_tool_conf', None )
        tool_path = payload.get( 'tool_path', None )
        tool_panel_section_id = payload.get( 'tool_panel_section_id', '' )
        all_installed_tool_shed_repositories = []
        for index, tool_shed_url in enumerate( tool_shed_urls ):
            current_payload = {}
            current_payload[ 'tool_shed_url' ] = tool_shed_url
            current_payload[ 'name' ] = names[ index ]
            current_payload[ 'owner' ] = owners[ index ]
            current_payload[ 'changeset_revision' ] = changeset_revisions[ index ]
            current_payload[ 'new_tool_panel_section_label' ] = new_tool_panel_section_label
            current_payload[ 'tool_panel_section_id' ] = tool_panel_section_id
            current_payload[ 'install_repository_dependencies' ] = install_repository_dependencies
            current_payload[ 'install_tool_dependencies' ] = install_tool_dependencies
            current_payload[ 'shed_tool_conf' ] = shed_tool_conf
            installed_tool_shed_repositories = self.install_repository_revision( trans, **current_payload )
            if isinstance( installed_tool_shed_repositories, dict ):
                # We encountered an error.
                return installed_tool_shed_repositories
            elif isinstance( installed_tool_shed_repositories, list ):
                all_installed_tool_shed_repositories.extend( installed_tool_shed_repositories )
        return all_installed_tool_shed_repositories
    
