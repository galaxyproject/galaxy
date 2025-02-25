import logging
from operator import itemgetter
from typing import (
    Optional,
    TYPE_CHECKING,
)

from sqlalchemy import select

from galaxy.tool_shed.util.hg_util import (
    INITIAL_CHANGELOG_HASH,
    reversed_lower_upper_bounded_changelog,
)
from galaxy.util.tool_shed.common_util import parse_repository_dependency_tuple
from tool_shed.util.hg_util import changeset2rev
from tool_shed.webapp.model.db import get_repository_by_name_and_owner

if TYPE_CHECKING:
    from tool_shed.structured_app import ToolShedApp
    from tool_shed.webapp.model import RepositoryMetadata
    from tool_shed.webapp.model.mapping import ToolShedModelMapping


log = logging.getLogger(__name__)


def get_all_dependencies(app: "ToolShedApp", metadata_entry, processed_dependency_links=None):
    processed_dependency_links = processed_dependency_links or []
    encoder = app.security.encode_id
    value_mapper = {"repository_id": encoder, "id": encoder, "user_id": encoder}
    metadata = metadata_entry.to_dict(value_mapper=value_mapper, view="element")
    returned_dependencies = []
    required_metadata = get_dependencies_for_metadata_revision(app, metadata)
    if required_metadata is None:
        return metadata
    for dependency_metadata in required_metadata:
        dependency_dict = dependency_metadata.to_dict(value_mapper=value_mapper, view="element")
        dependency_link = (metadata["id"], dependency_dict["id"])
        if dependency_link in processed_dependency_links:
            continue
        processed_dependency_links.append(dependency_link)
        repository = app.model.session.get(
            app.model.Repository, app.security.decode_id(dependency_dict["repository_id"])
        )
        assert repository
        dependency_dict["repository"] = repository.to_dict(value_mapper=value_mapper)
        if dependency_metadata.includes_tools:
            dependency_dict["tools"] = dependency_metadata.metadata["tools"]
        dependency_dict["invalid_tools"] = dependency_metadata.metadata.get("invalid_tools", [])
        dependency_dict["repository_dependencies"] = []
        if dependency_dict["includes_tool_dependencies"]:
            dependency_dict["tool_dependencies"] = repository.get_tool_dependencies(
                app, dependency_dict["changeset_revision"]
            )
        if dependency_dict["has_repository_dependencies"]:
            dependency_dict["repository_dependencies"] = get_all_dependencies(
                app, dependency_metadata, processed_dependency_links
            )
        else:
            dependency_dict["repository_dependencies"] = []
        returned_dependencies.append(dependency_dict)
    return returned_dependencies


def get_current_repository_metadata_for_changeset_revision(app, repository, changeset_revision):
    encoded_repository_id = app.security.encode_id(repository.id)
    repository_metadata = get_repository_metadata_by_changeset_revision(app, encoded_repository_id, changeset_revision)
    if repository_metadata:
        return repository_metadata
    # The installable changeset_revision may have been changed because it was "moved ahead"
    # in the repository changelog.
    updated_changeset_revision = get_next_downloadable_changeset_revision(
        app, repository, after_changeset_revision=changeset_revision
    )
    if updated_changeset_revision and updated_changeset_revision != changeset_revision:
        repository_metadata = get_repository_metadata_by_changeset_revision(
            app, encoded_repository_id, updated_changeset_revision
        )
        if repository_metadata:
            return repository_metadata
    return None


def get_dependencies_for_metadata_revision(app: "ToolShedApp", metadata):
    dependencies = []
    for _shed, name, owner, changeset, _prior, _ in metadata["repository_dependencies"]:
        required_repository = get_repository_by_name_and_owner(app.model.context, name, owner)
        updated_changeset = get_next_downloadable_changeset_revision(app, required_repository, changeset)
        if updated_changeset is None:
            continue
        metadata_entry = get_repository_metadata_by_changeset_revision(
            app, app.security.encode_id(required_repository.id), updated_changeset
        )
        dependencies.append(metadata_entry)
    return dependencies


def get_latest_changeset_revision(app, repository):
    repository_tip = repository.tip()
    repository_metadata = get_repository_metadata_by_changeset_revision(
        app, app.security.encode_id(repository.id), repository_tip
    )
    if repository_metadata and repository_metadata.downloadable:
        return repository_tip
    changeset_revisions = [revision[1] for revision in get_metadata_revisions(app, repository)]
    if changeset_revisions:
        return changeset_revisions[-1]
    return INITIAL_CHANGELOG_HASH


def get_latest_downloadable_changeset_revision(app, repository):
    repository_tip = repository.tip()
    repository_metadata = get_repository_metadata_by_changeset_revision(
        app, app.security.encode_id(repository.id), repository_tip
    )
    if repository_metadata and repository_metadata.downloadable:
        return repository_tip
    changeset_revisions = [revision[1] for revision in get_metadata_revisions(app, repository)]
    if changeset_revisions:
        return changeset_revisions[-1]
    return INITIAL_CHANGELOG_HASH


def get_latest_repository_metadata(app, decoded_repository_id, downloadable=False):
    """Get last metadata defined for a specified repository from the database."""
    sa_session = app.model.session
    repository = sa_session.get(app.model.Repository, decoded_repository_id)
    if downloadable:
        changeset_revision = get_latest_downloadable_changeset_revision(app, repository)
    else:
        changeset_revision = get_latest_changeset_revision(app, repository)
    return get_repository_metadata_by_changeset_revision(app, app.security.encode_id(repository.id), changeset_revision)


def get_metadata_revisions(app, repository, sort_revisions=True, reverse=False, downloadable=True):
    """
    Return a list of changesets for the provided repository.
    """
    sa_session = app.model.session
    if downloadable:
        metadata_revisions = repository.downloadable_revisions
    else:
        metadata_revisions = repository.metadata_revisions
    repo_path = repository.repo_path(app)
    changeset_tups = []
    for repository_metadata in metadata_revisions:
        if repository_metadata.numeric_revision == -1 or repository_metadata.numeric_revision is None:
            try:
                rev = changeset2rev(repo_path, repository_metadata.changeset_revision)
                repository_metadata.numeric_revision = rev
                sa_session.add(repository_metadata)
                session = sa_session()
                session.commit()
            except Exception:
                rev = -1
        else:
            rev = repository_metadata.numeric_revision
        changeset_tups.append((rev, repository_metadata.changeset_revision))
    if sort_revisions:
        changeset_tups.sort(key=itemgetter(0), reverse=reverse)
    return changeset_tups


def get_next_downloadable_changeset_revision(app, repository, after_changeset_revision):
    """
    Return the installable changeset_revision in the repository changelog after the changeset to which
    after_changeset_revision refers.  If there isn't one, return None. If there is only one installable
    changeset, and that matches the requested revision, return it.
    """
    changeset_revisions = [revision[1] for revision in get_metadata_revisions(app, repository)]
    if len(changeset_revisions) == 1:
        changeset_revision = changeset_revisions[0]
        if changeset_revision == after_changeset_revision:
            return after_changeset_revision
    found_after_changeset_revision = False
    repo = repository.hg_repo
    for changeset in repo.changelog:
        changeset_revision = str(repo[changeset])
        if found_after_changeset_revision:
            if changeset_revision in changeset_revisions:
                return changeset_revision
        elif changeset_revision == after_changeset_revision:
            # We've found the changeset in the changelog for which we need to get the next downloadable changeset.
            found_after_changeset_revision = True
    return None


def get_previous_metadata_changeset_revision(app, repository, before_changeset_revision, downloadable=True):
    """
    Return the changeset_revision in the repository changelog that has associated metadata prior to
    the changeset to which before_changeset_revision refers.  If there isn't one, return the hash value
    of an empty repository changelog, INITIAL_CHANGELOG_HASH.
    """
    changeset_revisions = [revision[1] for revision in get_metadata_revisions(app, repository)]
    if len(changeset_revisions) == 1:
        changeset_revision = changeset_revisions[0]
        if changeset_revision == before_changeset_revision:
            return INITIAL_CHANGELOG_HASH
        return changeset_revision
    previous_changeset_revision = None
    for changeset_revision in changeset_revisions:
        if changeset_revision == before_changeset_revision:
            if previous_changeset_revision:
                return previous_changeset_revision
            else:
                # Return the hash value of an empty repository changelog - note that this will not be a valid changeset revision.
                return INITIAL_CHANGELOG_HASH
        else:
            previous_changeset_revision = changeset_revision


def get_repository_dependency_tups_from_repository_metadata(
    app: "ToolShedApp", repository_metadata, deprecated_only=False
):
    """
    Return a list of of tuples defining repository objects required by the received repository.  The returned
    list defines the entire repository dependency tree.  This method is called only from the Tool Shed.
    """
    dependency_tups = []
    if repository_metadata is not None:
        metadata = repository_metadata.metadata
        if metadata:
            repository_dependencies_dict = metadata.get("repository_dependencies", None)
            if repository_dependencies_dict is not None:
                repository_dependency_tups = repository_dependencies_dict.get("repository_dependencies", None)
                if repository_dependency_tups is not None:
                    # The value of repository_dependency_tups is a list of repository dependency tuples like this:
                    # ['http://localhost:9009', 'package_samtools_0_1_18', 'devteam', 'ef37fc635cb9', 'False', 'False']
                    for repository_dependency_tup in repository_dependency_tups:
                        toolshed, name, owner, changeset_revision, pir, oicct = parse_repository_dependency_tuple(
                            repository_dependency_tup
                        )
                        repository = get_repository_by_name_and_owner(app.model.context, name, owner)
                        if repository:
                            if deprecated_only:
                                if repository.deprecated:
                                    dependency_tups.append(repository_dependency_tup)
                            else:
                                dependency_tups.append(repository_dependency_tup)
                        else:
                            log.debug(
                                "Cannot locate repository %s owned by %s for inclusion in repository dependency tups.",
                                name,
                                owner,
                            )
    return dependency_tups


def get_repository_metadata_by_changeset_revision(
    app: "ToolShedApp", id: str, changeset_revision: str
) -> Optional["RepositoryMetadata"]:
    """Get metadata for a specified repository change set from the database."""
    decoded_id = app.security.decode_id(id)
    return repository_metadata_by_changeset_revision(app.model, decoded_id, changeset_revision)


def repository_metadata_by_changeset_revision(
    model_mapping: "ToolShedModelMapping", id: int, changeset_revision: str
) -> Optional["RepositoryMetadata"]:
    # Make sure there are no duplicate records, and return the single unique record for the changeset_revision.
    # Duplicate records were somehow created in the past.  The cause of this issue has been resolved, but we'll
    # leave this method as is for a while longer to ensure all duplicate records are removed.

    sa_session = model_mapping.context
    all_metadata_records = get_metadata_by_changeset(
        sa_session, id, changeset_revision, model_mapping.RepositoryMetadata
    )
    if len(all_metadata_records) > 1:
        # Delete all records older than the last one updated.
        for repository_metadata in all_metadata_records[1:]:
            sa_session.delete(repository_metadata)
            session = sa_session()
            session.commit()
        return all_metadata_records[0]
    elif all_metadata_records:
        return all_metadata_records[0]
    return None


def get_repository_metadata_by_id(app, id):
    """Get repository metadata from the database"""
    sa_session = app.model.session
    return sa_session.get(app.model.RepositoryMetadata, app.security.decode_id(id))


def get_repository_metadata_by_repository_id_changeset_revision(app, id, changeset_revision, metadata_only=False):
    """Get a specified metadata record for a specified repository in the tool shed."""
    if metadata_only:
        repository_metadata = get_repository_metadata_by_changeset_revision(app, id, changeset_revision)
        if repository_metadata and repository_metadata.metadata:
            return repository_metadata.metadata
        return None
    return get_repository_metadata_by_changeset_revision(app, id, changeset_revision)


def get_updated_changeset_revisions(app: "ToolShedApp", name, owner, changeset_revision):
    """
    Return a string of comma-separated changeset revision hashes for all available updates to the received changeset
    revision for the repository defined by the received name and owner.
    """
    repository = get_repository_by_name_and_owner(app.model.context, name, owner)
    # Get the upper bound changeset revision.
    upper_bound_changeset_revision = get_next_downloadable_changeset_revision(app, repository, changeset_revision)
    # Build the list of changeset revision hashes defining each available update up to, but excluding
    # upper_bound_changeset_revision.
    repo = repository.hg_repo
    changeset_hashes = []
    for changeset in reversed_lower_upper_bounded_changelog(repo, changeset_revision, upper_bound_changeset_revision):
        # Make sure to exclude upper_bound_changeset_revision.
        if changeset != upper_bound_changeset_revision:
            changeset_hashes.append(str(repo[changeset]))
    if changeset_hashes:
        changeset_hashes_str = ",".join(changeset_hashes)
        return changeset_hashes_str
    return ""


def is_downloadable(metadata_dict):
    # NOTE: although repository README files are considered Galaxy utilities, they have no
    # effect on determining if a revision is installable.  See the comments in the
    # compare_readme_files() method.
    if "datatypes" in metadata_dict:
        # We have proprietary datatypes.
        return True
    if "repository_dependencies" in metadata_dict:
        # We have repository_dependencies.
        return True
    if "tools" in metadata_dict:
        # We have tools.
        return True
    if "tool_dependencies" in metadata_dict:
        # We have tool dependencies, and perhaps only tool dependencies!
        return True
    if "workflows" in metadata_dict:
        # We have exported workflows.
        return True
    return False


def is_malicious(app, id, changeset_revision, **kwd):
    """Check the malicious flag in repository metadata for a specified change set revision."""
    repository_metadata = get_repository_metadata_by_changeset_revision(app, id, changeset_revision)
    if repository_metadata:
        return repository_metadata.malicious
    return False


def get_metadata_by_changeset(session, repository_id, changeset_revision, repository_metadata_model):
    stmt = (
        select(repository_metadata_model)
        .where(repository_metadata_model.repository_id == repository_id)
        .where(repository_metadata_model.changeset_revision == changeset_revision)
    )
    return session.scalars(stmt).all()
