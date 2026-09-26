"""Missing-tool semantics of the curated catalog against a real toolbox.

``list_catalog`` checks tool ids through ``toolbox_availability``, which wraps
``ToolBox.has_tool``, so these pin down what that lookup treats as installed -- in particular that a pinned
Tool Shed version counts as satisfied by any installed version of the same
tool, which is how an imported workflow actually resolves its steps.
"""

from galaxy.app_unittest_utils.toolbox_support import BaseToolBoxTestCase
from galaxy.workflow import curated

INSTALLED_GUID = "github.com/galaxyproject/example/test_tool/0.1"
OTHER_VERSION_GUID = "github.com/galaxyproject/example/test_tool/0.9"
ABSENT_GUID = "github.com/galaxyproject/example/absent_tool/1.0"


class TestCuratedMissingTools(BaseToolBoxTestCase):
    def test_other_installed_version_is_not_missing_but_an_absent_tool_is(self) -> None:
        self._init_tool()
        self._setup_two_versions_in_config()
        self._setup_two_versions()
        entries = [
            {"id": "exact", "tool_ids": [INSTALLED_GUID]},
            {"id": "substituted", "tool_ids": [OTHER_VERSION_GUID]},
            {"id": "absent", "tool_ids": [INSTALLED_GUID, ABSENT_GUID]},
            {"id": "builtin-absent", "tool_ids": ["not_a_tool_here"]},
        ]

        missing = curated.find_missing_tools(entries, self.toolbox.has_tool)

        assert missing == {
            "exact": [],
            "substituted": [],
            "absent": [ABSENT_GUID],
            "builtin-absent": ["not_a_tool_here"],
        }

    def test_data_manager_tools_are_missing_for_non_admins_only(self) -> None:
        self._init_tool()
        self._setup_two_versions_in_config()
        self._setup_two_versions()
        installed = self.toolbox.get_tool(INSTALLED_GUID, exact=True)
        assert installed is not None
        self.toolbox.data_manager_tools[INSTALLED_GUID] = installed
        entries = [{"id": "dm", "tool_ids": [OTHER_VERSION_GUID]}]

        for is_admin, expected in ((False, [OTHER_VERSION_GUID]), (True, [])):
            available = curated.toolbox_availability(self.toolbox, is_admin)
            assert curated.find_missing_tools(entries, available) == {"dm": expected}
