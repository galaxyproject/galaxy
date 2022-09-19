import json
import logging
import os

from mako.template import Template

import tool_shed.util.shed_util_common as suc
from galaxy import web
from galaxy.util import (
    rst_to_html,
    unicodify,
    url_get,
)
from tool_shed.util import (
    basic_util,
    common_util,
    hg_util,
    metadata_util,
    repository_util,
)

log = logging.getLogger(__name__)


def build_readme_files_dict(app, repository, changeset_revision, metadata, tool_path=None):
    """
    Return a dictionary of valid readme file name <-> readme file content pairs for all readme files defined in the received metadata.  Since the
    received changeset_revision (which is associated with the received metadata) may not be the latest installable changeset revision, the README
    file contents may not be available on disk.  This method is used by both Galaxy and the Tool Shed.
    """
    if app.name == "galaxy":
        can_use_disk_files = True
    else:
        latest_downloadable_changeset_revision = metadata_util.get_latest_downloadable_changeset_revision(
            app, repository
        )
        can_use_disk_files = changeset_revision == latest_downloadable_changeset_revision
    readme_files_dict = {}
    if metadata:
        if "readme_files" in metadata:
            for relative_path_to_readme_file in metadata["readme_files"]:
                readme_file_name = os.path.split(relative_path_to_readme_file)[1]
                if can_use_disk_files:
                    if tool_path:
                        full_path_to_readme_file = os.path.abspath(
                            os.path.join(tool_path, relative_path_to_readme_file)
                        )
                    else:
                        full_path_to_readme_file = os.path.abspath(relative_path_to_readme_file)
                    text = None
                    try:
                        with open(full_path_to_readme_file, encoding="utf-8") as f:
                            text = f.read()
                    except Exception:
                        log.exception("Error reading README file '%s' from disk", relative_path_to_readme_file)
                        text = None
                    if text:
                        text_of_reasonable_length = basic_util.size_string(text)
                        if text_of_reasonable_length.find(".. image:: ") >= 0:
                            # Handle image display for README files that are contained in repositories in the tool shed or installed into Galaxy.
                            try:
                                text_of_reasonable_length = suc.set_image_paths(
                                    app,
                                    text_of_reasonable_length,
                                    encoded_repository_id=app.security.encode_id(repository.id),
                                )
                            except Exception:
                                log.exception(
                                    "Exception in build_readme_files_dict, so images may not be properly displayed"
                                )
                        if readme_file_name.endswith(".rst"):
                            text_of_reasonable_length = Template(
                                rst_to_html(text_of_reasonable_length),
                                input_encoding="utf-8",
                                default_filters=["decode.utf8"],
                                encoding_errors="replace",
                            )
                            text_of_reasonable_length = text_of_reasonable_length.render(
                                static_path=web.url_for("/static"), host_url=web.url_for("/", qualified=True)
                            )
                            text_of_reasonable_length = unicodify(text_of_reasonable_length)
                        else:
                            text_of_reasonable_length = basic_util.to_html_string(text_of_reasonable_length)
                        readme_files_dict[readme_file_name] = text_of_reasonable_length
                else:
                    # We must be in the tool shed and have an old changeset_revision, so we need to retrieve the file contents from the repository manifest.
                    repo = repository.hg_repo
                    ctx = hg_util.get_changectx_for_changeset(repo, changeset_revision)
                    if ctx:
                        fctx = hg_util.get_file_context_from_ctx(ctx, readme_file_name)
                        if fctx and fctx not in ["DELETED"]:
                            try:
                                text = unicodify(fctx.data())
                                readme_files_dict[readme_file_name] = basic_util.size_string(text)
                            except Exception:
                                log.exception(
                                    "Error reading README file '%s' from repository manifest",
                                    relative_path_to_readme_file,
                                )
    return readme_files_dict


def get_readme_files_dict_for_display(app, tool_shed_url, repo_info_dict):
    """
    Return a dictionary of README files contained in the single repository being installed so they can be displayed on the tool panel section
    selection page.
    """
    name = next(iter(repo_info_dict))
    repo_info_tuple = repo_info_dict[name]
    (
        description,
        repository_clone_url,
        changeset_revision,
        ctx_rev,
        repository_owner,
        repository_dependencies,
        installed_td,
    ) = repository_util.get_repo_info_tuple_contents(repo_info_tuple)
    # Handle changing HTTP protocols over time.
    tool_shed_url = common_util.get_tool_shed_url_from_tool_shed_registry(app, tool_shed_url)
    params = dict(name=name, owner=repository_owner, changeset_revision=changeset_revision)
    pathspec = ["repository", "get_readme_files"]
    raw_text = url_get(
        tool_shed_url, auth=app.tool_shed_registry.url_auth(tool_shed_url), pathspec=pathspec, params=params
    )
    readme_files_dict = json.loads(raw_text)
    return readme_files_dict
