import os
import tempfile
from abc import (
    ABCMeta,
    abstractmethod,
    abstractproperty,
)

import six


@six.add_metaclass(ABCMeta)
class ToolLocationResolver(object):
    """Parse a URI-like string and return a ToolSource object."""

    @abstractproperty
    def scheme(self):
        """Short label for the type of location resolver and URI scheme."""

    @abstractmethod
    def get_tool_source_path(self, uri_like):
        """Return a local path for the uri_like string."""

    def _temp_path(self, uri_like):
        """Create an abstraction for this so we can configure and cache later."""
        handle, filename = tempfile.mkstemp(suffix=uri_like.split("/")[-1])
        os.close(handle)
        return filename
