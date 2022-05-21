import abc
import os
import time
from typing import Set

from typing_extensions import ClassVar

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


class FilesSource(metaclass=abc.ABCMeta):
    """ """

    @abc.abstractmethod
    def get_uri_root(self) -> str:
        """Return a prefix for the root (e.g. gxfiles://prefix/)."""

    @abc.abstractmethod
    def get_scheme(self) -> str:
        """Return a prefix for the root (e.g. the gxfiles in gxfiles://prefix/path)."""

    @abc.abstractmethod
    def get_writable(self):
        """Return a boolean indicating if this target is writable."""

    @abc.abstractmethod
    def user_has_access(self, user_context) -> bool:
        """Return a boolean indicating if the user can access the FileSource."""

    # TODO: off-by-default
    @abc.abstractmethod
    def list(self, source_path="/", recursive=False, user_context=None):
        """Return dictionary of 'Directory's and 'File's."""

    @abc.abstractmethod
    def realize_to(self, source_path, native_path, user_context=None):
        """Realize source path (relative to uri root) to local file system path."""

    def write_from(self, target_path, native_path, user_context=None):
        """Write file at native path to target_path (relative to uri root)."""

    @abc.abstractmethod
    def to_dict(self, for_serialization=False, user_context=None):
        """Return a dictified representation of this FileSource instance.

        If ``user_context`` is supplied, properties should be written so user
        context doesn't need to be present after the plugin is re-hydrated.
        """


class BaseFilesSource(FilesSource):
    plugin_type: ClassVar[str]

    def get_prefix(self):
        return self.id

    def get_scheme(self):
        return "gxfiles"

    def get_writable(self):
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

    def get_uri_root(self):
        prefix = self.get_prefix()
        scheme = self.get_scheme()
        root = f"{scheme}://"
        if prefix:
            root = uri_join(root, prefix)
        return root

    def uri_from_path(self, path):
        uri_root = self.get_uri_root()
        return uri_join(uri_root, path)

    def _parse_common_config_opts(self, kwd: dict):
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
        return kwd

    def to_dict(self, for_serialization=False, user_context=None):
        rval = {
            "id": self.id,
            "type": self.plugin_type,
            "uri_root": self.get_uri_root(),
            "label": self.label,
            "doc": self.doc,
            "writable": self.writable,
            "requires_roles": self.requires_roles,
            "requires_groups": self.requires_groups,
        }
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
    def _serialization_props(self, user_context=None):
        """Serialize properties needed to recover plugin configuration.

        Used in to_dict method if for_serialization is True.
        """

    def list(self, path="/", recursive=False, user_context=None):
        self._check_user_access(user_context)
        return self._list(path, recursive, user_context)

    @abc.abstractmethod
    def _list(self, path="/", recursive=False, user_context=None):
        pass

    def write_from(self, target_path, native_path, user_context=None):
        if not self.get_writable():
            raise Exception("Cannot write to a non-writable file source.")
        self._check_user_access(user_context)
        self._write_from(target_path, native_path, user_context=user_context)

    @abc.abstractmethod
    def _write_from(self, target_path, native_path, user_context=None):
        pass

    def realize_to(self, source_path, native_path, user_context=None):
        self._check_user_access(user_context)
        self._realize_to(source_path, native_path, user_context)

    @abc.abstractmethod
    def _realize_to(self, source_path, native_path, user_context=None):
        pass

    def _check_user_access(self, user_context):
        """Raises an exception if the given user doesn't have the rights to access this file source.

        Warning: if the user_context is None, then the check is skipped. This is due to tool executions context
        not having access to the user_context. The validation will be done when checking the tool parameters.
        """
        if user_context is not None and not self.user_has_access(user_context):
            raise ItemAccessibilityException(f"User {user_context.username} has no access to file source.")

    def _evaluate_prop(self, prop_val, user_context):
        rval = prop_val
        if isinstance(prop_val, str) and "$" in prop_val:
            template_context = dict(
                user=user_context,
                environ=os.environ,
                config=self._file_sources_config,
            )
            rval = fill_template(prop_val, context=template_context, futurized=True)

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
