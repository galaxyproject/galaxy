import logging
import os

from galaxy import util
from galaxy.util import inflector
from galaxy.web.form_builder import SelectField

from tool_shed.metadata import metadata_generator

from tool_shed.util import common_util
from tool_shed.util import shed_util_common as suc
from tool_shed.util import tool_util

log = logging.getLogger( __name__ )


class InstalledRepositoryMetadataManager( metadata_generator.MetadataGenerator ):

    def __init__( self, app ):
        super( InstalledRepositoryMetadataManager, self ).__init__( app )
        self.app = app

    def build_repository_ids_select_field( self, name='repository_ids', multiple=True, display='checkboxes' ):
        """Generate the current list of repositories for resetting metadata."""
        repositories_select_field = SelectField( name=name, multiple=multiple, display=display )
        query = self.get_query_for_setting_metadata_on_repositories( order=True )
        for repository in query:
            owner = str( repository.owner )
            option_label = '%s (%s)' % ( str( repository.name ), owner )
            option_value = '%s' % self.app.security.encode_id( repository.id )
            repositories_select_field.add_option( option_label, option_value )
        return repositories_select_field

    def get_query_for_setting_metadata_on_repositories( self, order=True ):
        """
        Return a query containing repositories for resetting metadata.  The order parameter
        is used for displaying the list of repositories ordered alphabetically for display on
        a page.  When called from the Galaxy API, order is False.
        """
        if order:
            return self.app.install_model.context.query( self.app.install_model.ToolShedRepository ) \
                                                 .filter( self.app.install_model.ToolShedRepository.table.c.uninstalled == False ) \
                                                 .order_by( self.app.install_model.ToolShedRepository.table.c.name,
                                                            self.app.install_model.ToolShedRepository.table.c.owner )
        else:
            return self.app.install_model.context.query( self.app.install_model.ToolShedRepository ) \
                                                 .filter( self.app.install_model.ToolShedRepository.table.c.uninstalled == False )

    def reset_all_metadata_on_installed_repository( self, id ):
        """Reset all metadata on a single tool shed repository installed into a Galaxy instance."""
        invalid_file_tups = []
        metadata_dict = {}
        repository = suc.get_installed_tool_shed_repository( self.app, id )
        repository_clone_url = common_util.generate_clone_url_for_installed_repository( self.app, repository )
        tool_path, relative_install_dir = repository.get_tool_relative_path( self.app )
        if relative_install_dir:
            original_metadata_dict = repository.metadata
            metadata_dict, invalid_file_tups = \
                self.generate_metadata_for_changeset_revision( repository=repository,
                                                               changeset_revision=repository.changeset_revision,
                                                               repository_clone_url=repository_clone_url,
                                                               shed_config_dict = repository.get_shed_config_dict( self.app ),
                                                               relative_install_dir=relative_install_dir,
                                                               repository_files_dir=None,
                                                               resetting_all_metadata_on_repository=False,
                                                               updating_installed_repository=False,
                                                               persist=False )
            repository.metadata = metadata_dict
            if metadata_dict != original_metadata_dict:
                suc.update_in_shed_tool_config( self.app, repository )
                self.app.install_model.context.add( repository )
                self.app.install_model.context.flush()
                log.debug( 'Metadata has been reset on repository %s.' % repository.name )
            else:
                log.debug( 'Metadata did not need to be reset on repository %s.' % repository.name )
        else:
            log.debug( 'Error locating installation directory for repository %s.' % repository.name )
        return invalid_file_tups, metadata_dict

    def reset_metadata_on_selected_repositories( self, user, **kwd ):
        """
        Inspect the repository changelog to reset metadata for all appropriate changeset revisions.
        This method is called from both Galaxy and the Tool Shed.
        """
        repository_ids = util.listify( kwd.get( 'repository_ids', None ) )
        message = ''
        status = 'done'
        if repository_ids:
            successful_count = 0
            unsuccessful_count = 0
            for repository_id in repository_ids:
                try:
                    repository = suc.get_installed_tool_shed_repository( self.app, repository_id )
                    owner = str( repository.owner )
                    invalid_file_tups, metadata_dict = \
                        self.reset_all_metadata_on_installed_repository( repository_id )
                    if invalid_file_tups:
                        message = tool_util.generate_message_for_invalid_tools( self.app,
                                                                                invalid_file_tups,
                                                                                repository,
                                                                                None,
                                                                                as_html=False )
                        log.debug( message )
                        unsuccessful_count += 1
                    else:
                        log.debug( "Successfully reset metadata on repository %s owned by %s" % ( str( repository.name ), owner ) )
                        successful_count += 1
                except:
                    log.exception( "Error attempting to reset metadata on repository %s", str( repository.name ) )
                    unsuccessful_count += 1
            message = "Successfully reset metadata on %d %s.  " % \
                ( successful_count, inflector.cond_plural( successful_count, "repository" ) )
            if unsuccessful_count:
                message += "Error setting metadata on %d %s - see the paster log for details.  " % \
                    ( unsuccessful_count, inflector.cond_plural( unsuccessful_count, "repository" ) )
        else:
            message = 'Select at least one repository to on which to reset all metadata.'
            status = 'error'
        return message, status
