import logging
import re

from galaxy import util
from galaxy.tool_shed.util import repository_util
from galaxy.util.tool_shed import common_util

log = logging.getLogger(__name__)

MAX_CONTENT_SIZE = 1048576
DATATYPES_CONFIG_FILENAME = "datatypes_conf.xml"
REPOSITORY_DATA_MANAGER_CONFIG_FILENAME = "data_manager_conf.xml"


def can_eliminate_repository_dependency(metadata_dict, tool_shed_url, name, owner):
    """
    Determine if the relationship between a repository_dependency record
    associated with a tool_shed_repository record on the Galaxy side
    can be eliminated.
    """
    rd_dict = metadata_dict.get("repository_dependencies", {})
    rd_tups = rd_dict.get("repository_dependencies", [])
    for rd_tup in rd_tups:
        tsu, n, o, none1, none2, none3 = common_util.parse_repository_dependency_tuple(rd_tup)
        if tsu == tool_shed_url and n == name and o == owner:
            # The repository dependency is current, so keep it.
            return False
    return True


def clean_dependency_relationships(trans, metadata_dict, tool_shed_repository, tool_shed_url):
    """
    Repositories of type tool_dependency_definition allow for defining a
    package dependency at some point in the change log and then removing the
    dependency later in the change log.  This function keeps the dependency
    relationships on the Galaxy side current by deleting database records
    that defined the now-broken relationships.
    """
    for rrda in tool_shed_repository.required_repositories:
        rd = rrda.repository_dependency
        r = rd.repository
        if can_eliminate_repository_dependency(metadata_dict, tool_shed_url, r.name, r.owner):
            message = "Repository dependency %s by owner %s is not required by repository %s, owner %s, "
            message += "removing from list of repository dependencies."
            log.debug(message % (r.name, r.owner, tool_shed_repository.name, tool_shed_repository.owner))
            session = trans.install_model.context
            session.delete(rrda)
            session.commit()


def generate_tool_guid(repository_clone_url, tool):
    """
    Generate a guid for the installed tool.  It is critical that this guid matches the guid for
    the tool in the Galaxy tool shed from which it is being installed.  The form of the guid is
    <tool shed host>/repos/<repository owner>/<repository name>/<tool id>/<tool version>
    """
    tmp_url = common_util.remove_protocol_and_user_from_clone_url(repository_clone_url)
    return f"{tmp_url}/{tool.id}/{tool.version}"


def get_ctx_rev(app, tool_shed_url, name, owner, changeset_revision):
    """
    Send a request to the tool shed to retrieve the ctx_rev for a repository defined by the
    combination of a name, owner and changeset revision.
    """
    tool_shed_url = common_util.get_tool_shed_url_from_tool_shed_registry(app, tool_shed_url)
    params = dict(name=name, owner=owner, changeset_revision=changeset_revision)
    pathspec = ["repository", "get_ctx_rev"]
    ctx_rev = util.url_get(
        tool_shed_url, auth=app.tool_shed_registry.url_auth(tool_shed_url), pathspec=pathspec, params=params
    )
    return ctx_rev


def get_next_prior_import_or_install_required_dict_entry(prior_required_dict, processed_tsr_ids):
    """
    This method is used in the Tool Shed when exporting a repository and its dependencies, and in Galaxy
    when a repository and its dependencies are being installed.  The order in which the prior_required_dict
    is processed is critical in order to ensure that the ultimate repository import or installation order is
    correctly defined.  This method determines the next key / value pair from the received prior_required_dict
    that should be processed.
    """
    # Return the first key / value pair that is not yet processed and whose value is an empty list.
    for key, value in prior_required_dict.items():
        if key in processed_tsr_ids:
            continue
        if not value:
            return key
    # Return the first key / value pair that is not yet processed and whose ids in value are all included
    # in processed_tsr_ids.
    for key, value in prior_required_dict.items():
        if key in processed_tsr_ids:
            continue
        all_contained = True
        for required_repository_id in value:
            if required_repository_id not in processed_tsr_ids:
                all_contained = False
                break
        if all_contained:
            return key
    # Return the first key / value pair that is not yet processed.  Hopefully this is all that is necessary
    # at this point.
    for key in prior_required_dict.keys():
        if key in processed_tsr_ids:
            continue
        return key


def get_tool_panel_config_tool_path_install_dir(app, repository):
    """
    Return shed-related tool panel config, the tool_path configured in it, and the relative path to
    the directory where the repository is installed.  This method assumes all repository tools are
    defined in a single shed-related tool panel config.
    """
    tool_shed = common_util.remove_port_from_tool_shed_url(str(repository.tool_shed))
    relative_install_dir = (
        f"{tool_shed}/repos/{repository.owner}/{repository.name}/{repository.installed_changeset_revision}"
    )
    # Get the relative tool installation paths from each of the shed tool configs.
    shed_config_dict = repository.get_shed_config_dict(app)
    shed_tool_conf = shed_config_dict["config_filename"]
    tool_path = shed_config_dict["tool_path"]
    return shed_tool_conf, tool_path, relative_install_dir


def get_user(app, id):
    """Get a user from the database by id."""
    sa_session = app.model.session
    return sa_session.query(app.model.User).get(app.security.decode_id(id))


def have_shed_tool_conf_for_install(app):
    return bool(app.toolbox.dynamic_confs(include_migrated_tool_conf=False))


def set_image_paths(app, text, encoded_repository_id=None, tool_shed_repository=None, tool_id=None, tool_version=None):
    """
    Handle tool help image display for tools that are contained in repositories in
    the tool shed or installed into Galaxy as well as image display in repository
    README files.  This method will determine the location of the image file and
    return the path to it that will enable the caller to open the file.
    """
    if text:
        if repository_util.is_tool_shed_client(app) and encoded_repository_id:
            route_to_images = f"admin_toolshed/static/images/{encoded_repository_id}"
        elif encoded_repository_id:
            # We're in the tool shed.
            route_to_images = f"/repository/static/images/{encoded_repository_id}"
        elif tool_shed_repository and tool_id and tool_version:
            route_to_images = f"shed_tool_static/{tool_shed_repository.tool_shed}/{tool_shed_repository.owner}/{tool_shed_repository.name}/{tool_id}/{tool_version}"
        else:
            raise Exception(
                "encoded_repository_id or tool_shed_repository and tool_id and tool_version must be provided"
            )
        # We used to require $PATH_TO_IMAGES and ${static_path}, but
        # we now eliminate it if it's used.
        text = text.replace("$PATH_TO_IMAGES", "")
        text = text.replace("${static_path}", "")
        # Use regex to instantiate routes into the defined image paths, but replace
        # paths that start with neither http:// nor https://, which will allow for
        # settings like .. images:: http_files/images/help.png
        for match in re.findall(".. image:: (?!http)/?(.+)", text):
            text = text.replace(match, match.replace("/", "%2F"))
        text = re.sub(r"\.\. image:: (?!https?://)/?(.+)", rf".. image:: {route_to_images}/\1", text)
    return text


__all__ = (
    "can_eliminate_repository_dependency",
    "clean_dependency_relationships",
    "DATATYPES_CONFIG_FILENAME",
    "generate_tool_guid",
    "get_ctx_rev",
    "get_next_prior_import_or_install_required_dict_entry",
    "get_tool_panel_config_tool_path_install_dir",
    "get_user",
    "have_shed_tool_conf_for_install",
    "set_image_paths",
)
