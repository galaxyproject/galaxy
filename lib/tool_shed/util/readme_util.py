import logging
import os
from typing import (
    Any,
    TYPE_CHECKING,
)

from galaxy import web
from galaxy.tool_shed.util import basic_util
from galaxy.tool_shed.util.hg_util import get_ctx_file_path_from_manifest
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
    html = rst_to_html(text)
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
) -> dict[str, str]:
    """
    Return a dictionary of readme file name <-> rendered HTML for all readme files defined in the received metadata.
    README files of the latest downloadable revision are read from disk, older revisions from the repository manifest.
    """
    readme_files_dict: dict[str, str] = {}
    if not metadata or "readme_files" not in metadata:
        return readme_files_dict
    encoded_repository_id = app.security.encode_id(repository.id)
    use_disk_files = changeset_revision == get_latest_downloadable_changeset_revision(app, repository)
    for relative_path_to_readme_file in metadata["readme_files"]:
        readme_file_name = os.path.split(relative_path_to_readme_file)[1]
        if use_disk_files:
            text = _read_readme_from_disk(relative_path_to_readme_file)
        else:
            text = _read_readme_from_manifest(repository, changeset_revision, readme_file_name)
        if text:
            readme_files_dict[readme_file_name] = _render_repository_readme(
                app, encoded_repository_id, readme_file_name, text
            )
    return readme_files_dict


def _read_readme_from_disk(relative_path_to_readme_file: str) -> str | None:
    try:
        with open(os.path.abspath(relative_path_to_readme_file), encoding="utf-8") as f:
            return f.read()
    except Exception:
        log.exception("Error reading README file '%s' from disk", relative_path_to_readme_file)
        return None


def _read_readme_from_manifest(repository: "Repository", changeset_revision: str, readme_file_name: str) -> str | None:
    # The README may have last changed in an earlier changeset, so search back from changeset_revision.
    manifest_ctx, ctx_file = get_ctx_file_path_from_manifest(readme_file_name, repository.hg_repo, changeset_revision)
    if manifest_ctx is None:
        return None
    try:
        data: bytes = manifest_ctx[ctx_file].data()
    except LookupError:
        # The last change to the README deleted it.
        return None
    except Exception:
        log.exception("Error reading README file '%s' from repository manifest", readme_file_name)
        return None
    return unicodify(data)


def _render_repository_readme(app: "ToolShedApp", encoded_repository_id: str, readme_file_name: str, text: str) -> str:
    text = basic_util.size_string(text)
    if ".. image:: " in text:
        # Point relative image paths at the repository's image route.
        try:
            text = set_image_paths(app, text, encoded_repository_id=encoded_repository_id)
        except Exception:
            log.exception("Error setting image paths in README file '%s'", readme_file_name)
    return render_readme(readme_file_name, text)
