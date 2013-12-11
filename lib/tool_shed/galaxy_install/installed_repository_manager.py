"""
Class encapsulating the management of repositories installed from Galaxy tool sheds.
"""
import logging
import os
import tool_shed.util.shed_util_common as suc
from tool_shed.util import datatype_util
from tool_shed.util import repository_dependency_util
from tool_shed.util import tool_dependency_util
from tool_shed.util import xml_util
from galaxy.model.orm import and_

log = logging.getLogger( __name__ )


class InstalledRepositoryManager( object ):

    def __init__( self, app ):
        """
        Among other things, eep in in-memory set of installed repositories and tool dependencies along with the relationships
        between each of them.  This will allow for quick discovery of those repositories or components that can be uninstalled.
        The feature allowing a Galaxy administrator to uninstall a repository should not be available to repositories or tool
        dependency packages that are required by other repositories or their contents (packages). The uninstall feature should
        be available only at the repository hierarchy level where every dependency will be uninstalled.  The exception for this
        is if an item (repository or tool dependency package) is not in an INSTALLED state - in these cases, the specific item
        can be uninstalled in order to attempt re-installation.
        """
        self.app = app
        self.install_model = self.app.install_model
        self.context = self.install_model.context
        self.tool_configs = self.app.config.tool_configs
        if self.app.config.migrated_tools_config not in self.tool_configs:
            self.tool_configs.append( self.app.config.migrated_tools_config )
        self.installed_repository_dicts = []
        # Keep an in-memory dictionary whose keys are tool_shed_repository objects (whose status is 'Installed') and whose values
        # are a list of tool_shed_repository objects (whose status can be anything) required by the key.  The value defines the
        # entire repository dependency tree.
        self.repository_dependencies_of_installed_repositories = {}
        # Keep an in-memory dictionary whose keys are tool_shed_repository objects (whose status is 'Installed') and whose values
        # are a list of tool_shed_repository objects (whose status is 'Installed') required by the key.  The value defines the
        # entire repository dependency tree.
        self.installed_repository_dependencies_of_installed_repositories = {}
        # Keep an in-memory dictionary whose keys are tool_shed_repository objects (whose status is 'Installed') and whose values
        # are a list of its immediate tool_dependency objects (whose status can be anything).  The value defines only the immediate
        # tool dependencies of the repository and does not include any dependencies of the tool dependencies.
        self.tool_dependencies_of_installed_repositories = {}
        # Keep an in-memory dictionary whose keys are tool_shed_repository objects (whose status is 'Installed') and whose values
        # are a list of its immediate tool_dependency objects (whose status is 'Installed').  The value defines only the immediate
        # tool dependencies of the repository and does not include any dependencies of the tool dependencies.
        self.installed_tool_dependencies_of_installed_repositories = {}
        # Keep an in-memory dictionary whose keys are tool_dependency objects (whose status is 'Installed') and whose values are
        # a list of tool_dependency objects (whose status can be anything) required by the installed tool dependency at runtime.
        # The value defines the entire tool dependency tree.
        self.runtime_tool_dependencies_of_installed_tool_dependencies = {}
        # Keep an in-memory dictionary whose keys are tool_dependency objects (whose status is 'Installed') and whose values are
        # a list of tool_dependency objects (whose status is 'Installed') that require the key at runtime.  The value defines the
        # entire tool dependency tree.
        self.installed_runtime_dependent_tool_dependencies_of_installed_tool_dependencies = {}
        # Load defined dependency relationships for installed tool shed repositories and their contents.
        self.load_dependency_relationships()

    def add_entry_to_installed_repository_dependencies_of_installed_repositories( self, repository ):
        """Add an entry to self.installed_repository_dependencies_of_installed_repositories."""
        if repository.id not in self.ids_of_installed_repository_dependencies_of_installed_repositories_keys:
            debug_msg = "Adding an entry for revision %s of repository %s owned by %s " % \
                ( str( repository.changeset_revision ), str( repository.name ), str( repository.owner ) )
            debug_msg += "to installed_repository_dependencies_of_installed_repositories."
            log.debug( debug_msg )
            status = self.install_model.ToolShedRepository.installation_status.INSTALLED
            repository_dependency_tree = \
                repository_dependency_util.get_repository_dependency_tree_for_repository( self.app,
                                                                                          repository,
                                                                                          status=status )
            self.installed_repository_dependencies_of_installed_repositories[ repository ] = \
                repository_dependency_tree

    def add_entry_to_installed_runtime_dependent_tool_dependencies_of_installed_tool_dependencies( self, tool_dependency ):
        """Add an entry to self.installed_runtime_dependent_tool_dependencies_of_installed_tool_dependencies."""
        if tool_dependency.id not in self.ids_of_installed_runtime_dependent_tool_dependencies_of_installed_tool_dependencies_keys:
            debug_msg = "Adding an entry for version %s of %s %s " % \
                ( str( tool_dependency.version ), str( tool_dependency.type ), str( tool_dependency.name ) )
            debug_msg += "to installed_runtime_dependent_tool_dependencies_of_installed_tool_dependencies."
            log.debug( debug_msg )
            status = self.install_model.ToolDependency.installation_status.INSTALLED
            installed_runtime_dependent_tool_dependencies = \
                tool_dependency_util.get_runtime_dependent_tool_dependencies( self.app, tool_dependency, status=status )
            self.installed_runtime_dependent_tool_dependencies_of_installed_tool_dependencies[ tool_dependency ] = \
                installed_runtime_dependent_tool_dependencies

    def add_entry_to_installed_tool_dependencies_of_installed_repositories( self, repository ):
        """Add an entry to self.installed_tool_dependencies_of_installed_repositories."""
        if repository.id not in self.ids_of_installed_tool_dependencies_of_installed_repositories_keys:
            debug_msg = "Adding an entry for revision %s of repository %s owned by %s " % \
                ( str( repository.changeset_revision ), str( repository.name ), str( repository.owner ) )
            debug_msg += "to installed_tool_dependencies_of_installed_repositories."
            log.debug( debug_msg )
            installed_tool_dependencies = []
            for td in repository.tool_dependencies:
                if td.status == self.app.install_model.ToolDependency.installation_status.INSTALLED:
                    installed_tool_dependencies.append( td )
            self.installed_tool_dependencies_of_installed_repositories[ repository ] = installed_tool_dependencies

    def add_entry_to_repository_dependencies_of_installed_repositories( self, repository ):
        """Add an entry to self.repository_dependencies_of_installed_repositories."""
        if repository.id not in self.ids_of_repository_dependencies_of_installed_repositories_keys:
            debug_msg = "Adding an entry for revision %s of repository %s owned by %s " % \
                ( str( repository.changeset_revision ), str( repository.name ), str( repository.owner ) )
            debug_msg += "to repository_dependencies_of_installed_repositories."
            log.debug( debug_msg )
            repository_dependency_tree = \
                repository_dependency_util.get_repository_dependency_tree_for_repository( self.app,
                                                                                          repository,
                                                                                          status=None )
            self.repository_dependencies_of_installed_repositories[ repository ] = repository_dependency_tree

    def add_entry_to_runtime_tool_dependencies_of_installed_tool_dependencies( self, tool_dependency ):
        """Add an entry to self.runtime_tool_dependencies_of_installed_tool_dependencies."""
        if tool_dependency.id not in self.ids_of_runtime_tool_dependencies_of_installed_tool_dependencies_keys:
            debug_msg = "Adding an entry for version %s of %s %s " % \
                ( str( tool_dependency.version ), str( tool_dependency.type ), str( tool_dependency.name ) )
            debug_msg += "to runtime_tool_dependencies_of_installed_tool_dependencies."
            log.debug( debug_msg )
            runtime_dependent_tool_dependencies = \
                tool_dependency_util.get_runtime_dependent_tool_dependencies( self.app, tool_dependency, status=None )
            self.runtime_tool_dependencies_of_installed_tool_dependencies[ tool_dependency ] = \
                runtime_dependent_tool_dependencies

    def add_entry_to_tool_dependencies_of_installed_repositories( self, repository ):
        """Add an entry to self.tool_dependencies_of_installed_repositories."""
        if repository.id not in self.ids_of_tool_dependencies_of_installed_repositories_keys:
            debug_msg = "Adding an entry for revision %s of repository %s owned by %s " % \
                ( str( repository.changeset_revision ), str( repository.name ), str( repository.owner ) )
            debug_msg += "to tool_dependencies_of_installed_repositories."
            log.debug( debug_msg )
            self.tool_dependencies_of_installed_repositories[ repository ] = repository.tool_dependencies

    def get_containing_repository_for_tool_dependency( self, tool_dependency ):
        for installed_repository, tool_dependencies in self.tool_dependencies_of_installed_repositories.items():
            td_ids = [ td.id for td in tool_dependencies ]
            if tool_dependency.id in td_ids:
                return installed_repository
        return None
            
    def get_repository_install_dir( self, tool_shed_repository ):
        for tool_config in self.tool_configs:
            tree, error_message = xml_util.parse_xml( tool_config )
            if tree is None:
                return None
            root = tree.getroot()
            tool_path = root.get( 'tool_path', None )
            if tool_path:
                ts = suc.clean_tool_shed_url( tool_shed_repository.tool_shed )
                relative_path = os.path.join( tool_path,
                                              ts,
                                              'repos',
                                              tool_shed_repository.owner,
                                              tool_shed_repository.name,
                                              tool_shed_repository.installed_changeset_revision )
                if os.path.exists( relative_path ):
                    return relative_path
        return None

    def handle_install( self, repository ):
        """Load the dependency relationships for a repository that was just installed or reinstalled."""
        # Populate self.repository_dependencies_of_installed_repositories.
        self.add_entry_to_repository_dependencies_of_installed_repositories( repository )
        # Populate self.installed_repository_dependencies_of_installed_repositories.
        self.add_entry_to_installed_repository_dependencies_of_installed_repositories( repository )
        # Populate self.tool_dependencies_of_installed_repositories.
        self.add_entry_to_tool_dependencies_of_installed_repositories( repository )
        # Populate self.installed_tool_dependencies_of_installed_repositories.
        self.add_entry_to_installed_tool_dependencies_of_installed_repositories( repository )
        for tool_dependency in repository.tool_dependencies:
            # Populate self.runtime_tool_dependencies_of_installed_tool_dependencies.
            self.add_entry_to_runtime_tool_dependencies_of_installed_tool_dependencies( tool_dependency )
            # Populate self.installed_runtime_dependent_tool_dependencies_of_installed_tool_dependencies.
            self.add_entry_to_installed_runtime_dependent_tool_dependencies_of_installed_tool_dependencies( tool_dependency )

    def handle_uninstall( self, repository ):
        """Remove the dependency relationships for a repository that was just uninstalled."""
        for tool_dependency in repository.tool_dependencies:
            # Remove all this tool_dependency from all values in
            # self.installed_runtime_dependent_tool_dependencies_of_installed_tool_dependencies
            altered_installed_runtime_dependent_tool_dependencies_of_installed_tool_dependencies = {}
            for td, installed_runtime_dependent_tool_dependencies in \
                self.installed_runtime_dependent_tool_dependencies_of_installed_tool_dependencies.items():
                irdtd_ids = [ irdtd.id for irdtd in installed_runtime_dependent_tool_dependencies ]
                if td.id in irdtd_ids:
                    index = irdtd_ids[ td.id ]
                    # Remove the tool_dependency from the list.
                    del installed_runtime_dependent_tool_dependencies[ index ]
                # Add the possibly altered list to the altered dictionary.
                altered_installed_runtime_dependent_tool_dependencies_of_installed_tool_dependencies[ td ] = \
                    installed_runtime_dependent_tool_dependencies
            self.installed_runtime_dependent_tool_dependencies_of_installed_tool_dependencies = \
                altered_installed_runtime_dependent_tool_dependencies_of_installed_tool_dependencies
            # Remove the entry for this tool_dependency from self.runtime_tool_dependencies_of_installed_tool_dependencies.
            self.remove_entry_from_runtime_tool_dependencies_of_installed_tool_dependencies( tool_dependency )
            # Remove the entry for this tool_dependency from 
            # self.installed_runtime_dependent_tool_dependencies_of_installed_tool_dependencies.
            self.remove_entry_from_installed_runtime_dependent_tool_dependencies_of_installed_tool_dependencies( tool_dependency )
        # Remove this repository's entry from self.installed_tool_dependencies_of_installed_repositories.
        self.remove_entry_from_installed_tool_dependencies_of_installed_repositories( repository )
        # Remove this repository's entry from self.tool_dependencies_of_installed_repositories
        self.remove_entry_from_tool_dependencies_of_installed_repositories( repository )
        # Remove this repository's entry from self.installed_repository_dependencies_of_installed_repositories.
        self.remove_entry_from_installed_repository_dependencies_of_installed_repositories( repository )
        # Remove this repository's entry from self.repository_dependencies_of_installed_repositories.
        self.remove_entry_from_repository_dependencies_of_installed_repositories( repository )

    @property
    def ids_of_installed_repository_dependencies_of_installed_repositories_keys( self ):
        return [ r.id for r in self.installed_repository_dependencies_of_installed_repositories.keys() ]

    @property
    def ids_of_installed_runtime_dependent_tool_dependencies_of_installed_tool_dependencies_keys( self ):
        return [ td.id for td in self.installed_runtime_dependent_tool_dependencies_of_installed_tool_dependencies.keys() ]

    @property
    def ids_of_installed_tool_dependencies_of_installed_repositories_keys( self ):
        return [ r.id for r in self.installed_tool_dependencies_of_installed_repositories.keys() ]

    @property
    def ids_of_repository_dependencies_of_installed_repositories_keys( self ):
        return [ r.id for r in self.repository_dependencies_of_installed_repositories.keys() ]

    @property
    def ids_of_runtime_tool_dependencies_of_installed_tool_dependencies_keys( self ):
        return [ td.id for td in self.runtime_tool_dependencies_of_installed_tool_dependencies.keys() ]

    @property
    def ids_of_tool_dependencies_of_installed_repositories_keys( self ):
        return [ r.id for r in self.tool_dependencies_of_installed_repositories.keys() ]

    def load_dependency_relationships( self ):
        """Load relationships for all installed repositories and tool dependencies into in-memnory dictionaries."""
        # Get the list of installed tool shed repositories.
        for repository in self.context.query( self.app.install_model.ToolShedRepository ) \
                                      .filter( self.app.install_model.ToolShedRepository.table.c.status ==
                                               self.app.install_model.ToolShedRepository.installation_status.INSTALLED ):
            # Populate self.repository_dependencies_of_installed_repositories.
            self.add_entry_to_repository_dependencies_of_installed_repositories( repository )
            # Populate self.installed_repository_dependencies_of_installed_repositories.
            self.add_entry_to_installed_repository_dependencies_of_installed_repositories( repository )
            # Populate self.tool_dependencies_of_installed_repositories.
            self.add_entry_to_tool_dependencies_of_installed_repositories( repository )
            # Populate self.installed_tool_dependencies_of_installed_repositories.
            self.add_entry_to_installed_tool_dependencies_of_installed_repositories( repository )
        # Get the list of installed tool dependencies.
        for tool_dependency in self.context.query( self.app.install_model.ToolDependency ) \
                                           .filter( self.app.install_model.ToolDependency.table.c.status ==
                                                    self.app.install_model.ToolDependency.installation_status.INSTALLED ):
            # Populate self.runtime_tool_dependencies_of_installed_tool_dependencies.
            self.add_entry_to_runtime_tool_dependencies_of_installed_tool_dependencies( tool_dependency )
            # Populate self.installed_runtime_dependent_tool_dependencies_of_installed_tool_dependencies.
            self.add_entry_to_installed_runtime_dependent_tool_dependencies_of_installed_tool_dependencies( tool_dependency )

    def load_proprietary_datatypes( self ):
        for tool_shed_repository in self.context.query( self.install_model.ToolShedRepository ) \
                                                   .filter( and_( self.install_model.ToolShedRepository.table.c.includes_datatypes==True,
                                                                  self.install_model.ToolShedRepository.table.c.deleted==False ) ) \
                                                   .order_by( self.install_model.ToolShedRepository.table.c.id ):
            relative_install_dir = self.get_repository_install_dir( tool_shed_repository )
            if relative_install_dir:
                installed_repository_dict = datatype_util.load_installed_datatypes( self.app, tool_shed_repository, relative_install_dir )
                if installed_repository_dict:
                    self.installed_repository_dicts.append( installed_repository_dict )

    def load_proprietary_converters_and_display_applications( self, deactivate=False ):
        for installed_repository_dict in self.installed_repository_dicts:
            if installed_repository_dict[ 'converter_path' ]:
                datatype_util.load_installed_datatype_converters( self.app, installed_repository_dict, deactivate=deactivate )
            if installed_repository_dict[ 'display_path' ]:
                datatype_util.load_installed_display_applications( self.app, installed_repository_dict, deactivate=deactivate )

    def remove_entry_from_installed_repository_dependencies_of_installed_repositories( self, repository ):
        """Remove an entry from self.installed_repository_dependencies_of_installed_repositories"""
        for r in self.installed_repository_dependencies_of_installed_repositories:
            if r.id == repository.id:
                debug_msg = "Removing entry for revision %s of repository %s owned by %s " % \
                    ( str( repository.changeset_revision ), str( repository.name ), str( repository.owner ) )
                debug_msg += "from installed_repository_dependencies_of_installed_repositories."
                log.debug( debug_msg )
                del self.installed_repository_dependencies_of_installed_repositories[ r ]
                break

    def remove_entry_from_installed_runtime_dependent_tool_dependencies_of_installed_tool_dependencies( self, tool_dependency ):
        """Remove an entry from self.installed_runtime_dependent_tool_dependencies_of_installed_tool_dependencies."""
        for td in self.installed_runtime_dependent_tool_dependencies_of_installed_tool_dependencies:
            if td.id == tool_dependency.id:
                debug_msg = "Removing entry for version %s of %s %s " % \
                    ( str( tool_dependency.version ), str( tool_dependency.type ), str( tool_dependency.name ) )
                debug_msg += "from installed_runtime_dependent_tool_dependencies_of_installed_tool_dependencies."
                log.debug( debug_msg )
                del self.installed_runtime_dependent_tool_dependencies_of_installed_tool_dependencies[ td ]
                break

    def remove_entry_from_installed_tool_dependencies_of_installed_repositories( self, repository ):
        """Remove an entry from self.installed_tool_dependencies_of_installed_repositories"""
        for r in self.installed_tool_dependencies_of_installed_repositories:
            if r.id == repository.id:
                debug_msg = "Removing entry for revision %s of repository %s owned by %s " % \
                    ( str( repository.changeset_revision ), str( repository.name ), str( repository.owner ) )
                debug_msg += "from installed_tool_dependencies_of_installed_repositories."
                log.debug( debug_msg )
                del self.installed_tool_dependencies_of_installed_repositories[ r ]
                break

    def remove_entry_from_repository_dependencies_of_installed_repositories( self, repository ):
        """Remove an entry from self.repository_dependencies_of_installed_repositories."""
        for r in self.repository_dependencies_of_installed_repositories:
            if r.id == repository.id:
                debug_msg = "Removing entry for revision %s of repository %s owned by %s " % \
                    ( str( repository.changeset_revision ), str( repository.name ), str( repository.owner ) )
                debug_msg += "from repository_dependencies_of_installed_repositories."
                log.debug( debug_msg )
                del self.repository_dependencies_of_installed_repositories[ r ]
                break

    def remove_entry_from_runtime_tool_dependencies_of_installed_tool_dependencies( self, tool_dependency ):
        """Remove an entry from self.runtime_tool_dependencies_of_installed_tool_dependencies."""
        for td in self.runtime_tool_dependencies_of_installed_tool_dependencies:
            if td.id == tool_dependency.id:
                debug_msg = "Removing entry for version %s of %s %s " % \
                    ( str( tool_dependency.version ), str( tool_dependency.type ), str( tool_dependency.name ) )
                debug_msg += "from runtime_tool_dependencies_of_installed_tool_dependencies."
                log.debug( debug_msg )
                del self.runtime_tool_dependencies_of_installed_tool_dependencies[ td ]
                break

    def remove_entry_from_tool_dependencies_of_installed_repositories( self, repository ):
        """Remove an entry from self.tool_dependencies_of_installed_repositories."""
        for r in self.tool_dependencies_of_installed_repositories:
            if r.id == repository.id:
                debug_msg = "Removing entry for revision %s of repository %s owned by %s " % \
                    ( str( repository.changeset_revision ), str( repository.name ), str( repository.owner ) )
                debug_msg += "from tool_dependencies_of_installed_repositories."
                log.debug( debug_msg )
                del self.tool_dependencies_of_installed_repositories[ r ]
            break
