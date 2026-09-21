from galaxy.files.sources.gitlab import (
    GitLabFileSourceConfiguration,
    GitLabFileSourceTemplateConfiguration,
    GitLabFilesSource,
)

try:
    from arcfs.fs import GitLabARCFileSystem
except ImportError:
    GitLabARCFileSystem = None  # type: ignore[assignment, misc, unused-ignore]


class ARCFileSourceTemplateConfiguration(GitLabFileSourceTemplateConfiguration):
    """Template configuration for the ARC file source."""


class ARCFileSourceConfiguration(GitLabFileSourceConfiguration):
    """Resolved configuration for the ARC file source."""


class ARCFilesSource(GitLabFilesSource):
    """File source for ARCs (Annotated Research Contexts) on a DataPLANT DataHUB.

    A DataHUB is a GitLab instance and an ARC one of its projects, so reading is inherited unchanged.
    Only writing differs: the file goes to Git LFS, a pointer is committed on a ``run_results-*``
    branch and a merge request is opened, so an export is visible only once a maintainer merges it.
    """

    plugin_type = "arc"

    required_module = GitLabARCFileSystem

    entity_name = "ARC"

    # These replace ``GitLabFilesSource``'s wording, which describes a plain commit: an ARC export
    # never touches the default branch, sends no commit id, and takes several steps. It is itself
    # the large-file alternative that source points at, so that remedy is empty here.

    _large_file_remedy = ""

    _push_refused_hint = (
        ". Exporting to an ARC also needs permission to create a branch, commit to it and open a "
        "merge request, which a read-only role does not carry"
    )

    _write_refused_hint = (
        "The export branch may already hold a file by this name. Exports made with the same token "
        "share one branch, and it is not removed when its merge request is merged, so export under "
        "another name or delete that branch."
    )

    _timeout_hint = (
        " An ARC export is several steps, so a branch, an uploaded file or a merge request may "
        "have been created before it stopped."
    )

    _server_example = "https://git.nfdi4plants.org"

    template_config_class = ARCFileSourceTemplateConfiguration
    resolved_config_class = ARCFileSourceConfiguration


__all__ = ("ARCFilesSource",)
