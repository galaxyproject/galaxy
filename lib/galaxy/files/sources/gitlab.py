from collections.abc import Iterator
from contextlib import contextmanager
from typing import cast

from galaxy.exceptions import (
    AuthenticationRequired,
    MessageException,
    ObjectNotFound,
    RequestParameterInvalidException,
)
from galaxy.files.models import (
    AnyRemoteEntry,
    FilesSourceRuntimeContext,
)
from galaxy.files.sources._fsspec import (
    CacheOptionsDictType,
    FsspecBaseFileSourceConfiguration,
    FsspecBaseFileSourceTemplateConfiguration,
    FsspecFilesSource,
    MAX_ITEMS_LIMIT,
)
from galaxy.files.sources.gitlab_fsspec import WritableGitLabFileSystem
from galaxy.util.config_templates import TemplateExpansion

try:
    from arcfs.fs import GitLabARCFileSystem
except ImportError:
    GitLabARCFileSystem = None

# arcfs separates the GitLab project path from the path inside the repository with this marker, e.g.
# ``group/project:-:assays/data.csv``. Galaxy paths keep the marker, because the project boundary
# cannot be recovered from a plain path without asking GitLab, but add a "/" after it so that the
# usual assumptions about "/"-separated paths hold: an entry's name is its last segment, and a
# project's path is a prefix of the paths of the entries inside it.
ROOT_MARKER = ":-:"


class GitLabFileSourceTemplateConfiguration(FsspecBaseFileSourceTemplateConfiguration):
    base_url: str | TemplateExpansion
    token: str | TemplateExpansion | None = None


class GitLabFileSourceConfiguration(FsspecBaseFileSourceConfiguration):
    base_url: str
    token: str | None = None


class GitLabFilesSource(FsspecFilesSource[GitLabFileSourceTemplateConfiguration, GitLabFileSourceConfiguration]):
    """File source for the projects of a GitLab instance.

    Backed by the ``arcfs-fsspec`` package, which exposes the GitLab projects reachable with the
    configured credentials as top-level directories, with their repository trees below them.

    Exports commit the file to the branch, which is what a GitLab user expects. ARCs take data
    another way, so ``ARCFilesSource`` opens a filesystem that does that instead.
    use, so writing lives in the ARC subclass rather than here. See ``ARCFilesSource``.

    Known limitations, all of them properties of the backend rather than choices made here:

    - Entries carry no size, timestamp or hash. GitLab's repository tree API does not return them,
      and asking per file would cost a request each.
    - Search reads at most ``MAX_ITEMS_LIMIT`` entries and filters them by name, so on a server
      with more projects than that, a match beyond the cap is not found. It is a plain substring
      match, so wildcards are matched literally. GitLab can search projects server side, but the
      backend does not expose that yet.
    - The root listing is paged by offset, newest project first, and a window wider than one
      GitLab page is assembled from several requests. A project created or removed while that is
      going on shifts the ones after it, so such a window can repeat one project and miss another.
    - A listing without credentials cannot page very deep. GitLab caps how far an offset listing
      may page and applies the cap only to unauthenticated requests, so a token removes it.
    """

    plugin_type = "gitlab"

    required_module = WritableGitLabFileSystem
    required_package = "arcfs-fsspec"

    template_config_class = GitLabFileSourceTemplateConfiguration
    resolved_config_class = GitLabFileSourceConfiguration

    #: What a listing of the top level holds, for messages that have to name it.
    entity_name = "project"

    @property
    def required_token_scope(self) -> str:
        """Classic-token scope a user needs for what this source is configured to do.

        Reading needs no more than ``read_api``; a source that also exports needs ``api``, and
        asking a browse-only user for the wider one contradicts this source's own template help.
        """
        return "api" if self.get_writable() else "read_api"

    def _open_fs(
        self,
        context: FilesSourceRuntimeContext[GitLabFileSourceConfiguration],
        cache_options: CacheOptionsDictType,
    ) -> "GitLabARCFileSystem":
        # Read the class off the source rather than naming it here, so a subclass opens a
        # different filesystem by setting ``required_module`` alone. Which one it is decides how a
        # write behaves, and that is the whole of the difference between an ARC and a project.
        filesystem_class = self.required_module
        if filesystem_class is None:
            raise self.required_package_exception

        config = context.config
        return cast(
            "GitLabARCFileSystem",
            filesystem_class(
                base_url=config.base_url,
                token=config.token,
                asynchronous=False,
                # Without this, fsspec caches one instance per (base_url, token) for the whole
                # process, so closing it at the end of one request would tear down the aiohttp
                # session that other requests are still reading from.
                skip_instance_cache=True,
                **cache_options,
            ),
        )

    @contextmanager
    def _filesystem(
        self, context: FilesSourceRuntimeContext[GitLabFileSourceConfiguration], description: str
    ) -> Iterator[tuple["GitLabARCFileSystem", GitLabFileSourceConfiguration]]:
        """Open a filesystem for one operation and translate arcfs failures into Galaxy exceptions.

        ``_open_fs`` builds a fresh instance per operation, so closing it here cannot affect anything
        else in flight. ``description`` completes the "Problem ..." message of unexpected failures,
        including the one raised when the package is missing.
        """
        fs = None
        try:
            fs = self._open_fs(context, self._get_cache_options(context.config))
            yield fs, context.config
        except MessageException:
            raise  # already an actionable Galaxy exception, don't wrap it again
        except PermissionError as e:
            if e.filename is not None:
                # Refused by the local filesystem, so the user's GitLab credentials are not the problem.
                raise MessageException(f"Problem {description}. Reason: {e.strerror or e}") from e
            # arcfs does not raise this for authentication today, but a future version might.
            raise AuthenticationRequired(self._credentials_message(description, e))
        except FileNotFoundError as e:
            if e.filename is not None:
                # A local path that Galaxy staged, not anything in GitLab. Saying the project is missing
                # would be wrong, and would put a server-side path in front of the user.
                raise MessageException(f"Problem {description}. Reason: {e.strerror or e}") from e
            # Raised for a project without any commit yet, for one that was removed, and for one that
            # is invisible to these credentials. arcfs' own text is a numeric project id, a bare
            # repo-internal path, or a whole sentence depending on the raise site, so none of it
            # reads correctly inside a sentence. ``description`` already names what was asked for.
            raise ObjectNotFound(
                f"Problem {description}. Not found in {self.label}. The project may be empty, may have "
                "been removed, or may not be visible with your credentials."
            ) from e
        except Exception as e:
            # aiohttp reports HTTP failures as ClientResponseError, which is not an OSError, so they
            # arrive here. Matching on the status keeps this module importable without aiohttp, which
            # the standalone galaxy-files package does not depend on.
            status = getattr(e, "status", None)
            # aiohttp leaves ``message`` empty when the server sends no reason phrase, and the
            # exception itself stringifies to the full internal API URL, so it cannot stand in.
            reason_phrase = getattr(e, "message", None)
            detail = f"{status} {reason_phrase}" if reason_phrase else str(status)
            if status == 401:
                # A missing, invalid, expired or revoked token.
                raise AuthenticationRequired(self._credentials_message(description, detail))
            if status == 403:
                # The token authenticated but is not allowed to do this. A classic token is missing
                # the "api" scope; a fine-grained one is missing the resource permission this call
                # needs. GitLab names which in the response body, but aiohttp keeps only the status
                # and reason phrase on the error, so both causes have to be offered here.
                raise AuthenticationRequired(
                    self._credentials_message(
                        description,
                        f"{detail}. A classic token may lack the '{self.required_token_scope}' "
                        "scope; a fine-grained token may lack the permissions this operation needs",
                    )
                )
            if status == 405 and description.startswith("listing"):
                # GitLab limits how far an offset listing may page and answers 405 once past it,
                # with no hint that paging is what it objected to. It enforces this only for
                # unauthenticated requests, so a token removes the limit entirely. The cap applies
                # to listings, and this handler is shared with reading and writing, so only a
                # listing gets this wording.
                raise MessageException(
                    f"Problem {description}. {self.label} would not list any further into the "
                    "catalogue. Some GitLab servers cap how deep an anonymous listing can page. "
                    "Search for the project by name, or add an access token for this file source."
                ) from e
            if status == 429:
                raise MessageException(
                    f"Problem {description}. {self.label} is rate limiting these requests"
                    f"{self._retry_hint(e)}. Please wait and try again."
                ) from e
            # Statuses outside the ladder above still must not render the exception itself: for an
            # aiohttp error that is the internal API URL and its query string. Errors with no text
            # at all would otherwise leave a bare "Reason: ".
            reason = detail if isinstance(status, int) else (str(e) or type(e).__name__)
            raise MessageException(f"Problem {description}. Reason: {reason}") from e
        finally:
            if fs is not None:
                fs.close()

    def _list(
        self,
        context: FilesSourceRuntimeContext[GitLabFileSourceConfiguration],
        path="/",
        recursive=False,
        write_intent: bool = False,
        limit: int | None = None,
        offset: int | None = None,
        query: str | None = None,
        sort_by: str | None = None,
    ) -> tuple[list[AnyRemoteEntry], int]:
        """List the projects of a GitLab instance, or the entries inside one.

        Listings are built from arcfs' ``list_page``, which paginates against GitLab and reports the
        total number of entries that Galaxy needs for its pagination controls. ``fs.ls()`` reports no
        total, and makes arcfs fetch and keep the whole project catalogue in one call, so it is only
        used for recursion inside a project.
        """
        if recursive:
            if self._is_source_root(path):
                # fsspec would rewrite "/" to arcfs' root marker, which arcfs resolves as a project
                # with an empty path, calling GitLab's project *list* endpoint and failing obscurely.
                raise RequestParameterInvalidException(
                    "Listing every project recursively is not supported. Please list a single project instead."
                )
            with self._filesystem(context, f"listing file source path {path}") as (fs, config):
                entries, total = self._list_recursive(fs, self._to_filesystem_path(path, config), config)
                if query:
                    # Without this the filter is silently dropped and the whole subtree comes back
                    # looking like a result set. The cap in ``_list_recursive`` applies first, so a
                    # match beyond it is still not found, exactly as on the non-recursive path.
                    entries = self._filter_by_name(entries, query)
                    total = len(entries)
                return self._apply_pagination(entries, limit, offset), total

        with self._filesystem(context, f"listing file source path {path}") as (fs, config):
            fs_path = self._to_filesystem_path(path, config)

            if query:
                # The generic implementation globs, which needs ``_info``; arcfs implements no
                # ``_info``, so globbing fails with a bare NotImplementedError.
                entries, total = self._read_window(fs, fs_path, config, 0, MAX_ITEMS_LIMIT, write_intent)
                if total > len(entries):
                    self._on_listing_exceeded()
                matched = self._filter_by_name(entries, query)
                return self._apply_pagination(matched, limit, offset), len(matched)

            if limit is None:
                entries, total = self._read_window(fs, fs_path, config, 0, MAX_ITEMS_LIMIT, write_intent)
                if total > len(entries):
                    self._on_listing_exceeded()
                return self._apply_pagination(entries, limit, offset), total

            if limit > MAX_ITEMS_LIMIT:
                # Nothing bounds the limit a caller may ask for, and arcfs will fetch as many
                # GitLab pages as it takes to fill it.
                self._on_listing_exceeded()
            return self._read_window(fs, fs_path, config, offset or 0, min(limit, MAX_ITEMS_LIMIT), write_intent)

    def _read_window(
        self,
        fs: "GitLabARCFileSystem",
        fs_path: str,
        config: GitLabFileSourceConfiguration,
        start: int,
        count: int,
        membership: bool = False,
    ) -> tuple[list[AnyRemoteEntry], int]:
        """Return up to ``count`` entries from ``start``.

        Since 0.1.11 arcfs serves any window from the GitLab pages that cover it, so this only
        has to convert what comes back. On a server that reports no total it returns a lower
        bound that grows as the caller pages, and zero for a window past the end.

        ``membership`` narrows a root listing to the projects the credentials belong to. It is
        used when Galaxy is asking where a file may be written, since every visible project can be
        read but only some can be pushed to. arcfs ignores it below the root.
        """
        infos, total = fs.list_page(fs_path, True, offset=start, limit=count, membership=membership)
        return [self._info_to_entry(info, config) for info in infos], total

    def _adapt_entry_path(self, filesystem_path: str, config: GitLabFileSourceConfiguration) -> str:
        """Insert a "/" after the marker, turning ``group/repo:-:file`` into ``group/repo:-:/file``."""
        project, marker, inside = filesystem_path.partition(ROOT_MARKER)
        if not marker:
            return filesystem_path
        return f"{project}{marker}/{inside.lstrip('/')}"

    def _to_filesystem_path(self, path: str, config: GitLabFileSourceConfiguration) -> str:
        """Drop the "/" that ``_adapt_entry_path`` inserted, back to the path arcfs expects.

        Paths recorded before that separator was introduced simply pass through unchanged.
        """
        project, marker, inside = path.partition(ROOT_MARKER)
        if not marker:
            return path
        return f"{project}{marker}{inside.lstrip('/')}"

    def _realize_to(
        self,
        source_path: str,
        native_path: str,
        context: FilesSourceRuntimeContext[GitLabFileSourceConfiguration],
    ):
        with self._filesystem(context, f"reading file source path {source_path}") as (fs, config):
            fs.get_file(self._to_filesystem_path(source_path, config), native_path)

    def _write_from(
        self,
        target_path: str,
        native_path: str,
        context: FilesSourceRuntimeContext[GitLabFileSourceConfiguration],
    ):
        project, marker, inside = target_path.partition(ROOT_MARKER)
        if not marker or not project.strip("/") or not inside.strip("/"):
            # Each of the three ways a target can fail to name a file inside a project reaches
            # the backend as its own obscure failure. Without the marker the backend cannot tell
            # where the project path ends, so it probes prefixes and then builds the whole
            # project index before failing, with a message about a missing project for a path
            # that never named one. With nothing after the marker the target is a project
            # itself, which is what a listing of the top level offers verbatim as a destination;
            # the backend refuses that with an IsADirectoryError carrying only the path again, so
            # the user is told their path failed because of their path. With nothing before the
            # marker the project path is empty, which the backend does not catch at all: it asks
            # GitLab for the project named "", reaching the endpoint that lists projects instead,
            # and then fails on the shape of the answer.
            raise RequestParameterInvalidException(
                f"Exports have to name a file inside {self._article} {self.entity_name}, in the "
                f"form the file browser produces (group/project{ROOT_MARKER}/folder/file). The "
                f"top level of this file source lists the {self.entity_name}s themselves and "
                "cannot hold files."
            )
        with self._filesystem(context, f"writing to file source path {target_path}") as (fs, config):
            fs.put_file(native_path, self._to_filesystem_path(target_path, config))

    @property
    def _article(self) -> str:
        return "an" if self.entity_name[0].upper() in "AEIOU" else "a"

    def _info_to_entry(self, info: dict, config: GitLabFileSourceConfiguration) -> AnyRemoteEntry:
        entry = super()._info_to_entry(info, config)
        entry.name = self._display_name(entry.path)
        return entry

    def _credentials_message(self, description: str, reason: object) -> str:
        # Callers pass arcfs', the OS' or aiohttp's own text, none of which is under Galaxy's
        # control and any of which may already end in a period. Trimming here rather than at each
        # call site is what keeps "scope.." from coming back the next time one is added, and
        # ``description`` is a parameter for that same reason rather than something each caller
        # prefixes. Every other branch of the ladder leads with "Problem ...", and a credentials
        # failure that left it out told the user their token was refused without saying which
        # project, path or operation it was refused for - a failed export read as a bare permission
        # complaint about nothing in particular.
        return (
            f"Problem {description}. Permission Denied. Reason: {str(reason).rstrip(' .')}. "
            f"Please check your credentials in your preferences for {self.label}."
        )

    @staticmethod
    def _retry_hint(error: object) -> str:
        """Turn GitLab's ``Retry-After`` into something worth telling the user."""
        headers = getattr(error, "headers", None) or {}
        try:
            retry_after = headers.get("Retry-After")
        except AttributeError:
            return ""
        return f" and asked us to wait {retry_after} seconds" if retry_after else ""

    @staticmethod
    def _is_source_root(path: str) -> bool:
        return not path.strip("/")

    @staticmethod
    def _filter_by_name(entries: list[AnyRemoteEntry], query: str) -> list[AnyRemoteEntry]:
        needle = query.casefold()
        return [entry for entry in entries if needle in entry.name.casefold()]

    @staticmethod
    def _display_name(path: str) -> str:
        """Return the name to show for an arcfs path, hiding the ``:-:`` marker.

        Projects (paths ending with the marker) keep their full ``group/project`` path so that
        equally named projects in different groups stay distinguishable; entries inside a project
        show only their last path component.
        """
        project, marker, inside = path.partition(ROOT_MARKER)
        if not marker:
            return path.rstrip("/").rsplit("/", 1)[-1] or path
        inside = inside.strip("/")
        if not inside:
            return project
        return inside.rsplit("/", 1)[-1]


__all__ = ("GitLabFilesSource",)
