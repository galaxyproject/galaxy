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

    A DataHUB is a GitLab instance and an ARC is one of its projects, so browsing, searching and
    importing are inherited unchanged from :class:`GitLabFilesSource`. What this class adds is the
    way ARCs take new data.

    An export does not land on the project's default branch. The backend writes the file to the
    instance's Git LFS store, commits a pointer to it on a ``run_results-*`` branch, adds a
    ``.gitattributes`` entry for it, and opens a merge request, so an exported file appears in a
    listing only once a maintainer has merged that request. The branch is named from a hash of the
    access token rather than from the export, so everything written with one token shares a branch
    and the merge request the first export opened. A token shared between users therefore collects
    all of their exports together.

    That is how ARCs are meant to receive data, and it is why this class exists: a plain GitLab
    user exporting a file expects a commit, not a merge request. Only the filesystem differs, so
    that is the whole of what this class sets.
    """

    plugin_type = "arc"

    #: An ARC is a GitLab project, so only the filesystem differs: this one exports through
    #: Git LFS and a merge request where the GitLab source commits to the branch.
    required_module = GitLabARCFileSystem

    entity_name = "ARC"

    #: This source is the alternative the GitLab one points at, so it has none of its own.
    _large_file_remedy = ""

    #: An ARC export commits to a generated branch and opens a merge request, so it never pushes
    #: to the default branch and the protection that stops a project export does not apply.
    _push_refused_hint = (
        ". Exporting to an ARC also needs permission to create a branch, commit to it and open a "
        "merge request, which a read-only role does not carry"
    )

    #: The ARC path sends no commit id, so a refused write is not a stale-read that re-exporting
    #: resolves. The likeliest cause is that the export branch already carries this file name, and
    #: that branch outlives the merge request, so re-exporting fails the same way.
    _write_refused_hint = (
        "The export branch may already hold a file by this name. Exports made with the same token "
        "share one branch, and it is not removed when its merge request is merged, so export under "
        "another name or delete that branch."
    )

    #: Not a single commit but a branch, an LFS upload, two commits and a merge request, so a
    #: timeout part way through leaves some of it behind.
    _timeout_hint = (
        " An ARC export is several steps, so a branch, an uploaded file or a merge request may "
        "have been created before it stopped."
    )

    #: An ARC lives on a DataHUB, and gitlab.com is not one.
    _server_example = "https://git.nfdi4plants.org"

    template_config_class = ARCFileSourceTemplateConfiguration
    resolved_config_class = ARCFileSourceConfiguration


__all__ = ("ARCFilesSource",)
