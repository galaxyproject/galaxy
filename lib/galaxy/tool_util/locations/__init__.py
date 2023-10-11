import abc
import tempfile


class ToolLocationResolver(metaclass=abc.ABCMeta):
    """Parse a URI-like string and return a ToolSource object."""

    @property
    @abc.abstractmethod
    def scheme(self):
        """Short label for the type of location resolver and URI scheme."""

    @abc.abstractmethod
    def get_tool_source_path(self, uri_like: str) -> str:
        """Return a local path for the uri_like string."""

    def _temp_path(self, uri_like):
        """Create an abstraction for this so we can configure and cache later."""
        with tempfile.NamedTemporaryFile(suffix=uri_like.split("/")[-1], delete=False) as temp:
            return temp.name
