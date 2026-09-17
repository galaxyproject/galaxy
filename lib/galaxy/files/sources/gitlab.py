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

# arcfs separates the GitLab project path from the path inside the repository with this marker, e.g.
# ``group/project:-:assays/data.csv``. Galaxy paths keep the marker, because the project boundary
# cannot be recovered from a plain path without asking GitLab, but add a "/" after it so that the
# usual assumptions about "/"-separated paths hold: an entry's name is its last segment, and a
# project's path is a prefix of the paths of the entries inside it.
ROOT_MARKER = ":-:"

#: What the caller was doing, for the messages that name it and the two branches of the error
#: ladder that behave differently per operation. It reads as prose because it is spliced into
#: "Problem {operation} file source path ...", but the ladder compares the value rather than
#: parsing the sentence, so rewording a message cannot change which error a user gets.
Operation = Literal["listing", "reading", "writing to"]


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
    another way, so ``ARCFilesSource`` opens a filesystem that does that instead; the write path
    itself is shared, because both take the same paths and need the same guard.

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

    @staticmethod
    def _token_scope_for(operation: Operation) -> str:
        """Classic-token scope the refused operation needs, not the widest this source might.

        A writable source still serves users who only browse it, and a 403 on a listing that
        told them to mint a token with push rights on every project they can reach would be
        advice to over-privilege, contradicting this source's own template help.
        """
        return "api" if operation == "writing to" else "read_api"

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
        # A base_url with no scheme reaches aiohttp as a relative URL, which it refuses with an
        # exception carrying nothing but the URL it was handed. That surfaces to whoever filled in
        # the form as "Reason: gitlab.com/api/v4/projects", which names neither the problem nor the
        # field. Leaving out the protocol is the obvious thing to do, so it is worth saying so.
        # Stripped because a URL pasted from a browser or a wiki often carries whitespace, and
        # it survives into the hostname, where it becomes a connection failure naming a host
        # that looks exactly right.
        base_url = config.base_url.strip()
        parts = urlparse(base_url)
        if parts.scheme not in ("http", "https") or not parts.netloc:
            raise RequestParameterInvalidException(
                f"'{config.base_url}' is not a usable address for {self.label}. It needs a "
                "protocol and a host, as in 'https://gitlab.com'."
            )
        # The template exposes base_url as an ordinary variable, so a user creating their own
        # instance chooses which host Galaxy talks to and sends their token to. Without this a
        # personal file source pointed at a link-local or loopback address turns the server into
        # a probe for its own network, with the error ladder reporting what it found.
        self._refuse_a_private_address(base_url, parts)
        return cast(
            "GitLabARCFileSystem",
            filesystem_class(
                base_url=base_url,
                token=config.token,
                asynchronous=False,
                # Without this, fsspec caches one instance per (base_url, token) for the whole
                # process, so closing it at the end of one request would tear down the aiohttp
                # session that other requests are still reading from.
                skip_instance_cache=True,
                **cache_options,
            ),
        )

    def _refuse_a_private_address(self, base_url: str, parts: "ParseResult") -> None:
        """Refuse a base_url that points into the network Galaxy itself sits on.

        The template exposes base_url as an ordinary variable, so a user creating their own
        instance chooses which host Galaxy talks to and sends their token to. Without this a
        personal file source pointed at a loopback or link-local address turns the server into a
        probe for its own network, with the error ladder reporting what it found.

        ``validate_non_local`` is the shared check every such source uses, but it cannot be handed
        the raw URL here. It tests for a scheme with a case-sensitive ``startswith``, so an
        uppercase ``HTTP://127.0.0.1`` returns unchecked while the lowercase form is refused; and
        it resolves an IPv6 literal with its brackets still attached, which fails and is reported
        as an unresolvable host rather than as a private one. An address written either way would
        otherwise pass, because yarl normalises both before aiohttp connects.

        So the host is taken from ``urlparse``, which lowercases it and removes the brackets. A
        literal address needs no DNS and is checked directly against the same allowlist; anything
        else is a name, and goes to the shared check.

        Args:
            base_url: The address as configured, stripped, for the error message.
            parts: That address already parsed.

        Raises:
            ConfigDoesNotAllowException: If the address is private and not allowlisted.
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
                # A name that does not resolve. Galaxy cannot reach it either, so there is
                # nothing here to protect against, and the connection error that follows says
                # more than "could not verify" does.
                pass
            return

        if not literal.is_private:
            return
        for allowlisted in allowlist:
            if isinstance(allowlisted, (ipaddress.IPv4Network, ipaddress.IPv6Network)):
                if literal in allowlisted:
                    return
            elif literal == allowlisted:
                return
        raise ConfigDoesNotAllowException(f"'{base_url}' is not an address this server is allowed to reach.")

    @contextmanager
    def _filesystem(
        self, context: FilesSourceRuntimeContext[GitLabFileSourceConfiguration], operation: Operation, path: str
    ) -> Iterator[tuple["GitLabARCFileSystem", GitLabFileSourceConfiguration]]:
        """Open a filesystem for one operation and translate arcfs failures into Galaxy exceptions.

        ``_open_fs`` builds a fresh instance per operation, so closing it here cannot affect anything
        else in flight. ``operation`` says what the caller was doing: it completes the "Problem ..."
        message of unexpected failures, and the two branches that differ per operation compare it
        rather than reading the sentence it ends up in.
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
                # A local path that Galaxy staged, not anything in GitLab. Saying the project is missing
                # would be wrong, and would put a server-side path in front of the user.
                raise MessageException(f"Problem {description}. Reason: {e.strerror or e}") from e
            # Raised for a project without any commit yet, for one that was removed, and for one that
            # is invisible to these credentials. arcfs' own text is a numeric project id, a bare
            # repo-internal path, or a whole sentence depending on the raise site, so none of it
            # reads correctly inside a sentence. ``description`` already names what was asked for.
            raise ObjectNotFound(
                f"Problem {description}. Not found in {self.label}. The {self.entity_name} may be empty, may "
                "have been removed, or may not be visible with your credentials."
            ) from e
        except Exception as e:
            # aiohttp reports HTTP failures as ClientResponseError, which is not an OSError, so they
            # arrive here. Matching on the status keeps this module importable without aiohttp, which
            # the standalone galaxy-files package does not depend on.
            if isinstance(e, OSError) and getattr(e, "filename", None):
                # A local failure that is neither of the two named above: a directory where a file
                # was expected, a read error, a symlink loop. Those two branches exist to keep a
                # server-side staging path away from the user, and this keeps the rest of OSError
                # from going around them.
                raise MessageException(f"Problem {description}. Reason: {e.strerror or type(e).__name__}") from e
            status = getattr(e, "status", None)
            # aiohttp leaves ``message`` empty when the server sends no reason phrase, and the
            # exception itself stringifies to the full internal API URL, so it cannot stand in.
            reason_phrase = getattr(e, "message", None)
            detail = f"{status} {reason_phrase}" if reason_phrase else str(status)
            if status == 401:
                # A missing, invalid, expired or revoked token.
                raise AuthenticationRequired(self._credentials_message(description, detail)) from e
            if status == 403:
                # The token authenticated but is not allowed to do this. A classic token is missing
                # the "api" scope; a fine-grained one is missing the resource permission this call
                # needs. GitLab names which in the response body, but aiohttp keeps only the status
                # and reason phrase on the error, so both causes have to be offered here.
                raise AuthenticationRequired(
                    self._credentials_message(
                        description,
                        f"{detail}. A classic token may lack the '{self._token_scope_for(operation)}' "
                        "scope; a fine-grained token may lack the permissions this operation needs"
                        + (
                            ". A token with every scope is still refused by a protected branch, "
                            "which GitLab applies to the default branch"
                            if operation == "writing to"
                            else ""
                        ),
                    )
                ) from e
            if status == 200:
                # The server answered, and the answer was not the JSON a GitLab API returns. The
                # base_url points at something that is not an API root: most often the address of
                # the page the user was looking at when they copied it. aiohttp reports this as
                # a mimetype it could not decode, which explains nothing about the field to fix.
                raise RequestParameterInvalidException(
                    f"'{base_url_for_errors}' answered, but not as a GitLab API. Use the address of "
                    f"the {self.entity_name} server itself, as in 'https://gitlab.com', rather than "
                    "the address of a page on it."
                ) from e
            if status == 400 and operation == "writing to":
                # GitLab answers 400 for a commit it would not make, and aiohttp keeps only the
                # status, so the body saying which is gone by the time this runs. The likeliest
                # cause on a write is the one this source deliberately provokes: it sends the
                # commit id the file was read at, so a file changed since then is refused rather
                # than silently overwritten, and the user has to be told to try again.
                raise MessageException(
                    f"Problem {description}. {self.label} refused the commit. GitLab protects the "
                    "default branch by default, so the token may not be allowed to push to it; "
                    "otherwise the file may have changed since Galaxy read it, in which case "
                    "exporting again will pick up the new version."
                ) from e
            if status == 413:
                raise MessageException(
                    f"Problem {description}. The file is larger than {self.label} accepts in a "
                    f"single request.{self._large_file_remedy}"
                ) from e
            if status == 405 and operation == "listing":
                # GitLab limits how far an offset listing may page and answers 405 once past it,
                # with no hint that paging is what it objected to. It enforces this only for
                # unauthenticated requests, so a token removes the limit entirely. The cap applies
                # to listings, and this handler is shared with reading and writing, so only a
                # listing gets this wording.
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
            # Statuses outside the ladder above still must not render the exception itself: for an
            # aiohttp error that is the internal API URL and its query string. Errors with no text
            # at all would otherwise leave a bare "Reason: ".
            if type(e).__name__ == "FSTimeoutError":
                # fsspec rewrites asyncio.TimeoutError to this, and it stringifies to nothing.
                # The session's own budget covers the whole transfer, so a large file on a slow
                # link runs out of it having committed nothing.
                raise MessageException(
                    f"Problem {description}. {self.label} did not answer in time. A large file on "
                    "a slow connection can exhaust the request budget; nothing was committed."
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

        Listings are built from arcfs' ``list_page``, which paginates against GitLab and reports the
        total number of entries that Galaxy needs for its pagination controls. ``fs.ls()`` reports no
        total, and makes arcfs fetch and keep the whole project catalogue in one call, so it is only
        used for recursion inside a project.
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
                    # Without this the filter is silently dropped and the whole subtree comes back
                    # looking like a result set. The cap in ``_list_recursive`` applies first, so a
                    # match beyond it is still not found, exactly as on the non-recursive path.
                    entries = self._filter_by_name(entries, query)
                    total = len(entries)
                return self._paginate(entries, limit, offset), total

        with self._filesystem(context, "listing", path) as (fs, config):
            fs_path = self._to_filesystem_path(path, config)

            if query:
                # The generic implementation globs, which needs ``_info``; arcfs implements no
                # ``_info``, so globbing fails with a bare NotImplementedError.
                entries, total = self._read_window(fs, fs_path, config, 0, MAX_ITEMS_LIMIT, write_intent)
                if total > len(entries):
                    self._on_listing_exceeded()
                matched = self._filter_by_name(entries, query)
                return self._paginate(matched, limit, offset), len(matched)

            if limit is None:
                entries, total = self._read_window(fs, fs_path, config, 0, MAX_ITEMS_LIMIT, write_intent)
                if total > len(entries):
                    self._on_listing_exceeded()
                return self._paginate(entries, limit, offset), total

            if limit > MAX_ITEMS_LIMIT:
                # Nothing bounds the limit a caller may ask for, and arcfs will fetch as many
                # GitLab pages as it takes to fill it.
                self._on_listing_exceeded()
            return self._read_window(fs, fs_path, config, offset or 0, min(limit, MAX_ITEMS_LIMIT), write_intent)

    #: Appended to the message for a file too large to commit. An ARC has somewhere else to put
    #: it; a plain project does not, so only the GitLab source has something to suggest.
    _large_file_remedy = " An ARC file source, which uploads through Git LFS instead, can carry it."

    def _require_a_project(self, path: str) -> None:
        """Refuse a listing whose path carries the marker but names no project.

        ``:-:`` on its own, or anything with an empty left side, is a path a user can produce by
        editing the address bar or by pasting half of one. The backend does not catch it: it asks
        GitLab for the project named "", which is the endpoint that lists *all* projects, and then
        indexes the list as if it were one project's payload. That surfaces as
        ``list indices must be integers or slices, not str``, a Python error about Galaxy's own
        internals standing where an explanation of the user's path should be.

        Listing a project root is legitimate, so this only checks the project side, unlike
        ``_require_a_file_inside``.

        Args:
            path: The Galaxy-side path the caller named.

        Raises:
            RequestParameterInvalidException: If the marker is present with no project before it.
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

        Each of the three ways it can fail reaches the backend as its own obscure failure.
        Without the marker the backend cannot tell where the project path ends, so it probes
        prefixes and builds the whole project index before failing, with a message about a
        missing project for a path that never named one. With nothing after the marker the path
        is a project itself, which a listing of the top level offers verbatim, and the backend
        refuses it with an error carrying only the path again, so the user is told their path
        failed because of their path. With nothing before the marker the project part is empty,
        which the backend does not catch at all: it asks GitLab for the project named "",
        reaching the endpoint that lists projects, and fails on the shape of the answer.

        Args:
            path: The Galaxy-side path the caller named.
            what: "Exports" or "Imports", so the message names what the user was doing.
        """
        project, marker, inside = path.partition(ROOT_MARKER)
        if marker and self._names_something(project) and self._names_something(inside):
            return
        raise RequestParameterInvalidException(
            f"{what} have to name a file inside {self._article} {self.entity_name}, in the form "
            f"the file browser produces (group/project{ROOT_MARKER}/folder/file). The top level "
            f"of this file source lists the {self.entity_name}s themselves and cannot hold files."
        )

    def _paginate(self, entries: list[AnyRemoteEntry], limit: int | None, offset: int | None) -> list[AnyRemoteEntry]:
        """Apply the caller's window, including an offset given without a limit.

        The shared helper returns the list untouched unless a limit is set, so an offset on its
        own is dropped and every page comes back as the first one while the total says otherwise.
        """
        if limit is None and offset:
            return entries[offset:]
        return self._apply_pagination(entries, limit, offset)

    def _list_recursive(
        self, fs: "GitLabARCFileSystem", path: str, config: GitLabFileSourceConfiguration
    ) -> tuple[list[AnyRemoteEntry], int]:
        """Recurse with failures raised rather than omitted.

        fsspec's ``walk`` defaults to ``on_error="omit"``, which swallows FileNotFoundError and
        every OSError. A project that is missing, private or has no commits, and a GitLab that
        cannot be reached at all, would each come back as an empty folder, and the translation in
        ``_filesystem`` would never run. Listing the same path without recursion reports all of
        them correctly, so the two views would disagree about the same request.
        """
        entries: list[AnyRemoteEntry] = []
        count = 0
        for _, dirs, files in fs.walk(path, detail=True, on_error="raise"):
            to_entry = functools.partial(self._info_to_entry, config=config)
            entries.extend(map(to_entry, cast(dict[str, dict], dirs).values()))
            entries.extend(map(to_entry, cast(dict[str, dict], files).values()))
            count += len(dirs) + len(files)
            if count >= MAX_ITEMS_LIMIT:
                self._on_listing_exceeded()
                break
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
        # A push is never anonymous, so a writable source with no token cannot export at all.
        # Saying that here beats letting it travel to the server and come back as a 401 about
        # credentials, which reads as "your token is wrong" when there is no token to be wrong.
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

        The backend strips whitespace and slashes and drops segments that navigate rather than
        name, so a guard reading the raw text lets through targets it then fails on, reporting
        the path as its own explanation. ``..`` is refused rather than normalized away: nothing
        between the request and the API call bounds a target to inside the repository.
        """
        segments = [segment for segment in part.strip().strip("/").split("/") if segment not in ("", ".")]
        return bool(segments) and ".." not in segments

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
