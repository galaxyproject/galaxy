import logging

from sqlalchemy import (
    false,
    select,
    true,
)

log = logging.getLogger(__name__)


def in_tool_dict(tool_dict, exact_matches_checked, tool_id=None, tool_name=None, tool_version=None):
    found = False
    if tool_id and not tool_name and not tool_version:
        tool_dict_tool_id = tool_dict["id"].lower()
        found = (tool_id == tool_dict_tool_id) or (not exact_matches_checked and tool_dict_tool_id.find(tool_id) >= 0)
    elif tool_name and not tool_id and not tool_version:
        tool_dict_tool_name = tool_dict["name"].lower()
        found = (tool_name == tool_dict_tool_name) or (
            not exact_matches_checked and tool_dict_tool_name.find(tool_name) >= 0
        )
    elif tool_version and not tool_id and not tool_name:
        tool_dict_tool_version = tool_dict["version"].lower()
        found = (tool_version == tool_dict_tool_version) or (
            not exact_matches_checked and tool_dict_tool_version.find(tool_version) >= 0
        )
    elif tool_id and tool_name and not tool_version:
        tool_dict_tool_id = tool_dict["id"].lower()
        tool_dict_tool_name = tool_dict["name"].lower()
        found = (tool_id == tool_dict_tool_id and tool_name == tool_dict_tool_name) or (
            not exact_matches_checked
            and tool_dict_tool_id.find(tool_id) >= 0
            and tool_dict_tool_name.find(tool_name) >= 0
        )
    elif tool_id and tool_version and not tool_name:
        tool_dict_tool_id = tool_dict["id"].lower()
        tool_dict_tool_version = tool_dict["version"].lower()
        found = (tool_id == tool_dict_tool_id and tool_version == tool_dict_tool_version) or (
            not exact_matches_checked
            and tool_dict_tool_id.find(tool_id) >= 0
            and tool_dict_tool_version.find(tool_version) >= 0
        )
    elif tool_version and tool_name and not tool_id:
        tool_dict_tool_version = tool_dict["version"].lower()
        tool_dict_tool_name = tool_dict["name"].lower()
        found = (tool_version == tool_dict_tool_version and tool_name == tool_dict_tool_name) or (
            not exact_matches_checked
            and tool_dict_tool_version.find(tool_version) >= 0
            and tool_dict_tool_name.find(tool_name) >= 0
        )
    elif tool_version and tool_name and tool_id:
        tool_dict_tool_version = tool_dict["version"].lower()
        tool_dict_tool_name = tool_dict["name"].lower()
        tool_dict_tool_id = tool_dict["id"].lower()
        found = (
            tool_version == tool_dict_tool_version and tool_name == tool_dict_tool_name and tool_id == tool_dict_tool_id
        ) or (
            not exact_matches_checked
            and tool_dict_tool_version.find(tool_version) >= 0
            and tool_dict_tool_name.find(tool_name) >= 0
            and tool_dict_tool_id.find(tool_id) >= 0
        )
    return found


def make_same_length(list1, list2):
    # If either list is 1 item, we'll append to it until its length is the same as the other.
    if len(list1) == 1:
        for _ in range(1, len(list2)):
            list1.append(list1[0])
    elif len(list2) == 1:
        for _ in range(1, len(list1)):
            list2.append(list2[0])
    return list1, list2


def search_ids_names(tool_dict, exact_matches_checked, match_tuples, repository_metadata, tool_ids, tool_names):
    for i, tool_id in enumerate(tool_ids):
        tool_name = tool_names[i]
        if in_tool_dict(tool_dict, exact_matches_checked, tool_id=tool_id, tool_name=tool_name):
            match_tuples.append((repository_metadata.repository_id, repository_metadata.changeset_revision))
    return match_tuples


def search_ids_versions(tool_dict, exact_matches_checked, match_tuples, repository_metadata, tool_ids, tool_versions):
    for i, tool_id in enumerate(tool_ids):
        tool_version = tool_versions[i]
        if in_tool_dict(tool_dict, exact_matches_checked, tool_id=tool_id, tool_version=tool_version):
            match_tuples.append((repository_metadata.repository_id, repository_metadata.changeset_revision))
    return match_tuples


def search_names_versions(
    tool_dict, exact_matches_checked, match_tuples, repository_metadata, tool_names, tool_versions
):
    for i, tool_name in enumerate(tool_names):
        tool_version = tool_versions[i]
        if in_tool_dict(tool_dict, exact_matches_checked, tool_name=tool_name, tool_version=tool_version):
            match_tuples.append((repository_metadata.repository_id, repository_metadata.changeset_revision))
    return match_tuples


def search_repository_metadata(app, exact_matches_checked, tool_ids="", tool_names="", tool_versions=""):
    sa_session = app.model.session
    match_tuples = []
    ok = True
    if tool_ids or tool_names or tool_versions:
        for repository_metadata in get_metadata(sa_session, app.model.RepositoryMetadata, app.model.Repository):
            metadata = repository_metadata.metadata
            if metadata:
                tools = metadata.get("tools", [])
                for tool_dict in tools:
                    if tool_ids and not tool_names and not tool_versions:
                        for tool_id in tool_ids:
                            if in_tool_dict(tool_dict, exact_matches_checked, tool_id=tool_id):
                                match_tuples.append(
                                    (repository_metadata.repository_id, repository_metadata.changeset_revision)
                                )
                    elif tool_names and not tool_ids and not tool_versions:
                        for tool_name in tool_names:
                            if in_tool_dict(tool_dict, exact_matches_checked, tool_name=tool_name):
                                match_tuples.append(
                                    (repository_metadata.repository_id, repository_metadata.changeset_revision)
                                )
                    elif tool_versions and not tool_ids and not tool_names:
                        for tool_version in tool_versions:
                            if in_tool_dict(tool_dict, exact_matches_checked, tool_version=tool_version):
                                match_tuples.append(
                                    (repository_metadata.repository_id, repository_metadata.changeset_revision)
                                )
                    elif tool_ids and tool_names and not tool_versions:
                        if len(tool_ids) == len(tool_names):
                            match_tuples = search_ids_names(
                                tool_dict,
                                exact_matches_checked,
                                match_tuples,
                                repository_metadata,
                                tool_ids,
                                tool_names,
                            )
                        elif len(tool_ids) == 1 or len(tool_names) == 1:
                            tool_ids, tool_names = make_same_length(tool_ids, tool_names)
                            match_tuples = search_ids_names(
                                tool_dict,
                                exact_matches_checked,
                                match_tuples,
                                repository_metadata,
                                tool_ids,
                                tool_names,
                            )
                        else:
                            ok = False
                    elif tool_ids and tool_versions and not tool_names:
                        if len(tool_ids) == len(tool_versions):
                            match_tuples = search_ids_versions(
                                tool_dict,
                                exact_matches_checked,
                                match_tuples,
                                repository_metadata,
                                tool_ids,
                                tool_versions,
                            )
                        elif len(tool_ids) == 1 or len(tool_versions) == 1:
                            tool_ids, tool_versions = make_same_length(tool_ids, tool_versions)
                            match_tuples = search_ids_versions(
                                tool_dict,
                                exact_matches_checked,
                                match_tuples,
                                repository_metadata,
                                tool_ids,
                                tool_versions,
                            )
                        else:
                            ok = False
                    elif tool_versions and tool_names and not tool_ids:
                        if len(tool_versions) == len(tool_names):
                            match_tuples = search_names_versions(
                                tool_dict,
                                exact_matches_checked,
                                match_tuples,
                                repository_metadata,
                                tool_names,
                                tool_versions,
                            )
                        elif len(tool_versions) == 1 or len(tool_names) == 1:
                            tool_versions, tool_names = make_same_length(tool_versions, tool_names)
                            match_tuples = search_names_versions(
                                tool_dict,
                                exact_matches_checked,
                                match_tuples,
                                repository_metadata,
                                tool_names,
                                tool_versions,
                            )
                        else:
                            ok = False
                    elif tool_versions and tool_names and tool_ids:
                        if len(tool_versions) == len(tool_names) and len(tool_names) == len(tool_ids):
                            for i, tool_version in enumerate(tool_versions):
                                tool_name = tool_names[i]
                                tool_id = tool_ids[i]
                                if in_tool_dict(
                                    tool_dict,
                                    exact_matches_checked,
                                    tool_id=tool_id,
                                    tool_name=tool_name,
                                    tool_version=tool_version,
                                ):
                                    match_tuples.append(
                                        (repository_metadata.repository_id, repository_metadata.changeset_revision)
                                    )
                        else:
                            ok = False
    return ok, match_tuples


def get_metadata(session, repository_metadata_model, repository_model):
    stmt = (
        select(repository_metadata_model)
        .where(repository_metadata_model.includes_tools == true())
        .join(repository_model)
        .where(repository_model.deleted == false())
        .where(repository_model.deprecated == false())
    )
    return session.scalars(stmt)
