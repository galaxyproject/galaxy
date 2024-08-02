"""This module describes the abstract interface for :class:`InstrumentPlugin`.

These are responsible for collecting and formatting a coherent set of metrics.
"""

from abc import (
    ABCMeta,
    abstractmethod,
)


class ErrorPlugin(metaclass=ABCMeta):
    """Describes how to send bug reports to various locations."""

    @property
    @abstractmethod
    def plugin_type(self):
        """Short string providing labelling this plugin"""

    def submit_report(self, dataset, job, tool, **kwargs):
        """Submit the bug report and render a string to be displayed to the user."""
        return None
