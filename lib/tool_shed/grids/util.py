import logging

from galaxy.web.form_builder import SelectField
from tool_shed.util import hg_util, metadata_util

log = logging.getLogger(__name__)


def build_approved_select_field(trans, name, selected_value=None, for_component=True):
    options = [('No', trans.model.ComponentReview.approved_states.NO),
               ('Yes', trans.model.ComponentReview.approved_states.YES)]
    if for_component:
        options.append(('Not applicable', trans.model.ComponentReview.approved_states.NA))
        if selected_value is None:
            selected_value = trans.model.ComponentReview.approved_states.NA
    select_field = SelectField(name=name)
    for option_tup in options:
        selected = selected_value and option_tup[1] == selected_value
        select_field.add_option(option_tup[0], option_tup[1], selected=selected)
    return select_field


def build_changeset_revision_select_field(trans, repository, selected_value=None, add_id_to_name=True,
                                          downloadable=False, reviewed=False, not_reviewed=False):
    """
    Build a SelectField whose options are the changeset_rev strings of certain revisions of the
    received repository.
    """
    options = []
    changeset_tups = []
    refresh_on_change_values = []
    if downloadable:
        # Restrict the options to downloadable revisions.
        repository_metadata_revisions = repository.downloadable_revisions
    elif reviewed:
        # Restrict the options to revisions that have been reviewed.
        repository_metadata_revisions = []
        metadata_changeset_revision_hashes = []
        for metadata_revision in repository.metadata_revisions:
            metadata_changeset_revision_hashes.append(metadata_revision.changeset_revision)
        for review in repository.reviews:
            if review.changeset_revision in metadata_changeset_revision_hashes:
                repository_metadata_revisions.append(review.repository_metadata)
    elif not_reviewed:
        # Restrict the options to revisions that have not yet been reviewed.
        repository_metadata_revisions = []
        reviewed_metadata_changeset_revision_hashes = []
        for review in repository.reviews:
            reviewed_metadata_changeset_revision_hashes.append(review.changeset_revision)
        for metadata_revision in repository.metadata_revisions:
            if metadata_revision.changeset_revision not in reviewed_metadata_changeset_revision_hashes:
                repository_metadata_revisions.append(metadata_revision)
    else:
        # Restrict the options to all revisions that have associated metadata.
        repository_metadata_revisions = repository.metadata_revisions
    for repository_metadata in repository_metadata_revisions:
        rev, label, changeset_revision = \
            hg_util.get_rev_label_changeset_revision_from_repository_metadata(trans.app,
                                                                              repository_metadata,
                                                                              repository=repository,
                                                                              include_date=True,
                                                                              include_hash=False)
        changeset_tups.append((rev, label, changeset_revision))
        refresh_on_change_values.append(changeset_revision)
    # Sort options by the revision label.  Even though the downloadable_revisions query sorts by update_time,
    # the changeset revisions may not be sorted correctly because setting metadata over time will reset update_time.
    for changeset_tup in sorted(changeset_tups):
        # Display the latest revision first.
        options.insert(0, (changeset_tup[1], changeset_tup[2]))
    if add_id_to_name:
        name = 'changeset_revision_%d' % repository.id
    else:
        name = 'changeset_revision'
    select_field = SelectField(name=name, refresh_on_change=True)
    for option_tup in options:
        selected = selected_value and option_tup[1] == selected_value
        select_field.add_option(option_tup[0], option_tup[1], selected=selected)
    return select_field


def filter_by_latest_downloadable_changeset_revision_that_has_missing_tool_test_components(trans, repository):
    """
    Inspect the latest downloadable changeset revision for the received repository to see if it
    includes tools that are either missing functional tests or functional test data.  If the
    changset revision includes tools but is missing tool test components, return the changeset
    revision hash.  This will filter out repositories of type repository_suite_definition and
    tool_dependency_definition.
    """
    repository_metadata = get_latest_downloadable_repository_metadata_if_it_includes_tools(trans, repository)
    if repository_metadata is not None \
            and repository_metadata.missing_test_components:
        return repository_metadata.changeset_revision
    return None


def filter_by_latest_metadata_changeset_revision_that_has_invalid_tools(trans, repository):
    """
    Inspect the latest changeset revision with associated metadata for the received repository
    to see if it has invalid tools.  This will filter out repositories of type repository_suite_definition
    and tool_dependency_definition.
    """
    repository_metadata = get_latest_repository_metadata_if_it_includes_invalid_tools(trans, repository)
    if repository_metadata is not None:
        return repository_metadata.changeset_revision
    return None


def get_latest_downloadable_repository_metadata(trans, repository):
    """
    Return the latest downloadable repository_metadata record for the received repository.  This will
    return repositories of type unrestricted as well as types repository_suite_definition and
     tool_dependency_definition.
    """
    encoded_repository_id = trans.security.encode_id(repository.id)
    repo = hg_util.get_repo_for_repository(trans.app, repository=repository)
    tip_ctx = str(repo.changectx(repo.changelog.tip()))
    repository_metadata = None
    try:
        repository_metadata = metadata_util.get_repository_metadata_by_changeset_revision(trans.app, encoded_repository_id, tip_ctx)
        if repository_metadata is not None and repository_metadata.downloadable:
            return repository_metadata
        return None
    except Exception:
        latest_downloadable_revision = metadata_util.get_previous_metadata_changeset_revision(trans.app, repository, tip_ctx, downloadable=True)
        if latest_downloadable_revision == hg_util.INITIAL_CHANGELOG_HASH:
            return None
        repository_metadata = metadata_util.get_repository_metadata_by_changeset_revision(trans.app,
                                                                                          encoded_repository_id,
                                                                                          latest_downloadable_revision)
        if repository_metadata is not None and repository_metadata.downloadable:
            return repository_metadata
        return None


def get_latest_downloadable_repository_metadata_if_it_includes_tools(trans, repository):
    """
    Return the latest downloadable repository_metadata record for the received repository if its
    includes_tools attribute is True.  This will filter out repositories of type repository_suite_definition
    and tool_dependency_definition.
    """
    repository_metadata = get_latest_downloadable_repository_metadata(trans, repository)
    if repository_metadata is not None and repository_metadata.includes_tools:
        return repository_metadata
    return None


def get_latest_repository_metadata(trans, repository):
    """
    Return the latest repository_metadata record for the received repository if it exists.  This will
    return repositories of type unrestricted as well as types repository_suite_definition and
     tool_dependency_definition.
    """
    encoded_repository_id = trans.security.encode_id(repository.id)
    repo = hg_util.get_repo_for_repository(trans.app, repository=repository)
    tip_ctx = str(repo.changectx(repo.changelog.tip()))
    try:
        repository_metadata = metadata_util.get_repository_metadata_by_changeset_revision(trans.app, encoded_repository_id, tip_ctx)
        return repository_metadata
    except Exception:
        latest_downloadable_revision = metadata_util.get_previous_metadata_changeset_revision(trans.app, repository, tip_ctx, downloadable=False)
        if latest_downloadable_revision == hg_util.INITIAL_CHANGELOG_HASH:
            return None
        repository_metadata = metadata_util.get_repository_metadata_by_changeset_revision(trans.app,
                                                                                          encoded_repository_id,
                                                                                          latest_downloadable_revision)
        return repository_metadata


def get_latest_repository_metadata_if_it_includes_invalid_tools(trans, repository):
    """
    Return the latest repository_metadata record for the received repository that contains invalid
    tools if one exists.  This will filter out repositories of type repository_suite_definition and
    tool_dependency_definition.
    """
    repository_metadata = get_latest_repository_metadata(trans, repository)
    if repository_metadata is not None:
        metadata = repository_metadata.metadata
        if metadata is not None and 'invalid_tools' in metadata:
            return repository_metadata
    return None
