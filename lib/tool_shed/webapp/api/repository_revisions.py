import logging
from typing import (
    Callable,
    Dict,
)

from sqlalchemy import select

from galaxy import (
    util,
    web,
)
from galaxy.model.base import transaction
from galaxy.webapps.base.controller import HTTPBadRequest
from tool_shed.util import (
    metadata_util,
    repository_util,
)
from tool_shed.webapp.model import RepositoryMetadata
from . import BaseShedAPIController

log = logging.getLogger(__name__)


class RepositoryRevisionsController(BaseShedAPIController):
    """RESTful controller for interactions with tool shed repository revisions."""

    def __get_value_mapper(self, trans) -> Dict[str, Callable]:
        value_mapper = {
            "id": trans.security.encode_id,
            "repository_id": trans.security.encode_id,
            "user_id": trans.security.encode_id,
        }
        return value_mapper

    @web.legacy_expose_api_anonymous
    def index(self, trans, **kwd):
        """
        GET /api/repository_revisions
        Displays a collection (list) of repository revisions.
        """
        # Example URL: http://localhost:9009/api/repository_revisions
        downloadable = kwd.get("downloadable", None)
        malicious = kwd.get("malicious", None)
        missing_test_components = kwd.get("missing_test_components", None)
        includes_tools = kwd.get("includes_tools", None)
        repository_metadata_dicts = []
        all_repository_metadata = get_repository_metadata(
            trans.sa_session, downloadable, malicious, missing_test_components, includes_tools
        )
        for repository_metadata in all_repository_metadata:
            repository_metadata_dict = repository_metadata.to_dict(
                view="collection", value_mapper=self.__get_value_mapper(trans)
            )
            repository_metadata_dict["url"] = web.url_for(
                controller="repository_revisions", action="show", id=trans.security.encode_id(repository_metadata.id)
            )
            repository_metadata_dicts.append(repository_metadata_dict)
        return repository_metadata_dicts

    @web.legacy_expose_api_anonymous
    def repository_dependencies(self, trans, id, **kwd):
        """
        GET /api/repository_revisions/{encoded repository_metadata id}/repository_dependencies

        Returns a list of dictionaries that each define a specific downloadable revision of a
        repository in the Tool Shed.  This method returns dictionaries with more information in
        them than other methods in this controller.  The information about repository_metdata is
        enhanced to include information about the repository (e.g., name, owner, etc) associated
        with the repository_metadata record.

        :param id: the encoded id of the `RepositoryMetadata` object
        """
        # Example URL: http://localhost:9009/api/repository_revisions/repository_dependencies/bb125606ff9ea620
        repository_dependencies_dicts = []
        repository_metadata = metadata_util.get_repository_metadata_by_id(trans.app, id)
        if repository_metadata is None:
            log.debug(f"Invalid repository_metadata id received: {id}")
            return repository_dependencies_dicts
        metadata = repository_metadata.metadata
        if metadata is None:
            log.debug(f"The repository_metadata record with id {id} has no metadata.")
            return repository_dependencies_dicts
        if "repository_dependencies" in metadata:
            rd_tups = metadata["repository_dependencies"]["repository_dependencies"]
            for rd_tup in rd_tups:
                tool_shed, name, owner, changeset_revision = rd_tup[0:4]
                repository_dependency = repository_util.get_repository_by_name_and_owner(trans.app, name, owner)
                if repository_dependency is None:
                    log.debug(f"Cannot locate repository dependency {name} owned by {owner}.")
                    continue
                repository_dependency_id = trans.security.encode_id(repository_dependency.id)
                repository_dependency_repository_metadata = metadata_util.get_repository_metadata_by_changeset_revision(
                    trans.app, repository_dependency_id, changeset_revision
                )
                if repository_dependency_repository_metadata is None:
                    # The changeset_revision column in the repository_metadata table has been updated with a new
                    # value value, so find the changeset_revision to which we need to update.
                    new_changeset_revision = metadata_util.get_next_downloadable_changeset_revision(
                        trans.app, repository_dependency, changeset_revision
                    )
                    if new_changeset_revision != changeset_revision:
                        repository_dependency_repository_metadata = (
                            metadata_util.get_repository_metadata_by_changeset_revision(
                                trans.app, repository_dependency_id, new_changeset_revision
                            )
                        )
                        changeset_revision = new_changeset_revision
                    else:
                        decoded_repository_dependency_id = trans.security.decode_id(repository_dependency_id)
                        debug_msg = (
                            f"Cannot locate repository_metadata with id {decoded_repository_dependency_id} for repository dependency {name} owned by {owner} "
                            f"using either of these changeset_revisions: {changeset_revision}, {new_changeset_revision}."
                        )
                        log.debug(debug_msg)
                        continue
                repository_dependency_metadata_dict = repository_dependency_repository_metadata.to_dict(
                    view="element", value_mapper=self.__get_value_mapper(trans)
                )
                repository_dependency_dict = repository_dependency.to_dict(
                    view="element", value_mapper=self.__get_value_mapper(trans)
                )
                # We need to be careful with the entries in our repository_dependency_dict here since this Tool Shed API
                # controller is working with repository_metadata records.  The above to_dict() method returns a dictionary
                # with an id entry for the repository record.  However, all of the other methods in this controller have
                # the id entry associated with a repository_metadata record id.  To avoid confusion, we'll update the
                # repository_dependency_metadata_dict with entries from the repository_dependency_dict without using the
                # Python dictionary update() method because we do not want to overwrite existing entries.
                for k, v in repository_dependency_dict.items():
                    if k not in repository_dependency_metadata_dict:
                        repository_dependency_metadata_dict[k] = v
                repository_dependency_metadata_dict["url"] = web.url_for(
                    controller="repositories", action="show", id=repository_dependency_id
                )
                repository_dependencies_dicts.append(repository_dependency_metadata_dict)
        return repository_dependencies_dicts

    @web.legacy_expose_api_anonymous
    def show(self, trans, id, **kwd):
        """
        GET /api/repository_revisions/{encoded_repository_metadata_id}
        Displays information about a repository_metadata record in the Tool Shed.

        :param id: the encoded id of the `RepositoryMetadata` object
        """
        # Example URL: http://localhost:9009/api/repository_revisions/bb125606ff9ea620
        repository_metadata = metadata_util.get_repository_metadata_by_id(trans.app, id)
        if repository_metadata is None:
            log.debug(f"Cannot locate repository_metadata with id {id}")
            return {}
        encoded_repository_id = trans.security.encode_id(repository_metadata.repository_id)
        repository_metadata_dict = repository_metadata.to_dict(
            view="element", value_mapper=self.__get_value_mapper(trans)
        )
        repository_metadata_dict["url"] = web.url_for(
            controller="repositories", action="show", id=encoded_repository_id
        )
        return repository_metadata_dict

    @web.legacy_expose_api
    def update(self, trans, payload, **kwd):
        """
        PUT /api/repository_revisions/{encoded_repository_metadata_id}/{payload}
        Updates the value of specified columns of the repository_metadata table based on the key / value pairs in payload.

        :param id: the encoded id of the `RepositoryMetadata` object
        """
        repository_metadata_id = kwd.get("id", None)
        if repository_metadata_id is None:
            raise HTTPBadRequest(detail="Missing required parameter 'id'.")
        repository_metadata = metadata_util.get_repository_metadata_by_id(trans.app, repository_metadata_id)
        if repository_metadata is None:
            decoded_repository_metadata_id = trans.security.decode_id(repository_metadata_id)
            log.debug(f"Cannot locate repository_metadata with id {decoded_repository_metadata_id}")
            return {}
        else:
            decoded_repository_metadata_id = repository_metadata.id
        flush_needed = False
        for key, new_value in payload.items():
            if hasattr(repository_metadata, key):
                # log information when setting attributes associated with the Tool Shed's install and test framework.
                if key in ["includes_tools", "missing_test_components"]:
                    log.debug(
                        "Setting repository_metadata column %s to value %s for changeset_revision %s via the Tool Shed API.",
                        key,
                        new_value,
                        repository_metadata.changeset_revision,
                    )
                setattr(repository_metadata, key, new_value)
                flush_needed = True
        if flush_needed:
            log.debug(
                "Updating repository_metadata record with id %s and changeset_revision %s.",
                decoded_repository_metadata_id,
                repository_metadata.changeset_revision,
            )
            trans.sa_session.add(repository_metadata)
            with transaction(trans.sa_session):
                trans.sa_session.commit()
            trans.sa_session.refresh(repository_metadata)
        repository_metadata_dict = repository_metadata.to_dict(
            view="element", value_mapper=self.__get_value_mapper(trans)
        )
        repository_metadata_dict["url"] = web.url_for(
            controller="repository_revisions", action="show", id=repository_metadata_id
        )
        return repository_metadata_dict


def get_repository_metadata(session, downloadable, malicious, missing_test_components, includes_tools):
    stmt = select(RepositoryMetadata)
    if downloadable is not None:
        stmt = stmt.where(RepositoryMetadata.downloadable == util.asbool(downloadable))
    if malicious is not None:
        stmt = stmt.where(RepositoryMetadata.malicious == util.asbool(malicious))
    if missing_test_components is not None:
        stmt = stmt.where(RepositoryMetadata.missing_test_components == util.asbool(missing_test_components))
    if includes_tools is not None:
        stmt = stmt.where(RepositoryMetadata.includes_tools == util.asbool(includes_tools))
    stmt = stmt.order_by(RepositoryMetadata.repository_id.desc())
    return session.scalars(stmt)
