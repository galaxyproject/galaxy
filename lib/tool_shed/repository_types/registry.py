import logging

from . import (
    repository_suite_definition,
    tool_dependency_definition,
    unrestricted,
)
from tool_shed.repository_types.metadata import Metadata

log = logging.getLogger(__name__)


class Registry:
    def __init__(self):
        self.repository_types_by_label: dict[str, Metadata] = {}
        self.repository_types_by_label["unrestricted"] = unrestricted.Unrestricted()
        self.repository_types_by_label["repository_suite_definition"] = (
            repository_suite_definition.RepositorySuiteDefinition()
        )
        self.repository_types_by_label["tool_dependency_definition"] = (
            tool_dependency_definition.ToolDependencyDefinition()
        )

    def get_class_by_label(self, label):
        return self.repository_types_by_label.get(label, None)
