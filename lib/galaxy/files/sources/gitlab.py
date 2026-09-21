import functools
import ipaddress
from collections.abc import Iterator
from contextlib import contextmanager
from typing import (
    cast,
    Literal,
)
from urllib.parse import (
    ParseResult,
    urlparse,
)

from galaxy.exceptions import (
    AuthenticationRequired,
    ConfigDoesNotAllowException,
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
from galaxy.files.uris import validate_non_local
from galaxy.util.config_templates import TemplateExpansion

try:
    from arcfs.fs import GitLabARCFileSystem
except ImportError:
    GitLabARCFileSystem = None

# arcfs' separator between a project path and the path inside it: ``group/project:-:assays/x.csv``.
# Galaxy keeps it, since the project boundary cannot be recovered from a plain path, but adds a "/"
# after it so an entry's name is its last segment and a project's path a prefix of the paths in it.
ROOT_MARKER = ":-:"

Operation = Literal["listing", "reading", "writing to"]


class GitLabFileSourceTemplateConfiguration(FsspecBaseFileSourceTemplateConfiguration):
    base_url: str | TemplateExpansion
    token: str | TemplateExpansion | None = None


class GitLabFileSourceConfiguration(FsspecBaseFileSourceConfiguration):
    base_url: str
    token: str | None = None


class GitLabFilesSource(FsspecFilesSource[GitLabFileSourceTemplateConfiguration, GitLabFileSourceConfiguration]):
    """File source for the projects of a GitLab instance, backed by ``arcfs-fsspec``.

    Projects reachable with the configured credentials are the top-level directories, with their
    repository trees below them. Everything is read from the default branch; exports commit to it.

    Known limitations:

    - Entries carry no size, timestamp or hash; GitLab's tree API does not return them.
    - Search is a substring match over at most ``MAX_ITEMS_LIMIT`` entries.
    - The root listing pages by offset over a list ordered by last activity, so a window assembled
      from several pages can repeat one project and miss another.
    - An anonymous listing cannot page very deep; a token lifts GitLab's cap.
    """

    plugin_type = "gitlab"

    required_module = WritableGitLabFileSystem
    required_package = "arcfs-fsspec"

    template_config_class = GitLabFileSourceTemplateConfiguration
    resolved_config_class = GitLabFileSourceConfiguration

    # What a listing of the top level holds, for messages that have to name it.
    entity_name = "project"

    @staticmethod
    def _token_scope_for(operation: Operation) -> str:
        """Classic-token scope the refused operation needs, not the widest this source might use."""
        return "api" if operation == "writing to" else "read_api"

    def _open_fs(
        self,
        context: FilesSourceRuntimeContext[GitLabFileSourceConfiguration],
        cache_options: CacheOptionsDictType,
    ) -> "GitLabARCFileSystem":
        # Off the class, so a subclass swaps the filesystem - and with it write behaviour - by
        # setting ``required_module`` alone.
        filesystem_class = self.required_module
        if filesystem_class is None:
            raise self.required_package_exception

        config = context.config
        # Without a scheme aiohttp fails with an exception carrying only the URL, which reached the
        # form as "Reason: gitlab.com/api/v4/projects". Stripped: pasted whitespace reaches the host.
        base_url = config.base_url.strip()
        parts = urlparse(base_url)
        if parts.scheme not in ("http", "https") or not parts.netloc:
            raise RequestParameterInvalidException(
                f"'{config.base_url}' is not a usable address for {self.label}. It needs a "
                "protocol and a host, as in 'https://gitlab.com'."
            )
        self._refuse_a_private_address(base_url, parts)
        return cast(
            "GitLabARCFileSystem",
            filesystem_class(
                base_url=base_url,
                token=config.token,
                asynchronous=False,
                # Else fsspec caches one instance per (base_url, token) process-wide, and closing
                # it after one request tears down the aiohttp session others are still reading.
                skip_instance_cache=True,
                **cache_options,
            ),
        )

    def _refuse_a_private_address(self, base_url: str, parts: "ParseResult") -> None:
        """Refuse a base_url that points into the network Galaxy itself sits on.

        ``validate_non_local`` cannot take the raw URL: it tests the scheme with a case-sensitive
        ``startswith`` (``HTTP://127.0.0.1`` passes unchecked) and resolves IPv6 literals with their
        brackets attached. yarl normalises both before aiohttp connects, so the host comes from
        ``urlparse`` and a literal is checked against the allowlist directly.
        """
        allowlist = self._file_sources_config.fetch_url_allowlist or []
        host = parts.hostname or ""
        try:
            literal = ipaddress.ip_address(host)
        except ValueError:
            literal = None

        if literal is None:
            try:
                validate_non_local(f"{parts.scheme}://{host}", allowlist)
            except RequestParameterInvalidException:
                # Does not resolve, so Galaxy cannot reach it either; the connection error that
                # follows says more than "could not verify" would.
                pass
            except ConfigDoesNotAllowException as e:
                # The shared message names neither the address nor the file source, and a
                # self-hosted GitLab on a private network lands here routinely.
                raise ConfigDoesNotAllowException(self._private_address_message(base_url)) from e
            return

        if not literal.is_private:
            return
        for allowlisted in allowlist:
            if isinstance(allowlisted, (ipaddress.IPv4Network, ipaddress.IPv6Network)):
                if literal in allowlisted:
                    return
            elif literal == allowlisted:
                return
        raise ConfigDoesNotAllowException(self._private_address_message(base_url))

    def _private_address_message(self, base_url: str) -> str:
        return (
            f"{self.label} is configured with '{base_url}', which is an address on this server's "
            "own network. Galaxy does not fetch from those unless an administrator lists them in "
            "fetch_url_allowlist. A self-hosted GitLab usually needs that entry; list the host "
            "itself rather than a whole private range, since the allowlist applies to every URL "
            "Galaxy fetches."
        )

    @contextmanager
    def _filesystem(
        self, context: FilesSourceRuntimeContext[GitLabFileSourceConfiguration], operation: Operation, path: str
    ) -> Iterator[tuple["GitLabARCFileSystem", GitLabFileSourceConfiguration]]:
        """Open a filesystem for one operation and translate arcfs failures into Galaxy exceptions.

        ``_open_fs`` builds a fresh instance per operation, so closing it here affects nothing else.
        """
        description = f"{operation} file source path {path}"
        base_url_for_errors = (context.config.base_url or "").strip()
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
            raise AuthenticationRequired(self._credentials_message(description, e)) from e
        except FileNotFoundError as e:
            if e.filename is not None:
                # A local path Galaxy staged, not anything in GitLab; a server-side path must not
                # reach the user.
                raise MessageException(f"Problem {description}. Reason: {e.strerror or e}") from e
            # Empty project, removed project, or one invisible to these credentials. arcfs' own text
            # is a project id, a bare path or a sentence depending on the raise site, so it is dropped.
            raise ObjectNotFound(
                f"Problem {description}. Not found in {self.label}. The {self.entity_name} may be empty, may "
                "have been removed, or may not be visible with your credentials."
            ) from e
        except Exception as e:
            # aiohttp's ClientResponseError is not an OSError, so HTTP failures arrive here. Matching
            # on the status keeps this importable without aiohttp, which galaxy-files does not need.
            if isinstance(e, OSError) and getattr(e, "filename", None):
                # Any other local failure; keeps a server-side staging path away from the user.
                raise MessageException(f"Problem {description}. Reason: {e.strerror or type(e).__name__}") from e
            status = getattr(e, "status", None)
            # The exception stringifies to the internal API URL, so it cannot stand in for the phrase.
            reason_phrase = getattr(e, "message", None)
            detail = f"{status} {reason_phrase}" if reason_phrase else str(status)
            if status == 401:
                raise AuthenticationRequired(self._credentials_message(description, detail)) from e
            if status == 403:
                # GitLab names the cause in the body, but aiohttp keeps only status and reason
                # phrase, so both a missing scope and a missing permission have to be offered.
                raise AuthenticationRequired(
                    self._credentials_message(
                        description,
                        f"{detail}. A classic token may lack the '{self._token_scope_for(operation)}' "
                        "scope; a fine-grained token may lack the permissions this operation needs"
                        + (self._push_refused_hint if operation == "writing to" else ""),
                    )
                ) from e
            if status == 200:
                # Answered, but not as an API: usually the address of a page the user copied.
                # aiohttp reports an undecodable mimetype, which says nothing about the field to fix.
                raise RequestParameterInvalidException(
                    f"'{base_url_for_errors}' answered, but not as a GitLab API. Use the address of "
                    f"the server itself, as in '{self._server_example}', rather than the address "
                    "of a page on it."
                ) from e
            if status == 400 and operation == "writing to":
                # GitLab refuses a commit it will not make and aiohttp drops the body saying which.
                # The likeliest cause is the one this source provokes: it sends the commit id the
                # file was read at, so a file changed since is refused rather than overwritten.
                raise MessageException(
                    f"Problem {description}. {self.label} refused the write. "
                    f"{self._write_refused_hint}{self._said(reason_phrase)}"
                ) from e
            if status == 413:
                raise MessageException(
                    f"Problem {description}. The file is larger than {self.label} accepts in a "
                    f"single request.{self._large_file_remedy}"
                ) from e
            if status == 405 and operation == "listing":
                # GitLab caps how far an offset listing may page and answers 405 past it, with no
                # hint that paging was the objection. Enforced only for unauthenticated requests.
                raise MessageException(
                    f"Problem {description}. {self.label} would not list any further into the "
                    "catalogue. Some GitLab servers cap how deep an anonymous listing can page. "
                    f"Search for the {self.entity_name} by name, or add an access token for this file source."
                ) from e
            if status == 429:
                raise MessageException(
                    f"Problem {description}. {self.label} is rate limiting these requests"
                    f"{self._retry_hint(e)}. Please wait and try again."
                ) from e
            # Anything below still must not render the exception itself: for an aiohttp error that
            # is the internal API URL and its query string.
            if type(e).__name__ == "FSTimeoutError":
                # fsspec rewrites asyncio.TimeoutError to this, and it stringifies to nothing.
                raise MessageException(
                    f"Problem {description}. {self.label} did not answer in time. A large file on "
                    f"a slow connection can exhaust the request budget.{self._timeout_hint}"
                ) from e
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

        Built from arcfs' ``list_page``, which reports the total that Galaxy's pagination needs.
        ``fs.ls()`` reports none and fetches the whole catalogue, so it is only used for recursion.
        """
        self._require_a_project(path)
        if recursive:
            if self._is_source_root(path):
                # fsspec would rewrite "/" to arcfs' root marker, which arcfs resolves as a project
                # with an empty path, calling GitLab's project *list* endpoint and failing obscurely.
                raise RequestParameterInvalidException(
                    "Listing every project recursively is not supported. Please list a single project instead."
                )
            with self._filesystem(context, "listing", path) as (fs, config):
                entries, total = self._list_recursive(fs, self._to_filesystem_path(path, config), config)
                if query:
                    # Else the filter is silently dropped and the whole subtree comes back looking
                    # like a result set.
                    entries = self._filter_by_name(entries, query)
                    total = len(entries)
                return self._apply_pagination(entries, limit, offset), total

        with self._filesystem(context, "listing", path) as (fs, config):
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
                # The window has to start where the caller asked: reading from zero and slicing
                # afterwards returned nothing for any offset past MAX_ITEMS_LIMIT.
                start = offset or 0
                entries, total = self._read_window(fs, fs_path, config, start, MAX_ITEMS_LIMIT, write_intent)
                if total > start + len(entries):
                    self._on_listing_exceeded()
                return entries, total

            if limit > MAX_ITEMS_LIMIT:
                # Nothing bounds the caller's limit, and arcfs fetches as many pages as it takes.
                self._on_listing_exceeded()
            return self._read_window(fs, fs_path, config, offset or 0, min(limit, MAX_ITEMS_LIMIT), write_intent)

    # Overridden by ``ARCFilesSource``, whose exports are not plain commits.

    _push_refused_hint = (
        ". A token with every scope is still refused by a protected branch, which GitLab applies "
        "to the default branch"
    )

    _write_refused_hint = (
        "GitLab protects the default branch by default, so the token may not be allowed to push "
        "to it; otherwise the file may have changed since Galaxy read it, in which case exporting "
        "again will pick up the new version."
    )

    _timeout_hint = " Nothing was committed unless the server had already processed the request."

    _server_example = "https://gitlab.com"

    _large_file_remedy = " An ARC file source, which uploads through Git LFS instead, can carry it."

    def _require_a_project(self, path: str) -> None:
        """Refuse a listing whose path carries the marker but names no project.

        ``:-:`` with nothing before it asks GitLab for the project named "", which is the endpoint
        that lists every project; the result was then indexed as one project's payload.
        """
        project, marker, _ = path.partition(ROOT_MARKER)
        if marker and not self._names_something(project):
            raise RequestParameterInvalidException(
                f"'{path}' does not name {self._article} {self.entity_name}. A path is "
                f"'group/project{ROOT_MARKER}' with an optional folder after it. Use the file "
                "browser rather than editing the path by hand."
            )

    def _require_a_file_inside(self, path: str, what: str) -> None:
        """Refuse a path that does not name a file inside a project.

        A missing marker makes the backend build the whole project index; nothing after the marker
        repeats the path back. ``what`` is "Exports" or "Imports".
        """
        project, marker, inside = path.partition(ROOT_MARKER)
        if marker and self._names_something(project) and self._names_something(inside):
            return
        raise RequestParameterInvalidException(
            f"{what} have to name a file inside {self._article} {self.entity_name}, in the form "
            f"the file browser produces (group/project{ROOT_MARKER}/folder/file). The top level "
            f"of this file source lists the {self.entity_name}s themselves and cannot hold files."
        )

    def _list_recursive(
        self, fs: "GitLabARCFileSystem", path: str, config: GitLabFileSourceConfiguration
    ) -> tuple[list[AnyRemoteEntry], int]:
        """Recurse with failures raised rather than omitted.

        Its own stack rather than ``fs.walk(on_error="raise")``: fsspec passes only ``**kwargs`` when
        it recurses and ``on_error`` is named, so every level below the first reverts to ``"omit"``
        (fsspec 2026.7.0). ``walk`` swallows ``OSError``, which aiohttp's connection errors subclass,
        so a reset partway through returned the remaining folders empty with HTTP 200.
        """
        entries: list[AnyRemoteEntry] = []
        to_entry = functools.partial(self._info_to_entry, config=config)
        pending = [path]
        while pending:
            listing = cast(list[dict], fs.ls(pending.pop(), detail=True))
            entries.extend(map(to_entry, listing))
            if len(entries) >= MAX_ITEMS_LIMIT:
                self._on_listing_exceeded()
                break
            pending.extend(info["name"] for info in listing if info.get("type") == "directory")
        return entries, len(entries)

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

        ``membership`` narrows a root listing to projects the credentials belong to, for when Galaxy
        asks where a file may be written: every visible project can be read, only some pushed to.
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
        """Drop the "/" that ``_adapt_entry_path`` inserted, back to the path arcfs expects."""
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
        self._require_a_file_inside(source_path, "Imports")
        with self._filesystem(context, "reading", source_path) as (fs, config):
            fs.get_file(self._to_filesystem_path(source_path, config), native_path)

    def _write_from(
        self,
        target_path: str,
        native_path: str,
        context: FilesSourceRuntimeContext[GitLabFileSourceConfiguration],
    ):
        self._require_a_file_inside(target_path, "Exports")
        # A push is never anonymous. Caught here because the server's 401 reads as "your token is
        # wrong" when there is no token to be wrong.
        if not (context.config.token or "").strip():
            raise AuthenticationRequired(
                f"{self.label} has no access token, and exporting to {self.entity_name} requires "
                f"one: a push is never anonymous. Add a token with write access, or turn off "
                f"writing to browse and import only."
            )
        with self._filesystem(context, "writing to", target_path) as (fs, config):
            fs.put_file(native_path, self._to_filesystem_path(target_path, config))

    @staticmethod
    def _names_something(part: str) -> bool:
        """Whether one side of the marker names anything the backend will keep.

        The backend strips whitespace and slashes, so a guard reading the raw text lets through
        targets it then fails on. ``..`` is refused rather than normalized away: nothing between
        here and the API call bounds a target to inside the repository.
        """
        segments = [segment for segment in part.strip().strip("/").split("/") if segment not in ("", ".")]
        return bool(segments) and ".." not in segments

    @staticmethod
    def _said(reason: str | None) -> str:
        """Append GitLab's own words, dropping the reason phrases that only repeat the status."""
        if not reason or reason.strip().lower() in ("bad request", "forbidden", "unauthorized"):
            return ""
        return f" GitLab said: {reason}"

    @property
    def _article(self) -> str:
        return "an" if self.entity_name[0].upper() in "AEIOU" else "a"

    def _info_to_entry(self, info: dict, config: GitLabFileSourceConfiguration) -> AnyRemoteEntry:
        entry = super()._info_to_entry(info, config)
        entry.name = self._display_name(entry.path)
        return entry

    def _credentials_message(self, description: str, reason: object) -> str:
        # Callers' text may already end in a period, so the trim lives here, not at each call site.
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
        """Whether the path names the source itself rather than anything inside it.

        arcfs resolves a path of blanks to the root listing, so "/ /" has to count as the root or a
        recursive listing of it walks every project on the instance. Slashes go first: whitespace
        can sit between them, and bare ``str.strip`` covers all of Unicode's.
        """
        return not path.replace("/", "").strip()

    @staticmethod
    def _filter_by_name(entries: list[AnyRemoteEntry], query: str) -> list[AnyRemoteEntry]:
        needle = query.casefold()
        return [entry for entry in entries if needle in entry.name.casefold()]

    @staticmethod
    def _display_name(path: str) -> str:
        """Return the name to show for an arcfs path, hiding the ``:-:`` marker.

        Projects keep their full ``group/project`` path, so equal names in different groups stay
        distinguishable; entries inside one show only their last component.
        """
        project, marker, inside = path.partition(ROOT_MARKER)
        if not marker:
            return path.rstrip("/").rsplit("/", 1)[-1] or path
        inside = inside.strip("/")
        if not inside:
            return project
        return inside.rsplit("/", 1)[-1]


__all__ = ("GitLabFilesSource",)
