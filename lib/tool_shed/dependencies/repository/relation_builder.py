import logging

import tool_shed.util.repository_util
from galaxy.util import (
    asbool,
    listify,
)
from tool_shed.util import (
    common_util,
    container_util,
    metadata_util,
    shed_util_common as suc,
)

log = logging.getLogger(__name__)


class RelationBuilder:
    def __init__(self, app, repository, repository_metadata, tool_shed_url):
        self.all_repository_dependencies = {}
        self.app = app
        self.circular_repository_dependencies = []
        self.repository = repository
        self.repository_metadata = repository_metadata
        self.handled_key_rd_dicts = []
        self.key_rd_dicts_to_be_processed = []
        self.tool_shed_url = tool_shed_url

    def can_add_to_key_rd_dicts(self, key_rd_dict, key_rd_dicts):
        """Handle the case where an update to the changeset revision was done."""
        k = next(iter(key_rd_dict))
        rd = key_rd_dict[k]
        partial_rd = rd[0:3]
        for kr_dict in key_rd_dicts:
            key = next(iter(kr_dict))
            if key == k:
                repository_dependency = kr_dict[key]
                if repository_dependency[0:3] == partial_rd:
                    return False
        return True

    def filter_only_if_compiling_contained_td(self, key_rd_dict):
        """
        Return a copy of the received key_rd_dict with repository dependencies that are needed
        only_if_compiling_contained_td filtered out of the list of repository dependencies for
        each rd_key.
        """
        filtered_key_rd_dict = {}
        for rd_key, required_rd_tup in key_rd_dict.items():
            (
                tool_shed,
                name,
                owner,
                changeset_revision,
                prior_installation_required,
                only_if_compiling_contained_td,
            ) = common_util.parse_repository_dependency_tuple(required_rd_tup)
            if not asbool(only_if_compiling_contained_td):
                filtered_key_rd_dict[rd_key] = required_rd_tup
        return filtered_key_rd_dict

    def get_prior_installation_required_and_only_if_compiling_contained_td(self):
        """
        This method is called from the tool shed and never Galaxy.  If self.all_repository_dependencies
        contains a repository dependency tuple that is associated with self.repository, return the
        value of the tuple's prior_installation_required component.
        """
        cleaned_toolshed_base_url = common_util.remove_protocol_from_tool_shed_url(self.tool_shed_url)
        if self.all_repository_dependencies:
            for rd_key, rd_tups in self.all_repository_dependencies.items():
                if rd_key in ["root_key", "description"]:
                    continue
                for rd_tup in rd_tups:
                    (
                        rd_toolshed,
                        rd_name,
                        rd_owner,
                        rd_changeset_revision,
                        rd_prior_installation_required,
                        rd_only_if_compiling_contained_td,
                    ) = common_util.parse_repository_dependency_tuple(rd_tup)
                    cleaned_rd_toolshed = common_util.remove_protocol_from_tool_shed_url(rd_toolshed)
                    if (
                        cleaned_rd_toolshed == cleaned_toolshed_base_url
                        and rd_name == self.repository.name
                        and rd_owner == self.repository.user.username
                        and rd_changeset_revision == self.repository_metadata.changeset_revision
                    ):
                        return rd_prior_installation_required, rd_only_if_compiling_contained_td
        elif self.repository_metadata:
            # Get the list of changeset revisions from the tool shed to which self.repository may be updated.
            metadata = self.repository_metadata.metadata
            current_changeset_revision = str(self.repository_metadata.changeset_revision)
            # Get the changeset revision to which the current value of required_repository_changeset_revision
            # should be updated if it's not current.
            text = metadata_util.get_updated_changeset_revisions(
                self.app,
                name=str(self.repository.name),
                owner=str(self.repository.user.username),
                changeset_revision=current_changeset_revision,
            )
            if text:
                valid_changeset_revisions = listify(text)
                if current_changeset_revision not in valid_changeset_revisions:
                    valid_changeset_revisions.append(current_changeset_revision)
            else:
                valid_changeset_revisions = [current_changeset_revision]
            repository_dependencies_dict = metadata["repository_dependencies"]
            rd_tups = repository_dependencies_dict.get("repository_dependencies", [])
            for rd_tup in rd_tups:
                (
                    rd_toolshed,
                    rd_name,
                    rd_owner,
                    rd_changeset_revision,
                    rd_prior_installation_required,
                    rd_only_if_compiling_contained_td,
                ) = common_util.parse_repository_dependency_tuple(rd_tup)
                cleaned_rd_toolshed = common_util.remove_protocol_from_tool_shed_url(rd_toolshed)
                if (
                    cleaned_rd_toolshed == cleaned_toolshed_base_url
                    and rd_name == self.repository.name
                    and rd_owner == self.repository.user.username
                    and rd_changeset_revision in valid_changeset_revisions
                ):
                    return rd_prior_installation_required, rd_only_if_compiling_contained_td
        # Default both prior_installation_required and only_if_compiling_contained_td to False.
        return "False", "False"

    def get_key_for_repository_changeset_revision(self):
        # The received toolshed_base_url must include the port, but doesn't have to include the protocol.
        (
            prior_installation_required,
            only_if_compiling_contained_td,
        ) = self.get_prior_installation_required_and_only_if_compiling_contained_td()
        # Create a key with the value of prior_installation_required defaulted to False.
        key = container_util.generate_repository_dependencies_key_for_repository(
            self.tool_shed_url,
            self.repository.name,
            self.repository.user.username,
            self.repository_metadata.changeset_revision,
            prior_installation_required,
            only_if_compiling_contained_td,
        )
        return key

    def get_repository_dependencies_for_changeset_revision(self):
        """
        Return a dictionary of all repositories upon which the contents of self.repository_metadata
        record depend.  The dictionary keys are name-spaced values consisting of:
        self.tool_shed_url/repository_name/repository_owner/changeset_revision
        and the values are lists of repository_dependency tuples consisting of:
        ( self.tool_shed_url, repository_name, repository_owner, changeset_revision ).
        This method ensures that all required repositories to the nth degree are returned.
        """
        # Assume the current repository does not have repository dependencies defined for it.
        current_repository_key = None
        metadata = self.repository_metadata.metadata
        if metadata:
            # The value of self.tool_shed_url must include the port, but doesn't have to include
            # the protocol.
            if "repository_dependencies" in metadata:
                current_repository_key = self.get_key_for_repository_changeset_revision()
                repository_dependencies_dict = metadata["repository_dependencies"]
                if not self.all_repository_dependencies:
                    self.initialize_all_repository_dependencies(current_repository_key, repository_dependencies_dict)
                # Handle the repository dependencies defined in the current repository, if any, and populate
                # the various repository dependency objects for this round of processing.
                current_repository_key_rd_dicts = self.populate_repository_dependency_objects_for_processing(
                    current_repository_key, repository_dependencies_dict
                )
        if current_repository_key:
            if current_repository_key_rd_dicts:
                # There should be only a single current_repository_key_rd_dict in this list.
                current_repository_key_rd_dict = current_repository_key_rd_dicts[0]
                # Handle circular repository dependencies.
                if not self.in_circular_repository_dependencies(current_repository_key_rd_dict):
                    if current_repository_key in self.all_repository_dependencies:
                        self.handle_current_repository_dependency(current_repository_key)
                elif self.key_rd_dicts_to_be_processed:
                    self.handle_next_repository_dependency()
            elif self.key_rd_dicts_to_be_processed:
                self.handle_next_repository_dependency()
        elif self.key_rd_dicts_to_be_processed:
            self.handle_next_repository_dependency()
        self.all_repository_dependencies = self.prune_invalid_repository_dependencies(self.all_repository_dependencies)
        return self.all_repository_dependencies

    def get_repository_dependency_as_key(self, repository_dependency):
        (
            tool_shed,
            name,
            owner,
            changeset_revision,
            prior_installation_required,
            only_if_compiling_contained_td,
        ) = common_util.parse_repository_dependency_tuple(repository_dependency)
        return container_util.generate_repository_dependencies_key_for_repository(
            tool_shed, name, owner, changeset_revision, prior_installation_required, only_if_compiling_contained_td
        )

    def get_updated_changeset_revisions_for_repository_dependencies(self, key_rd_dicts):
        updated_key_rd_dicts = []
        for key_rd_dict in key_rd_dicts:
            key = next(iter(key_rd_dict))
            repository_dependency = key_rd_dict[key]
            (
                rd_toolshed,
                rd_name,
                rd_owner,
                rd_changeset_revision,
                rd_prior_installation_required,
                rd_only_if_compiling_contained_td,
            ) = common_util.parse_repository_dependency_tuple(repository_dependency)
            if suc.tool_shed_is_this_tool_shed(rd_toolshed):
                repository = tool_shed.util.repository_util.get_repository_by_name_and_owner(
                    self.app, rd_name, rd_owner
                )
                if repository:
                    repository_id = self.app.security.encode_id(repository.id)
                    repository_metadata = metadata_util.get_repository_metadata_by_repository_id_changeset_revision(
                        self.app, repository_id, rd_changeset_revision
                    )
                    if repository_metadata:
                        # The repository changeset_revision is installable, so no updates are available.
                        new_key_rd_dict = {}
                        new_key_rd_dict[key] = repository_dependency
                        updated_key_rd_dicts.append(key_rd_dict)
                    else:
                        # The repository changeset_revision is no longer installable, so see if there's been an update.
                        changeset_revision = metadata_util.get_next_downloadable_changeset_revision(
                            self.app, repository, rd_changeset_revision
                        )
                        if changeset_revision != rd_changeset_revision:
                            repository_metadata = (
                                metadata_util.get_repository_metadata_by_repository_id_changeset_revision(
                                    self.app, repository_id, changeset_revision
                                )
                            )
                        if repository_metadata:
                            new_key_rd_dict = {}
                            new_key_rd_dict[key] = [
                                rd_toolshed,
                                rd_name,
                                rd_owner,
                                repository_metadata.changeset_revision,
                                rd_prior_installation_required,
                                rd_only_if_compiling_contained_td,
                            ]
                            # We have the updated changeset revision.
                            updated_key_rd_dicts.append(new_key_rd_dict)
                        else:
                            repository_components_tuple = container_util.get_components_from_key(key)
                            components_list = tool_shed.util.repository_util.extract_components_from_tuple(
                                repository_components_tuple
                            )
                            (
                                toolshed,
                                repository_name,
                                repository_owner,
                                repository_changeset_revision,
                            ) = components_list[0:4]
                            # For backward compatibility to the 12/20/12 Galaxy release.
                            if len(components_list) in (4, 5):
                                rd_only_if_compiling_contained_td = "False"
                            message = (
                                "The revision %s defined for repository %s owned by %s is invalid, so repository "
                                % (str(rd_changeset_revision), str(rd_name), str(rd_owner))
                            )
                            message += f"dependencies defined for repository {repository_name} will be ignored."
                            log.debug(message)
                else:
                    repository_components_tuple = container_util.get_components_from_key(key)
                    components_list = tool_shed.util.repository_util.extract_components_from_tuple(
                        repository_components_tuple
                    )
                    toolshed, repository_name, repository_owner, repository_changeset_revision = components_list[0:4]
                    message = f"The revision {rd_changeset_revision} defined for repository {rd_name} owned by {rd_owner} is invalid, "
                    message += f"so repository dependencies defined for repository {repository_name} will be ignored."
                    log.debug(message)
        return updated_key_rd_dicts

    def handle_circular_repository_dependency(self, repository_key, repository_dependency):
        all_repository_dependencies_root_key = self.all_repository_dependencies["root_key"]
        repository_dependency_as_key = self.get_repository_dependency_as_key(repository_dependency)
        self.update_circular_repository_dependencies(
            repository_key, repository_dependency, self.all_repository_dependencies[repository_dependency_as_key]
        )
        if all_repository_dependencies_root_key != repository_dependency_as_key:
            self.all_repository_dependencies[repository_key] = [repository_dependency]

    def handle_current_repository_dependency(self, current_repository_key):
        current_repository_key_rd_dicts = []
        for rd in self.all_repository_dependencies[current_repository_key]:
            rd_copy = [str(item) for item in rd]
            new_key_rd_dict = {}
            new_key_rd_dict[current_repository_key] = rd_copy
            current_repository_key_rd_dicts.append(new_key_rd_dict)
        if current_repository_key_rd_dicts:
            self.handle_key_rd_dicts_for_repository(current_repository_key, current_repository_key_rd_dicts)
            return self.get_repository_dependencies_for_changeset_revision()

    def handle_key_rd_dicts_for_repository(self, current_repository_key, repository_key_rd_dicts):
        key_rd_dict = repository_key_rd_dicts.pop(0)
        repository_dependency = key_rd_dict[current_repository_key]
        (
            toolshed,
            name,
            owner,
            changeset_revision,
            prior_installation_required,
            only_if_compiling_contained_td,
        ) = common_util.parse_repository_dependency_tuple(repository_dependency)
        if suc.tool_shed_is_this_tool_shed(toolshed):
            required_repository = tool_shed.util.repository_util.get_repository_by_name_and_owner(self.app, name, owner)
            self.repository = required_repository
            repository_id = self.app.security.encode_id(required_repository.id)
            required_repository_metadata = metadata_util.get_repository_metadata_by_repository_id_changeset_revision(
                self.app, repository_id, changeset_revision
            )
            self.repository_metadata = required_repository_metadata
            if required_repository_metadata:
                # The required_repository_metadata changeset_revision is installable.
                required_metadata = required_repository_metadata.metadata
                if required_metadata:
                    for current_repository_key_rd_dict in repository_key_rd_dicts:
                        if not self.in_key_rd_dicts(current_repository_key_rd_dict, self.key_rd_dicts_to_be_processed):
                            # Add the current repository_dependency into self.key_rd_dicts_to_be_processed.
                            self.key_rd_dicts_to_be_processed.append(current_repository_key_rd_dict)
            if not self.in_key_rd_dicts(key_rd_dict, self.handled_key_rd_dicts):
                # Add the current repository_dependency into self.handled_key_rd_dicts.
                self.handled_key_rd_dicts.append(key_rd_dict)
            if self.in_key_rd_dicts(key_rd_dict, self.key_rd_dicts_to_be_processed):
                # Remove the current repository from self.key_rd_dicts_to_be_processed.
                self.key_rd_dicts_to_be_processed = self.remove_from_key_rd_dicts(
                    key_rd_dict, self.key_rd_dicts_to_be_processed
                )
        else:
            # The repository is in a different tool shed, so build an url and send a request.
            error_message = "Repository dependencies are currently supported only within the same Tool Shed.  "
            error_message += "Ignoring repository dependency definition for tool shed "
            error_message += f"{toolshed}, name {name}, owner {owner}, changeset revision {changeset_revision}"
            log.debug(error_message)

    def handle_next_repository_dependency(self):
        next_repository_key_rd_dict = self.key_rd_dicts_to_be_processed.pop(0)
        next_repository_key_rd_dicts = [next_repository_key_rd_dict]
        next_repository_key = next(iter(next_repository_key_rd_dict))
        self.handle_key_rd_dicts_for_repository(next_repository_key, next_repository_key_rd_dicts)
        return self.get_repository_dependencies_for_changeset_revision()

    def in_all_repository_dependencies(self, repository_key, repository_dependency):
        """
        Return True if { repository_key : repository_dependency } is in self.all_repository_dependencies.
        """
        for key, val in self.all_repository_dependencies.items():
            if key != repository_key:
                continue
            if repository_dependency in val:
                return True
        return False

    def in_circular_repository_dependencies(self, repository_key_rd_dict):
        """
        Return True if any combination of a circular dependency tuple is the key : value pair defined
        in the received repository_key_rd_dict.  This means that each circular dependency tuple is converted
        into the key : value pair for comparison.
        """
        for tup in self.circular_repository_dependencies:
            rd_0, rd_1 = tup
            rd_0_as_key = self.get_repository_dependency_as_key(rd_0)
            rd_1_as_key = self.get_repository_dependency_as_key(rd_1)
            if rd_0_as_key in repository_key_rd_dict and repository_key_rd_dict[rd_0_as_key] == rd_1:
                return True
            if rd_1_as_key in repository_key_rd_dict and repository_key_rd_dict[rd_1_as_key] == rd_0:
                return True
        return False

    def in_key_rd_dicts(self, key_rd_dict, key_rd_dicts):
        """Return True if key_rd_dict is contained in the list of key_rd_dicts."""
        k = next(iter(key_rd_dict))
        v = key_rd_dict[k]
        for key_rd_dict in key_rd_dicts:
            for key, val in key_rd_dict.items():
                if key == k and val == v:
                    return True
        return False

    def initialize_all_repository_dependencies(self, current_repository_key, repository_dependencies_dict):
        """Initialize the self.all_repository_dependencies dictionary."""
        # It's safe to assume that current_repository_key in this case will have a value.
        self.all_repository_dependencies["root_key"] = current_repository_key
        self.all_repository_dependencies[current_repository_key] = []
        # Store the value of the 'description' key only once, the first time through this recursive method.
        description = repository_dependencies_dict.get("description", None)
        self.all_repository_dependencies["description"] = description

    def is_circular_repository_dependency(self, repository_key, repository_dependency):
        """
        Return True if the received repository_dependency is a key in self.all_repository_dependencies
        whose list of repository dependencies includes the received repository_key.
        """
        repository_dependency_as_key = self.get_repository_dependency_as_key(repository_dependency)
        repository_key_as_repository_dependency = repository_key.split(container_util.STRSEP)
        for key, val in self.all_repository_dependencies.items():
            if key != repository_dependency_as_key:
                continue
            if repository_key_as_repository_dependency in val:
                return True
        return False

    def populate_repository_dependency_objects_for_processing(
        self, current_repository_key, repository_dependencies_dict
    ):
        """
        The process that discovers all repository dependencies for a specified repository's changeset
        revision uses this method to populate the following items for the current processing loop:
        filtered_current_repository_key_rd_dicts, self.key_rd_dicts_to_be_processed,
        self.handled_key_rd_dicts, self.all_repository_dependencies.  Each processing loop may discover
        more repository dependencies, so this method is repeatedly called until all repository
        dependencies have been discovered.
        """
        current_repository_key_rd_dicts = []
        filtered_current_repository_key_rd_dicts = []
        for rd_tup in repository_dependencies_dict["repository_dependencies"]:
            new_key_rd_dict = {}
            new_key_rd_dict[current_repository_key] = rd_tup
            current_repository_key_rd_dicts.append(new_key_rd_dict)
        if current_repository_key_rd_dicts and current_repository_key:
            # Remove all repository dependencies that point to a revision within its own repository.
            current_repository_key_rd_dicts = self.remove_repository_dependency_reference_to_self(
                current_repository_key_rd_dicts
            )
        current_repository_key_rd_dicts = self.get_updated_changeset_revisions_for_repository_dependencies(
            current_repository_key_rd_dicts
        )
        for key_rd_dict in current_repository_key_rd_dicts:
            # Filter out repository dependencies that are required only if compiling the dependent
            # repository's tool dependency.
            # TODO: this temporary work-around should be removed when the underlying framework
            # support for handling only_if_compiling_contained_td-flagged repositories is completed.
            key_rd_dict = self.filter_only_if_compiling_contained_td(key_rd_dict)
            if key_rd_dict:
                is_circular = False
                in_handled_key_rd_dicts = self.in_key_rd_dicts(key_rd_dict, self.handled_key_rd_dicts)
                in_key_rd_dicts_to_be_processed = self.in_key_rd_dicts(key_rd_dict, self.key_rd_dicts_to_be_processed)
                if not in_handled_key_rd_dicts and not in_key_rd_dicts_to_be_processed:
                    filtered_current_repository_key_rd_dicts.append(key_rd_dict)
                    repository_dependency = key_rd_dict[current_repository_key]
                    if current_repository_key in self.all_repository_dependencies:
                        # Add all repository dependencies for the current repository into its entry
                        # in self.all_repository_dependencies.
                        all_repository_dependencies_val = self.all_repository_dependencies[current_repository_key]
                        if repository_dependency not in all_repository_dependencies_val:
                            all_repository_dependencies_val.append(repository_dependency)
                            self.all_repository_dependencies[current_repository_key] = all_repository_dependencies_val
                    elif not self.in_all_repository_dependencies(current_repository_key, repository_dependency):
                        # Handle circular repository dependencies.
                        if self.is_circular_repository_dependency(current_repository_key, repository_dependency):
                            is_circular = True
                            self.handle_circular_repository_dependency(current_repository_key, repository_dependency)
                        else:
                            self.all_repository_dependencies[current_repository_key] = [repository_dependency]
                    if not is_circular and self.can_add_to_key_rd_dicts(key_rd_dict, self.key_rd_dicts_to_be_processed):
                        new_key_rd_dict = {}
                        new_key_rd_dict[current_repository_key] = repository_dependency
                        self.key_rd_dicts_to_be_processed.append(new_key_rd_dict)
        return filtered_current_repository_key_rd_dicts

    def prune_invalid_repository_dependencies(self, repository_dependencies):
        """
        Eliminate all invalid entries in the received repository_dependencies dictionary.  An entry
        is invalid if the value_list of the key/value pair is empty.  This occurs when an invalid
        combination of tool shed, name , owner, changeset_revision is used and a repository_metadata
        record is not found.
        """
        valid_repository_dependencies = {}
        description = repository_dependencies.get("description", None)
        root_key = repository_dependencies.get("root_key", None)
        if root_key is None:
            return valid_repository_dependencies
        for key, value in repository_dependencies.items():
            if key in ["description", "root_key"]:
                continue
            if value:
                valid_repository_dependencies[key] = value
        if valid_repository_dependencies:
            valid_repository_dependencies["description"] = description
            valid_repository_dependencies["root_key"] = root_key
        return valid_repository_dependencies

    def remove_from_key_rd_dicts(self, key_rd_dict, key_rd_dicts):
        """Eliminate the key_rd_dict from the list of key_rd_dicts if it is contained in the list."""
        k = next(iter(key_rd_dict))
        v = key_rd_dict[k]
        clean_key_rd_dicts = []
        for krd_dict in key_rd_dicts:
            key = next(iter(krd_dict))
            val = krd_dict[key]
            if key == k and val == v:
                continue
            clean_key_rd_dicts.append(krd_dict)
        return clean_key_rd_dicts

    def remove_repository_dependency_reference_to_self(self, key_rd_dicts):
        """Remove all repository dependencies that point to a revision within its own repository."""
        clean_key_rd_dicts = []
        key = next(iter(key_rd_dicts[0]))
        repository_tup = key.split(container_util.STRSEP)
        (
            rd_toolshed,
            rd_name,
            rd_owner,
            rd_changeset_revision,
            rd_prior_installation_required,
            rd_only_if_compiling_contained_td,
        ) = common_util.parse_repository_dependency_tuple(repository_tup)
        cleaned_rd_toolshed = common_util.remove_protocol_from_tool_shed_url(rd_toolshed)
        for key_rd_dict in key_rd_dicts:
            k = next(iter(key_rd_dict))
            repository_dependency = key_rd_dict[k]
            (
                toolshed,
                name,
                owner,
                changeset_revision,
                prior_installation_required,
                only_if_compiling_contained_td,
            ) = common_util.parse_repository_dependency_tuple(repository_dependency)
            cleaned_toolshed = common_util.remove_protocol_from_tool_shed_url(toolshed)
            if cleaned_rd_toolshed == cleaned_toolshed and rd_name == name and rd_owner == owner:
                debug_msg = f"Removing repository dependency for repository {name} owned by {owner} "
                debug_msg += "since it refers to a revision within itself."
                log.debug(debug_msg)
            else:
                new_key_rd_dict = {}
                new_key_rd_dict[key] = repository_dependency
                clean_key_rd_dicts.append(new_key_rd_dict)
        return clean_key_rd_dicts

    def update_circular_repository_dependencies(self, repository_key, repository_dependency, repository_dependencies):
        repository_key_as_repository_dependency = repository_key.split(container_util.STRSEP)
        if repository_key_as_repository_dependency in repository_dependencies:
            found = False
            for tup in self.circular_repository_dependencies:
                if repository_dependency in tup and repository_key_as_repository_dependency in tup:
                    # The circular dependency has already been included.
                    found = True
            if not found:
                new_circular_tup = [repository_dependency, repository_key_as_repository_dependency]
                self.circular_repository_dependencies.append(new_circular_tup)
