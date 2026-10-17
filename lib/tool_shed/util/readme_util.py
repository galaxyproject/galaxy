import logging
import os
from typing import (
    Any,
    TYPE_CHECKING,
)

from galaxy import web
from galaxy.tool_shed.util import basic_util
from galaxy.tool_shed.util.hg_util import get_file_data_from_manifest
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
    image_changeset_revision = None if use_disk_files else changeset_revision
    for relative_path_to_readme_file in metadata["readme_files"]:
        readme_file_name = os.path.split(relative_path_to_readme_file)[1]
        if use_disk_files:
            text = _read_readme_from_disk(relative_path_to_readme_file)
        else:
            # Metadata paths are prefixed with the repository's location on disk.
            path_in_repository = os.path.relpath(relative_path_to_readme_file, repository.repo_path())
            text = _read_readme_from_manifest(repository, changeset_revision, path_in_repository)
        if text:
            readme_files_dict[readme_file_name] = _render_repository_readme(
                app, encoded_repository_id, image_changeset_revision, readme_file_name, text
            )
    return readme_files_dict


def _read_readme_from_disk(relative_path_to_readme_file: str) -> str | None:
    try:
        with open(os.path.abspath(relative_path_to_readme_file), encoding="utf-8") as f:
            return f.read()
    except Exception:
        log.exception("Error reading README file '%s' from disk", relative_path_to_readme_file)
        return None


def _read_readme_from_manifest(repository: "Repository", changeset_revision: str, readme_path: str) -> str | None:
    try:
        data = get_file_data_from_manifest(readme_path, repository.hg_repo, changeset_revision)
    except Exception:
        log.exception("Error reading README file '%s' from repository manifest", readme_path)
        return None
    if data is None:
        return None
    # Translate newlines as reading the file from disk in text mode does.
    return unicodify(data).replace("\r\n", "\n").replace("\r", "\n")


def _render_repository_readme(
    app: "ToolShedApp",
    encoded_repository_id: str,
    image_changeset_revision: str | None,
    readme_file_name: str,
    text: str,
) -> str:
    text = basic_util.size_string(text)
    if ".. image:: " in text:
        # Point relative image paths at the repository's image route.
        text = set_image_paths(
            app, text, encoded_repository_id=encoded_repository_id, changeset_revision=image_changeset_revision
        )
    return render_readme(readme_file_name, text)
