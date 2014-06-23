import json
import logging
import os

from galaxy.util import asbool
from galaxy.util import listify

import tool_shed.util.shed_util_common as suc
from tool_shed.util import common_util
from tool_shed.util import container_util
from tool_shed.util import encoding_util
from tool_shed.util import hg_util
from tool_shed.util import metadata_util
from tool_shed.util import tool_util

log = logging.getLogger( __name__ )

def can_add_to_key_rd_dicts( key_rd_dict, key_rd_dicts ):
    """Handle the case where an update to the changeset revision was done."""
    k = key_rd_dict.keys()[ 0 ]
    rd = key_rd_dict[ k ]
    partial_rd = rd[ 0:3 ]
    for kr_dict in key_rd_dicts:
        key = kr_dict.keys()[ 0 ]
        if key == k:
            repository_dependency = kr_dict[ key ]
            if repository_dependency[ 0:3 ] == partial_rd:
                return False
    return True

def generate_message_for_invalid_repository_dependencies( metadata_dict, error_from_tuple=False ):
    """Get or generate and return an error message associated with an invalid repository dependency."""
    message = ''
    if metadata_dict:
        if error_from_tuple:
            # Return the error messages associated with a set of one or more invalid repository dependency tuples.
            invalid_repository_dependencies_dict = metadata_dict.get( 'invalid_repository_dependencies', None )
            if invalid_repository_dependencies_dict is not None:
                invalid_repository_dependencies = invalid_repository_dependencies_dict.get( 'invalid_repository_dependencies', [] )
                for repository_dependency_tup in invalid_repository_dependencies:
                    toolshed, name, owner, changeset_revision, prior_installation_required, only_if_compiling_contained_td, error = \
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
                        if asbool( pir ):
                            pir_str = 'True'
                        else:
                            pir_str = ''
                        message += '<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % \
                            ( tool_shed, name, owner, changeset_revision, pir_str )
                    message += '</table>'
    return message

def get_key_for_repository_changeset_revision( app, toolshed_base_url, repository, repository_metadata, all_repository_dependencies ):
    # The received toolshed_base_url must include the port, but doesn't have to include the protocol.
    prior_installation_required, only_if_compiling_contained_td = \
        get_prior_installation_required_and_only_if_compiling_contained_td( app,
                                                                            toolshed_base_url,
                                                                            repository,
                                                                            repository_metadata,
                                                                            all_repository_dependencies )
    # Create a key with the value of prior_installation_required defaulted to False.
    key = container_util.generate_repository_dependencies_key_for_repository( toolshed_base_url=toolshed_base_url,
                                                                              repository_name=repository.name,
                                                                              repository_owner=repository.user.username,
                                                                              changeset_revision=repository_metadata.changeset_revision,
                                                                              prior_installation_required=prior_installation_required,
                                                                              only_if_compiling_contained_td=only_if_compiling_contained_td )
    return key

def get_prior_installation_required_and_only_if_compiling_contained_td( app, toolshed_base_url, repository, repository_metadata,
                                                                        all_repository_dependencies ):
    """
    This method is called from the tool shed and never Galaxy.  If all_repository_dependencies contains
    a repository dependency tuple that is associated with the received repository, return the value of
    the tuple's prior_installation_required component.
    """
    cleaned_toolshed_base_url = common_util.remove_protocol_from_tool_shed_url( toolshed_base_url )
    if all_repository_dependencies:
        for rd_key, rd_tups in all_repository_dependencies.items():
            if rd_key in [ 'root_key', 'description' ]:
                continue
            for rd_tup in rd_tups:
                rd_toolshed, rd_name, rd_owner, rd_changeset_revision, rd_prior_installation_required, rd_only_if_compiling_contained_td = \
                    common_util.parse_repository_dependency_tuple( rd_tup )
                cleaned_rd_toolshed = common_util.remove_protocol_from_tool_shed_url( rd_toolshed )
                if cleaned_rd_toolshed == cleaned_toolshed_base_url and \
                    rd_name == repository.name and \
                    rd_owner == repository.user.username and \
                    rd_changeset_revision == repository_metadata.changeset_revision:
                    return rd_prior_installation_required, rd_only_if_compiling_contained_td
    elif repository_metadata:
        # Get the list of changeset revisions from the tool shed to which the repository may be updated.
        metadata = repository_metadata.metadata
        current_changeset_revision = str( repository_metadata.changeset_revision )
        # Get the changeset revision to which the current value of required_repository_changeset_revision should be updated if it's not current.
        text = suc.get_updated_changeset_revisions( app,
                                                    name=str( repository.name ),
                                                    owner=str( repository.user.username ),
                                                    changeset_revision=current_changeset_revision )
        if text:
            valid_changeset_revisions = listify( text )
            if current_changeset_revision not in valid_changeset_revisions:
                valid_changeset_revisions.append( current_changeset_revision )
        else:
            valid_changeset_revisions = [ current_changeset_revision ]
        repository_dependencies_dict = metadata[ 'repository_dependencies' ]
        rd_tups = repository_dependencies_dict.get( 'repository_dependencies', [] )
        for rd_tup in rd_tups:
            rd_toolshed, rd_name, rd_owner, rd_changeset_revision, rd_prior_installation_required, rd_only_if_compiling_contained_td = \
                common_util.parse_repository_dependency_tuple( rd_tup )
            cleaned_rd_toolshed = common_util.remove_protocol_from_tool_shed_url( rd_toolshed )
            if cleaned_rd_toolshed == cleaned_toolshed_base_url and \
                rd_name == repository.name and \
                rd_owner == repository.user.username and \
                rd_changeset_revision in valid_changeset_revisions:
                return rd_prior_installation_required, rd_only_if_compiling_contained_td
    # Default both prior_installation_required and only_if_compiling_contained_td to False.
    return 'False', 'False'

def get_repository_dependency_as_key( repository_dependency ):
    tool_shed, name, owner, changeset_revision, prior_installation_required, only_if_compiling_contained_td = \
        common_util.parse_repository_dependency_tuple( repository_dependency )
    return container_util.generate_repository_dependencies_key_for_repository( tool_shed,
                                                                               name,
                                                                               owner,
                                                                               changeset_revision,
                                                                               prior_installation_required,
                                                                               only_if_compiling_contained_td )

def get_repository_dependencies_for_changeset_revision( app, repository, repository_metadata, toolshed_base_url,
                                                        key_rd_dicts_to_be_processed=None, all_repository_dependencies=None,
                                                        handled_key_rd_dicts=None, circular_repository_dependencies=None ):
    """
    Return a dictionary of all repositories upon which the contents of the received
    repository_metadata record depend.  The dictionary keys are name-spaced values
    consisting of:
    toolshed_base_url/repository_name/repository_owner/changeset_revision
    and the values are lists of repository_dependency tuples consisting of:
    ( toolshed_base_url, repository_name, repository_owner, changeset_revision ).
    This method ensures that all required repositories to the nth degree are returned.
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
        # The value of the received toolshed_base_url must include the port, but doesn't have
        # to include the protocol.
        if 'repository_dependencies' in metadata:
            current_repository_key = get_key_for_repository_changeset_revision( app,
                                                                                toolshed_base_url,
                                                                                repository,
                                                                                repository_metadata,
                                                                                all_repository_dependencies )
            repository_dependencies_dict = metadata[ 'repository_dependencies' ]
            if not all_repository_dependencies:
                all_repository_dependencies = initialize_all_repository_dependencies( current_repository_key,
                                                                                      repository_dependencies_dict,
                                                                                      all_repository_dependencies )
            # Handle the repository dependencies defined in the current repository, if any, and populate
            # the various repository dependency objects for this round of processing.
            current_repository_key_rd_dicts, key_rd_dicts_to_be_processed, handled_key_rd_dicts, all_repository_dependencies = \
                populate_repository_dependency_objects_for_processing( app,
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
            if not in_circular_repository_dependencies( current_repository_key_rd_dict,
                                                        circular_repository_dependencies ):
                if current_repository_key in all_repository_dependencies:
                    handle_current_repository_dependency( app,
                                                          current_repository_key,
                                                          key_rd_dicts_to_be_processed,
                                                          all_repository_dependencies,
                                                          handled_key_rd_dicts,
                                                          circular_repository_dependencies )
            elif key_rd_dicts_to_be_processed:
                handle_next_repository_dependency( app,
                                                   key_rd_dicts_to_be_processed,
                                                   all_repository_dependencies,
                                                   handled_key_rd_dicts,
                                                   circular_repository_dependencies )
        elif key_rd_dicts_to_be_processed:
            handle_next_repository_dependency( app,
                                               key_rd_dicts_to_be_processed,
                                               all_repository_dependencies,
                                               handled_key_rd_dicts,
                                               circular_repository_dependencies )
    elif key_rd_dicts_to_be_processed:
        handle_next_repository_dependency( app,
                                           key_rd_dicts_to_be_processed,
                                           all_repository_dependencies,
                                           handled_key_rd_dicts,
                                           circular_repository_dependencies )
    all_repository_dependencies = prune_invalid_repository_dependencies( all_repository_dependencies )
    return all_repository_dependencies

def get_repository_dependency_tups_from_repository_metadata( app, repository_metadata, deprecated_only=False ):
    """
    Return a list of of tuples defining repository objects required by the received repository.  The returned
    list defines the entire repository dependency tree.  This method is called only from the Tool Shed.
    """
    dependency_tups = []
    if repository_metadata is not None:
        metadata = repository_metadata.metadata
        if metadata:
            repository_dependencies_dict = metadata.get( 'repository_dependencies', None )
            if repository_dependencies_dict is not None:
                repository_dependency_tups = repository_dependencies_dict.get( 'repository_dependencies', None )
                if repository_dependency_tups is not None:
                    # The value of repository_dependency_tups is a list of repository dependency tuples like this:
                    # ['http://localhost:9009', 'package_samtools_0_1_18', 'devteam', 'ef37fc635cb9', 'False', 'False']
                    for repository_dependency_tup in repository_dependency_tups:
                        toolshed, name, owner, changeset_revision, pir, oicct = \
                        common_util.parse_repository_dependency_tuple( repository_dependency_tup )
                        repository = suc.get_repository_by_name_and_owner( app, name, owner )
                        if repository:
                            if deprecated_only:
                                if repository.deprecated:
                                    dependency_tups.append( repository_dependency_tup )
                            else:
                                dependency_tups.append( repository_dependency_tup )
                        else:
                            log.debug( "Cannot locate repository %s owned by %s for inclusion in repository dependency tups." % \
                                ( name, owner ) )
    return dependency_tups
    
def get_updated_changeset_revisions_for_repository_dependencies( app, key_rd_dicts ):
    updated_key_rd_dicts = []
    for key_rd_dict in key_rd_dicts:
        key = key_rd_dict.keys()[ 0 ]
        repository_dependency = key_rd_dict[ key ]
        rd_toolshed, rd_name, rd_owner, rd_changeset_revision, rd_prior_installation_required, rd_only_if_compiling_contained_td = \
            common_util.parse_repository_dependency_tuple( repository_dependency )
        if suc.tool_shed_is_this_tool_shed( rd_toolshed ):
            repository = suc.get_repository_by_name_and_owner( app, rd_name, rd_owner )
            if repository:
                repository_metadata = \
                    metadata_util.get_repository_metadata_by_repository_id_changeset_revision( app,
                                                                                               app.security.encode_id( repository.id ),
                                                                                               rd_changeset_revision )
                if repository_metadata:
                    # The repository changeset_revision is installable, so no updates are available.
                    new_key_rd_dict = {}
                    new_key_rd_dict[ key ] = repository_dependency
                    updated_key_rd_dicts.append( key_rd_dict )
                else:
                    # The repository changeset_revision is no longer installable, so see if there's been an update.
                    repo = hg_util.get_repo_for_repository( app, repository=repository, repo_path=None, create=False )
                    changeset_revision = suc.get_next_downloadable_changeset_revision( repository, repo, rd_changeset_revision )
                    repository_metadata = \
                        metadata_util.get_repository_metadata_by_repository_id_changeset_revision( app,
                                                                                                   app.security.encode_id( repository.id ),
                                                                                                   changeset_revision )
                    if repository_metadata:
                        new_key_rd_dict = {}
                        new_key_rd_dict[ key ] = \
                            [ rd_toolshed, rd_name, rd_owner, repository_metadata.changeset_revision, rd_prior_installation_required, rd_only_if_compiling_contained_td ]
                        # We have the updated changset revision.
                        updated_key_rd_dicts.append( new_key_rd_dict )
                    else:
                        repository_components_tuple = container_util.get_components_from_key( key )
                        components_list = suc.extract_components_from_tuple( repository_components_tuple )
                        toolshed, repository_name, repository_owner, repository_changeset_revision = components_list[ 0:4 ]
                        # For backward compatibility to the 12/20/12 Galaxy release.
                        if len( components_list ) == 4:
                            prior_installation_required = 'False'
                            rd_only_if_compiling_contained_td = 'False'
                        elif len( components_list ) == 5:
                            rd_only_if_compiling_contained_td = 'False'
                        message = "The revision %s defined for repository %s owned by %s is invalid, so repository dependencies defined for repository %s will be ignored." % \
                            ( str( rd_changeset_revision ), str( rd_name ), str( rd_owner ), str( repository_name ) )
                        log.debug( message )
            else:
                repository_components_tuple = container_util.get_components_from_key( key )
                components_list = suc.extract_components_from_tuple( repository_components_tuple )
                toolshed, repository_name, repository_owner, repository_changeset_revision = components_list[ 0:4 ]
                message = "The revision %s defined for repository %s owned by %s is invalid, so repository dependencies defined for repository %s will be ignored." % \
                    ( str( rd_changeset_revision ), str( rd_name ), str( rd_owner ), str( repository_name ) )
                log.debug( message )
    return updated_key_rd_dicts

def handle_circular_repository_dependency( repository_key, repository_dependency, circular_repository_dependencies,
                                           handled_key_rd_dicts, all_repository_dependencies ):
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

def handle_current_repository_dependency( app, current_repository_key, key_rd_dicts_to_be_processed, all_repository_dependencies, handled_key_rd_dicts,
                                          circular_repository_dependencies ):
    current_repository_key_rd_dicts = []
    for rd in all_repository_dependencies[ current_repository_key ]:
        rd_copy = [ str( item ) for item in rd ]
        new_key_rd_dict = {}
        new_key_rd_dict[ current_repository_key ] = rd_copy
        current_repository_key_rd_dicts.append( new_key_rd_dict )
    if current_repository_key_rd_dicts:
        toolshed, required_repository, required_repository_metadata, repository_key_rd_dicts, key_rd_dicts_to_be_processed, handled_key_rd_dicts = \
            handle_key_rd_dicts_for_repository( app,
                                                current_repository_key,
                                                current_repository_key_rd_dicts,
                                                key_rd_dicts_to_be_processed,
                                                handled_key_rd_dicts,
                                                circular_repository_dependencies )
        return get_repository_dependencies_for_changeset_revision( app=app,
                                                                   repository=required_repository,
                                                                   repository_metadata=required_repository_metadata,
                                                                   toolshed_base_url=toolshed,
                                                                   key_rd_dicts_to_be_processed=key_rd_dicts_to_be_processed,
                                                                   all_repository_dependencies=all_repository_dependencies,
                                                                   handled_key_rd_dicts=handled_key_rd_dicts,
                                                                   circular_repository_dependencies=circular_repository_dependencies )

def handle_key_rd_dicts_for_repository( app, current_repository_key, repository_key_rd_dicts, key_rd_dicts_to_be_processed, handled_key_rd_dicts, circular_repository_dependencies ):
    key_rd_dict = repository_key_rd_dicts.pop( 0 )
    repository_dependency = key_rd_dict[ current_repository_key ]
    toolshed, name, owner, changeset_revision, prior_installation_required, only_if_compiling_contained_td = \
        common_util.parse_repository_dependency_tuple( repository_dependency )
    if suc.tool_shed_is_this_tool_shed( toolshed ):
        required_repository = suc.get_repository_by_name_and_owner( app, name, owner )
        required_repository_metadata = \
            metadata_util.get_repository_metadata_by_repository_id_changeset_revision( app,
                                                                                       app.security.encode_id( required_repository.id ),
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
        error_message = "Repository dependencies are currently supported only within the same Tool Shed.  Ignoring repository dependency definition "
        error_message += "for tool shed %s, name %s, owner %s, changeset revision %s" % ( toolshed, name, owner, changeset_revision )
        log.debug( error_message )
    return toolshed, required_repository, required_repository_metadata, repository_key_rd_dicts, key_rd_dicts_to_be_processed, handled_key_rd_dicts

def handle_next_repository_dependency( app, key_rd_dicts_to_be_processed, all_repository_dependencies, handled_key_rd_dicts,
                                       circular_repository_dependencies ):
    next_repository_key_rd_dict = key_rd_dicts_to_be_processed.pop( 0 )
    next_repository_key_rd_dicts = [ next_repository_key_rd_dict ]
    next_repository_key = next_repository_key_rd_dict.keys()[ 0 ]
    toolshed, required_repository, required_repository_metadata, repository_key_rd_dicts, key_rd_dicts_to_be_processed, handled_key_rd_dicts = \
        handle_key_rd_dicts_for_repository( app,
                                            next_repository_key,
                                            next_repository_key_rd_dicts,
                                            key_rd_dicts_to_be_processed,
                                            handled_key_rd_dicts,
                                            circular_repository_dependencies )
    return get_repository_dependencies_for_changeset_revision( app=app,
                                                               repository=required_repository,
                                                               repository_metadata=required_repository_metadata,
                                                               toolshed_base_url=toolshed,
                                                               key_rd_dicts_to_be_processed=key_rd_dicts_to_be_processed,
                                                               all_repository_dependencies=all_repository_dependencies,
                                                               handled_key_rd_dicts=handled_key_rd_dicts,
                                                               circular_repository_dependencies=circular_repository_dependencies )

def in_all_repository_dependencies( repository_key, repository_dependency, all_repository_dependencies ):
    """Return True if { repository_key : repository_dependency } is in all_repository_dependencies."""
    for key, val in all_repository_dependencies.items():
        if key != repository_key:
            continue
        if repository_dependency in val:
            return True
    return False

def in_circular_repository_dependencies( repository_key_rd_dict, circular_repository_dependencies ):
    """
    Return True if any combination of a circular dependency tuple is the key : value pair defined
    in the received repository_key_rd_dict.  This means that each circular dependency tuple is converted
    into the key : value pair for comparison.
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
    """Initialize the all_repository_dependencies dictionary."""
    # It's safe to assume that current_repository_key in this case will have a value.
    all_repository_dependencies[ 'root_key' ] = current_repository_key
    all_repository_dependencies[ current_repository_key ] = []
    # Store the value of the 'description' key only once, the first time through this recursive method.
    description = repository_dependencies_dict.get( 'description', None )
    all_repository_dependencies[ 'description' ] = description
    return all_repository_dependencies

def in_key_rd_dicts( key_rd_dict, key_rd_dicts ):
    """Return True if key_rd_dict is contained in the list of key_rd_dicts."""
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

def filter_only_if_compiling_contained_td( key_rd_dict ):
    """
    Return a copy of the received key_rd_dict with repository dependencies that are needed
    only_if_compiling_contained_td filtered out of the list of repository dependencies for
    each rd_key.
    """
    filtered_key_rd_dict = {}
    for rd_key, required_rd_tup in key_rd_dict.items():
        tool_shed, name, owner, changeset_revision, prior_installation_required, only_if_compiling_contained_td = \
            common_util.parse_repository_dependency_tuple( required_rd_tup )
        if not asbool( only_if_compiling_contained_td ):
            filtered_key_rd_dict[ rd_key ] = required_rd_tup
    return filtered_key_rd_dict

def populate_repository_dependency_objects_for_processing( app, current_repository_key, repository_dependencies_dict,
                                                           key_rd_dicts_to_be_processed, handled_key_rd_dicts,
                                                           circular_repository_dependencies, all_repository_dependencies ):
    """
    The process that discovers all repository dependencies for a specified repository's
    changeset revision uses this method to populate the following items for the current
    processing loop: filtered_current_repository_key_rd_dicts, key_rd_dicts_to_be_processed,
    handled_key_rd_dicts, all_repository_dependencies.  Each processing loop may discover
    more repository dependencies, so this method is repeatedly called until all repository
    dependencies have been discovered.
    """
    current_repository_key_rd_dicts = []
    filtered_current_repository_key_rd_dicts = []
    for rd_tup in repository_dependencies_dict[ 'repository_dependencies' ]:
        new_key_rd_dict = {}
        new_key_rd_dict[ current_repository_key ] = rd_tup
        current_repository_key_rd_dicts.append( new_key_rd_dict )
    if current_repository_key_rd_dicts and current_repository_key:
        # Remove all repository dependencies that point to a revision within its own repository.
        current_repository_key_rd_dicts = remove_ropository_dependency_reference_to_self( current_repository_key_rd_dicts )
    current_repository_key_rd_dicts = \
        get_updated_changeset_revisions_for_repository_dependencies( app, current_repository_key_rd_dicts )
    for key_rd_dict in current_repository_key_rd_dicts:
        # Filter out repository dependencies that are required only if compiling the dependent repository's tool dependency.
        key_rd_dict = filter_only_if_compiling_contained_td( key_rd_dict )
        if key_rd_dict:
            is_circular = False
            if not in_key_rd_dicts( key_rd_dict, handled_key_rd_dicts ) and not in_key_rd_dicts( key_rd_dict,
                                                                                                 key_rd_dicts_to_be_processed ):
                filtered_current_repository_key_rd_dicts.append( key_rd_dict )
                repository_dependency = key_rd_dict[ current_repository_key ]
                if current_repository_key in all_repository_dependencies:
                    # Add all repository dependencies for the current repository into its entry in all_repository_dependencies.
                    all_repository_dependencies_val = all_repository_dependencies[ current_repository_key ]
                    if repository_dependency not in all_repository_dependencies_val:
                        all_repository_dependencies_val.append( repository_dependency )
                        all_repository_dependencies[ current_repository_key ] = all_repository_dependencies_val
                elif not in_all_repository_dependencies( current_repository_key, repository_dependency, all_repository_dependencies ):
                    # Handle circular repository dependencies.
                    if is_circular_repository_dependency( current_repository_key,
                                                          repository_dependency,
                                                          all_repository_dependencies ):
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
    Eliminate all invalid entries in the received repository_dependencies dictionary.  An entry
    is invalid if the value_list of the key/value pair is empty.  This occurs when an invalid
    combination of tool shed, name , owner, changeset_revision is used and a repository_metadata
    record is not found.
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
    """Eliminate the key_rd_dict from the list of key_rd_dicts if it is contained in the list."""
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
    rd_toolshed, rd_name, rd_owner, rd_changeset_revision, rd_prior_installation_required, rd_only_if_compiling_contained_td = \
        common_util.parse_repository_dependency_tuple( repository_tup )
    cleaned_rd_toolshed = common_util.remove_protocol_from_tool_shed_url( rd_toolshed )
    for key_rd_dict in key_rd_dicts:
        k = key_rd_dict.keys()[ 0 ]
        repository_dependency = key_rd_dict[ k ]
        toolshed, name, owner, changeset_revision, prior_installation_required, only_if_compiling_contained_td = \
            common_util.parse_repository_dependency_tuple( repository_dependency )
        cleaned_toolshed = common_util.remove_protocol_from_tool_shed_url( toolshed )
        if cleaned_rd_toolshed == cleaned_toolshed and rd_name == name and rd_owner == owner:
            debug_msg = "Removing repository dependency for repository %s owned by %s " % ( name, owner )
            debug_msg += 'since it refers to a revision within itself.'
            log.debug( debug_msg )
        else:
            new_key_rd_dict = {}
            new_key_rd_dict[ key ] = repository_dependency
            clean_key_rd_dicts.append( new_key_rd_dict )
    return clean_key_rd_dicts

def update_circular_repository_dependencies( repository_key, repository_dependency, repository_dependencies,
                                             circular_repository_dependencies ):
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
