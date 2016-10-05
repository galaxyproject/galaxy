import logging
import tempfile

from tool_shed.galaxy_install import install_manager
from tool_shed.galaxy_install.repository_dependencies import repository_dependency_manager
from tool_shed.galaxy_install.tools import tool_panel_manager
from tool_shed.util import basic_util
from tool_shed.util import common_util
from tool_shed.util import container_util
from tool_shed.util import hg_util
from tool_shed.util import repository_util
from tool_shed.util import shed_util_common as suc
from tool_shed.util import tool_dependency_util

log = logging.getLogger( __name__ )


class RepairRepositoryManager():

    def __init__( self, app ):
        self.app = app

    def get_installed_repositories_from_repository_dependencies( self, repository_dependencies_dict ):
        installed_repositories = []
        if repository_dependencies_dict and isinstance( repository_dependencies_dict, dict ):
            for rd_key, rd_vals in repository_dependencies_dict.items():
                if rd_key in [ 'root_key', 'description' ]:
                    continue
                # rd_key is something like: 'http://localhost:9009__ESEP__package_rdkit_2012_12__ESEP__test__ESEP__d635ffb9c665__ESEP__True'
                # rd_val is something like: [['http://localhost:9009', 'package_numpy_1_7', 'test', 'cddd64ecd985', 'True']]
                repository_components_tuple = container_util.get_components_from_key( rd_key )
                components_list = repository_util.extract_components_from_tuple( repository_components_tuple )
                tool_shed, name, owner, changeset_revision = components_list[ 0:4 ]
                installed_repository = repository_util.get_installed_repository( self.app,
                                                                                 tool_shed=tool_shed,
                                                                                 name=name,
                                                                                 owner=owner,
                                                                                 changeset_revision=changeset_revision )
                if ( installed_repository ) and ( installed_repository not in installed_repositories ):
                    installed_repositories.append( installed_repository )
                for rd_val in rd_vals:
                    tool_shed, name, owner, changeset_revision = rd_val[ 0:4 ]
                    installed_repository = repository_util.get_installed_repository( self.app,
                                                                                     tool_shed=tool_shed,
                                                                                     name=name,
                                                                                     owner=owner,
                                                                                     changeset_revision=changeset_revision )
                    if ( installed_repository ) and ( installed_repository not in installed_repositories ):
                        installed_repositories.append( installed_repository )
        return installed_repositories

    def get_repair_dict( self, repository ):
        """
        Inspect the installed repository dependency hierarchy for a specified repository
        and attempt to make sure they are all properly installed as well as each repository's
        tool dependencies.  This method is called only from Galaxy when attempting to correct
        issues with an installed repository that has installation problems somewhere in its
        dependency hierarchy. Problems with dependencies that have never been installed
        cannot be resolved with a repair.
        """
        rdim = repository_dependency_manager.RepositoryDependencyInstallManager( self.app )
        tsr_ids = []
        repo_info_dicts = []
        tool_panel_section_keys = []
        repair_dict = {}
        irm = install_manager.InstallRepositoryManager( self.app )
        # Get a dictionary of all repositories upon which the contents of the current repository_metadata
        # record depend.
        repository_dependencies_dict = rdim.get_repository_dependencies_for_installed_tool_shed_repository( self.app,
                                                                                                            repository )
        if repository_dependencies_dict:
            # Generate the list of installed repositories from the information contained in the
            # repository_dependencies dictionary.
            installed_repositories = self.get_installed_repositories_from_repository_dependencies( repository_dependencies_dict )
            # Some repositories may have repository dependencies that are required to be installed before
            # the dependent repository, so we'll order the list of tsr_ids to ensure all repositories are
            # repaired in the required order.
            installed_repositories.append(repository)
            for installed_repository in installed_repositories:
                tsr_ids.append( self.app.security.encode_id( installed_repository.id ) )
                repo_info_dict, tool_panel_section_key = self.get_repo_info_dict_for_repair( rdim,
                                                                                             installed_repository )
                tool_panel_section_keys.append( tool_panel_section_key )
                repo_info_dicts.append( repo_info_dict )
        else:
            # The received repository has no repository dependencies.
            tsr_ids.append( self.app.security.encode_id( repository.id ) )
            repo_info_dict, tool_panel_section_key = self.get_repo_info_dict_for_repair( rdim,
                                                                                         repository )
            tool_panel_section_keys.append( tool_panel_section_key )
            repo_info_dicts.append( repo_info_dict )
        ordered_tsr_ids, ordered_repo_info_dicts, ordered_tool_panel_section_keys = \
            irm.order_components_for_installation( tsr_ids,
                                                   repo_info_dicts,
                                                   tool_panel_section_keys=tool_panel_section_keys )
        repair_dict[ 'ordered_tsr_ids' ] = ordered_tsr_ids
        repair_dict[ 'ordered_repo_info_dicts' ] = ordered_repo_info_dicts
        repair_dict[ 'ordered_tool_panel_section_keys' ] = ordered_tool_panel_section_keys
        return repair_dict

    def get_repo_info_dict_for_repair( self, rdim, repository ):
        tool_panel_section_key = None
        repository_clone_url = common_util.generate_clone_url_for_installed_repository( self.app, repository )
        repository_dependencies = rdim.get_repository_dependencies_for_installed_tool_shed_repository( self.app,
                                                                                                       repository )
        metadata = repository.metadata
        if metadata:
            tool_dependencies = metadata.get( 'tool_dependencies', None )
            tool_panel_section_dict = metadata.get( 'tool_panel_section', None )
            if tool_panel_section_dict:
                # The repository must be in the uninstalled state.  The structure of tool_panel_section_dict is:
                # {<tool guid> :
                # [{ 'id':<section id>, 'name':<section name>, 'version':<section version>, 'tool_config':<tool config file name> }]}
                # Here is an example:
                # {"localhost:9009/repos/test/filter/Filter1/1.1.0":
                # [{"id": "filter_and_sort", "name": "Filter and Sort", "tool_config": "filtering.xml", "version": ""}]}
                # Currently all tools contained within an installed tool shed repository must be loaded into the same
                # section in the tool panel, so we can get the section id of the first guid in the tool_panel_section_dict.
                # In the future, we'll have to handle different sections per guid.
                guid = next(iter(tool_panel_section_dict))
                section_dicts = tool_panel_section_dict[ guid ]
                section_dict = section_dicts[ 0 ]
                tool_panel_section_id = section_dict[ 'id' ]
                tool_panel_section_name = section_dict[ 'name' ]
                if tool_panel_section_id:
                    tpm = tool_panel_manager.ToolPanelManager( self.app )
                    tool_panel_section_key, _ = \
                        tpm.get_or_create_tool_section( self.app.toolbox,
                                                        tool_panel_section_id=tool_panel_section_id,
                                                        new_tool_panel_section_label=tool_panel_section_name )
        else:
            tool_dependencies = None
        repo_info_dict = repository_util.create_repo_info_dict( app=self.app,
                                                                repository_clone_url=repository_clone_url,
                                                                changeset_revision=repository.changeset_revision,
                                                                ctx_rev=repository.ctx_rev,
                                                                repository_owner=repository.owner,
                                                                repository_name=repository.name,
                                                                repository=None,
                                                                repository_metadata=None,
                                                                tool_dependencies=tool_dependencies,
                                                                repository_dependencies=repository_dependencies )
        return repo_info_dict, tool_panel_section_key

    def repair_tool_shed_repository( self, repository, repo_info_dict ):

        def add_repair_dict_entry( repository_name, error_message ):
            if repository_name in repair_dict:
                repair_dict[ repository_name ].append( error_message )
            else:
                repair_dict[ repository_name ] = [ error_message ]
            return repair_dict
        tool_shed_url = common_util.get_tool_shed_url_from_tool_shed_registry( self.app, repository.tool_shed )
        metadata = repository.metadata
        # The repository.metadata contains dependency information that corresponds to the current changeset revision,
        # which may be different from what is stored in the database
        # If any of these repository-repository dependency associations is obsolete, clean_dependency_relationships removes them.
        suc.clean_dependency_relationships(self.app, metadata, repository, tool_shed_url)
        repair_dict = {}
        tpm = tool_panel_manager.ToolPanelManager( self.app )
        if repository.status in [ self.app.install_model.ToolShedRepository.installation_status.DEACTIVATED ]:
            try:
                self.app.installed_repository_manager.activate_repository( repository )
            except Exception as e:
                error_message = "Error activating repository %s: %s" % ( repository.name, str( e ) )
                log.debug( error_message )
                repair_dict[ repository.name ] = error_message
        elif repository.status not in [ self.app.install_model.ToolShedRepository.installation_status.INSTALLED ]:
            shed_tool_conf, tool_path, relative_install_dir = \
                suc.get_tool_panel_config_tool_path_install_dir( self.app, repository )
            # Reset the repository attributes to the New state for installation.
            if metadata:
                _, tool_panel_section_key = \
                    tpm.handle_tool_panel_selection( self.app.toolbox,
                                                     metadata,
                                                     no_changes_checked=True,
                                                     tool_panel_section_id=None,
                                                     new_tool_panel_section_label=None )
            else:
                # The tools will be loaded outside of any sections in the tool panel.
                tool_panel_section_key = None
            repository_util.set_repository_attributes( self.app,
                                                       repository,
                                                       status=self.app.install_model.ToolShedRepository.installation_status.NEW,
                                                       error_message=None,
                                                       deleted=False,
                                                       uninstalled=False,
                                                       remove_from_disk=True )
            irm = install_manager.InstallRepositoryManager( self.app, tpm )
            irm.install_tool_shed_repository( repository,
                                              repo_info_dict,
                                              tool_panel_section_key,
                                              shed_tool_conf,
                                              tool_path,
                                              install_tool_dependencies=True,
                                              install_resolver_dependencies=False,  # Assuming repairs are only necessary toolshed packages
                                              reinstalling=True )
            if repository.status in [ self.app.install_model.ToolShedRepository.installation_status.ERROR ]:
                repair_dict = add_repair_dict_entry( repository.name, repository.error_message )
        else:
            irm = install_manager.InstallRepositoryManager( self.app, tpm )
            # We have an installed tool shed repository, so handle tool dependencies if necessary.
            if repository.missing_tool_dependencies and metadata and 'tool_dependencies' in metadata:
                work_dir = tempfile.mkdtemp( prefix="tmp-toolshed-itdep" )
                # Reset missing tool dependencies.
                for tool_dependency in repository.missing_tool_dependencies:
                    if tool_dependency.status in [ self.app.install_model.ToolDependency.installation_status.ERROR,
                                                   self.app.install_model.ToolDependency.installation_status.INSTALLING ]:
                        tool_dependency = \
                            tool_dependency_util.set_tool_dependency_attributes( self.app,
                                                                                 tool_dependency=tool_dependency,
                                                                                 status=self.app.install_model.ToolDependency.installation_status.UNINSTALLED )
                # Install tool dependencies.
                irm.update_tool_shed_repository_status( repository,
                                                        self.app.install_model.ToolShedRepository.installation_status.INSTALLING_TOOL_DEPENDENCIES )
                # Get the tool_dependencies.xml file from the repository.
                tool_dependencies_config = hg_util.get_config_from_disk( 'tool_dependencies.xml', repository.repo_path( self.app ) )
                itdm = install_manager.InstallToolDependencyManager( self.app )
                installed_tool_dependencies = itdm.install_specified_tool_dependencies( tool_shed_repository=repository,
                                                                                        tool_dependencies_config=tool_dependencies_config,
                                                                                        tool_dependencies=repository.tool_dependencies,
                                                                                        from_tool_migration_manager=False )
                for installed_tool_dependency in installed_tool_dependencies:
                    if installed_tool_dependency.status in [ self.app.install_model.ToolDependency.installation_status.ERROR ]:
                        repair_dict = add_repair_dict_entry( repository.name, installed_tool_dependency.error_message )
                basic_util.remove_dir( work_dir )
            irm.update_tool_shed_repository_status( repository,
                                                    self.app.install_model.ToolShedRepository.installation_status.INSTALLED )
        return repair_dict
