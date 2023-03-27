import abc
import os
import time
from typing import (
    Any,
    ClassVar,
    Optional,
    Set,
    TYPE_CHECKING,
)

from typing_extensions import (
    NotRequired,
    TypedDict,
)

from galaxy.exceptions import (
    ConfigurationError,
    ItemAccessibilityException,
)
from galaxy.util.bool_expressions import (
    BooleanExpressionEvaluator,
    TokenContainedEvaluator,
)
from galaxy.util.template import fill_template

DEFAULT_SCHEME = "gxfiles"
DEFAULT_WRITABLE = False

if TYPE_CHECKING:
    from galaxy.files import ConfiguredFileSourcesConfig


class FilesSourceProperties(TypedDict):
    """Initial set of properties used to initialize a filesource.

    Filesources can extend this typed dict to define any additional
    filesource specific properties.
    """

    file_sources_config: NotRequired["ConfiguredFileSourcesConfig"]
    id: NotRequired[str]
    label: NotRequired[str]
    doc: NotRequired[Optional[str]]
    scheme: NotRequired[str]
    writable: NotRequired[bool]
    requires_roles: NotRequired[Optional[str]]
    requires_groups: NotRequired[Optional[str]]
    # API helper values
    uri_root: NotRequired[str]
    type: NotRequired[str]
    browsable: NotRequired[bool]


class FilesSourceOptions:
    """Options to control behaviour of filesource operations, such as realize_to and write_from"""

    # Property overrides for values initially configured through the constructor. For example
    # the HTTPFilesSource passes in additional http_headers through these properties, which
    # are merged with constructor defined http_headers. The interpretation of these properties
    # are filesystem specific.
    extra_props: Optional[FilesSourceProperties]


class SingleFileSource(metaclass=abc.ABCMeta):
    """
    Represents a protocol handler for a single remote file that can be read by or written to by Galaxy.
    A remote file source can typically handle a url like `https://galaxyproject.org/myfile.txt` or
    `drs://myserver/123456`. The filesource abstraction allows programmatic control over the specific source
    to access, injection of credentials and access control. Filesources are typically listed and configured
    through `file_sources_conf.yml` or programmatically, as required.

    Filesources can be contextualized with a `user_context`, which contains information related to the current
    user attempting to access that filesource such as the username, preferences, roles etc., which can then
    be used by the filesource to make authorization decisions or inject credentials.

    Filesources are loaded through Galaxy's plugin system in `galaxy.util.plugin_config`.
    """

    @abc.abstractmethod
    def get_writable(self) -> bool:
        """Return a boolean indicating whether this target is writable."""

    @abc.abstractmethod
    def user_has_access(self, user_context) -> bool:
        """Return a boolean indicating whether the user can access the FileSource."""

    @abc.abstractmethod
    def realize_to(
        self, source_path: str, native_path: str, user_context=None, opts: Optional[FilesSourceOptions] = None
    ):
        """Realize source path (relative to uri root) to local file system path.

        :param source_path: url of the source file to copy from. e.g. `https://galaxyproject.org/myfile.txt`
        :type source_path: str
        :param native_path: local path to write to. e.g. `/tmp/myfile.txt`
        :type native_path: str
        :param user_context: A user context , defaults to None
        :type user_context: FileSourceDictifiable, optional
        :param opts: A set of options to exercise additional control over the realize_to method. Filesource specific, defaults to None
        :type opts: Optional[FilesSourceOptions], optional
        """

    @abc.abstractmethod
    def write_from(
        self, target_path: str, native_path: str, user_context=None, opts: Optional[FilesSourceOptions] = None
    ):
        """Write file at native path to target_path (relative to uri root).

        :param target_path: url of the target file to write to within the filesource. e.g. `gxfiles://myftp1/myfile.txt`
        :type target_path: str
        :param native_path: The local file to read. e.g. `/tmp/myfile.txt`
        :type native_path: str
        :param user_context: A user context , defaults to None
        :type user_context: _type_, optional
        :param opts: A set of options to exercise additional control over the write_from method. Filesource specific, defaults to None
        :type opts: Optional[FilesSourceOptions], optional
        """

    @abc.abstractmethod
    def score_url_match(self, url: str) -> int:
        """Return how well a given url matches this filesource. A score greater than zero indicates that
        this filesource is capable of processing the given url.

        Scoring is based on the following rules:
        a. The maximum score will be the length of the url.
        b. The minimum score will be the length of the scheme if the filesource can handle the file.
        c. The score will be zero if the filesource cannot handle the file.

        For example, given the following file source config:
        - type: webdav
          id: cloudstor
          url: "https://cloudstor.aarnet.edu.au"
          root: "/plus/remote.php/webdav"
        - type: http
          id: generic_http

        the generic http handler may return a score of 8 for the url
        https://cloudstor.aarnet.edu.au/plus/remote.php/webdav/myfolder/myfile.txt,
        as it can handle only the scheme part of the url. A webdav handler may return a score of
        55 for the same url, as both the webdav url and root combined are a specific match.

        :param url: The url to score for a match against this filesource.
        :type url: str
        :return: A score based on the aforementioned rules.
        :rtype: int
        """

    @abc.abstractmethod
    def to_relative_path(self, url: str) -> str:
        """Convert this url to a filesource relative path. For example, given the url
        `gxfiles://mysource1/myfile.txt` it will return `/myfile.txt`. Protocols directly understood
        by the handler need not be relativized. For example, the url `s3://bucket/myfile.txt` can be
        returned unchanged."""

    @abc.abstractmethod
    def to_dict(self, for_serialization=False, user_context=None) -> FilesSourceProperties:
        """Return a dictified representation of this FileSource instance.

        If ``user_context`` is supplied, properties should be written so user
        context doesn't need to be present after the plugin is re-hydrated.
        """


class SupportsBrowsing(metaclass=abc.ABCMeta):
    """An interface indicating that this filesource is browsable.

    Browsable filesources will typically have a root uri from which to start browsing.
    e.g. In an s3 bucket, the root uri may be gxfiles://bucket1/

    They will also have a list method to list files in a specific path within the filesource.
    """

    @abc.abstractmethod
    def get_uri_root(self) -> str:
        """Return a prefix for the root (e.g. gxfiles://prefix/)."""

    @abc.abstractmethod
    def list(self, path="/", recursive=False, user_context=None, opts: Optional[FilesSourceOptions] = None) -> dict:
        """Return dictionary of 'Directory's and 'File's."""


class FilesSource(SingleFileSource, SupportsBrowsing):
    """Represents a combined interface for single or browsable filesources.
    The `get_browsable` method can be used to determine whether the filesource is browsable and
    implements the `SupportsBrowsing` interface.
    """

    @abc.abstractmethod
    def get_browsable(self) -> bool:
        """Return true if the filesource implements the SupportsBrowsing interface."""


class BaseFilesSource(FilesSource):
    plugin_type: ClassVar[str]

    def get_browsable(self) -> bool:
        # Check whether the list method has been overridden
        return type(self).list != BaseFilesSource.list or type(self)._list != BaseFilesSource._list

    def get_prefix(self) -> Optional[str]:
        return self.id

    def get_scheme(self) -> str:
        return "gxfiles"

    def get_writable(self) -> bool:
        return self.writable

    def user_has_access(self, user_context) -> bool:
        if user_context is None and self.user_context_required:
            return False
        return (
            user_context is None
            or user_context.is_admin
            or (self._user_has_required_roles(user_context) and self._user_has_required_groups(user_context))
        )

    @property
    def user_context_required(self) -> bool:
        return self.requires_roles is not None or self.requires_groups is not None

    def get_uri_root(self) -> str:
        prefix = self.get_prefix()
        scheme = self.get_scheme()
        root = f"{scheme}://"
        if prefix:
            root = uri_join(root, prefix)
        return root

    def to_relative_path(self, url: str) -> str:
        return url.replace(self.get_uri_root(), "") or "/"

    def score_url_match(self, url: str) -> int:
        root = self.get_uri_root()
        return len(root) if root in url else 0

    def uri_from_path(self, path) -> str:
        uri_root = self.get_uri_root()
        return uri_join(uri_root, path)

    def _parse_common_config_opts(self, kwd: FilesSourceProperties):
        self._file_sources_config = kwd.pop("file_sources_config")
        self.id = kwd.pop("id")
        self.label = kwd.pop("label", None) or self.id
        self.doc = kwd.pop("doc", None)
        self.scheme = kwd.pop("scheme", DEFAULT_SCHEME)
        self.writable = kwd.pop("writable", DEFAULT_WRITABLE)
        self.requires_roles = kwd.pop("requires_roles", None)
        self.requires_groups = kwd.pop("requires_groups", None)
        self._validate_security_rules()
        # If coming from to_dict, strip API helper values
        kwd.pop("uri_root", None)
        kwd.pop("type", None)
        kwd.pop("browsable", None)
        return kwd

    def to_dict(self, for_serialization=False, user_context=None) -> FilesSourceProperties:
        rval: FilesSourceProperties = {
            "id": self.id,
            "type": self.plugin_type,
            "label": self.label,
            "doc": self.doc,
            "writable": self.writable,
            "browsable": self.get_browsable(),
            "requires_roles": self.requires_roles,
            "requires_groups": self.requires_groups,
        }
        if self.get_browsable():
            rval["uri_root"] = self.get_uri_root()
        if for_serialization:
            rval.update(self._serialization_props(user_context=user_context))
        return rval

    def to_dict_time(self, ctime):
        if ctime is None:
            return None
        elif isinstance(ctime, (int, float)):
            return time.strftime("%m/%d/%Y %I:%M:%S %p", time.localtime(ctime))
        else:
            return ctime.strftime("%m/%d/%Y %I:%M:%S %p")

    @abc.abstractmethod
    def _serialization_props(self, user_context=None) -> FilesSourceProperties:
        """Serialize properties needed to recover plugin configuration.
        Used in to_dict method if for_serialization is True.
        """

    def list(self, path="/", recursive=False, user_context=None, opts: Optional[FilesSourceOptions] = None):
        self._check_user_access(user_context)
        return self._list(path, recursive, user_context, opts)

    def _list(self, path="/", recursive=False, user_context=None, opts: Optional[FilesSourceOptions] = None):
        pass

    def write_from(self, target_path, native_path, user_context=None, opts: Optional[FilesSourceOptions] = None):
        if not self.get_writable():
            raise Exception("Cannot write to a non-writable file source.")
        self._check_user_access(user_context)
        self._write_from(target_path, native_path, user_context=user_context, opts=opts)

    @abc.abstractmethod
    def _write_from(self, target_path, native_path, user_context=None, opts: Optional[FilesSourceOptions] = None):
        pass

    def realize_to(self, source_path, native_path, user_context=None, opts: Optional[FilesSourceOptions] = None):
        self._check_user_access(user_context)
        self._realize_to(source_path, native_path, user_context, opts=opts)

    @abc.abstractmethod
    def _realize_to(self, source_path, native_path, user_context=None, opts: Optional[FilesSourceOptions] = None):
        pass

    def _check_user_access(self, user_context):
        """Raises an exception if the given user doesn't have the rights to access this file source.

        Warning: if the user_context is None, then the check is skipped. This is due to tool executions context
        not having access to the user_context. The validation will be done when checking the tool parameters.
        """
        if user_context is not None and not self.user_has_access(user_context):
            raise ItemAccessibilityException(f"User {user_context.username} has no access to file source.")

    def _evaluate_prop(self, prop_val: Any, user_context):
        rval = prop_val
        if isinstance(prop_val, str) and "$" in prop_val:
            template_context = dict(
                user=user_context,
                environ=os.environ,
                config=self._file_sources_config,
            )
            rval = fill_template(prop_val, context=template_context, futurized=True)
        elif isinstance(prop_val, dict):
            rval = {key: self._evaluate_prop(childprop, user_context) for key, childprop in prop_val.items()}
        elif isinstance(prop_val, list):
            rval = [self._evaluate_prop(childprop, user_context) for childprop in prop_val]

        return rval

    def _user_has_required_roles(self, user_context) -> bool:
        if self.requires_roles:
            return self._evaluate_security_rules(self.requires_roles, user_context.role_names)
        return True

    def _user_has_required_groups(self, user_context) -> bool:
        if self.requires_groups:
            return self._evaluate_security_rules(self.requires_groups, user_context.group_names)
        return True

    def _evaluate_security_rules(self, rule_expression: str, user_credentials: Set[str]) -> bool:
        token_evaluator = TokenContainedEvaluator(user_credentials)
        evaluator = BooleanExpressionEvaluator(token_evaluator)
        return evaluator.evaluate_expression(rule_expression)

    def _validate_security_rules(self) -> None:
        """Checks if the security rules defined in the plugin configuration are valid boolean expressions or raises
        a ConfigurationError exception otherwise."""

        def _get_error_msg_for(rule_name: str) -> str:
            return f"Invalid boolean expression for '{rule_name}' in {self.label} file source plugin configuration."

        if self.requires_roles and not BooleanExpressionEvaluator.is_valid_expression(self.requires_roles):
            raise ConfigurationError(_get_error_msg_for("requires_roles"))
        if self.requires_groups and not BooleanExpressionEvaluator.is_valid_expression(self.requires_groups):
            raise ConfigurationError(_get_error_msg_for("requires_groups"))


def uri_join(*args):
    # url_join doesn't work with non-standard scheme
    arg0 = args[0]
    if "://" in arg0:
        scheme, path = arg0.split("://", 1)
        rval = f"{scheme}://{slash_join(path, *args[1:]) if path else slash_join(*args[1:])}"
    else:
        rval = slash_join(*args)
    return rval


def slash_join(*args):
    # https://codereview.stackexchange.com/questions/175421/joining-strings-to-form-a-url
    return "/".join(arg.strip("/") for arg in args)
