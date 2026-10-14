import logging
import os
from typing import (
    Any,
    TYPE_CHECKING,
)

from galaxy import web
from galaxy.tool_shed.util import basic_util
from galaxy.tool_shed.util.hg_util import (
    get_changectx_for_changeset,
    get_file_context_from_ctx,
)
from galaxy.tool_shed.util.shed_util_common import set_image_paths
from galaxy.util import (
    rst_to_html,
    unicodify,
)
from galaxy.util.sanitize_html import sanitize_html
from tool_shed.util.metadata_util import get_latest_downloadable_changeset_revision

if TYPE_CHECKING:
    from tool_shed.structured_app import ToolShedApp
    from tool_shed.webapp.model import Repository

log = logging.getLogger(__name__)


def render_readme(readme_file_name: str, text: str) -> str:
    """Render repository-owner supplied README text as HTML that is safe to display."""
    if not readme_file_name.endswith(".rst"):
        return basic_util.to_html_string(text)
    html = unicodify(rst_to_html(text))
    # Substitute the legacy placeholders literally - README text must never be evaluated as a template.
    if "${static_path}" in html:
        html = html.replace("${static_path}", web.url_for("/static"))
    if "${host_url}" in html:
        html = html.replace("${host_url}", web.url_for("/", qualified=True))
    return sanitize_html(html)


def build_readme_files_dict(
    app: "ToolShedApp",
    repository: "Repository",
    changeset_revision: str,
    metadata: dict[str, Any],
    tool_path: str | None = None,
) -> dict[str, str]:
    """
    Return a dictionary of valid readme file name <-> readme file content pairs for all readme files defined in the received metadata.  Since the
    received changeset_revision (which is associated with the received metadata) may not be the latest installable changeset revision, the README
    file contents may not be available on disk.  This method is used by both Galaxy and the Tool Shed.
    """
    if app.name == "galaxy":
        can_use_disk_files = True
    else:
        latest_downloadable_changeset_revision = get_latest_downloadable_changeset_revision(app, repository)
        can_use_disk_files = changeset_revision == latest_downloadable_changeset_revision
    readme_files_dict: dict[str, str] = {}
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
                                text_of_reasonable_length = set_image_paths(
                                    app,
                                    text_of_reasonable_length,
                                    encoded_repository_id=app.security.encode_id(repository.id),
                                )
                            except Exception:
                                log.exception(
                                    "Exception in build_readme_files_dict, so images may not be properly displayed"
                                )
                        readme_files_dict[readme_file_name] = render_readme(readme_file_name, text_of_reasonable_length)
                else:
                    # We must be in the tool shed and have an old changeset_revision, so we need to retrieve the file contents from the repository manifest.
                    repo = repository.hg_repo
                    ctx = get_changectx_for_changeset(repo, changeset_revision)
                    if ctx:
                        fctx = get_file_context_from_ctx(ctx, readme_file_name)
                        if fctx is not None and fctx != "DELETED":
                            try:
                                text = unicodify(fctx.data())
                                readme_files_dict[readme_file_name] = render_readme(
                                    readme_file_name, basic_util.size_string(text)
                                )
                            except Exception:
                                log.exception(
                                    "Error reading README file '%s' from repository manifest",
                                    relative_path_to_readme_file,
                                )
    return readme_files_dict
