"""
Class encapsulating the management of repositories installed from Galaxy tool sheds.
"""
import logging
import os
from tool_shed.util import common_util
from tool_shed.util import datatype_util
from tool_shed.util import repository_dependency_util
from tool_shed.util import tool_dependency_util
from tool_shed.util import xml_util
from galaxy.model.orm import and_

log = logging.getLogger( __name__ )


class InstalledRepositoryManager( object ):

    def __init__( self, app ):
        """
        Among other things, keep in in-memory sets of tuples defining installed repositories and tool dependencies along with
        the relationships between each of them.  This will allow for quick discovery of those repositories or components that
        can be uninstalled.  The feature allowing a Galaxy administrator to uninstall a repository should not be available to
        repositories or tool dependency packages that are required by other repositories or their contents (packages). The
        uninstall feature should be available only at the repository hierarchy level where every dependency will be uninstalled.
        The exception for this is if an item (repository or tool dependency package) is not in an INSTALLED state - in these
        cases, the specific item can be uninstalled in order to attempt re-installation.
        """
        self.app = app
        self.install_model = self.app.install_model
        self.context = self.install_model.context
        self.tool_configs = self.app.config.tool_configs
        if self.app.config.migrated_tools_config not in self.tool_configs:
            self.tool_configs.append( self.app.config.migrated_tools_config )
        self.installed_repository_dicts = []
        # Keep an in-memory dictionary whose keys are tuples defining tool_shed_repository objects (whose status is 'Installed')
        # and whose values are a list of tuples defining tool_shed_repository objects (whose status can be anything) required by
        # the key.  The value defines the entire repository dependency tree.
        self.repository_dependencies_of_installed_repositories = {}
        # Keep an in-memory dictionary whose keys are tuples defining tool_shed_repository objects (whose status is 'Installed')
        # and whose values are a list of tuples defining tool_shed_repository objects (whose status is 'Installed') required by
        # the key.  The value defines the entire repository dependency tree.
        self.installed_repository_dependencies_of_installed_repositories = {}
        # Keep an in-memory dictionary whose keys are tuples defining tool_shed_repository objects (whose status is 'Installed')
        # and whose values are a list of tuples defining tool_shed_repository objects (whose status is 'Installed') that require
        # the key.
        self.installed_dependent_repositories_of_installed_repositories = {}
        # Keep an in-memory dictionary whose keys are tuples defining tool_shed_repository objects (whose status is 'Installed')
        # and whose values are a list of tuples defining its immediate tool_dependency objects (whose status can be anything).
        # The value defines only the immediate tool dependencies of the repository and does not include any dependencies of the
        # tool dependencies.
        self.tool_dependencies_of_installed_repositories = {}
        # Keep an in-memory dictionary whose keys are tuples defining tool_shed_repository objects (whose status is 'Installed')
        # and whose values are a list of tuples defining its immediate tool_dependency objects (whose status is 'Installed').
        # The value defines only the immediate tool dependencies of the repository and does not include any dependencies of the
        # tool dependencies.
        self.installed_tool_dependencies_of_installed_repositories = {}
        # Keep an in-memory dictionary whose keys are tuples defining tool_dependency objects (whose status is 'Installed') and
        # whose values are a list of tuples defining tool_dependency objects (whose status can be anything) required by the
        # installed tool dependency at runtime.  The value defines the entire tool dependency tree.
        self.runtime_tool_dependencies_of_installed_tool_dependencies = {}
        # Keep an in-memory dictionary whose keys are tuples defining tool_dependency objects (whose status is 'Installed') and
        # whose values are a list of tuples defining tool_dependency objects (whose status is 'Installed') that require the key
        # at runtime.  The value defines the entire tool dependency tree.
        self.installed_runtime_dependent_tool_dependencies_of_installed_tool_dependencies = {}
        if app.config.manage_dependency_relationships:
            # Load defined dependency relationships for installed tool shed repositories and their contents.
            self.load_dependency_relationships()

    def add_entry_to_installed_repository_dependencies_of_installed_repositories( self, repository ):
        """
        Add an entry to self.installed_repository_dependencies_of_installed_repositories.  A side-effect of this method
        is the population of self.installed_dependent_repositories_of_installed_repositories.  Since this method discovers
        all repositories required by the received repository, it can use the list to add entries to the reverse dictionary.
        """
        repository_tup = repository_dependency_util.get_repository_tuple_for_installed_repository_manager( repository )
        tool_shed, name, owner, installed_changeset_revision = repository_tup
        # Get the list of repository dependencies for this repository.
        status = self.install_model.ToolShedRepository.installation_status.INSTALLED
        repository_dependency_tups = \
            repository_dependency_util.get_repository_dependency_tups_for_installed_repository( self.app, repository, status=status )
        # Add an entry to self.installed_repository_dependencies_of_installed_repositories.
        if repository_tup not in self.installed_repository_dependencies_of_installed_repositories:
            debug_msg = "Adding an entry for revision %s of repository %s owned by %s " % ( installed_changeset_revision, name, owner )
            debug_msg += "to installed_repository_dependencies_of_installed_repositories."
            log.debug( debug_msg )
            self.installed_repository_dependencies_of_installed_repositories[ repository_tup ] = repository_dependency_tups
        # Use the repository_dependency_tups to add entries to the reverse dictionary
        # self.installed_dependent_repositories_of_installed_repositories.
        for required_repository_tup in repository_dependency_tups:
            debug_msg = "Appending revision %s of repository %s owned by %s " % ( installed_changeset_revision, name, owner )
            debug_msg += "to all dependent repositories in installed_dependent_repositories_of_installed_repositories."
            log.debug( debug_msg )
            if required_repository_tup in self.installed_dependent_repositories_of_installed_repositories:
                self.installed_dependent_repositories_of_installed_repositories[ required_repository_tup ].append( repository_tup )
            else:
                self.installed_dependent_repositories_of_installed_repositories[ required_repository_tup ] = [ repository_tup ]

    def add_entry_to_installed_runtime_dependent_tool_dependencies_of_installed_tool_dependencies( self, tool_dependency ):
        """Add an entry to self.installed_runtime_dependent_tool_dependencies_of_installed_tool_dependencies."""
        tool_dependency_tup = tool_dependency_util.get_tool_dependency_tuple_for_installed_repository_manager( tool_dependency )
        if tool_dependency_tup not in self.installed_runtime_dependent_tool_dependencies_of_installed_tool_dependencies:
            tool_shed_repository_id, name, version, type = tool_dependency_tup
            debug_msg = "Adding an entry for version %s of %s %s " % ( version, type, name )
            debug_msg += "to installed_runtime_dependent_tool_dependencies_of_installed_tool_dependencies."
            log.debug( debug_msg )
            status = self.install_model.ToolDependency.installation_status.INSTALLED
            installed_runtime_dependent_tool_dependency_tups = \
                tool_dependency_util.get_runtime_dependent_tool_dependency_tuples( self.app, tool_dependency, status=status )
            self.installed_runtime_dependent_tool_dependencies_of_installed_tool_dependencies[ tool_dependency_tup ] = \
                installed_runtime_dependent_tool_dependency_tups

    def add_entry_to_installed_tool_dependencies_of_installed_repositories( self, repository ):
        """Add an entry to self.installed_tool_dependencies_of_installed_repositories."""
        repository_tup = repository_dependency_util.get_repository_tuple_for_installed_repository_manager( repository )
        if repository_tup not in self.installed_tool_dependencies_of_installed_repositories:
            tool_shed, name, owner, installed_changeset_revision = repository_tup
            debug_msg = "Adding an entry for revision %s of repository %s owned by %s " % ( installed_changeset_revision, name, owner )
            debug_msg += "to installed_tool_dependencies_of_installed_repositories."
            log.debug( debug_msg )
            installed_tool_dependency_tups = []
            for tool_dependency in repository.tool_dependencies:
                if tool_dependency.status == self.app.install_model.ToolDependency.installation_status.INSTALLED:
                    tool_dependency_tup = tool_dependency_util.get_tool_dependency_tuple_for_installed_repository_manager( tool_dependency )
                    installed_tool_dependency_tups.append( tool_dependency_tup )
            self.installed_tool_dependencies_of_installed_repositories[ repository_tup ] = installed_tool_dependency_tups

    def add_entry_to_repository_dependencies_of_installed_repositories( self, repository ):
        """Add an entry to self.repository_dependencies_of_installed_repositories."""
        repository_tup = repository_dependency_util.get_repository_tuple_for_installed_repository_manager( repository )
        if repository_tup not in self.repository_dependencies_of_installed_repositories:
            tool_shed, name, owner, installed_changeset_revision = repository_tup
            debug_msg = "Adding an entry for revision %s of repository %s owned by %s " % ( installed_changeset_revision, name, owner )
            debug_msg += "to repository_dependencies_of_installed_repositories."
            log.debug( debug_msg )
            repository_dependency_tups = \
                repository_dependency_util.get_repository_dependency_tups_for_installed_repository( self.app, repository, status=None )
            self.repository_dependencies_of_installed_repositories[ repository_tup ] = repository_dependency_tups

    def add_entry_to_runtime_tool_dependencies_of_installed_tool_dependencies( self, tool_dependency ):
        """Add an entry to self.runtime_tool_dependencies_of_installed_tool_dependencies."""
        tool_dependency_tup = tool_dependency_util.get_tool_dependency_tuple_for_installed_repository_manager( tool_dependency )
        if tool_dependency_tup not in self.runtime_tool_dependencies_of_installed_tool_dependencies:
            tool_shed_repository_id, name, version, type = tool_dependency_tup
            debug_msg = "Adding an entry for version %s of %s %s " % ( version, type, name )
            debug_msg += "to runtime_tool_dependencies_of_installed_tool_dependencies."
            log.debug( debug_msg )
            runtime_dependent_tool_dependency_tups = \
                tool_dependency_util.get_runtime_dependent_tool_dependency_tuples( self.app, tool_dependency, status=None )
            self.runtime_tool_dependencies_of_installed_tool_dependencies[ tool_dependency_tup ] = \
                runtime_dependent_tool_dependency_tups

    def add_entry_to_tool_dependencies_of_installed_repositories( self, repository ):
        """Add an entry to self.tool_dependencies_of_installed_repositories."""
        repository_tup = repository_dependency_util.get_repository_tuple_for_installed_repository_manager( repository )
        if repository_tup not in self.tool_dependencies_of_installed_repositories:
            tool_shed, name, owner, installed_changeset_revision = repository_tup
            debug_msg = "Adding an entry for revision %s of repository %s owned by %s " % ( installed_changeset_revision, name, owner )
            debug_msg += "to tool_dependencies_of_installed_repositories."
            log.debug( debug_msg )
            tool_dependency_tups = []
            for tool_dependency in repository.tool_dependencies:
                tool_dependency_tup = tool_dependency_util.get_tool_dependency_tuple_for_installed_repository_manager( tool_dependency )
                tool_dependency_tups.append( tool_dependency_tup )
            self.tool_dependencies_of_installed_repositories[ repository_tup ] = tool_dependency_tups

    def get_containing_repository_for_tool_dependency( self, tool_dependency_tup ):
        tool_shed_repository_id, name, version, type = tool_dependency_tup
        return self.app.install_model.context.query( self.app.install_model.ToolShedRepository ).get( tool_shed_repository_id )
            
    def get_repository_install_dir( self, tool_shed_repository ):
        for tool_config in self.tool_configs:
            tree, error_message = xml_util.parse_xml( tool_config )
            if tree is None:
                return None
            root = tree.getroot()
            tool_path = root.get( 'tool_path', None )
            if tool_path:
                ts = common_util.remove_port_from_tool_shed_url( str( tool_shed_repository.tool_shed ) )
                relative_path = os.path.join( tool_path,
                                              ts,
                                              'repos',
                                              str( tool_shed_repository.owner ),
                                              str( tool_shed_repository.name ),
                                              str( tool_shed_repository.installed_changeset_revision ) )
                if os.path.exists( relative_path ):
                    return relative_path
        return None

    def handle_repository_install( self, repository ):
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

    def handle_repository_uninstall( self, repository ):
        """Remove the dependency relationships for a repository that was just uninstalled."""
        for tool_dependency in repository.tool_dependencies:
            tool_dependency_tup = tool_dependency_util.get_tool_dependency_tuple_for_installed_repository_manager( tool_dependency )
            # Remove this tool_dependency from all values in
            # self.installed_runtime_dependent_tool_dependencies_of_installed_tool_dependencies
            altered_installed_runtime_dependent_tool_dependencies_of_installed_tool_dependencies = {}
            for td_tup, installed_runtime_dependent_tool_dependency_tups in \
                self.installed_runtime_dependent_tool_dependencies_of_installed_tool_dependencies.items():
                if tool_dependency_tup in installed_runtime_dependent_tool_dependency_tups:
                    # Remove the tool_dependency from the list.
                    installed_runtime_dependent_tool_dependency_tups.remove( tool_dependency_tup )
                # Add the possibly altered list to the altered dictionary.
                altered_installed_runtime_dependent_tool_dependencies_of_installed_tool_dependencies[ td_tup ] = \
                    installed_runtime_dependent_tool_dependency_tups
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

    def handle_tool_dependency_install( self, repository, tool_dependency ):
        """Load the dependency relationships for a tool dependency that was just installed independently of its containing repository."""
        # The received repository must have a status of 'Installed'.  The value of tool_dependency.status will either be
        # 'Installed' or 'Error', but we only need to change the in-memory dictionaries if it is 'Installed'.
        if tool_dependency.is_installed:
            # Populate self.installed_runtime_dependent_tool_dependencies_of_installed_tool_dependencies.
            self.add_entry_to_installed_runtime_dependent_tool_dependencies_of_installed_tool_dependencies( tool_dependency )
            # Populate self.installed_tool_dependencies_of_installed_repositories.
            repository_tup = repository_dependency_util.get_repository_tuple_for_installed_repository_manager( repository )
            tool_dependency_tup = tool_dependency_util.get_tool_dependency_tuple_for_installed_repository_manager( tool_dependency )
            if repository_tup in self.installed_tool_dependencies_of_installed_repositories:
                self.installed_tool_dependencies_of_installed_repositories[ repository_tup ].append( tool_dependency_tup )
            else:
                self.installed_tool_dependencies_of_installed_repositories[ repository_tup ] = [ tool_dependency_tup ]

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
        """
        Remove an entry from self.installed_repository_dependencies_of_installed_repositories.  A side-effect of this method
        is removal of appropriate value items from self.installed_dependent_repositories_of_installed_repositories.
        """
        # Remove tuples defining this repository from value lists in self.installed_dependent_repositories_of_installed_repositories.
        repository_tup = repository_dependency_util.get_repository_tuple_for_installed_repository_manager( repository )
        tool_shed, name, owner, installed_changeset_revision = repository_tup
        altered_installed_dependent_repositories_of_installed_repositories = {}
        for r_tup, v_tups in self.installed_dependent_repositories_of_installed_repositories.items():
            if repository_tup in v_tups:
                debug_msg = "Removing entry for revision %s of repository %s owned by %s " % \
                    ( installed_changeset_revision, name, owner )
                r_tool_shed, r_name, r_owner, r_installed_changeset_revision = r_tup
                debug_msg += "from the dependent list for revision %s of repository %s owned by %s " % \
                    ( r_installed_changeset_revision, r_name, r_owner )
                debug_msg += "in installed_repository_dependencies_of_installed_repositories."
                log.debug( debug_msg )                
                v_tups.remove( repository_tup )
            altered_installed_dependent_repositories_of_installed_repositories[ r_tup ] = v_tups
        self.installed_dependent_repositories_of_installed_repositories = \
            altered_installed_dependent_repositories_of_installed_repositories
        # Remove this repository's entry from self.installed_repository_dependencies_of_installed_repositories.
        if repository_tup in self.installed_repository_dependencies_of_installed_repositories:
            debug_msg = "Removing entry for revision %s of repository %s owned by %s " % ( installed_changeset_revision, name, owner )
            debug_msg += "from installed_repository_dependencies_of_installed_repositories."
            log.debug( debug_msg )
            del self.installed_repository_dependencies_of_installed_repositories[ repository_tup ]

    def remove_entry_from_installed_runtime_dependent_tool_dependencies_of_installed_tool_dependencies( self, tool_dependency ):
        """Remove an entry from self.installed_runtime_dependent_tool_dependencies_of_installed_tool_dependencies."""
        tool_dependency_tup = tool_dependency_util.get_tool_dependency_tuple_for_installed_repository_manager( tool_dependency )
        if tool_dependency_tup in self.installed_runtime_dependent_tool_dependencies_of_installed_tool_dependencies:
            tool_shed_repository_id, name, version, type = tool_dependency_tup
            debug_msg = "Removing entry for version %s of %s %s " % ( version, type, name )
            debug_msg += "from installed_runtime_dependent_tool_dependencies_of_installed_tool_dependencies."
            log.debug( debug_msg )
            del self.installed_runtime_dependent_tool_dependencies_of_installed_tool_dependencies[ tool_dependency_tup ]

    def remove_entry_from_installed_tool_dependencies_of_installed_repositories( self, repository ):
        """Remove an entry from self.installed_tool_dependencies_of_installed_repositories."""
        repository_tup = repository_dependency_util.get_repository_tuple_for_installed_repository_manager( repository )
        if repository_tup in self.installed_tool_dependencies_of_installed_repositories:
            tool_shed, name, owner, installed_changeset_revision = repository_tup
            debug_msg = "Removing entry for revision %s of repository %s owned by %s " % ( installed_changeset_revision, name, owner )
            debug_msg += "from installed_tool_dependencies_of_installed_repositories."
            log.debug( debug_msg )
            del self.installed_tool_dependencies_of_installed_repositories[ repository_tup ]

    def remove_entry_from_repository_dependencies_of_installed_repositories( self, repository ):
        """Remove an entry from self.repository_dependencies_of_installed_repositories."""
        repository_tup = repository_dependency_util.get_repository_tuple_for_installed_repository_manager( repository )
        if repository_tup in self.repository_dependencies_of_installed_repositories:
            tool_shed, name, owner, installed_changeset_revision = repository_tup
            debug_msg = "Removing entry for revision %s of repository %s owned by %s " % ( installed_changeset_revision, name, owner )
            debug_msg += "from repository_dependencies_of_installed_repositories."
            log.debug( debug_msg )
            del self.repository_dependencies_of_installed_repositories[ repository_tup ]

    def remove_entry_from_runtime_tool_dependencies_of_installed_tool_dependencies( self, tool_dependency ):
        """Remove an entry from self.runtime_tool_dependencies_of_installed_tool_dependencies."""
        tool_dependency_tup = tool_dependency_util.get_tool_dependency_tuple_for_installed_repository_manager( tool_dependency )
        if tool_dependency_tup in self.runtime_tool_dependencies_of_installed_tool_dependencies:
            tool_shed_repository_id, name, version, type = tool_dependency_tup
            debug_msg = "Removing entry for version %s of %s %s from runtime_tool_dependencies_of_installed_tool_dependencies." % \
                ( version, type, name )
            log.debug( debug_msg )
            del self.runtime_tool_dependencies_of_installed_tool_dependencies[ tool_dependency_tup ]

    def remove_entry_from_tool_dependencies_of_installed_repositories( self, repository ):
        """Remove an entry from self.tool_dependencies_of_installed_repositories."""
        repository_tup = repository_dependency_util.get_repository_tuple_for_installed_repository_manager( repository )
        if repository_tup in self.tool_dependencies_of_installed_repositories:
            tool_shed, name, owner, installed_changeset_revision = repository_tup
            debug_msg = "Removing entry for revision %s of repository %s owned by %s from tool_dependencies_of_installed_repositories." % \
                ( installed_changeset_revision, name, owner )
            log.debug( debug_msg )
            del self.tool_dependencies_of_installed_repositories[ repository_tup ]
