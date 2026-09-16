from galaxy.exceptions import RequestParameterInvalidException
from galaxy.files.models import FilesSourceRuntimeContext
from galaxy.files.sources.gitlab import (
    GitLabFileSourceConfiguration,
    GitLabFileSourceTemplateConfiguration,
    GitLabFilesSource,
    ROOT_MARKER,
)


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

    That is how ARCs are meant to receive data, and it is why writing lives here rather than on the
    GitLab source: a plain GitLab user exporting a file expects a commit, not a merge request.
    """

    plugin_type = "arc"

    template_config_class = ARCFileSourceTemplateConfiguration
    resolved_config_class = ARCFileSourceConfiguration

    def get_writable(self) -> bool:
        """Writable when configured so, unlike the read-only GitLab source this extends."""
        return self.writable

    def _write_from(
        self,
        target_path: str,
        native_path: str,
        context: FilesSourceRuntimeContext[GitLabFileSourceConfiguration],
    ):
        if ROOT_MARKER not in target_path:
            # Without the marker the backend cannot tell where the project path ends, so it probes
            # prefixes and then builds the whole project index before failing, with a message about
            # a missing ARC for a path that never named one.
            raise RequestParameterInvalidException(
                "Exports have to name a file inside an ARC, in the form the file browser produces "
                f"(group/project{ROOT_MARKER}/folder/file). The top level of this file source lists "
                "the ARCs themselves and cannot hold files."
            )
        with self._filesystem(context, f"writing to file source path {target_path}") as (fs, config):
            fs.put_file(native_path, self._to_filesystem_path(target_path, config))


__all__ = ("ARCFilesSource",)
