import json
import logging
import os
import threading

from galaxy import util

from tool_shed.galaxy_install.utility_containers import GalaxyUtilityContainerManager
from tool_shed.utility_containers import utility_container_manager

from tool_shed.util import common_util
from tool_shed.util import container_util
from tool_shed.util import readme_util
from tool_shed.util import shed_util_common as suc
from tool_shed.util import tool_dependency_util

log = logging.getLogger( __name__ )


class DependencyDisplayer( object ):

    def __init__( self, app ):
        self.app = app

    def add_installation_directories_to_tool_dependencies( self, tool_dependencies ):
        """
        Determine the path to the installation directory for each of the received
        tool dependencies.  This path will be displayed within the tool dependencies
        container on the select_tool_panel_section or reselect_tool_panel_section
        pages when installing or reinstalling repositories that contain tools with
        the defined tool dependencies.  The list of tool dependencies may be associated
        with more than a single repository.
        """
        for dependency_key, requirements_dict in tool_dependencies.items():
            if dependency_key in [ 'set_environment' ]:
                continue
            repository_name = requirements_dict.get( 'repository_name', 'unknown' )
            repository_owner = requirements_dict.get( 'repository_owner', 'unknown' )
            changeset_revision = requirements_dict.get( 'changeset_revision', 'unknown' )
            dependency_name = requirements_dict[ 'name' ]
            version = requirements_dict[ 'version' ]
            type = requirements_dict[ 'type' ]
            if self.app.config.tool_dependency_dir:
                root_dir = self.app.config.tool_dependency_dir
            else:
                root_dir = '<set your tool_dependency_dir in your Galaxy configuration file>'
            install_dir = os.path.join( root_dir,
                                        dependency_name,
                                        version,
                                        repository_owner,
                                        repository_name,
                                        changeset_revision )
            requirements_dict[ 'install_dir' ] = install_dir
            tool_dependencies[ dependency_key ] = requirements_dict
        return tool_dependencies

    def generate_message_for_invalid_repository_dependencies( self, metadata_dict, error_from_tuple=False ):
        """
        Get or generate and return an error message associated with an invalid repository dependency.
        """
        message = ''
        if metadata_dict:
            if error_from_tuple:
                # Return the error messages associated with a set of one or more invalid repository
                # dependency tuples.
                invalid_repository_dependencies_dict = metadata_dict.get( 'invalid_repository_dependencies', None )
                if invalid_repository_dependencies_dict is not None:
                    invalid_repository_dependencies = \
                        invalid_repository_dependencies_dict.get( 'invalid_repository_dependencies', [] )
                    for repository_dependency_tup in invalid_repository_dependencies:
                        toolshed, \
                        name, \
                        owner, \
                        changeset_revision, \
                        prior_installation_required, \
                        only_if_compiling_contained_td, error = \
                            common_util.parse_repository_dependency_tuple( repository_dependency_tup, contains_error=True )
                        if error:
                            message += '%s  ' % str( error )
            else:
                # The complete dependency hierarchy could not be determined for a repository being installed into
                # Galaxy.  This is likely due to invalid repository dependency definitions, so we'll get them from
                # the metadata and parse them for display in an error message.  This will hopefully communicate the
                # problem to the user in such a way that a resolution can be determined.
                message += 'The complete dependency hierarchy could not be determined for this repository, so no required '
                message += 'repositories will not be installed.  This is likely due to invalid repository dependency definitions.  '
                repository_dependencies_dict = metadata_dict.get( 'repository_dependencies', None )
                if repository_dependencies_dict is not None:
                    rd_tups = repository_dependencies_dict.get( 'repository_dependencies', None )
                    if rd_tups is not None:
                        message += 'Here are the attributes of the dependencies defined for this repository to help determine the '
                        message += 'cause of this problem.<br/>'
                        message += '<table cellpadding="2" cellspacing="2">'
                        message += '<tr><th>Tool shed</th><th>Repository name</th><th>Owner</th><th>Changeset revision</th>'
                        message += '<th>Prior install required</th></tr>'
                        for rd_tup in rd_tups:
                            tool_shed, name, owner, changeset_revision, pir, oicct = \
                                common_util.parse_repository_dependency_tuple( rd_tup )
                            if util.asbool( pir ):
                                pir_str = 'True'
                            else:
                                pir_str = ''
                            message += '<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % \
                                ( tool_shed, name, owner, changeset_revision, pir_str )
                        message += '</table>'
        return message

    def generate_message_for_invalid_tool_dependencies( self, metadata_dict ):
        """
        Tool dependency definitions can only be invalid if they include a definition for a complex
        repository dependency and the repository dependency definition is invalid.  This method
        retrieves the error message associated with the invalid tool dependency for display in the
        caller.
        """
        message = ''
        if metadata_dict:
            invalid_tool_dependencies = metadata_dict.get( 'invalid_tool_dependencies', None )
            if invalid_tool_dependencies:
                for td_key, requirement_dict in invalid_tool_dependencies.items():
                    error = requirement_dict.get( 'error', None )
                    if error:
                        message = '%s  ' % str( error )
        return message

    def generate_message_for_orphan_tool_dependencies( self, repository, metadata_dict ):
        """
        The designation of a ToolDependency into the "orphan" category has evolved over time,
        and is significantly restricted since the introduction of the TOOL_DEPENDENCY_DEFINITION
        repository type.  This designation is still critical, however, in that it handles the
        case where a repository contains both tools and a tool_dependencies.xml file, but the
        definition in the tool_dependencies.xml file is in no way related to anything defined
        by any of the contained tool's requirements tag sets.  This is important in that it is
        often a result of a typo (e.g., dependency name or version) that differs between the tool
        dependency definition within the tool_dependencies.xml file and what is defined in the
        tool config's <requirements> tag sets.  In these cases, the user should be presented with
        a warning message, and this warning message is is in fact displayed if the following
        is_orphan attribute is True.  This is tricky because in some cases it may be intentional,
        and tool dependencies that are categorized as "orphan" are in fact valid.
        """
        has_orphan_package_dependencies = False
        has_orphan_set_environment_dependencies = False
        message = ''
        package_orphans_str = ''
        set_environment_orphans_str = ''
        # Tool dependencies are categorized as orphan only if the repository contains tools.
        if metadata_dict:
            tools = metadata_dict.get( 'tools', [] )
            invalid_tools = metadata_dict.get( 'invalid_tools', [] )
            tool_dependencies = metadata_dict.get( 'tool_dependencies', {} )
            # The use of the orphan_tool_dependencies category in metadata has been deprecated,
            # but we still need to check in case the metadata is out of date.
            orphan_tool_dependencies = metadata_dict.get( 'orphan_tool_dependencies', {} )
            # Updating should cause no problems here since a tool dependency cannot be included
            # in both dictionaries.
            tool_dependencies.update( orphan_tool_dependencies )
            if tool_dependencies and tools:
                for td_key, requirements_dict in tool_dependencies.items():
                    if td_key == 'set_environment':
                        # "set_environment": [{"name": "R_SCRIPT_PATH", "type": "set_environment"}]
                        for env_requirements_dict in requirements_dict:
                            name = env_requirements_dict[ 'name' ]
                            type = env_requirements_dict[ 'type' ]
                            if self.tool_dependency_is_orphan( type, name, None, tools ):
                                if not has_orphan_set_environment_dependencies:
                                    has_orphan_set_environment_dependencies = True
                                set_environment_orphans_str += "<b>* name:</b> %s, <b>type:</b> %s<br/>" % \
                                    ( str( name ), str( type ) )
                    else:
                        # "R/2.15.1": {"name": "R", "readme": "some string", "type": "package", "version": "2.15.1"}
                        name = requirements_dict[ 'name' ]
                        type = requirements_dict[ 'type' ]
                        version = requirements_dict[ 'version' ]
                        if self.tool_dependency_is_orphan( type, name, version, tools ):
                            if not has_orphan_package_dependencies:
                                has_orphan_package_dependencies = True
                            package_orphans_str += "<b>* name:</b> %s, <b>type:</b> %s, <b>version:</b> %s<br/>" % \
                                ( str( name ), str( type ), str( version ) )
        if has_orphan_package_dependencies:
            message += "The settings for <b>name</b>, <b>version</b> and <b>type</b> from a "
            message += "contained tool configuration file's <b>requirement</b> tag does not match "
            message += "the information for the following tool dependency definitions in the "
            message += "<b>tool_dependencies.xml</b> file, so these tool dependencies have no "
            message += "relationship with any tools within this repository.<br/>"
            message += package_orphans_str
        if has_orphan_set_environment_dependencies:
            message += "The settings for <b>name</b> and <b>type</b> from a contained tool "
            message += "configuration file's <b>requirement</b> tag does not match the information "
            message += "for the following tool dependency definitions in the <b>tool_dependencies.xml</b> "
            message += "file, so these tool dependencies have no relationship with any tools within "
            message += "this repository.<br/>"
            message += set_environment_orphans_str
        return message

    def get_installed_and_missing_tool_dependencies_for_installed_repository( self, repository, all_tool_dependencies ):
        """
        Return the lists of installed tool dependencies and missing tool dependencies for a Tool Shed
        repository that has been installed into Galaxy.
        """
        if all_tool_dependencies:
            tool_dependencies = {}
            missing_tool_dependencies = {}
            for td_key, val in all_tool_dependencies.items():
                if td_key in [ 'set_environment' ]:
                    for index, td_info_dict in enumerate( val ):
                        name = td_info_dict[ 'name' ]
                        version = None
                        type = td_info_dict[ 'type' ]
                        tool_dependency = tool_dependency_util.get_tool_dependency_by_name_type_repository( self.app,
                                                                                                            repository,
                                                                                                            name,
                                                                                                            type )
                        if tool_dependency:
                            td_info_dict[ 'repository_id' ] = repository.id
                            td_info_dict[ 'tool_dependency_id' ] = tool_dependency.id
                            if tool_dependency.status:
                                tool_dependency_status = str( tool_dependency.status )
                            else:
                                tool_dependency_status = 'Never installed'
                            td_info_dict[ 'status' ] = tool_dependency_status
                            val[ index ] = td_info_dict
                            if tool_dependency.status == self.app.install_model.ToolDependency.installation_status.INSTALLED:
                                tool_dependencies[ td_key ] = val
                            else:
                                missing_tool_dependencies[ td_key ] = val
                else:
                    name = val[ 'name' ]
                    version = val[ 'version' ]
                    type = val[ 'type' ]
                    tool_dependency = tool_dependency_util.get_tool_dependency_by_name_version_type_repository( self.app,
                                                                                                                repository,
                                                                                                                name,
                                                                                                                version,
                                                                                                                type )
                    if tool_dependency:
                        val[ 'repository_id' ] = repository.id
                        val[ 'tool_dependency_id' ] = tool_dependency.id
                        if tool_dependency.status:
                            tool_dependency_status = str( tool_dependency.status )
                        else:
                            tool_dependency_status = 'Never installed'
                        val[ 'status' ] = tool_dependency_status
                        if tool_dependency.status == self.app.install_model.ToolDependency.installation_status.INSTALLED:
                            tool_dependencies[ td_key ] = val
                        else:
                            missing_tool_dependencies[ td_key ] = val
        else:
            tool_dependencies = None
            missing_tool_dependencies = None
        return tool_dependencies, missing_tool_dependencies

    def merge_containers_dicts_for_new_install( self, containers_dicts ):
        """
        When installing one or more tool shed repositories for the first time, the received list of
        containers_dicts contains a containers_dict for each repository being installed.  Since the
        repositories are being installed for the first time, all entries are None except the repository
        dependencies and tool dependencies.  The entries for missing dependencies are all None since
        they have previously been merged into the installed dependencies.  This method will merge the
        dependencies entries into a single container and return it for display.
        """
        new_containers_dict = dict( readme_files=None,
                                    datatypes=None,
                                    missing_repository_dependencies=None,
                                    repository_dependencies=None,
                                    missing_tool_dependencies=None,
                                    tool_dependencies=None,
                                    invalid_tools=None,
                                    valid_tools=None,
                                    workflows=None )
        if containers_dicts:
            lock = threading.Lock()
            lock.acquire( True )
            try:
                repository_dependencies_root_folder = None
                tool_dependencies_root_folder = None
                # Use a unique folder id (hopefully the following is).
                folder_id = 867
                for old_container_dict in containers_dicts:
                    # Merge repository_dependencies.
                    old_container_repository_dependencies_root = old_container_dict[ 'repository_dependencies' ]
                    if old_container_repository_dependencies_root:
                        if repository_dependencies_root_folder is None:
                            repository_dependencies_root_folder = utility_container_manager.Folder( id=folder_id,
                                                                                                    key='root',
                                                                                                    label='root',
                                                                                                    parent=None )
                            folder_id += 1
                            repository_dependencies_folder = utility_container_manager.Folder( id=folder_id,
                                                                                               key='merged',
                                                                                               label='Repository dependencies',
                                                                                               parent=repository_dependencies_root_folder )
                            folder_id += 1
                        # The old_container_repository_dependencies_root will be a root folder containing a single sub_folder.
                        old_container_repository_dependencies_folder = old_container_repository_dependencies_root.folders[ 0 ]
                        # Change the folder id so it won't confict with others being merged.
                        old_container_repository_dependencies_folder.id = folder_id
                        folder_id += 1
                        repository_components_tuple = \
                            container_util.get_components_from_key( old_container_repository_dependencies_folder.key )
                        components_list = suc.extract_components_from_tuple( repository_components_tuple )
                        name = components_list[ 1 ]
                        # Generate the label by retrieving the repository name.
                        old_container_repository_dependencies_folder.label = str( name )
                        repository_dependencies_folder.folders.append( old_container_repository_dependencies_folder )
                    # Merge tool_dependencies.
                    old_container_tool_dependencies_root = old_container_dict[ 'tool_dependencies' ]
                    if old_container_tool_dependencies_root:
                        if tool_dependencies_root_folder is None:
                            tool_dependencies_root_folder = utility_container_manager.Folder( id=folder_id,
                                                                                              key='root',
                                                                                              label='root',
                                                                                              parent=None )
                            folder_id += 1
                            tool_dependencies_folder = utility_container_manager.Folder( id=folder_id,
                                                                                         key='merged',
                                                                                         label='Tool dependencies',
                                                                                         parent=tool_dependencies_root_folder )
                            folder_id += 1
                        else:
                            td_list = [ td.listify for td in tool_dependencies_folder.tool_dependencies ]
                            # The old_container_tool_dependencies_root will be a root folder containing a single sub_folder.
                            old_container_tool_dependencies_folder = old_container_tool_dependencies_root.folders[ 0 ]
                            for td in old_container_tool_dependencies_folder.tool_dependencies:
                                if td.listify not in td_list:
                                    tool_dependencies_folder.tool_dependencies.append( td )
                if repository_dependencies_root_folder:
                    repository_dependencies_root_folder.folders.append( repository_dependencies_folder )
                    new_containers_dict[ 'repository_dependencies' ] = repository_dependencies_root_folder
                if tool_dependencies_root_folder:
                    tool_dependencies_root_folder.folders.append( tool_dependencies_folder )
                    new_containers_dict[ 'tool_dependencies' ] = tool_dependencies_root_folder
            except Exception, e:
                log.debug( "Exception in merge_containers_dicts_for_new_install: %s" % str( e ) )
            finally:
                lock.release()
        return new_containers_dict

    def merge_missing_repository_dependencies_to_installed_container( self, containers_dict ):
        """
        Merge the list of missing repository dependencies into the list of installed
        repository dependencies.
        """
        missing_rd_container_root = containers_dict.get( 'missing_repository_dependencies', None )
        if missing_rd_container_root:
            # The missing_rd_container_root will be a root folder containing a single sub_folder.
            missing_rd_container = missing_rd_container_root.folders[ 0 ]
            installed_rd_container_root = containers_dict.get( 'repository_dependencies', None )
            # The installed_rd_container_root will be a root folder containing a single sub_folder.
            if installed_rd_container_root:
                installed_rd_container = installed_rd_container_root.folders[ 0 ]
                installed_rd_container.label = 'Repository dependencies'
                for index, rd in enumerate( missing_rd_container.repository_dependencies ):
                    # Skip the header row.
                    if index == 0:
                        continue
                    installed_rd_container.repository_dependencies.append( rd )
                installed_rd_container_root.folders = [ installed_rd_container ]
                containers_dict[ 'repository_dependencies' ] = installed_rd_container_root
            else:
                # Change the folder label from 'Missing repository dependencies' to be
                # 'Repository dependencies' for display.
                root_container = containers_dict[ 'missing_repository_dependencies' ]
                for sub_container in root_container.folders:
                    # There should only be 1 sub-folder.
                    sub_container.label = 'Repository dependencies'
                containers_dict[ 'repository_dependencies' ] = root_container
        containers_dict[ 'missing_repository_dependencies' ] = None
        return containers_dict

    def merge_missing_tool_dependencies_to_installed_container( self, containers_dict ):
        """
        Merge the list of missing tool dependencies into the list of installed tool
        dependencies.
        """
        missing_td_container_root = containers_dict.get( 'missing_tool_dependencies', None )
        if missing_td_container_root:
            # The missing_td_container_root will be a root folder containing a single sub_folder.
            missing_td_container = missing_td_container_root.folders[ 0 ]
            installed_td_container_root = containers_dict.get( 'tool_dependencies', None )
            # The installed_td_container_root will be a root folder containing a single sub_folder.
            if installed_td_container_root:
                installed_td_container = installed_td_container_root.folders[ 0 ]
                installed_td_container.label = 'Tool dependencies'
                for index, td in enumerate( missing_td_container.tool_dependencies ):
                    # Skip the header row.
                    if index == 0:
                        continue
                    installed_td_container.tool_dependencies.append( td )
                installed_td_container_root.folders = [ installed_td_container ]
                containers_dict[ 'tool_dependencies' ] = installed_td_container_root
            else:
                # Change the folder label from 'Missing tool dependencies' to be
                # 'Tool dependencies' for display.
                root_container = containers_dict[ 'missing_tool_dependencies' ]
                for sub_container in root_container.folders:
                    # There should only be 1 subfolder.
                    sub_container.label = 'Tool dependencies'
                containers_dict[ 'tool_dependencies' ] = root_container
        containers_dict[ 'missing_tool_dependencies' ] = None
        return containers_dict

    def populate_containers_dict_for_new_install( self, tool_shed_url, tool_path, readme_files_dict,
                                                  installed_repository_dependencies, missing_repository_dependencies,
                                                  installed_tool_dependencies, missing_tool_dependencies,
                                                  updating=False ):
        """
        Return the populated containers for a repository being installed for the first time
        or for an installed repository that is being updated and the updates include newly
        defined repository (and possibly tool) dependencies.
        """
        installed_tool_dependencies, missing_tool_dependencies = \
            self.populate_tool_dependencies_dicts( tool_shed_url=tool_shed_url,
                                                   tool_path=tool_path,
                                                   repository_installed_tool_dependencies=installed_tool_dependencies,
                                                   repository_missing_tool_dependencies=missing_tool_dependencies,
                                                   required_repo_info_dicts=None )
        # Most of the repository contents are set to None since we don't yet know what they are.
        gucm = GalaxyUtilityContainerManager( self.app )
        containers_dict = gucm.build_repository_containers( repository=None,
                                                            datatypes=None,
                                                            invalid_tools=None,
                                                            missing_repository_dependencies=missing_repository_dependencies,
                                                            missing_tool_dependencies=missing_tool_dependencies,
                                                            readme_files_dict=readme_files_dict,
                                                            repository_dependencies=installed_repository_dependencies,
                                                            tool_dependencies=installed_tool_dependencies,
                                                            valid_tools=None,
                                                            workflows=None,
                                                            valid_data_managers=None,
                                                            invalid_data_managers=None,
                                                            data_managers_errors=None,
                                                            new_install=True,
                                                            reinstalling=False )
        if not updating:
            # If we installing a new repository and not updaing an installed repository, we can merge
            # the missing_repository_dependencies container contents to the installed_repository_dependencies
            # container.  When updating an installed repository, merging will result in losing newly defined
            # dependencies included in the updates.
            containers_dict = self.merge_missing_repository_dependencies_to_installed_container( containers_dict )
            # Merge the missing_tool_dependencies container contents to the installed_tool_dependencies container.
            containers_dict = self.merge_missing_tool_dependencies_to_installed_container( containers_dict )
        return containers_dict

    def populate_containers_dict_from_repository_metadata( self, tool_shed_url, tool_path, repository, reinstalling=False,
                                                           required_repo_info_dicts=None ):
        """
        Retrieve necessary information from the received repository's metadata to populate the
        containers_dict for display.  This method is called only from Galaxy (not the tool shed)
        when displaying repository dependencies for installed repositories and when displaying
        them for uninstalled repositories that are being reinstalled.
        """
        metadata = repository.metadata
        if metadata:
            # Handle proprietary datatypes.
            datatypes = metadata.get( 'datatypes', None )
            # Handle invalid tools.
            invalid_tools = metadata.get( 'invalid_tools', None )
            # Handle README files.
            if repository.has_readme_files:
                if reinstalling or repository.status not in \
                    [ self.app.install_model.ToolShedRepository.installation_status.DEACTIVATED,
                      self.app.install_model.ToolShedRepository.installation_status.INSTALLED ]:
                    # Since we're reinstalling, we need to send a request to the tool shed to get the README files.
                    tool_shed_url = common_util.get_tool_shed_url_from_tool_shed_registry( self.app, tool_shed_url )
                    params = '?name=%s&owner=%s&changeset_revision=%s' % ( str( repository.name ),
                                                                           str( repository.owner ),
                                                                           str( repository.installed_changeset_revision ) )
                    url = common_util.url_join( tool_shed_url,
                                                'repository/get_readme_files%s' % params )
                    raw_text = common_util.tool_shed_get( self.app, tool_shed_url, url )
                    readme_files_dict = json.loads( raw_text )
                else:
                    readme_files_dict = readme_util.build_readme_files_dict( self.app,
                                                                             repository,
                                                                             repository.changeset_revision,
                                                                             repository.metadata, tool_path )
            else:
                readme_files_dict = None
            # Handle repository dependencies.
            installed_repository_dependencies, missing_repository_dependencies = \
                self.app.installed_repository_manager.get_installed_and_missing_repository_dependencies( repository )
            # Handle the current repository's tool dependencies.
            repository_tool_dependencies = metadata.get( 'tool_dependencies', None )
            # Make sure to display missing tool dependencies as well.
            repository_invalid_tool_dependencies = metadata.get( 'invalid_tool_dependencies', None )
            if repository_invalid_tool_dependencies is not None:
                if repository_tool_dependencies is None:
                    repository_tool_dependencies = {}
                repository_tool_dependencies.update( repository_invalid_tool_dependencies )
            repository_installed_tool_dependencies, repository_missing_tool_dependencies = \
                self.get_installed_and_missing_tool_dependencies_for_installed_repository( repository,
                                                                                           repository_tool_dependencies )
            if reinstalling:
                installed_tool_dependencies, missing_tool_dependencies = \
                    self.populate_tool_dependencies_dicts( tool_shed_url,
                                                           tool_path,
                                                           repository_installed_tool_dependencies,
                                                           repository_missing_tool_dependencies,
                                                           required_repo_info_dicts )
            else:
                installed_tool_dependencies = repository_installed_tool_dependencies
                missing_tool_dependencies = repository_missing_tool_dependencies
            # Handle valid tools.
            valid_tools = metadata.get( 'tools', None )
            # Handle workflows.
            workflows = metadata.get( 'workflows', None )
            # Handle Data Managers
            valid_data_managers = None
            invalid_data_managers = None
            data_managers_errors = None
            if 'data_manager' in metadata:
                valid_data_managers = metadata['data_manager'].get( 'data_managers', None )
                invalid_data_managers = metadata['data_manager'].get( 'invalid_data_managers', None )
                data_managers_errors = metadata['data_manager'].get( 'messages', None )
            gucm = GalaxyUtilityContainerManager( self.app )
            containers_dict = gucm.build_repository_containers( repository=repository,
                                                                datatypes=datatypes,
                                                                invalid_tools=invalid_tools,
                                                                missing_repository_dependencies=missing_repository_dependencies,
                                                                missing_tool_dependencies=missing_tool_dependencies,
                                                                readme_files_dict=readme_files_dict,
                                                                repository_dependencies=installed_repository_dependencies,
                                                                tool_dependencies=installed_tool_dependencies,
                                                                valid_tools=valid_tools,
                                                                workflows=workflows,
                                                                valid_data_managers=valid_data_managers,
                                                                invalid_data_managers=invalid_data_managers,
                                                                data_managers_errors=data_managers_errors,
                                                                new_install=False,
                                                                reinstalling=reinstalling )
        else:
            containers_dict = dict( datatypes=None,
                                    invalid_tools=None,
                                    readme_files_dict=None,
                                    repository_dependencies=None,
                                    tool_dependencies=None,
                                    valid_tools=None,
                                    workflows=None )
        return containers_dict

    def populate_tool_dependencies_dicts( self, tool_shed_url, tool_path, repository_installed_tool_dependencies,
                                          repository_missing_tool_dependencies, required_repo_info_dicts ):
        """
        Return the populated installed_tool_dependencies and missing_tool_dependencies dictionaries
        for all repositories defined by entries in the received required_repo_info_dicts.
        """
        installed_tool_dependencies = None
        missing_tool_dependencies = None
        if repository_installed_tool_dependencies is None:
            repository_installed_tool_dependencies = {}
        else:
            # Add the install_dir attribute to the tool_dependencies.
            repository_installed_tool_dependencies = \
                self.add_installation_directories_to_tool_dependencies( repository_installed_tool_dependencies )
        if repository_missing_tool_dependencies is None:
            repository_missing_tool_dependencies = {}
        else:
            # Add the install_dir attribute to the tool_dependencies.
            repository_missing_tool_dependencies = \
                self.add_installation_directories_to_tool_dependencies( repository_missing_tool_dependencies )
        if required_repo_info_dicts:
            # Handle the tool dependencies defined for each of the repository's repository dependencies.
            for rid in required_repo_info_dicts:
                for name, repo_info_tuple in rid.items():
                    description, \
                    repository_clone_url, \
                    changeset_revision, \
                    ctx_rev, \
                    repository_owner, \
                    repository_dependencies, \
                    tool_dependencies = \
                        suc.get_repo_info_tuple_contents( repo_info_tuple )
                    if tool_dependencies:
                        # Add the install_dir attribute to the tool_dependencies.
                        tool_dependencies = self.add_installation_directories_to_tool_dependencies( tool_dependencies )
                        # The required_repository may have been installed with a different changeset revision.
                        required_repository, installed_changeset_revision = \
                            suc.repository_was_previously_installed( self.app,
                                                                     tool_shed_url,
                                                                     name,
                                                                     repo_info_tuple,
                                                                     from_tip=False )
                        if required_repository:
                            required_repository_installed_tool_dependencies, required_repository_missing_tool_dependencies = \
                                self.get_installed_and_missing_tool_dependencies_for_installed_repository( required_repository,
                                                                                                           tool_dependencies )
                            if required_repository_installed_tool_dependencies:
                                # Add the install_dir attribute to the tool_dependencies.
                                required_repository_installed_tool_dependencies = \
                                    self.add_installation_directories_to_tool_dependencies( required_repository_installed_tool_dependencies )
                                for td_key, td_dict in required_repository_installed_tool_dependencies.items():
                                    if td_key not in repository_installed_tool_dependencies:
                                        repository_installed_tool_dependencies[ td_key ] = td_dict
                            if required_repository_missing_tool_dependencies:
                                # Add the install_dir attribute to the tool_dependencies.
                                required_repository_missing_tool_dependencies = \
                                    self.add_installation_directories_to_tool_dependencies( required_repository_missing_tool_dependencies )
                                for td_key, td_dict in required_repository_missing_tool_dependencies.items():
                                    if td_key not in repository_missing_tool_dependencies:
                                        repository_missing_tool_dependencies[ td_key ] = td_dict
        if repository_installed_tool_dependencies:
            installed_tool_dependencies = repository_installed_tool_dependencies
        if repository_missing_tool_dependencies:
            missing_tool_dependencies = repository_missing_tool_dependencies
        return installed_tool_dependencies, missing_tool_dependencies

    def tool_dependency_is_orphan( self, type, name, version, tools ):
        """
        Determine if the combination of the received type, name and version is defined in the <requirement>
        tag for at least one tool in the received list of tools.  If not, the tool dependency defined by the
        combination is considered an orphan in its repository in the tool shed.
        """
        if type == 'package':
            if name and version:
                for tool_dict in tools:
                    requirements = tool_dict.get( 'requirements', [] )
                    for requirement_dict in requirements:
                        req_name = requirement_dict.get( 'name', None )
                        req_version = requirement_dict.get( 'version', None )
                        req_type = requirement_dict.get( 'type', None )
                        if req_name == name and req_version == version and req_type == type:
                            return False
        elif type == 'set_environment':
            if name:
                for tool_dict in tools:
                    requirements = tool_dict.get( 'requirements', [] )
                    for requirement_dict in requirements:
                        req_name = requirement_dict.get( 'name', None )
                        req_type = requirement_dict.get( 'type', None )
                        if req_name == name and req_type == type:
                            return False
        return True
