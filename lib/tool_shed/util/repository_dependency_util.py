import os, logging
from galaxy.util import json
import tool_shed.util.shed_util_common as suc
from tool_shed.util import common_install_util, encoding_util, metadata_util, tool_util
from galaxy.webapps.tool_shed.util import container_util

from galaxy import eggs
import pkg_resources

pkg_resources.require( 'mercurial' )
from mercurial import hg, ui, commands

log = logging.getLogger( __name__ )

def build_repository_dependency_relationships( trans, repo_info_dicts, tool_shed_repositories ):
    """
    Build relationships between installed tool shed repositories and other installed tool shed repositories upon which they depend.  These
    relationships are defined in the repository_dependencies entry for each dictionary in the received list of repo_info_dicts.  Each of
    these dictionaries is associated with a repository in the received tool_shed_repositories list.
    """
    for repo_info_dict in repo_info_dicts:
        for name, repo_info_tuple in repo_info_dict.items():
            description, repository_clone_url, changeset_revision, ctx_rev, repository_owner, repository_dependencies, tool_dependencies = \
                suc.get_repo_info_tuple_contents( repo_info_tuple )
            if repository_dependencies:
                for key, val in repository_dependencies.items():
                    if key in [ 'root_key', 'description' ]:
                        continue
                    dependent_repository = None
                    dependent_toolshed, dependent_name, dependent_owner, dependent_changeset_revision = container_util.get_components_from_key( key )
                    for tsr in tool_shed_repositories:
                        # Get the the tool_shed_repository defined by name, owner and changeset_revision.  This is the repository that will be
                        # dependent upon each of the tool shed repositories contained in val.
                        # TODO: Check tool_shed_repository.tool_shed as well when repository dependencies across tool sheds is supported.
                        if tsr.name == dependent_name and tsr.owner == dependent_owner and tsr.changeset_revision == dependent_changeset_revision:
                            dependent_repository = tsr
                            break
                    if dependent_repository is None:
                        # The dependent repository is not in the received list so look in the database.
                        dependent_repository = suc.get_or_create_tool_shed_repository( trans, dependent_toolshed, dependent_name, dependent_owner, dependent_changeset_revision )
                    # Process each repository_dependency defined for the current dependent repository.
                    for repository_dependency_components_list in val:
                        required_repository = None
                        rd_toolshed, rd_name, rd_owner, rd_changeset_revision = repository_dependency_components_list
                        # Get the the tool_shed_repository defined by rd_name, rd_owner and rd_changeset_revision.  This is the repository that will be
                        # required by the current dependent_repository.
                        # TODO: Check tool_shed_repository.tool_shed as well when repository dependencies across tool sheds is supported.
                        for tsr in tool_shed_repositories:
                            if tsr.name == rd_name and tsr.owner == rd_owner and tsr.changeset_revision == rd_changeset_revision:
                                required_repository = tsr
                                break
                        if required_repository is None:
                            # The required repository is not in the received list so look in the database.
                            required_repository = suc.get_or_create_tool_shed_repository( trans, rd_toolshed, rd_name, rd_owner, rd_changeset_revision )                                                             
                        # Ensure there is a repository_dependency relationship between dependent_repository and required_repository.
                        rrda = None
                        for rd in dependent_repository.repository_dependencies:
                            if rd.id == required_repository.id:
                                rrda = rd
                                break
                        if not rrda:
                            # Make sure required_repository is in the repository_dependency table.
                            repository_dependency = get_repository_dependency_by_repository_id( trans, required_repository.id )
                            if not repository_dependency:
                                repository_dependency = trans.model.RepositoryDependency( tool_shed_repository_id=required_repository.id )
                                trans.sa_session.add( repository_dependency )
                                trans.sa_session.flush()
                            # Build the relationship between the dependent_repository and the required_repository.
                            rrda = trans.model.RepositoryRepositoryDependencyAssociation( tool_shed_repository_id=dependent_repository.id,
                                                                                          repository_dependency_id=repository_dependency.id )
                            trans.sa_session.add( rrda )
                            trans.sa_session.flush()

def can_add_to_key_rd_dicts( key_rd_dict, key_rd_dicts ):
    """Handle the case where an update to the changeset revision was done."""
    k = key_rd_dict.keys()[ 0 ]
    rd = key_rd_dict[ k ]
    partial_rd = rd[ 0:3 ]
    for kr_dict in key_rd_dicts:
        key = kr_dict.keys()[ 0 ]
        if key == k:
            val = kr_dict[ key ]
            for repository_dependency in val:
                if repository_dependency[ 0:3 ] == partial_rd:
                    return False
    return True

def create_repository_dependency_objects( trans, tool_path, tool_shed_url, repo_info_dicts, reinstalling=False, install_repository_dependencies=False,
                                          no_changes_checked=False, tool_panel_section=None, new_tool_panel_section=None ):
    """
    Discover all repository dependencies and make sure all tool_shed_repository and associated repository_dependency records exist as well as
    the dependency relationships between installed repositories.  This method is called when new repositories are being installed into a Galaxy
    instance and when uninstalled repositories are being reinstalled.
    """
    message = ''
    # The following list will be maintained within this method to contain all created or updated tool shed repositories, including repository dependencies
    # that may not be installed.
    all_created_or_updated_tool_shed_repositories = []
    # There will be a one-to-one mapping between items in 3 lists: created_or_updated_tool_shed_repositories, tool_panel_section_keys and filtered_repo_info_dicts.
    # The 3 lists will filter out repository dependencies that are not to be installed.
    created_or_updated_tool_shed_repositories = []
    tool_panel_section_keys = []
    # Repositories will be filtered (e.g., if already installed, if elected to not be installed, etc), so filter the associated repo_info_dicts accordingly.
    filtered_repo_info_dicts = []
    # Discover all repository dependencies and retrieve information for installing them.  Even if the user elected to not install repository dependencies we have
    # to make sure all repository dependency objects exist so that the appropriate repository dependency relationships can be built.
    all_repo_info_dicts = suc.get_required_repo_info_dicts( tool_shed_url, repo_info_dicts )
    if not all_repo_info_dicts:
        # No repository dependencies were discovered so process the received repositories.
        all_repo_info_dicts = [ rid for rid in repo_info_dicts ]
    for repo_info_dict in all_repo_info_dicts:
        for name, repo_info_tuple in repo_info_dict.items():
            description, repository_clone_url, changeset_revision, ctx_rev, repository_owner, repository_dependencies, tool_dependencies = \
                suc.get_repo_info_tuple_contents( repo_info_tuple )
            # Make sure the repository was not already installed.
            installed_tool_shed_repository, installed_changeset_revision = suc.repository_was_previously_installed( trans, tool_shed_url, name, repo_info_tuple )
            if installed_tool_shed_repository:
                tool_section, new_tool_panel_section, tool_panel_section_key = tool_util.handle_tool_panel_selection( trans=trans,
                                                                                                                      metadata=installed_tool_shed_repository.metadata,
                                                                                                                      no_changes_checked=no_changes_checked,
                                                                                                                      tool_panel_section=tool_panel_section,
                                                                                                                      new_tool_panel_section=new_tool_panel_section )
                if reinstalling or install_repository_dependencies:
                    # If the user elected to install repository dependencies, all items in the all_repo_info_dicts list will be processed.  However, if
                    # repository dependencies are not to be installed, only those items contained in the received repo_info_dicts list will be processed.
                    if is_in_repo_info_dicts( repo_info_dict, repo_info_dicts ) or install_repository_dependencies:
                        if installed_tool_shed_repository.status in [ trans.model.ToolShedRepository.installation_status.ERROR,
                                                                      trans.model.ToolShedRepository.installation_status.UNINSTALLED ]:
                            # The current tool shed repository is not currently installed, so we can update it's record in the database.
                            can_update = True
                            name = installed_tool_shed_repository.name
                            description = installed_tool_shed_repository.description
                            installed_changeset_revision = installed_tool_shed_repository.installed_changeset_revision
                            metadata_dict = installed_tool_shed_repository.metadata
                            dist_to_shed = installed_tool_shed_repository.dist_to_shed
                        elif installed_tool_shed_repository.status in [ trans.model.ToolShedRepository.installation_status.DEACTIVATED ]:
                            # The current tool shed repository is deactivated, so updating it's database record is not necessary - just activate it.
                            common_install_util.activate_repository( trans, installed_tool_shed_repository )
                            can_update = False
                        else:
                            # The tool shed repository currently being processed is already installed or is in the process of being installed, so it's record
                            # in the database cannot be updated.
                            can_update = False
                    else:
                        # This block will be reached only if reinstalling is True, install_repository_dependencies is False and is_in_repo_info_dicts is False.
                        # The tool shed repository currently being processed must be a repository dependency that the user elected to not install, so it's
                        # record in the database cannot be updated.
                        can_update = False
                else:
                    # This block will be reached only if reinstalling is False and install_repository_dependencies is False.  This implies that the tool shed
                    # repository currently being processed has already been installed.
                    if len( all_repo_info_dicts ) == 1:
                        # If only a single repository is being installed, return an informative message to the user.
                        message += "Revision <b>%s</b> of tool shed repository <b>%s</b> owned by <b>%s</b> " % ( changeset_revision, name, repository_owner )
                        if installed_changeset_revision != changeset_revision:
                            message += "was previously installed using changeset revision <b>%s</b>.  " % installed_changeset_revision
                        else:
                            message += "was previously installed.  "
                        if installed_tool_shed_repository.uninstalled:
                            message += "The repository has been uninstalled, however, so reinstall the original repository instead of installing it again.  "
                        elif installed_tool_shed_repository.deleted:
                            message += "The repository has been deactivated, however, so activate the original repository instead of installing it again.  "
                        if installed_changeset_revision != changeset_revision:
                            message += "You can get the latest updates for the repository using the <b>Get updates</b> option from the repository's "
                            message += "<b>Repository Actions</b> pop-up menu.  "
                        created_or_updated_tool_shed_repositories.append( installed_tool_shed_repository )
                        tool_panel_section_keys.append( tool_panel_section_key )
                        return created_or_updated_tool_shed_repositories, tool_panel_section_keys, all_repo_info_dicts, filtered_repo_info_dicts, message
                    else:
                        # We're in the process of installing multiple tool shed repositories into Galaxy.  Since the repository currently being processed
                        # has already been installed, skip it and process the next repository in the list.
                        can_update = False
            else:
                # A tool shed repository is being installed into a Galaxy instance for the first time, or we're attempting to install it or reinstall it resulted
                # in an error.  In the latter case, the repository record in the database has no metadata and it's status has been set to 'New'.  In either case,
                # the repository's database record may be updated.
                can_update = True
                installed_changeset_revision = changeset_revision
                metadata_dict = {}
                dist_to_shed = False
            if can_update:
                # The database record for the tool shed repository currently being processed can be updated.
                if reinstalling or install_repository_dependencies:
                    # Get the repository metadata to see where it was previously located in the tool panel.
                    if installed_tool_shed_repository:
                        # The tool shed repository status is one of 'New', 'Uninstalled', or 'Error'.
                        tool_section, new_tool_panel_section, tool_panel_section_key = tool_util.handle_tool_panel_selection( trans=trans,
                                                                                                                              metadata=installed_tool_shed_repository.metadata,
                                                                                                                              no_changes_checked=no_changes_checked,
                                                                                                                              tool_panel_section=tool_panel_section,
                                                                                                                              new_tool_panel_section=new_tool_panel_section )
                    else:
                        # We're installing a new tool shed repository that does not yet have a database record.  This repository is a repository dependency
                        # of a different repository being installed.
                        if new_tool_panel_section:
                            section_id = new_tool_panel_section.lower().replace( ' ', '_' )
                            tool_panel_section_key = 'section_%s' % str( section_id )
                        elif tool_panel_section:
                            tool_panel_section_key = 'section_%s' % tool_panel_section
                        else:
                            tool_panel_section_key = None
                else:
                    # We're installing a new tool shed repository that does not yet have a database record.
                    if new_tool_panel_section:
                        section_id = new_tool_panel_section.lower().replace( ' ', '_' )
                        tool_panel_section_key = 'section_%s' % str( section_id )
                    elif tool_panel_section:
                        tool_panel_section_key = 'section_%s' % tool_panel_section
                    else:
                        tool_panel_section_key = None
                tool_shed_repository = suc.create_or_update_tool_shed_repository( app=trans.app,
                                                                                  name=name,
                                                                                  description=description,
                                                                                  installed_changeset_revision=changeset_revision,
                                                                                  ctx_rev=ctx_rev,
                                                                                  repository_clone_url=repository_clone_url,
                                                                                  metadata_dict={},
                                                                                  status=trans.model.ToolShedRepository.installation_status.NEW,
                                                                                  current_changeset_revision=changeset_revision,
                                                                                  owner=repository_owner,
                                                                                  dist_to_shed=False )
                # Add the processed tool shed repository to the list of all processed repositories maintained within this method.
                all_created_or_updated_tool_shed_repositories.append( tool_shed_repository )
                # Only append the tool shed repository to the list of created_or_updated_tool_shed_repositories if it is supposed to be installed.
                if install_repository_dependencies or is_in_repo_info_dicts( repo_info_dict, repo_info_dicts ):
                    # Keep the one-to-one mapping between items in 3 lists.
                    created_or_updated_tool_shed_repositories.append( tool_shed_repository )
                    tool_panel_section_keys.append( tool_panel_section_key )
                    filtered_repo_info_dicts.append( repo_info_dict )
    # Build repository dependency relationships even if the user chose to not install repository dependencies.
    build_repository_dependency_relationships( trans, all_repo_info_dicts, all_created_or_updated_tool_shed_repositories )                     
    return created_or_updated_tool_shed_repositories, tool_panel_section_keys, all_repo_info_dicts, filtered_repo_info_dicts, message

def generate_message_for_invalid_repository_dependencies( metadata_dict ):
    """Return the error message associated with an invalid repository dependency for display in the caller."""
    message = ''
    if metadata_dict:
        invalid_repository_dependencies_dict = metadata_dict.get( 'invalid_repository_dependencies', None )
        if invalid_repository_dependencies_dict:
            invalid_repository_dependencies = invalid_repository_dependencies_dict[ 'invalid_repository_dependencies' ]
            for repository_dependency_tup in invalid_repository_dependencies:
                toolshed, name, owner, changeset_revision, error = repository_dependency_tup
                if error:
                    message = '%s  ' % str( error )
    return message

def get_key_for_repository_changeset_revision( toolshed_base_url, repository, repository_metadata ):
    return container_util.generate_repository_dependencies_key_for_repository( toolshed_base_url=toolshed_base_url,
                                                                               repository_name=repository.name,
                                                                               repository_owner=repository.user.username,
                                                                               changeset_revision=repository_metadata.changeset_revision )

def get_repository_dependencies_for_changeset_revision( trans, repository, repository_metadata, toolshed_base_url,
                                                        key_rd_dicts_to_be_processed=None, all_repository_dependencies=None,
                                                        handled_key_rd_dicts=None, circular_repository_dependencies=None ):
    """
    Return a dictionary of all repositories upon which the contents of the received repository_metadata record depend.  The dictionary keys
    are name-spaced values consisting of toolshed_base_url/repository_name/repository_owner/changeset_revision and the values are lists of
    repository_dependency tuples consisting of ( toolshed_base_url, repository_name, repository_owner, changeset_revision ).  This method
    ensures that all required repositories to the nth degree are returned.
    """
    if handled_key_rd_dicts is None:
        handled_key_rd_dicts = []
    if all_repository_dependencies is None:
        all_repository_dependencies = {}
    if key_rd_dicts_to_be_processed is None:
        key_rd_dicts_to_be_processed = []
    if circular_repository_dependencies is None:
        circular_repository_dependencies = []
    # Assume the current repository does not have repository dependencies defined for it.
    current_repository_key = None
    metadata = repository_metadata.metadata
    if metadata:
        if 'repository_dependencies' in metadata:
            current_repository_key = get_key_for_repository_changeset_revision( toolshed_base_url, repository, repository_metadata )
            repository_dependencies_dict = metadata[ 'repository_dependencies' ]
            if not all_repository_dependencies:
                all_repository_dependencies = initialize_all_repository_dependencies( current_repository_key,
                                                                                      repository_dependencies_dict,
                                                                                      all_repository_dependencies )
            # Handle the repository dependencies defined in the current repository, if any, and populate the various repository dependency objects for
            # this round of processing.
            current_repository_key_rd_dicts, key_rd_dicts_to_be_processed, handled_key_rd_dicts, all_repository_dependencies = \
                populate_repository_dependency_objects_for_processing( trans,
                                                                       current_repository_key,
                                                                       repository_dependencies_dict,
                                                                       key_rd_dicts_to_be_processed,
                                                                       handled_key_rd_dicts,
                                                                       circular_repository_dependencies,
                                                                       all_repository_dependencies )
    if current_repository_key:
        if current_repository_key_rd_dicts:
            # There should be only a single current_repository_key_rd_dict in this list.
            current_repository_key_rd_dict = current_repository_key_rd_dicts[ 0 ]
            # Handle circular repository dependencies.
            if not in_circular_repository_dependencies( current_repository_key_rd_dict, circular_repository_dependencies ):
                if current_repository_key in all_repository_dependencies:
                    handle_current_repository_dependency( trans,
                                                          current_repository_key,
                                                          key_rd_dicts_to_be_processed,
                                                          all_repository_dependencies,
                                                          handled_key_rd_dicts,
                                                          circular_repository_dependencies )
            elif key_rd_dicts_to_be_processed:
                handle_next_repository_dependency( trans, key_rd_dicts_to_be_processed, all_repository_dependencies, handled_key_rd_dicts, circular_repository_dependencies )
        elif key_rd_dicts_to_be_processed:
            handle_next_repository_dependency( trans, key_rd_dicts_to_be_processed, all_repository_dependencies, handled_key_rd_dicts, circular_repository_dependencies )
    elif key_rd_dicts_to_be_processed:
        handle_next_repository_dependency( trans, key_rd_dicts_to_be_processed, all_repository_dependencies, handled_key_rd_dicts, circular_repository_dependencies )
    all_repository_dependencies = prune_invalid_repository_dependencies( all_repository_dependencies )
    return all_repository_dependencies

def get_updated_changeset_revisions_for_repository_dependencies( trans, key_rd_dicts ):
    updated_key_rd_dicts = []
    for key_rd_dict in key_rd_dicts:
        key = key_rd_dict.keys()[ 0 ]
        repository_dependency = key_rd_dict[ key ]
        rd_toolshed, rd_name, rd_owner, rd_changeset_revision = repository_dependency
        if suc.tool_shed_is_this_tool_shed( rd_toolshed ):
            repository = suc.get_repository_by_name_and_owner( trans.app, rd_name, rd_owner )
            if repository:
                repository_metadata = metadata_util.get_repository_metadata_by_repository_id_changeset_revision( trans,
                                                                                                                 trans.security.encode_id( repository.id ),
                                                                                                                 rd_changeset_revision )
                if repository_metadata:
                    # The repository changeset_revision is installable, so no updates are available.
                    new_key_rd_dict = {}
                    new_key_rd_dict[ key ] = repository_dependency
                    updated_key_rd_dicts.append( key_rd_dict )
                else:
                    # The repository changeset_revision is no longer installable, so see if there's been an update.
                    repo_dir = repository.repo_path( trans.app )
                    repo = hg.repository( suc.get_configured_ui(), repo_dir )
                    changeset_revision = suc.get_next_downloadable_changeset_revision( repository, repo, rd_changeset_revision )
                    repository_metadata = metadata_util.get_repository_metadata_by_repository_id_changeset_revision( trans,
                                                                                                                     trans.security.encode_id( repository.id ),
                                                                                                                     changeset_revision )
                    if repository_metadata:
                        new_key_rd_dict = {}
                        new_key_rd_dict[ key ] = [ rd_toolshed, rd_name, rd_owner, repository_metadata.changeset_revision ]
                        # We have the updated changset revision.
                        updated_key_rd_dicts.append( new_key_rd_dict )
                    else:
                        toolshed, repository_name, repository_owner, repository_changeset_revision = container_util.get_components_from_key( key )
                        message = "The revision %s defined for repository %s owned by %s is invalid, so repository dependencies defined for repository %s will be ignored." % \
                            ( str( rd_changeset_revision ), str( rd_name ), str( rd_owner ), str( repository_name ) )
                        log.debug( message )
            else:
                toolshed, repository_name, repository_owner, repository_changeset_revision = container_util.get_components_from_key( key )
                message = "The revision %s defined for repository %s owned by %s is invalid, so repository dependencies defined for repository %s will be ignored." % \
                    ( str( rd_changeset_revision ), str( rd_name ), str( rd_owner ), str( repository_name ) )
                log.debug( message )
    return updated_key_rd_dicts

def handle_circular_repository_dependency( repository_key, repository_dependency, circular_repository_dependencies, handled_key_rd_dicts, all_repository_dependencies ):
    all_repository_dependencies_root_key = all_repository_dependencies[ 'root_key' ]
    repository_dependency_as_key = get_repository_dependency_as_key( repository_dependency )
    repository_key_as_repository_dependency = repository_key.split( container_util.STRSEP )
    update_circular_repository_dependencies( repository_key,
                                             repository_dependency,
                                             all_repository_dependencies[ repository_dependency_as_key ],
                                             circular_repository_dependencies )
    if all_repository_dependencies_root_key != repository_dependency_as_key:
        all_repository_dependencies[ repository_key ] = [ repository_dependency ]
    return circular_repository_dependencies, handled_key_rd_dicts, all_repository_dependencies

def handle_current_repository_dependency( trans, current_repository_key, key_rd_dicts_to_be_processed, all_repository_dependencies, handled_key_rd_dicts,
                                          circular_repository_dependencies ):
    current_repository_key_rd_dicts = []
    for rd in all_repository_dependencies[ current_repository_key ]:
        rd_copy = [ str( item ) for item in rd ]
        new_key_rd_dict = {}
        new_key_rd_dict[ current_repository_key ] = rd_copy
        current_repository_key_rd_dicts.append( new_key_rd_dict )
    if current_repository_key_rd_dicts:
        toolshed, required_repository, required_repository_metadata, repository_key_rd_dicts, key_rd_dicts_to_be_processed, handled_key_rd_dicts = \
            handle_key_rd_dicts_for_repository( trans,
                                                current_repository_key,
                                                current_repository_key_rd_dicts,
                                                key_rd_dicts_to_be_processed,
                                                handled_key_rd_dicts,
                                                circular_repository_dependencies )
        return get_repository_dependencies_for_changeset_revision( trans=trans,
                                                                   repository=required_repository,
                                                                   repository_metadata=required_repository_metadata,
                                                                   toolshed_base_url=toolshed,
                                                                   key_rd_dicts_to_be_processed=key_rd_dicts_to_be_processed,
                                                                   all_repository_dependencies=all_repository_dependencies,
                                                                   handled_key_rd_dicts=handled_key_rd_dicts,
                                                                   circular_repository_dependencies=circular_repository_dependencies )

def handle_key_rd_dicts_for_repository( trans, current_repository_key, repository_key_rd_dicts, key_rd_dicts_to_be_processed, handled_key_rd_dicts, circular_repository_dependencies ):
    key_rd_dict = repository_key_rd_dicts.pop( 0 )
    repository_dependency = key_rd_dict[ current_repository_key ]
    toolshed, name, owner, changeset_revision = repository_dependency
    if suc.tool_shed_is_this_tool_shed( toolshed ):
        required_repository = suc.get_repository_by_name_and_owner( trans.app, name, owner )
        required_repository_metadata = metadata_util.get_repository_metadata_by_repository_id_changeset_revision( trans,
                                                                                                                  trans.security.encode_id( required_repository.id ),
                                                                                                                  changeset_revision )
        if required_repository_metadata:
            # The required_repository_metadata changeset_revision is installable.
            required_metadata = required_repository_metadata.metadata
            if required_metadata:
                for current_repository_key_rd_dict in repository_key_rd_dicts:
                    if not in_key_rd_dicts( current_repository_key_rd_dict, key_rd_dicts_to_be_processed ):
                        key_rd_dicts_to_be_processed.append( current_repository_key_rd_dict )
        # Mark the current repository_dependency as handled_key_rd_dicts.
        if not in_key_rd_dicts( key_rd_dict, handled_key_rd_dicts ):
            handled_key_rd_dicts.append( key_rd_dict )
        # Remove the current repository from the list of repository_dependencies to be processed.
        if in_key_rd_dicts( key_rd_dict, key_rd_dicts_to_be_processed ):
            key_rd_dicts_to_be_processed = remove_from_key_rd_dicts( key_rd_dict, key_rd_dicts_to_be_processed )
    else:
        # The repository is in a different tool shed, so build an url and send a request.
        error_message = "Repository dependencies are currently supported only within the same tool shed.  Ignoring repository dependency definition "
        error_message += "for tool shed %s, name %s, owner %s, changeset revision %s" % ( toolshed, name, owner, changeset_revision )
        log.debug( error_message )
    return toolshed, required_repository, required_repository_metadata, repository_key_rd_dicts, key_rd_dicts_to_be_processed, handled_key_rd_dicts

def handle_next_repository_dependency( trans, key_rd_dicts_to_be_processed, all_repository_dependencies, handled_key_rd_dicts, circular_repository_dependencies ):
    next_repository_key_rd_dict = key_rd_dicts_to_be_processed.pop( 0 )
    next_repository_key_rd_dicts = [ next_repository_key_rd_dict ]
    next_repository_key = next_repository_key_rd_dict.keys()[ 0 ]
    toolshed, required_repository, required_repository_metadata, repository_key_rd_dicts, key_rd_dicts_to_be_processed, handled_key_rd_dicts = \
        handle_key_rd_dicts_for_repository( trans,
                                            next_repository_key,
                                            next_repository_key_rd_dicts,
                                            key_rd_dicts_to_be_processed,
                                            handled_key_rd_dicts,
                                            circular_repository_dependencies )
    return get_repository_dependencies_for_changeset_revision( trans=trans,
                                                               repository=required_repository,
                                                               repository_metadata=required_repository_metadata,
                                                               toolshed_base_url=toolshed,
                                                               key_rd_dicts_to_be_processed=key_rd_dicts_to_be_processed,
                                                               all_repository_dependencies=all_repository_dependencies,
                                                               handled_key_rd_dicts=handled_key_rd_dicts,
                                                               circular_repository_dependencies=circular_repository_dependencies )

def in_all_repository_dependencies( repository_key, repository_dependency, all_repository_dependencies ):
    """Return True if { repository_key :repository_dependency } is in all_repository_dependencies."""
    for key, val in all_repository_dependencies.items():
        if key != repository_key:
            continue
        if repository_dependency in val:
            return True
    return False

def in_circular_repository_dependencies( repository_key_rd_dict, circular_repository_dependencies ):
    """
    Return True if any combination of a circular dependency tuple is the key : value pair defined in the received repository_key_rd_dict.  This
    means that each circular dependency tuple is converted into the key : value pair for vomparision.
    """
    for tup in circular_repository_dependencies:
        rd_0, rd_1 = tup
        rd_0_as_key = get_repository_dependency_as_key( rd_0 )
        rd_1_as_key = get_repository_dependency_as_key( rd_1 )
        if rd_0_as_key in repository_key_rd_dict and repository_key_rd_dict[ rd_0_as_key ] == rd_1:
            return True
        if rd_1_as_key in repository_key_rd_dict and repository_key_rd_dict[ rd_1_as_key ] == rd_0:
            return True
    return False

def initialize_all_repository_dependencies( current_repository_key, repository_dependencies_dict, all_repository_dependencies ):
    # Initialize the all_repository_dependencies dictionary.  It's safe to assume that current_repository_key in this case will have a value.
    all_repository_dependencies[ 'root_key' ] = current_repository_key
    all_repository_dependencies[ current_repository_key ] = []
    # Store the value of the 'description' key only once, the first time through this recursive method.
    description = repository_dependencies_dict.get( 'description', None )
    all_repository_dependencies[ 'description' ] = description
    return all_repository_dependencies

def in_key_rd_dicts( key_rd_dict, key_rd_dicts ):
    k = key_rd_dict.keys()[ 0 ]
    v = key_rd_dict[ k ]
    for key_rd_dict in key_rd_dicts:
        for key, val in key_rd_dict.items():
            if key == k and val == v:
                return True
    return False

def is_circular_repository_dependency( repository_key, repository_dependency, all_repository_dependencies ):
    """
    Return True if the received repository_dependency is a key in all_repository_dependencies whose list of repository dependencies
    includes the received repository_key.
    """
    repository_dependency_as_key = get_repository_dependency_as_key( repository_dependency )
    repository_key_as_repository_dependency = repository_key.split( container_util.STRSEP )
    for key, val in all_repository_dependencies.items():
        if key != repository_dependency_as_key:
            continue
        if repository_key_as_repository_dependency in val:
            return True
    return False

def is_in_repo_info_dicts( repo_info_dict, repo_info_dicts ):
    """Return True if the received repo_info_dict is contained in the list of received repo_info_dicts."""
    for name, repo_info_tuple in repo_info_dict.items():
        for rid in repo_info_dicts:
            for rid_name, rid_repo_info_tuple in rid.items():
                if rid_name == name:
                    if len( rid_repo_info_tuple ) == len( repo_info_tuple ):
                        for item in rid_repo_info_tuple:
                            if item not in repo_info_tuple:
                                return False
                        return True
        return False

def merge_missing_repository_dependencies_to_installed_container( containers_dict ):
    """ Merge the list of missing repository dependencies into the list of installed repository dependencies."""
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
            # Change the folder label from 'Missing repository dependencies' to be 'Repository dependencies' for display.
            root_container = containers_dict[ 'missing_repository_dependencies' ]
            for sub_container in root_container.folders:
                # There should only be 1 subfolder.
                sub_container.label = 'Repository dependencies'
            containers_dict[ 'repository_dependencies' ] = root_container
    containers_dict[ 'missing_repository_dependencies' ] = None
    return containers_dict

def populate_repository_dependency_objects_for_processing( trans, current_repository_key, repository_dependencies_dict, key_rd_dicts_to_be_processed,
                                                           handled_key_rd_dicts, circular_repository_dependencies, all_repository_dependencies ):
    current_repository_key_rd_dicts = []
    filtered_current_repository_key_rd_dicts = []
    for rd in repository_dependencies_dict[ 'repository_dependencies' ]:
        new_key_rd_dict = {}
        new_key_rd_dict[ current_repository_key ] = rd
        current_repository_key_rd_dicts.append( new_key_rd_dict )
    if current_repository_key_rd_dicts and current_repository_key:
        # Remove all repository dependencies that point to a revision within its own repository.
        current_repository_key_rd_dicts = remove_ropository_dependency_reference_to_self( current_repository_key_rd_dicts )
    current_repository_key_rd_dicts = get_updated_changeset_revisions_for_repository_dependencies( trans, current_repository_key_rd_dicts )
    for key_rd_dict in current_repository_key_rd_dicts:
        is_circular = False
        if not in_key_rd_dicts( key_rd_dict, handled_key_rd_dicts ) and not in_key_rd_dicts( key_rd_dict, key_rd_dicts_to_be_processed ):
            filtered_current_repository_key_rd_dicts.append( key_rd_dict )
            repository_dependency = key_rd_dict[ current_repository_key ]
            if current_repository_key in all_repository_dependencies:
                # Add all repository dependencies for the current repository into it's entry in all_repository_dependencies.
                all_repository_dependencies_val = all_repository_dependencies[ current_repository_key ]
                if repository_dependency not in all_repository_dependencies_val:
                    all_repository_dependencies_val.append( repository_dependency )
                    all_repository_dependencies[ current_repository_key ] = all_repository_dependencies_val
            elif not in_all_repository_dependencies( current_repository_key, repository_dependency, all_repository_dependencies ):
                # Handle circular repository dependencies.
                if is_circular_repository_dependency( current_repository_key, repository_dependency, all_repository_dependencies ):
                    is_circular = True
                    circular_repository_dependencies, handled_key_rd_dicts, all_repository_dependencies = \
                        handle_circular_repository_dependency( current_repository_key,
                                                               repository_dependency,
                                                               circular_repository_dependencies,
                                                               handled_key_rd_dicts,
                                                               all_repository_dependencies )
                else:
                    all_repository_dependencies[ current_repository_key ] = [ repository_dependency ]
            if not is_circular and can_add_to_key_rd_dicts( key_rd_dict, key_rd_dicts_to_be_processed ):
                new_key_rd_dict = {}
                new_key_rd_dict[ current_repository_key ] = repository_dependency
                key_rd_dicts_to_be_processed.append( new_key_rd_dict )
    return filtered_current_repository_key_rd_dicts, key_rd_dicts_to_be_processed, handled_key_rd_dicts, all_repository_dependencies

def prune_invalid_repository_dependencies( repository_dependencies ):
    """
    Eliminate all invalid entries in the received repository_dependencies dictionary.  An entry is invalid if if the value_list of the key/value pair is
    empty.  This occurs when an invalid combination of tool shed, name , owner, changeset_revision is used and a repository_metadata reocrd is not found.
    """
    valid_repository_dependencies = {}
    description = repository_dependencies.get( 'description', None )
    root_key = repository_dependencies.get( 'root_key', None )
    if root_key is None:
        return valid_repository_dependencies
    for key, value in repository_dependencies.items():
        if key in [ 'description', 'root_key' ]:
            continue
        if value:
            valid_repository_dependencies[ key ] = value
    if valid_repository_dependencies:
        valid_repository_dependencies[ 'description' ] = description
        valid_repository_dependencies[ 'root_key' ] = root_key
    return valid_repository_dependencies

def remove_from_key_rd_dicts( key_rd_dict, key_rd_dicts ):
    k = key_rd_dict.keys()[ 0 ]
    v = key_rd_dict[ k ]
    clean_key_rd_dicts = []
    for krd_dict in key_rd_dicts:
        key = krd_dict.keys()[ 0 ]
        val = krd_dict[ key ]
        if key == k and val == v:
            continue
        clean_key_rd_dicts.append( krd_dict )
    return clean_key_rd_dicts

def remove_ropository_dependency_reference_to_self( key_rd_dicts ):
    """Remove all repository dependencies that point to a revision within its own repository."""
    clean_key_rd_dicts = []
    key = key_rd_dicts[ 0 ].keys()[ 0 ]
    repository_tup = key.split( container_util.STRSEP )
    rd_toolshed, rd_name, rd_owner, rd_changeset_revision = repository_tup
    for key_rd_dict in key_rd_dicts:
        k = key_rd_dict.keys()[ 0 ]
        repository_dependency = key_rd_dict[ k ]
        toolshed, name, owner, changeset_revision = repository_dependency
        if rd_toolshed == toolshed and rd_name == name and rd_owner == owner:
            log.debug( "Removing repository dependency for repository %s owned by %s since it refers to a revision within itself." % ( name, owner ) )
        else:
            new_key_rd_dict = {}
            new_key_rd_dict[ key ] = repository_dependency
            clean_key_rd_dicts.append( new_key_rd_dict )
    return clean_key_rd_dicts

def repository_dependencies_have_tool_dependencies( trans, repository_dependencies ):
    rd_tups_processed = []
    for key, rd_tups in repository_dependencies.items():
        if key in [ 'root_key', 'description' ]:
            continue
        rd_tup = container_util.get_components_from_key( key )
        if rd_tup not in rd_tups_processed:
            toolshed, name, owner, changeset_revision = rd_tup
            repository = suc.get_repository_by_name_and_owner( trans.app, name, owner )
            repository_metadata = metadata_util.get_repository_metadata_by_repository_id_changeset_revision( trans,
                                                                                                             trans.security.encode_id( repository.id ),
                                                                                                             changeset_revision )
            if repository_metadata:
                metadata = repository_metadata.metadata
                if metadata:
                    if 'tool_dependencies' in metadata:
                        return True
            rd_tups_processed.append( rd_tup )
        for rd_tup in rd_tups:
            if rd_tup not in rd_tups_processed:
                toolshed, name, owner, changeset_revision = rd_tup
                repository = suc.get_repository_by_name_and_owner( trans.app, name, owner )
                repository_metadata = metadata_util.get_repository_metadata_by_repository_id_changeset_revision( trans,
                                                                                                                 trans.security.encode_id( repository.id ),
                                                                                                                 changeset_revision )
                if repository_metadata:
                    metadata = repository_metadata.metadata
                    if metadata:
                        if 'tool_dependencies' in metadata:
                            return True
                rd_tups_processed.append( rd_tup )
    return False

def get_repository_dependency_as_key( repository_dependency ):
    return container_util.generate_repository_dependencies_key_for_repository( repository_dependency[ 0 ],
                                                                               repository_dependency[ 1 ],
                                                                               repository_dependency[ 2 ],
                                                                               repository_dependency[ 3 ] )

def get_repository_dependency_by_repository_id( trans, decoded_repository_id ):
    return trans.sa_session.query( trans.model.RepositoryDependency ) \
                           .filter( trans.model.RepositoryDependency.table.c.tool_shed_repository_id == decoded_repository_id ) \
                           .first()

def update_circular_repository_dependencies( repository_key, repository_dependency, repository_dependencies, circular_repository_dependencies ):
    repository_dependency_as_key = get_repository_dependency_as_key( repository_dependency )
    repository_key_as_repository_dependency = repository_key.split( container_util.STRSEP )
    if repository_key_as_repository_dependency in repository_dependencies:
        found = False
        for tup in circular_repository_dependencies:
            if repository_dependency in tup and repository_key_as_repository_dependency in tup:
                # The circular dependency has already been included.
                found = True
        if not found:
            new_circular_tup = [ repository_dependency, repository_key_as_repository_dependency ]
            circular_repository_dependencies.append( new_circular_tup )
        return circular_repository_dependencies
