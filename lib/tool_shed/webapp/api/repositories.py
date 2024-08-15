import json
import logging
import os
from io import StringIO
from time import strftime
from typing import (
    Callable,
    Dict,
)

from webob.compat import cgi_FieldStorage

from galaxy import (
    util,
    web,
)
from galaxy.exceptions import (
    ActionInputError,
    InsufficientPermissionsException,
    MessageException,
    ObjectNotFound,
    RequestParameterInvalidException,
    RequestParameterMissingException,
)
from galaxy.web import (
    expose_api,
    expose_api_anonymous_and_sessionless,
    expose_api_raw_anonymous_and_sessionless,
)
from galaxy.webapps.base.controller import HTTPBadRequest
from tool_shed.managers.repositories import (
    can_update_repo,
    check_updates,
    create_repository,
    get_install_info,
    get_ordered_installable_revisions,
    get_repository_metadata_dict,
    get_value_mapper,
    index_repositories,
    index_tool_ids,
    reset_metadata_on_repository,
    search,
    to_element_dict,
    UpdatesRequest,
    upload_tar_and_set_metadata,
)
from tool_shed.metadata import repository_metadata_manager
from tool_shed.repository_types import util as rt_util
from tool_shed.util import (
    metadata_util,
    repository_util,
    tool_util,
)
from tool_shed.webapp import model
from tool_shed_client.schema import (
    CreateRepositoryRequest,
    LegacyInstallInfoTuple,
)
from . import BaseShedAPIController

log = logging.getLogger(__name__)


class RepositoriesController(BaseShedAPIController):
    """RESTful controller for interactions with repositories in the Tool Shed."""

    @web.legacy_expose_api
    def add_repository_registry_entry(self, trans, payload, **kwd):
        """
        POST /api/repositories/add_repository_registry_entry
        Adds appropriate entries to the repository registry for the repository defined by the received name and owner.

        :param key: the user's API key

        The following parameters are included in the payload.
        :param tool_shed_url (required): the base URL of the Tool Shed containing the Repository
        :param name (required): the name of the Repository
        :param owner (required): the owner of the Repository
        """
        response_dict = {}
        if not trans.user_is_admin:
            response_dict["status"] = "error"
            response_dict["message"] = "You are not authorized to add entries to this Tool Shed's repository registry."
            return response_dict
        tool_shed_url = payload.get("tool_shed_url", "")
        if not tool_shed_url:
            raise HTTPBadRequest(detail="Missing required parameter 'tool_shed_url'.")
        tool_shed_url = tool_shed_url.rstrip("/")
        name = payload.get("name", "")
        if not name:
            raise HTTPBadRequest(detail="Missing required parameter 'name'.")
        owner = payload.get("owner", "")
        if not owner:
            raise HTTPBadRequest(detail="Missing required parameter 'owner'.")
        repository = repository_util.get_repository_by_name_and_owner(self.app, name, owner)
        if repository is None:
            error_message = f"Cannot locate repository with name {name} and owner {owner},"
            log.debug(error_message)
            response_dict["status"] = "error"
            response_dict["message"] = error_message
            return response_dict
        # Update the repository registry.
        self.app.repository_registry.add_entry(repository)
        response_dict["status"] = "ok"
        response_dict["message"] = (
            f"Entries for repository {name} owned by {owner} have been added to the Tool Shed repository registry."
        )
        return response_dict

    @web.legacy_expose_api_anonymous
    def get_ordered_installable_revisions(self, trans, name=None, owner=None, **kwd):
        """
        GET /api/repositories/get_ordered_installable_revisions

        :param name: the name of the Repository
        :param owner: the owner of the Repository

        Returns the ordered list of changeset revision hash strings that are associated with installable revisions.
        As in the changelog, the list is ordered oldest to newest.
        """
        # Example URL: http://localhost:9009/api/repositories/get_ordered_installable_revisions?name=add_column&owner=test
        if name is None:
            name = kwd.get("name", None)
        if owner is None:
            owner = kwd.get("owner", None)
        tsr_id = kwd.get("tsr_id", None)
        return get_ordered_installable_revisions(self.app, name, owner, tsr_id)

    @web.legacy_expose_api_anonymous
    def get_repository_revision_install_info(
        self, trans, name, owner, changeset_revision, **kwd
    ) -> LegacyInstallInfoTuple:
        """
        GET /api/repositories/get_repository_revision_install_info

        :param name: the name of the Repository
        :param owner: the owner of the Repository
        :param changeset_revision: the changeset_revision of the RepositoryMetadata object associated with the Repository

        Returns a list of the following dictionaries

        - a dictionary defining the Repository.  For example::

            {
                "deleted": false,
                "deprecated": false,
                "description": "add_column hello",
                "id": "f9cad7b01a472135",
                "long_description": "add_column hello",
                "name": "add_column",
                "owner": "test",
                "private": false,
                "times_downloaded": 6,
                "url": "/api/repositories/f9cad7b01a472135",
                "user_id": "f9cad7b01a472135"
            }

        - a dictionary defining the Repository revision (RepositoryMetadata).  For example::

            {
                "changeset_revision": "3a08cc21466f",
                "downloadable": true,
                "has_repository_dependencies": false,
                "has_repository_dependencies_only_if_compiling_contained_td": false,
                "id": "f9cad7b01a472135",
                "includes_datatypes": false,
                "includes_tool_dependencies": false,
                "includes_tools": true,
                "includes_tools_for_display_in_tool_panel": true,
                "includes_workflows": false,
                "malicious": false,
                "repository_id": "f9cad7b01a472135",
                "url": "/api/repository_revisions/f9cad7b01a472135",
                "valid_tools": [{u'add_to_tool_panel': True,
                    u'description': u'data on any column using simple expressions',
                    u'guid': u'localhost:9009/repos/enis/sample_repo_1/Filter1/2.2.0',
                    u'id': u'Filter1',
                    u'name': u'Filter',
                    u'requirements': [],
                    u'tests': [{u'inputs': [[u'input', u'1.bed'], [u'cond', u"c1=='chr22'"]],
                    u'name': u'Test-1',
                    u'outputs': [[u'out_file1', u'filter1_test1.bed']],
                    u'required_files': [u'1.bed', u'filter1_test1.bed']}],
                    u'tool_config': u'database/community_files/000/repo_1/filtering.xml',
                    u'tool_type': u'default',
                    u'version': u'2.2.0',
                    u'version_string_cmd': None}]
            }

        - a dictionary including the additional information required to install the repository.  For example::

            {
                "add_column": [
                    "add_column hello",
                    "http://test@localhost:9009/repos/test/add_column",
                    "3a08cc21466f",
                    "1",
                    "test",
                    {},
                    {}
                ]
            }

        """
        return get_install_info(trans, name, owner, changeset_revision)

    @web.legacy_expose_api_anonymous
    def get_installable_revisions(self, trans, **kwd):
        """
        GET /api/repositories/get_installable_revisions

        :param tsr_id: the encoded toolshed ID of the repository

        Returns a list of lists of changesets, in the format [ [ 0, fbb391dc803c ], [ 1, 9d9ec4d9c03e ], [ 2, 9b5b20673b89 ], [ 3, e8c99ce51292 ] ].
        """
        # Example URL: http://localhost:9009/api/repositories/get_installable_revisions?tsr_id=9d37e53072ff9fa4
        if (tsr_id := kwd.get("tsr_id", None)) is not None:
            repository = repository_util.get_repository_in_tool_shed(
                self.app, tsr_id, eagerload_columns=[model.Repository.downloadable_revisions]
            )
        else:
            error_message = "Error in the Tool Shed repositories API in get_ordered_installable_revisions: "
            error_message += "missing or invalid parameter received."
            log.debug(error_message)
            return []
        return repository.installable_revisions(self.app)

    def __get_value_mapper(self, trans) -> Dict[str, Callable]:
        return get_value_mapper(self.app)

    @expose_api_raw_anonymous_and_sessionless
    def index(self, trans, deleted=False, owner=None, name=None, **kwd):
        """
        GET /api/repositories
        Displays a collection of repositories with optional criteria.

        :param q:        (optional)if present search on the given query will be performed
        :type  q:        str

        :param page:     (optional)requested page of the search
        :type  page:     int

        :param page_size:     (optional)requested page_size of the search
        :type  page_size:     int

        :param jsonp:    (optional)flag whether to use jsonp format response, defaults to False
        :type  jsonp:    bool

        :param callback: (optional)name of the function to wrap callback in
                         used only when jsonp is true, defaults to 'callback'
        :type  callback: str

        :param deleted:  (optional)displays repositories that are or are not set to deleted.
        :type  deleted:  bool

        :param owner:    (optional)the owner's public username.
        :type  owner:    str

        :param name:     (optional)the repository name.
        :type  name:     str

        :param tool_ids:  (optional) a tool GUID to find the repository for
        :param tool_ids:  str

        :returns dict:   object containing list of results

        Examples:
            GET http://localhost:9009/api/repositories
            GET http://localhost:9009/api/repositories?q=fastq
        """
        repository_dicts = []
        deleted = util.asbool(deleted)
        if q := kwd.get("q", ""):
            page = kwd.get("page", 1)
            page_size = kwd.get("page_size", 10)
            try:
                page = int(page)
                page_size = int(page_size)
            except ValueError:
                raise RequestParameterInvalidException('The "page" and "page_size" parameters have to be integers.')
            return_jsonp = util.asbool(kwd.get("jsonp", False))
            callback = kwd.get("callback", "callback")
            search_results = search(trans, q, page, page_size)
            if return_jsonp:
                response = str(f"{callback}({json.dumps(search_results)});")
            else:
                response = json.dumps(search_results)
            return response
        if (tool_ids := kwd.get("tool_ids", None)) is not None:
            tool_ids = util.listify(tool_ids)
            response = index_tool_ids(self.app, tool_ids)
            return json.dumps(response)
        else:
            repositories = index_repositories(self.app, name, owner, deleted)
            repository_dicts = []
            for repository in repositories:
                repository_dict = repository.to_dict(view="collection", value_mapper=self.__get_value_mapper(trans))
                repository_dict["category_ids"] = [
                    trans.security.encode_id(x.category.id) for x in repository.categories
                ]
                repository_dicts.append(repository_dict)
            return json.dumps(repository_dicts)

    @web.legacy_expose_api
    def remove_repository_registry_entry(self, trans, payload, **kwd):
        """
        POST /api/repositories/remove_repository_registry_entry
        Removes appropriate entries from the repository registry for the repository defined by the received name and owner.

        :param key: the user's API key

        The following parameters are included in the payload.
        :param tool_shed_url (required): the base URL of the Tool Shed containing the Repository
        :param name (required): the name of the Repository
        :param owner (required): the owner of the Repository
        """
        response_dict = {}
        if not trans.user_is_admin:
            response_dict["status"] = "error"
            response_dict["message"] = (
                "You are not authorized to remove entries from this Tool Shed's repository registry."
            )
            return response_dict
        tool_shed_url = payload.get("tool_shed_url", "")
        if not tool_shed_url:
            raise HTTPBadRequest(detail="Missing required parameter 'tool_shed_url'.")
        tool_shed_url = tool_shed_url.rstrip("/")
        name = payload.get("name", "")
        if not name:
            raise HTTPBadRequest(detail="Missing required parameter 'name'.")
        owner = payload.get("owner", "")
        if not owner:
            raise HTTPBadRequest(detail="Missing required parameter 'owner'.")
        repository = repository_util.get_repository_by_name_and_owner(self.app, name, owner)
        if repository is None:
            error_message = f"Cannot locate repository with name {name} and owner {owner},"
            log.debug(error_message)
            response_dict["status"] = "error"
            response_dict["message"] = error_message
            return response_dict
        # Update the repository registry.
        self.app.repository_registry.remove_entry(repository)
        response_dict["status"] = "ok"
        response_dict["message"] = (
            f"Entries for repository {name} owned by {owner} have been removed from the Tool Shed repository registry."
        )
        return response_dict

    @web.legacy_expose_api
    def reset_metadata_on_repositories(self, trans, payload, **kwd):
        """
        PUT /api/repositories/reset_metadata_on_repositories

        Resets all metadata on all repositories in the Tool Shed in an "orderly fashion".  Since there are currently only two
        repository types (tool_dependecy_definition and unrestricted), the order in which metadata is reset is repositories of
        type tool_dependecy_definition first followed by repositories of type unrestricted, and only one pass is necessary.  If
        a new repository type is introduced, the process will undoubtedly need to be revisited.  To facilitate this order, an
        in-memory list of repository ids that have been processed is maintained.

        :param key: the API key of the Tool Shed user.
        :param my_writable (optional):
            if the API key is associated with an admin user in the Tool Shed, setting this param value
            to True will restrict resetting metadata to only repositories that are writable by the user
            in addition to those repositories of type tool_dependency_definition.  This param is ignored
            if the current user is not an admin user, in which case this same restriction is automatic.

        :param encoded_ids_to_skip (optional): a list of encoded repository ids for repositories that should not be processed.
        :param skip_file (optional):
            A local file name that contains the encoded repository ids associated with repositories to skip.
            This param can be used as an alternative to the above encoded_ids_to_skip.

        """

        def handle_repository(trans, repository, results):
            log.debug(f"Resetting metadata on repository {repository.name}")
            try:
                rmm = repository_metadata_manager.RepositoryMetadataManager(
                    trans,
                    resetting_all_metadata_on_repository=True,
                    updating_installed_repository=False,
                    repository=repository,
                    persist=False,
                )
                rmm.reset_all_metadata_on_repository_in_tool_shed()
                rmm_invalid_file_tups = rmm.get_invalid_file_tups()
                if rmm_invalid_file_tups:
                    message = tool_util.generate_message_for_invalid_tools(
                        self.app, rmm_invalid_file_tups, repository, None, as_html=False
                    )
                    results["unsuccessful_count"] += 1
                else:
                    message = f"Successfully reset metadata on repository {repository.name} owned by {repository.user.username}"
                    results["successful_count"] += 1
            except Exception as e:
                message = (
                    f"Error resetting metadata on repository {repository.name} owned by {repository.user.username}: {e}"
                )
                results["unsuccessful_count"] += 1
            status = f"{repository.name} : {message}"
            results["repository_status"].append(status)
            return results

        start_time = strftime("%Y-%m-%d %H:%M:%S")
        results = dict(start_time=start_time, repository_status=[], successful_count=0, unsuccessful_count=0)
        handled_repository_ids = []
        encoded_ids_to_skip = payload.get("encoded_ids_to_skip", [])
        skip_file = payload.get("skip_file", None)
        if skip_file and os.path.exists(skip_file) and not encoded_ids_to_skip:
            # Load the list of encoded_ids_to_skip from the skip_file.
            # Contents of file must be 1 encoded repository id per line.
            lines = open(skip_file, "rb").readlines()
            for line in lines:
                if line.startswith("#"):
                    # Skip comments.
                    continue
                encoded_ids_to_skip.append(line.rstrip("\n"))
        if trans.user_is_admin:
            my_writable = util.asbool(payload.get("my_writable", False))
        else:
            my_writable = True
        rmm = repository_metadata_manager.RepositoryMetadataManager(
            trans,
            resetting_all_metadata_on_repository=True,
            updating_installed_repository=False,
            persist=False,
        )
        # First reset metadata on all repositories of type repository_dependency_definition.
        for repository in rmm.get_repositories_for_setting_metadata(my_writable=my_writable, order=False):
            encoded_id = trans.security.encode_id(repository.id)
            if encoded_id in encoded_ids_to_skip:
                log.debug(
                    "Skipping repository with id %s because it is in encoded_ids_to_skip %s",
                    repository.id,
                    encoded_ids_to_skip,
                )
            elif repository.type == rt_util.TOOL_DEPENDENCY_DEFINITION and repository.id not in handled_repository_ids:
                results = handle_repository(trans, repository, results)
        # Now reset metadata on all remaining repositories.
        for repository in rmm.get_repositories_for_setting_metadata(my_writable=my_writable, order=False):
            encoded_id = trans.security.encode_id(repository.id)
            if encoded_id in encoded_ids_to_skip:
                log.debug(
                    "Skipping repository with id %s because it is in encoded_ids_to_skip %s",
                    repository.id,
                    encoded_ids_to_skip,
                )
            elif repository.type != rt_util.TOOL_DEPENDENCY_DEFINITION and repository.id not in handled_repository_ids:
                results = handle_repository(trans, repository, results)
        stop_time = strftime("%Y-%m-%d %H:%M:%S")
        results["stop_time"] = stop_time
        return json.dumps(results, sort_keys=True, indent=4)

    @web.legacy_expose_api
    def reset_metadata_on_repository(self, trans, payload, **kwd):
        """
        POST /api/repositories/reset_metadata_on_repository

        Resets all metadata on a specified repository in the Tool Shed.

        :param key: the API key of the Tool Shed user.

        The following parameters must be included in the payload.
        :param repository_id: the encoded id of the repository on which metadata is to be reset.
        """
        repository_id = payload.get("repository_id", None)
        return reset_metadata_on_repository(trans, repository_id).model_dump()

    @expose_api_anonymous_and_sessionless
    def show(self, trans, id, **kwd):
        """
        GET /api/repositories/{encoded_repository_id}
        Returns information about a repository in the Tool Shed.

        Example URL: http://localhost:9009/api/repositories/f9cad7b01a472135

        :param id: the encoded id of the Repository object
        :type  id: encoded str

        :returns:   detailed repository information
        :rtype:     dict

        :raises:  ObjectNotFound, MalformedId
        """
        repository = repository_util.get_repository_in_tool_shed(self.app, id)
        if repository is None:
            raise ObjectNotFound("Unable to locate repository for the given id.")
        repository_dict = repository.to_dict(view="element", value_mapper=self.__get_value_mapper(trans))
        # TODO the following property would be better suited in the to_dict method
        repository_dict["category_ids"] = [trans.security.encode_id(x.category.id) for x in repository.categories]
        return repository_dict

    @expose_api_raw_anonymous_and_sessionless
    def updates(self, trans, **kwd):
        """
        GET /api/repositories/updates
        Return a dictionary with boolean values for whether there are updates available
        for the repository revision, newer installable revisions available,
        the revision is the latest installable revision, and if the repository is deprecated.

        :param owner: owner of the repository
        :type  owner: str
        :param name: name of the repository
        :type  name: str
        :param changeset_revision: changeset of the repository
        :type  changeset_revision: str
        :param hexlify: flag whether to hexlify the response (for backward compatibility)
        :type  changeset: boolean

        :returns:   information about repository deprecations, updates, and upgrades
        :rtype:     dict
        """
        name = kwd.get("name", None)
        owner = kwd.get("owner", None)
        changeset_revision = kwd.get("changeset_revision", None)
        hexlify_this = util.asbool(kwd.get("hexlify", True))
        request = UpdatesRequest(
            name=name,
            owner=owner,
            changeset_revision=changeset_revision,
            hexlify=hexlify_this,
        )
        return check_updates(trans.app, request)

    @expose_api_anonymous_and_sessionless
    def show_tools(self, trans, id, changeset, **kwd):
        repository_metadata = metadata_util.get_repository_metadata_by_changeset_revision(self.app, id, changeset)
        if repository_metadata is not None:
            encoded_repository_metadata_id = trans.security.encode_id(repository_metadata.id)
            repository_metadata_dict = repository_metadata.to_dict(
                view="collection", value_mapper=self.__get_value_mapper(trans)
            )
            repository_metadata_dict["url"] = web.url_for(
                controller="repository_revisions", action="show", id=encoded_repository_metadata_id
            )
            if "tools" in repository_metadata.metadata:
                repository_metadata_dict["valid_tools"] = repository_metadata.metadata["tools"]
            return repository_metadata_dict
        else:
            log.debug(
                "Unable to locate repository_metadata record for repository id %s and changeset_revision %s",
                id,
                changeset,
            )
            return {}

    @expose_api_anonymous_and_sessionless
    def metadata(self, trans, id, **kwd):
        """
        GET /api/repositories/{encoded_repository_id}/metadata
        Returns information about a repository in the Tool Shed.

        Example URL: http://localhost:9009/api/repositories/f9cad7b01a472135/metadata

        :param id: the encoded id of the Repository object

        :param downloadable_only: Return only downloadable revisions (defaults to True).
                                  Added for test cases - shouldn't be considered part of the stable API.

        :returns:   A dictionary containing the specified repository's metadata, by changeset,
                    recursively including dependencies and their metadata.

        :not found:  Empty dictionary.
        """
        recursive = util.asbool(kwd.get("recursive", "True"))
        downloadable_only = util.asbool(kwd.get("downloadable_only", "True"))
        return get_repository_metadata_dict(self.app, id, recursive, downloadable_only)

    @expose_api
    def update(self, trans, id, **kwd):
        """
        PATCH /api/repositories/{encoded_repository_id}
        Updates information about a repository in the Tool Shed.

        :param id: the encoded id of the Repository object

        :param payload: dictionary structure containing

            'name':                  repo's name (optional)
            'synopsis':              repo's synopsis (optional)
            'description':           repo's description (optional)
            'remote_repository_url': repo's remote repo (optional)
            'homepage_url':          repo's homepage url (optional)
            'category_ids':          list of existing encoded TS category ids the updated repo should be associated with (optional)

        :type payload: dict

        :returns:   detailed repository information
        :rtype:     dict

        :raises: RequestParameterInvalidException, InsufficientPermissionsException
        """
        payload = kwd.get("payload", None)
        if not payload:
            raise RequestParameterMissingException("You did not specify any payload.")

        name = payload.get("name", None)
        synopsis = payload.get("synopsis", None)
        description = payload.get("description", None)
        remote_repository_url = payload.get("remote_repository_url", None)
        homepage_url = payload.get("homepage_url", None)
        category_ids = payload.get("category_ids", None)
        if category_ids is not None:
            # We need to know if it was actually passed, and listify turns None into []
            category_ids = util.listify(category_ids)

        update_kwds = dict(
            name=name,
            description=synopsis,
            long_description=description,
            remote_repository_url=remote_repository_url,
            homepage_url=homepage_url,
            category_ids=category_ids,
        )

        repo, message = repository_util.update_repository(trans, id, **update_kwds)
        if repo is None:
            if "You are not the owner" in message:
                raise InsufficientPermissionsException(message)
            else:
                raise ActionInputError(message)

        repository_dict = repo.to_dict(view="element", value_mapper=self.__get_value_mapper(trans))
        repository_dict["category_ids"] = [trans.security.encode_id(x.category.id) for x in repo.categories]
        return repository_dict

    @expose_api
    def create(self, trans, **kwd):
        """
        POST /api/repositories:

        Creates a new repository.
        Only ``name`` and ``synopsis`` parameters are required.

        :param payload: dictionary structure containing

            'name':                  new repo's name (required)
            'synopsis':              new repo's synopsis (required)
            'description':           new repo's description (optional)
            'remote_repository_url': new repo's remote repo (optional)
            'homepage_url':          new repo's homepage url (optional)
            'category_ids[]':        list of existing encoded TS category ids the new repo should be associated with (optional)
            'type':                  new repo's type, defaults to ``unrestricted`` (optional)

        :type payload: dict

        :returns:   detailed repository information
        :rtype:     dict

        :raises: RequestParameterMissingException, RequestParameterInvalidException
        """
        payload = kwd.get("payload", None)
        if not payload:
            raise RequestParameterMissingException("You did not specify any payload.")
        name = payload.get("name", None)
        if not name:
            raise RequestParameterMissingException("Missing required parameter 'name'.")
        synopsis = payload.get("synopsis", None)
        if not synopsis:
            raise RequestParameterMissingException("Missing required parameter 'synopsis'.")

        description = payload.get("description", "")
        remote_repository_url = payload.get("remote_repository_url", "")
        homepage_url = payload.get("homepage_url", "")

        repo_type = payload.get("type", rt_util.UNRESTRICTED)
        if repo_type not in rt_util.types:
            raise RequestParameterInvalidException("This repository type is not valid")

        request = CreateRepositoryRequest(
            name=name,
            synopsis=synopsis,
            description=description,
            remote_repository_url=remote_repository_url,
            homepage_url=homepage_url,
            category_ids=payload.get("category_ids[]", ""),
            type_=repo_type,
        )
        repo = create_repository(trans, request)
        return to_element_dict(self.app, repo, include_categories=True)

    @web.legacy_expose_api
    def create_changeset_revision(self, trans, id, payload, **kwd):
        """
        POST /api/repositories/{encoded_repository_id}/changeset_revision

        Create a new tool shed repository commit - leaving PUT on parent
        resource open for updating meta-attributes of the repository (and
        Galaxy doesn't allow PUT multipart data anyway
        https://trello.com/c/CQwmCeG6).

        :param id: the encoded id of the Repository object

        The following parameters may be included in the payload.
        :param commit_message: hg commit message for update.
        """

        # Example URL: http://localhost:9009/api/repositories/f9cad7b01a472135
        repository = repository_util.get_repository_in_tool_shed(self.app, id)

        if not can_update_repo(trans, repository):
            trans.response.status = 400
            return {
                "err_msg": "You do not have permission to update this repository.",
            }

        file_data = payload.get("file")
        # Code stolen from gx's upload_common.py
        if isinstance(file_data, cgi_FieldStorage):
            assert not isinstance(file_data.file, StringIO)
            assert file_data.file.name != "<fdopen>"
            local_filename = util.mkstemp_ln(file_data.file.name, "upload_file_data_")
            file_data.file.close()
            file_data = dict(filename=file_data.filename, local_filename=local_filename)
        elif isinstance(file_data, dict) and "local_filename" not in file_data:
            raise Exception("Uploaded file was encoded in a way not understood.")

        commit_message = kwd.get("commit_message", "Uploaded")

        uploaded_file_name = file_data["local_filename"]
        try:
            message = upload_tar_and_set_metadata(
                trans,
                trans.request.host,
                repository,
                uploaded_file_name,
                commit_message,
            )
            rval = {"message": message}
        except MessageException as e:
            trans.response.status = e.status_code
            rval = {"err_msg": str(e)}
        if os.path.exists(uploaded_file_name):
            os.remove(uploaded_file_name)
        return rval
