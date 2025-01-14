import logging
import os
import shutil

from sqlalchemy import and_

from galaxy import util

log = logging.getLogger(__name__)


def get_tool_dependency(app, id):
    """Get a tool_dependency from the database via id"""
    return app.install_model.context.query(app.install_model.ToolDependency).get(app.security.decode_id(id))


def get_tool_dependency_by_name_type_repository(app, repository, name, type):
    context = app.install_model.context
    return (
        context.query(app.install_model.ToolDependency)
        .filter(
            and_(
                app.install_model.ToolDependency.table.c.tool_shed_repository_id == repository.id,
                app.install_model.ToolDependency.table.c.name == name,
                app.install_model.ToolDependency.table.c.type == type,
            )
        )
        .first()
    )


def get_tool_dependency_by_name_version_type(app, name, version, type):
    context = app.install_model.context
    return (
        context.query(app.install_model.ToolDependency)
        .filter(
            and_(
                app.install_model.ToolDependency.table.c.name == name,
                app.install_model.ToolDependency.table.c.version == version,
                app.install_model.ToolDependency.table.c.type == type,
            )
        )
        .first()
    )


def get_tool_dependency_by_name_version_type_repository(app, repository, name, version, type):
    context = app.install_model.context
    return (
        context.query(app.install_model.ToolDependency)
        .filter(
            and_(
                app.install_model.ToolDependency.table.c.tool_shed_repository_id == repository.id,
                app.install_model.ToolDependency.table.c.name == name,
                app.install_model.ToolDependency.table.c.version == version,
                app.install_model.ToolDependency.table.c.type == type,
            )
        )
        .first()
    )


def get_tool_dependency_ids(as_string=False, **kwd):
    tool_dependency_id = kwd.get("tool_dependency_id", None)
    if "tool_dependency_ids" in kwd:
        tool_dependency_ids = util.listify(kwd["tool_dependency_ids"])
    elif "id" in kwd:
        tool_dependency_ids = util.listify(kwd["id"])
    elif "inst_td_ids" in kwd:
        tool_dependency_ids = util.listify(kwd["inst_td_ids"])
    elif "uninstalled_tool_dependency_ids" in kwd:
        tool_dependency_ids = util.listify(kwd["uninstalled_tool_dependency_ids"])
    else:
        tool_dependency_ids = []
    if tool_dependency_id and tool_dependency_id not in tool_dependency_ids:
        tool_dependency_ids.append(tool_dependency_id)
    if as_string:
        return ",".join(tool_dependency_ids)
    return tool_dependency_ids


def parse_package_elem(package_elem, platform_info_dict=None, include_after_install_actions=True):
    """
    Parse a <package> element within a tool dependency definition and return a list of action tuples.
    This method is called when setting metadata on a repository that includes a tool_dependencies.xml
    file or when installing a repository that includes a tool_dependencies.xml file.  If installing,
    platform_info_dict must be a valid dictionary and include_after_install_actions must be True.
    """
    # The actions_elem_tuples list contains <actions> tag sets (possibly inside of an <actions_group>
    # tag set) to be processed in the order they are defined in the tool_dependencies.xml file.
    actions_elem_tuples = []
    # The tag sets that will go into the actions_elem_list are those that install a compiled binary if
    # the architecture and operating system match its defined attributes.  If compiled binary is not
    # installed, the first <actions> tag set [following those that have the os and architecture attributes]
    # that does not have os or architecture attributes will be processed.  This tag set must contain the
    # recipe for downloading and compiling source.
    actions_elem_list = []
    for elem in package_elem:
        if elem.tag == "actions":
            # We have an <actions> tag that should not be matched against a specific combination of
            # architecture and operating system.
            in_actions_group = False
            actions_elem_tuples.append((in_actions_group, elem))
        elif elem.tag == "actions_group":
            # We have an actions_group element, and its child <actions> elements should therefore be compared
            # with the current operating system
            # and processor architecture.
            in_actions_group = True
            # Record the number of <actions> elements so we can filter out any <action> elements that precede
            # <actions> elements.
            actions_elem_count = len(elem.findall("actions"))
            # Record the number of <actions> elements that have both architecture and os specified, in order
            # to filter out any platform-independent <actions> elements that come before platform-specific
            # <actions> elements.
            platform_actions_elements = []
            for actions_elem in elem.findall("actions"):
                if actions_elem.get("architecture") is not None and actions_elem.get("os") is not None:
                    platform_actions_elements.append(actions_elem)
            platform_actions_element_count = len(platform_actions_elements)
            platform_actions_elements_processed = 0
            actions_elems_processed = 0
            # The tag sets that will go into the after_install_actions list are <action> tags instead of <actions>
            # tags.  These will be processed only if they are at the very end of the <actions_group> tag set (after
            # all <actions> tag sets). See below for details.
            after_install_actions = []
            # Inspect the <actions_group> element and build the actions_elem_list and the after_install_actions list.
            for child_element in elem:
                if child_element.tag == "actions":
                    actions_elems_processed += 1
                    system = child_element.get("os")
                    architecture = child_element.get("architecture")
                    # Skip <actions> tags that have only one of architecture or os specified, in order for the
                    # count in platform_actions_elements_processed to remain accurate.
                    if (system and not architecture) or (architecture and not system):
                        log.debug("Error: Both architecture and os attributes must be specified in an <actions> tag.")
                        continue
                    # Since we are inside an <actions_group> tag set, compare it with our current platform information
                    # and filter the <actions> tag sets that don't match. Require both the os and architecture attributes
                    # to be defined in order to find a match.
                    if system and architecture:
                        platform_actions_elements_processed += 1
                        # If either the os or architecture do not match the platform, this <actions> tag will not be
                        # considered a match. Skip it and proceed with checking the next one.
                        if platform_info_dict:
                            if platform_info_dict["os"] != system or platform_info_dict["architecture"] != architecture:
                                continue
                        else:
                            # We must not be installing a repository into Galaxy, so determining if we can install a
                            # binary is not necessary.
                            continue
                    else:
                        # <actions> tags without both os and architecture attributes are only allowed to be specified
                        # after platform-specific <actions> tags. If we find a platform-independent <actions> tag before
                        # all platform-specific <actions> tags have been processed.
                        if platform_actions_elements_processed < platform_actions_element_count:
                            debug_msg = "Error: <actions> tags without os and architecture attributes are only allowed "
                            debug_msg += (
                                "after all <actions> tags with os and architecture attributes have been defined.  "
                            )
                            debug_msg += (
                                "Skipping the <actions> tag set with no os or architecture attributes that has "
                            )
                            debug_msg += (
                                "been defined between two <actions> tag sets that have these attributes defined.  "
                            )
                            log.debug(debug_msg)
                            continue
                    # If we reach this point, it means one of two things: 1) The system and architecture attributes are
                    # not defined in this <actions> tag, or 2) The system and architecture attributes are defined, and
                    # they are an exact match for the current platform. Append the child element to the list of elements
                    # to process.
                    actions_elem_list.append(child_element)
                elif child_element.tag == "action":
                    # Any <action> tags within an <actions_group> tag set must come after all <actions> tags.
                    if actions_elems_processed == actions_elem_count:
                        # If all <actions> elements have been processed, then this <action> element can be appended to the
                        # list of actions to execute within this group.
                        after_install_actions.append(child_element)
                    else:
                        # If any <actions> elements remain to be processed, then log a message stating that <action>
                        # elements are not allowed to precede any <actions> elements within an <actions_group> tag set.
                        debug_msg = (
                            "Error: <action> tags are only allowed at the end of an <actions_group> tag set after "
                        )
                        debug_msg += f"all <actions> tags.  Skipping <{child_element.tag}> element with type {child_element.get('type', 'unknown')}."
                        log.debug(debug_msg)
                        continue
            if platform_info_dict is None and not include_after_install_actions:
                # We must be setting metadata on a repository.
                if len(actions_elem_list) >= 1:
                    actions_elem_tuples.append((in_actions_group, actions_elem_list[0]))
                else:
                    # We are processing a recipe that contains only an <actions_group> tag set for installing a binary,
                    # but does not include an additional recipe for installing and compiling from source.
                    actions_elem_tuples.append((in_actions_group, []))
            elif platform_info_dict is not None and include_after_install_actions:
                # We must be installing a repository.
                if after_install_actions:
                    actions_elem_list.extend(after_install_actions)
                actions_elem_tuples.append((in_actions_group, actions_elem_list))
        else:
            # Skip any element that is not <actions> or <actions_group> - this will skip comments, <repository> tags
            # and <readme> tags.
            in_actions_group = False
            continue
    return actions_elem_tuples


def remove_tool_dependency(app, tool_dependency):
    """The received tool_dependency must be in an error state."""
    context = app.install_model.context
    dependency_install_dir = tool_dependency.installation_directory(app)
    removed, error_message = remove_tool_dependency_installation_directory(dependency_install_dir)
    if removed:
        tool_dependency.status = app.install_model.ToolDependency.installation_status.UNINSTALLED
        tool_dependency.error_message = None
        context.add(tool_dependency)
        context.commit()
        # Since the received tool_dependency is in an error state, nothing will need to be changed in any
        # of the in-memory dictionaries in the installed_repository_manager because changing the state from
        # error to uninstalled requires no in-memory changes..
    return removed, error_message


def remove_tool_dependency_installation_directory(dependency_install_dir):
    if os.path.exists(dependency_install_dir):
        try:
            shutil.rmtree(dependency_install_dir)
            removed = True
            error_message = ""
            log.debug(f"Removed tool dependency installation directory: {dependency_install_dir}")
        except Exception as e:
            removed = False
            error_message = f"Error removing tool dependency installation directory {dependency_install_dir}: {e}"
            log.warning(error_message)
    else:
        removed = True
        error_message = ""
    return removed, error_message
