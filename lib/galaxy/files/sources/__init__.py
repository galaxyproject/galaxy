import abc
import os
import time

import six

from galaxy.util.template import fill_template

DEFAULT_SCHEME = "gxfiles"
DEFAULT_WRITABLE = False


@six.add_metaclass(abc.ABCMeta)
class FilesSource(object):
    """
    """

    @abc.abstractmethod
    def get_uri_root(self):
        """Return a prefix for the root (e.g. gxfiles://prefix/)."""

    @abc.abstractmethod
    def get_scheme(self):
        """Return a prefix for the root (e.g. the gxfiles in gxfiles://prefix/path)."""

    @abc.abstractmethod
    def get_writable(self):
        """Return a boolean indicating if this target is writable."""

    # TODO: off-by-default
    @abc.abstractmethod
    def list(self, source_path="/", recursive=False, user_context=None):
        """Return dictionary of 'Directory's and 'File's."""

    @abc.abstractmethod
    def realize_to(self, source_path, native_path, user_context=None):
        """Realize source path (relative to uri root) to local file system path."""

    def write_from(self, target_path, native_path, user_context=None):
        """Write file at native path to target_path (relative to uri root).
        """

    @abc.abstractmethod
    def to_dict(self, for_serialization=False, user_context=None):
        """Return a dictified representation of this FileSource instance.

        If ``user_context`` is supplied, properties should be written so user
        context doesn't need to be present after the plugin is re-hydrated.
        """


class BaseFilesSource(FilesSource):

    def get_prefix(self):
        return self.id

    def get_scheme(self):
        return "gxfiles"

    def get_writable(self):
        return self.writable

    def get_uri_root(self):
        prefix = self.get_prefix()
        scheme = self.get_scheme()
        root = "%s://" % scheme
        if prefix:
            root = uri_join(root, prefix)
        return root

    def uri_from_path(self, path):
        uri_root = self.get_uri_root()
        return uri_join(uri_root, path)

    def _parse_common_config_opts(self, kwd):
        self._file_sources_config = kwd.pop("file_sources_config")
        self.id = kwd.pop("id")
        self.label = kwd.pop("label", None) or self.id
        self.doc = kwd.pop("doc", None)
        self.scheme = kwd.pop("scheme", DEFAULT_SCHEME)
        self.writable = kwd.pop("writable", DEFAULT_WRITABLE)
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
    def _serialization_props(self):
        """Serialize properties needed to recover plugin configuration.

        Used in to_dict method if for_serialization is True.
        """

    def write_from(self, target_path, native_path, user_context=None):
        if not self.get_writable():
            raise Exception("Cannot write to a non-writable file source.")
        self._write_from(target_path, native_path, user_context=user_context)

    @abc.abstractmethod
    def _write_from(self, target_path, native_path, user_context=None):
        pass

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


def uri_join(*args):
    # url_join doesn't work with non-standard scheme
    arg0 = args[0]
    if "://" in arg0:
        scheme, path = arg0.split("://", 1)
        rval = scheme + "://" + (slash_join(path, *args[1:]) if path else slash_join(*args[1:]))
    else:
        rval = slash_join(*args)
    return rval


def slash_join(*args):
    # https://codereview.stackexchange.com/questions/175421/joining-strings-to-form-a-url
    return "/".join(arg.strip("/") for arg in args)
