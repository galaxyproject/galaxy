import logging
import os

from tool_shed.util import common_util
from tool_shed.util import hg_util
from tool_shed.util import shed_util_common as suc

log = logging.getLogger( __name__ )

def get_latest_changeset_revision( app, repository, repo ):
    repository_tip = repository.tip( app )
    repository_metadata = suc.get_repository_metadata_by_changeset_revision( app,
                                                                             app.security.encode_id( repository.id ),
                                                                             repository_tip )
    if repository_metadata and repository_metadata.downloadable:
        return repository_tip
    changeset_revisions = suc.get_ordered_metadata_changeset_revisions( repository, repo, downloadable=False )
    if changeset_revisions:
        return changeset_revisions[ -1 ]
    return hg_util.INITIAL_CHANGELOG_HASH

def get_latest_repository_metadata( app, decoded_repository_id, downloadable=False ):
    """Get last metadata defined for a specified repository from the database."""
    sa_session = app.model.context.current
    repository = sa_session.query( app.model.Repository ).get( decoded_repository_id )
    repo = hg_util.get_repo_for_repository( app, repository=repository, repo_path=None, create=False )
    if downloadable:
        changeset_revision = suc.get_latest_downloadable_changeset_revision( app, repository, repo )
    else:
        changeset_revision = get_latest_changeset_revision( app, repository, repo )
    return suc.get_repository_metadata_by_changeset_revision( app,
                                                              app.security.encode_id( repository.id ),
                                                              changeset_revision )

def get_previous_metadata_changeset_revision( repository, repo, before_changeset_revision, downloadable=True ):
    """
    Return the changeset_revision in the repository changelog that has associated metadata prior to
    the changeset to which before_changeset_revision refers.  If there isn't one, return the hash value
    of an empty repository changelog, hg_util.INITIAL_CHANGELOG_HASH.
    """
    changeset_revisions = suc.get_ordered_metadata_changeset_revisions( repository, repo, downloadable=downloadable )
    if len( changeset_revisions ) == 1:
        changeset_revision = changeset_revisions[ 0 ]
        if changeset_revision == before_changeset_revision:
            return hg_util.INITIAL_CHANGELOG_HASH
        return changeset_revision
    previous_changeset_revision = None
    for changeset_revision in changeset_revisions:
        if changeset_revision == before_changeset_revision:
            if previous_changeset_revision:
                return previous_changeset_revision
            else:
                # Return the hash value of an empty repository changelog - note that this will not be a valid changeset revision.
                return hg_util.INITIAL_CHANGELOG_HASH
        else:
            previous_changeset_revision = changeset_revision

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

def get_repository_metadata_by_id( app, id ):
    """Get repository metadata from the database"""
    sa_session = app.model.context.current
    return sa_session.query( app.model.RepositoryMetadata ).get( app.security.decode_id( id ) )

def get_repository_metadata_by_repository_id_changeset_revision( app, id, changeset_revision, metadata_only=False ):
    """Get a specified metadata record for a specified repository in the tool shed."""
    if metadata_only:
        repository_metadata = suc.get_repository_metadata_by_changeset_revision( app, id, changeset_revision )
        if repository_metadata and repository_metadata.metadata:
            return repository_metadata.metadata
        return None
    return suc.get_repository_metadata_by_changeset_revision( app, id, changeset_revision )
    
def get_repository_metadata_revisions_for_review( repository, reviewed=True ):
    repository_metadata_revisions = []
    metadata_changeset_revision_hashes = []
    if reviewed:
        for metadata_revision in repository.metadata_revisions:
            metadata_changeset_revision_hashes.append( metadata_revision.changeset_revision )
        for review in repository.reviews:
            if review.changeset_revision in metadata_changeset_revision_hashes:
                rmcr_hashes = [ rmr.changeset_revision for rmr in repository_metadata_revisions ]
                if review.changeset_revision not in rmcr_hashes:
                    repository_metadata_revisions.append( review.repository_metadata )
    else:
        for review in repository.reviews:
            if review.changeset_revision not in metadata_changeset_revision_hashes:
                metadata_changeset_revision_hashes.append( review.changeset_revision )
        for metadata_revision in repository.metadata_revisions:
            if metadata_revision.changeset_revision not in metadata_changeset_revision_hashes:
                repository_metadata_revisions.append( metadata_revision )
    return repository_metadata_revisions

def is_downloadable( metadata_dict ):
    # NOTE: although repository README files are considered Galaxy utilities, they have no
    # effect on determining if a revision is installable.  See the comments in the
    # compare_readme_files() method.
    if 'datatypes' in metadata_dict:
        # We have proprietary datatypes.
        return True
    if 'repository_dependencies' in metadata_dict:
        # We have repository_dependencies.
        return True
    if 'tools' in metadata_dict:
        # We have tools.
        return True
    if 'tool_dependencies' in metadata_dict:
        # We have tool dependencies, and perhaps only tool dependencies!
        return True
    if 'workflows' in metadata_dict:
        # We have exported workflows.
        return True
    return False

def is_malicious( app, id, changeset_revision, **kwd ):
    """Check the malicious flag in repository metadata for a specified change set revision."""
    repository_metadata = suc.get_repository_metadata_by_changeset_revision( app, id, changeset_revision )
    if repository_metadata:
        return repository_metadata.malicious
    return False
