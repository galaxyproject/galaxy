import json
import logging
import os
import tarfile
from collections import namedtuple
from io import StringIO
from time import strftime

from sqlalchemy import (
    and_,
    false,
)
from webob.compat import cgi_FieldStorage

from galaxy import (
    util,
    web,
)
from galaxy.exceptions import (
    ActionInputError,
    ConfigDoesNotAllowException,
    InsufficientPermissionsException,
    ObjectNotFound,
    RequestParameterInvalidException,
    RequestParameterMissingException,
)
from galaxy.util import checkers
from galaxy.web import (
    expose_api,
    expose_api_anonymous_and_sessionless,
    expose_api_raw_anonymous_and_sessionless,
)
from galaxy.webapps.base.controller import (
    BaseAPIController,
    HTTPBadRequest,
)
from tool_shed.dependencies import attribute_handlers
from tool_shed.metadata import repository_metadata_manager
from tool_shed.repository_types import util as rt_util
from tool_shed.util import (
    commit_util,
    encoding_util,
    hg_util,
    metadata_util,
    repository_content_util,
    repository_util,
    tool_util,
)
from tool_shed.webapp.search.repo_search import RepoSearch

log = logging.getLogger(__name__)


class RepositoriesController(BaseAPIController):
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
        response_dict[
            "message"
        ] = f"Entries for repository {name} owned by {owner} have been added to the Tool Shed repository registry."
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
        eagerload_columns = ["downloadable_revisions"]
        if None not in [name, owner]:
            # Get the repository information.
            repository = repository_util.get_repository_by_name_and_owner(
                self.app, name, owner, eagerload_columns=eagerload_columns
            )
            if repository is None:
                trans.response.status = 404
                return {"status": "error", "message": f"No repository named {name} found with owner {owner}"}
        elif tsr_id is not None:
            repository = repository_util.get_repository_in_tool_shed(
                self.app, tsr_id, eagerload_columns=eagerload_columns
            )
        else:
            error_message = "Error in the Tool Shed repositories API in get_ordered_installable_revisions: "
            error_message += "invalid parameters received."
            log.debug(error_message)
            return []
        return [revision[1] for revision in repository.installable_revisions(self.app, sort_revisions=True)]

    @web.legacy_expose_api_anonymous
    def get_repository_revision_install_info(self, trans, name, owner, changeset_revision, **kwd):
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
        # Example URL:
        # http://<xyz>/api/repositories/get_repository_revision_install_info?name=<n>&owner=<o>&changeset_revision=<cr>
        if name and owner and changeset_revision:
            # Get the repository information.
            repository = repository_util.get_repository_by_name_and_owner(
                self.app, name, owner, eagerload_columns=["downloadable_revisions"]
            )
            if repository is None:
                log.debug(f"Cannot locate repository {name} owned by {owner}")
                return {}, {}, {}
            encoded_repository_id = trans.security.encode_id(repository.id)
            repository_dict = repository.to_dict(view="element", value_mapper=self.__get_value_mapper(trans))
            repository_dict["url"] = web.url_for(controller="repositories", action="show", id=encoded_repository_id)
            # Get the repository_metadata information.
            repository_metadata = metadata_util.get_repository_metadata_by_changeset_revision(
                self.app, encoded_repository_id, changeset_revision
            )
            if repository_metadata is None:
                # The changeset_revision column in the repository_metadata table has been updated with a new
                # value value, so find the changeset_revision to which we need to update.
                new_changeset_revision = metadata_util.get_next_downloadable_changeset_revision(
                    self.app, repository, changeset_revision
                )
                repository_metadata = metadata_util.get_repository_metadata_by_changeset_revision(
                    self.app, encoded_repository_id, new_changeset_revision
                )
                changeset_revision = new_changeset_revision
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
                # Get the repo_info_dict for installing the repository.
                (
                    repo_info_dict,
                    includes_tools,
                    includes_tool_dependencies,
                    includes_tools_for_display_in_tool_panel,
                    has_repository_dependencies,
                    has_repository_dependencies_only_if_compiling_contained_td,
                ) = repository_util.get_repo_info_dict(self.app, trans.user, encoded_repository_id, changeset_revision)
                return repository_dict, repository_metadata_dict, repo_info_dict
            else:
                log.debug(
                    "Unable to locate repository_metadata record for repository id %s and changeset_revision %s"
                    % (str(repository.id), str(changeset_revision))
                )
                return repository_dict, {}, {}
        else:
            debug_msg = "Error in the Tool Shed repositories API in get_repository_revision_install_info: "
            debug_msg += f"Invalid name {name} or owner {owner} or changeset_revision {changeset_revision} received."
            log.debug(debug_msg)
            return {}, {}, {}

    @web.legacy_expose_api_anonymous
    def get_installable_revisions(self, trans, **kwd):
        """
        GET /api/repositories/get_installable_revisions

        :param tsr_id: the encoded toolshed ID of the repository

        Returns a list of lists of changesets, in the format [ [ 0, fbb391dc803c ], [ 1, 9d9ec4d9c03e ], [ 2, 9b5b20673b89 ], [ 3, e8c99ce51292 ] ].
        """
        # Example URL: http://localhost:9009/api/repositories/get_installable_revisions?tsr_id=9d37e53072ff9fa4
        tsr_id = kwd.get("tsr_id", None)
        if tsr_id is not None:
            repository = repository_util.get_repository_in_tool_shed(
                self.app, tsr_id, eagerload_columns=["downloadable_revisions"]
            )
        else:
            error_message = "Error in the Tool Shed repositories API in get_ordered_installable_revisions: "
            error_message += "missing or invalid parameter received."
            log.debug(error_message)
            return []
        return repository.installable_revisions(self.app)

    def __get_value_mapper(self, trans):
        value_mapper = {
            "id": trans.security.encode_id,
            "repository_id": trans.security.encode_id,
            "user_id": trans.security.encode_id,
        }
        return value_mapper

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
        q = kwd.get("q", "")
        if q:
            page = kwd.get("page", 1)
            page_size = kwd.get("page_size", 10)
            try:
                page = int(page)
                page_size = int(page_size)
            except ValueError:
                raise RequestParameterInvalidException('The "page" and "page_size" parameters have to be integers.')
            return_jsonp = util.asbool(kwd.get("jsonp", False))
            callback = kwd.get("callback", "callback")
            search_results = self._search(trans, q, page, page_size)
            if return_jsonp:
                response = str(f"{callback}({json.dumps(search_results)});")
            else:
                response = json.dumps(search_results)
            return response
        tool_ids = kwd.get("tool_ids", None)
        if tool_ids is not None:
            tool_ids = util.listify(tool_ids)
            repository_found = []
            all_metadata = dict()
            for tool_id in tool_ids:
                # A valid GUID looks like toolshed.g2.bx.psu.edu/repos/bgruening/deeptools/deeptools_computeMatrix/1.1.0
                shed, _, owner, name, tool, version = tool_id.split("/")
                clause_list = [
                    and_(
                        self.app.model.Repository.table.c.deprecated == false(),
                        self.app.model.Repository.table.c.deleted == false(),
                        self.app.model.Repository.table.c.name == name,
                        self.app.model.User.table.c.username == owner,
                        self.app.model.Repository.table.c.user_id == self.app.model.User.table.c.id,
                    )
                ]
                repository = trans.sa_session.query(self.app.model.Repository).filter(*clause_list).first()
                if not repository:
                    log.warning(f"Repository {owner}/{name} does not exist, skipping")
                    continue
                for changeset, changehash in repository.installable_revisions(self.app):
                    metadata = metadata_util.get_current_repository_metadata_for_changeset_revision(
                        self.app, repository, changehash
                    )
                    tools = metadata.metadata.get("tools")
                    if not tools:
                        log.warning(f"Repository {owner}/{name}/{changehash} does not contain valid tools, skipping")
                        continue
                    for tool in tools:
                        if tool["guid"] in tool_ids:
                            repository_found.append("%d:%s" % (int(changeset), changehash))
                    metadata = metadata_util.get_current_repository_metadata_for_changeset_revision(
                        self.app, repository, changehash
                    )
                    if metadata is None:
                        continue
                    metadata_dict = metadata.to_dict(
                        value_mapper={"id": self.app.security.encode_id, "repository_id": self.app.security.encode_id}
                    )
                    metadata_dict["repository"] = repository.to_dict(value_mapper={"id": self.app.security.encode_id})
                    if metadata.has_repository_dependencies:
                        metadata_dict["repository_dependencies"] = metadata_util.get_all_dependencies(
                            self.app, metadata, processed_dependency_links=[]
                        )
                    else:
                        metadata_dict["repository_dependencies"] = []
                    if metadata.includes_tool_dependencies:
                        metadata_dict["tool_dependencies"] = repository.get_tool_dependencies(self.app, changehash)
                    else:
                        metadata_dict["tool_dependencies"] = {}
                    if metadata.includes_tools:
                        metadata_dict["tools"] = metadata.metadata["tools"]
                    all_metadata[f"{int(changeset)}:{changehash}"] = metadata_dict
            if repository_found:
                all_metadata["current_changeset"] = repository_found[0]
                # all_metadata[ 'found_changesets' ] = repository_found
                return json.dumps(all_metadata)
            return "{}"

        clause_list = [
            and_(
                self.app.model.Repository.table.c.deprecated == false(),
                self.app.model.Repository.table.c.deleted == deleted,
            )
        ]
        if owner is not None:
            clause_list.append(
                and_(
                    self.app.model.User.table.c.username == owner,
                    self.app.model.Repository.table.c.user_id == self.app.model.User.table.c.id,
                )
            )
        if name is not None:
            clause_list.append(self.app.model.Repository.table.c.name == name)
        for repository in (
            trans.sa_session.query(self.app.model.Repository)
            .filter(*clause_list)
            .order_by(self.app.model.Repository.table.c.name)
        ):
            repository_dict = repository.to_dict(view="collection", value_mapper=self.__get_value_mapper(trans))
            repository_dict["category_ids"] = [trans.security.encode_id(x.category.id) for x in repository.categories]
            repository_dicts.append(repository_dict)
        return json.dumps(repository_dicts)

    def _search(self, trans, q, page=1, page_size=10):
        """
        Perform the search over TS repositories.
        Note that search works over the Whoosh index which you have
        to pre-create with scripts/tool_shed/build_ts_whoosh_index.sh manually.
        Also TS config option toolshed_search_on has to be True and
        whoosh_index_dir has to be specified.
        """
        conf = self.app.config
        if not conf.toolshed_search_on:
            raise ConfigDoesNotAllowException("Searching the TS through the API is turned off for this instance.")
        if not conf.whoosh_index_dir:
            raise ConfigDoesNotAllowException(
                "There is no directory for the search index specified. Please contact the administrator."
            )
        search_term = q.strip()
        if len(search_term) < 1:
            raise RequestParameterInvalidException("The search term has to be at least one character long.")

        repo_search = RepoSearch()

        Boosts = namedtuple(
            "Boosts",
            [
                "repo_name_boost",
                "repo_description_boost",
                "repo_long_description_boost",
                "repo_homepage_url_boost",
                "repo_remote_repository_url_boost",
                "categories_boost",
                "repo_owner_username_boost",
            ],
        )
        boosts = Boosts(
            float(conf.get("repo_name_boost", 0.9)),
            float(conf.get("repo_description_boost", 0.6)),
            float(conf.get("repo_long_description_boost", 0.5)),
            float(conf.get("repo_homepage_url_boost", 0.3)),
            float(conf.get("repo_remote_repository_url_boost", 0.2)),
            float(conf.get("categories_boost", 0.5)),
            float(conf.get("repo_owner_username_boost", 0.3)),
        )

        results = repo_search.search(trans, search_term, page, page_size, boosts)
        results["hostname"] = web.url_for("/", qualified=True)
        return results

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
            response_dict[
                "message"
            ] = "You are not authorized to remove entries from this Tool Shed's repository registry."
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
        response_dict[
            "message"
        ] = f"Entries for repository {name} owned by {owner} have been removed from the Tool Shed repository registry."
        return response_dict

    @web.legacy_expose_api
    def repository_ids_for_setting_metadata(self, trans, my_writable=False, **kwd):
        """
        GET /api/repository_ids_for_setting_metadata

        Displays a collection (list) of repository ids ordered for setting metadata.

        :param key: the API key of the Tool Shed user.
        :param my_writable (optional): if the API key is associated with an admin user in the Tool Shed, setting this param value
                                       to True will restrict resetting metadata to only repositories that are writable by the user
                                       in addition to those repositories of type tool_dependency_definition.  This param is ignored
                                       if the current user is not an admin user, in which case this same restriction is automatic.
        """
        if trans.user_is_admin:
            my_writable = util.asbool(my_writable)
        else:
            my_writable = True
        handled_repository_ids = []
        repository_ids = []
        rmm = repository_metadata_manager.RepositoryMetadataManager(self.app, trans.user)
        query = rmm.get_query_for_setting_metadata_on_repositories(my_writable=my_writable, order=False)
        # Make sure repositories of type tool_dependency_definition are first in the list.
        for repository in query:
            if repository.type == rt_util.TOOL_DEPENDENCY_DEFINITION and repository.id not in handled_repository_ids:
                repository_ids.append(trans.security.encode_id(repository.id))
        # Now add all remaining repositories to the list.
        for repository in query:
            if repository.type != rt_util.TOOL_DEPENDENCY_DEFINITION and repository.id not in handled_repository_ids:
                repository_ids.append(trans.security.encode_id(repository.id))
        return repository_ids

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

        def handle_repository(trans, rmm, repository, results):
            log.debug(f"Resetting metadata on repository {repository.name}")
            try:
                rmm.set_repository(repository)
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

        rmm = repository_metadata_manager.RepositoryMetadataManager(
            app=self.app,
            user=trans.user,
            resetting_all_metadata_on_repository=True,
            updating_installed_repository=False,
            persist=False,
        )
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
        query = rmm.get_query_for_setting_metadata_on_repositories(my_writable=my_writable, order=False)
        # First reset metadata on all repositories of type repository_dependency_definition.
        for repository in query:
            encoded_id = trans.security.encode_id(repository.id)
            if encoded_id in encoded_ids_to_skip:
                log.debug(
                    "Skipping repository with id %s because it is in encoded_ids_to_skip %s"
                    % (str(repository.id), str(encoded_ids_to_skip))
                )
            elif repository.type == rt_util.TOOL_DEPENDENCY_DEFINITION and repository.id not in handled_repository_ids:
                results = handle_repository(trans, rmm, repository, results)
        # Now reset metadata on all remaining repositories.
        for repository in query:
            encoded_id = trans.security.encode_id(repository.id)
            if encoded_id in encoded_ids_to_skip:
                log.debug(
                    "Skipping repository with id %s because it is in encoded_ids_to_skip %s"
                    % (str(repository.id), str(encoded_ids_to_skip))
                )
            elif repository.type != rt_util.TOOL_DEPENDENCY_DEFINITION and repository.id not in handled_repository_ids:
                results = handle_repository(trans, rmm, repository, results)
        stop_time = strftime("%Y-%m-%d %H:%M:%S")
        results["stop_time"] = stop_time
        return json.dumps(results, sort_keys=True, indent=4)

    @web.legacy_expose_api
    def reset_metadata_on_repository(self, trans, payload, **kwd):
        """
        PUT /api/repositories/reset_metadata_on_repository

        Resets all metadata on a specified repository in the Tool Shed.

        :param key: the API key of the Tool Shed user.

        The following parameters must be included in the payload.
        :param repository_id: the encoded id of the repository on which metadata is to be reset.
        """

        def handle_repository(trans, start_time, repository):
            results = dict(start_time=start_time, repository_status=[])
            try:
                rmm = repository_metadata_manager.RepositoryMetadataManager(
                    app=self.app,
                    user=trans.user,
                    repository=repository,
                    resetting_all_metadata_on_repository=True,
                    updating_installed_repository=False,
                    persist=False,
                )
                rmm.reset_all_metadata_on_repository_in_tool_shed()
                rmm_invalid_file_tups = rmm.get_invalid_file_tups()
                if rmm_invalid_file_tups:
                    message = tool_util.generate_message_for_invalid_tools(
                        self.app, rmm_invalid_file_tups, repository, None, as_html=False
                    )
                    results["status"] = "warning"
                else:
                    message = f"Successfully reset metadata on repository {repository.name} owned by {repository.user.username}"
                    results["status"] = "ok"
            except Exception as e:
                message = (
                    f"Error resetting metadata on repository {repository.name} owned by {repository.user.username}: {e}"
                )
                results["status"] = "error"
            status = f"{repository.name} : {message}"
            results["repository_status"].append(status)
            return results

        repository_id = payload.get("repository_id", None)
        if repository_id is not None:
            repository = repository_util.get_repository_in_tool_shed(self.app, repository_id)
            start_time = strftime("%Y-%m-%d %H:%M:%S")
            log.debug(f"{start_time}...resetting metadata on repository {repository.name}")
            results = handle_repository(trans, start_time, repository)
            stop_time = strftime("%Y-%m-%d %H:%M:%S")
            results["stop_time"] = stop_time
        return results

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
        repository = repository_util.get_repository_by_name_and_owner(
            trans.app, name, owner, eagerload_columns=["downloadable_revisions"]
        )
        if repository and repository.downloadable_revisions:
            repository_metadata = metadata_util.get_repository_metadata_by_changeset_revision(
                trans.app, trans.security.encode_id(repository.id), changeset_revision
            )
            tool_shed_status_dict = {}
            # Handle repository deprecation.
            tool_shed_status_dict["repository_deprecated"] = str(repository.deprecated)
            tip_revision = repository.downloadable_revisions[0]
            # Handle latest installable revision.
            if changeset_revision == tip_revision:
                tool_shed_status_dict["latest_installable_revision"] = "True"
            else:
                next_installable_revision = metadata_util.get_next_downloadable_changeset_revision(
                    trans.app, repository, changeset_revision
                )
                if repository_metadata is None:
                    if next_installable_revision and next_installable_revision != changeset_revision:
                        tool_shed_status_dict["latest_installable_revision"] = "True"
                    else:
                        tool_shed_status_dict["latest_installable_revision"] = "False"
                else:
                    if next_installable_revision and next_installable_revision != changeset_revision:
                        tool_shed_status_dict["latest_installable_revision"] = "False"
                    else:
                        tool_shed_status_dict["latest_installable_revision"] = "True"
            # Handle revision updates.
            if changeset_revision == tip_revision:
                tool_shed_status_dict["revision_update"] = "False"
            else:
                if repository_metadata is None:
                    tool_shed_status_dict["revision_update"] = "True"
                else:
                    tool_shed_status_dict["revision_update"] = "False"
            # Handle revision upgrades.
            metadata_revisions = [
                revision[1] for revision in metadata_util.get_metadata_revisions(trans.app, repository)
            ]
            num_metadata_revisions = len(metadata_revisions)
            for index, metadata_revision in enumerate(metadata_revisions):
                if index == num_metadata_revisions:
                    tool_shed_status_dict["revision_upgrade"] = "False"
                    break
                if metadata_revision == changeset_revision:
                    if num_metadata_revisions - index > 1:
                        tool_shed_status_dict["revision_upgrade"] = "True"
                    else:
                        tool_shed_status_dict["revision_upgrade"] = "False"
                    break
            return (
                encoding_util.tool_shed_encode(tool_shed_status_dict)
                if hexlify_this
                else json.dumps(tool_shed_status_dict)
            )
        return encoding_util.tool_shed_encode({}) if hexlify_this else json.dumps({})

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
                "Unable to locate repository_metadata record for repository id %s and changeset_revision %s"
                % (str(id), str(changeset))
            )
            return {}

    @expose_api_anonymous_and_sessionless
    def metadata(self, trans, id, **kwd):
        """
        GET /api/repositories/{encoded_repository_id}/metadata
        Returns information about a repository in the Tool Shed.

        Example URL: http://localhost:9009/api/repositories/f9cad7b01a472135/metadata

        :param id: the encoded id of the Repository object

        :returns:   A dictionary containing the specified repository's metadata, by changeset,
                    recursively including dependencies and their metadata.

        :not found:  Empty dictionary.
        """
        recursive = util.asbool(kwd.get("recursive", "True"))
        all_metadata = {}
        repository = repository_util.get_repository_in_tool_shed(
            self.app, id, eagerload_columns=["downloadable_revisions"]
        )
        for changeset, changehash in repository.installable_revisions(self.app):
            metadata = metadata_util.get_current_repository_metadata_for_changeset_revision(
                self.app, repository, changehash
            )
            if metadata is None:
                continue
            metadata_dict = metadata.to_dict(
                value_mapper={"id": self.app.security.encode_id, "repository_id": self.app.security.encode_id}
            )
            metadata_dict["repository"] = repository.to_dict(value_mapper={"id": self.app.security.encode_id})
            if metadata.has_repository_dependencies and recursive:
                metadata_dict["repository_dependencies"] = metadata_util.get_all_dependencies(
                    self.app, metadata, processed_dependency_links=[]
                )
            else:
                metadata_dict["repository_dependencies"] = []
            if metadata.includes_tools:
                metadata_dict["tools"] = metadata.metadata["tools"]
            all_metadata[f"{int(changeset)}:{changehash}"] = metadata_dict
        return all_metadata

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

        repo, message = repository_util.update_repository(app=self.app, trans=trans, id=id, **update_kwds)
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
        category_ids = util.listify(payload.get("category_ids[]", ""))

        repo_type = payload.get("type", rt_util.UNRESTRICTED)
        if repo_type not in rt_util.types:
            raise RequestParameterInvalidException("This repository type is not valid")

        invalid_message = repository_util.validate_repository_name(self.app, name, trans.user)
        if invalid_message:
            raise RequestParameterInvalidException(invalid_message)

        repo, message = repository_util.create_repository(
            app=self.app,
            name=name,
            type=repo_type,
            description=synopsis,
            long_description=description,
            user_id=trans.user.id,
            category_ids=category_ids,
            remote_repository_url=remote_repository_url,
            homepage_url=homepage_url,
        )

        repository_dict = repo.to_dict(view="element", value_mapper=self.__get_value_mapper(trans))
        repository_dict["category_ids"] = [trans.security.encode_id(x.category.id) for x in repo.categories]
        return repository_dict

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
        rdah = attribute_handlers.RepositoryDependencyAttributeHandler(self.app, unpopulate=False)
        tdah = attribute_handlers.ToolDependencyAttributeHandler(self.app, unpopulate=False)

        repository = repository_util.get_repository_in_tool_shed(self.app, id)

        if not (
            trans.user_is_admin
            or self.app.security_agent.user_can_administer_repository(trans.user, repository)
            or self.app.security_agent.can_push(self.app, trans.user, repository)
        ):
            trans.response.status = 400
            return {
                "err_msg": "You do not have permission to update this repository.",
            }

        repo_dir = repository.repo_path(self.app)

        upload_point = commit_util.get_upload_point(repository, **kwd)
        tip = repository.tip()

        file_data = payload.get("file")
        # Code stolen from gx's upload_common.py
        if isinstance(file_data, cgi_FieldStorage):
            assert not isinstance(file_data.file, StringIO)
            assert file_data.file.name != "<fdopen>"
            local_filename = util.mkstemp_ln(file_data.file.name, "upload_file_data_")
            file_data.file.close()
            file_data = dict(filename=file_data.filename, local_filename=local_filename)
        elif type(file_data) == dict and "local_filename" not in file_data:
            raise Exception("Uploaded file was encoded in a way not understood.")

        commit_message = kwd.get("commit_message", "Uploaded")

        uploaded_file = open(file_data["local_filename"], "rb")
        uploaded_file_name = file_data["local_filename"]

        isgzip = False
        isbz2 = False
        isgzip = checkers.is_gzip(uploaded_file_name)
        if not isgzip:
            isbz2 = checkers.is_bz2(uploaded_file_name)
        if isgzip or isbz2:
            # Open for reading with transparent compression.
            tar = tarfile.open(uploaded_file_name, "r:*")
        else:
            tar = tarfile.open(uploaded_file_name)

        new_repo_alert = False
        remove_repo_files_not_in_tar = True

        (
            ok,
            message,
            files_to_remove,
            content_alert_str,
            undesirable_dirs_removed,
            undesirable_files_removed,
        ) = repository_content_util.upload_tar(
            trans,
            rdah,
            tdah,
            repository,
            tar,
            uploaded_file,
            upload_point,
            remove_repo_files_not_in_tar,
            commit_message,
            new_repo_alert,
        )
        if ok:
            # Update the repository files for browsing.
            hg_util.update_repository(repo_dir)
            # Get the new repository tip.
            if tip == repository.tip():
                trans.response.status = 400
                message = "No changes to repository."
                ok = False
            else:
                rmm = repository_metadata_manager.RepositoryMetadataManager(
                    app=self.app, user=trans.user, repository=repository
                )
                status, error_message = rmm.set_repository_metadata_due_to_new_tip(
                    trans.request.host, content_alert_str=content_alert_str, **kwd
                )
                if error_message:
                    ok = False
                    trans.response.status = 500
                    message = error_message
        else:
            trans.response.status = 500
        if os.path.exists(uploaded_file_name):
            os.remove(uploaded_file_name)
        if not ok:
            return {"err_msg": message}
        else:
            return {"message": message}
