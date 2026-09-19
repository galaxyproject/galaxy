import logging

import tool_shed.repository_types.util as rt_util
from galaxy.util import unicodify
from tool_shed.repository_types.metadata import TipOnly
from tool_shed.util import basic_util

log = logging.getLogger(__name__)


class RepositorySuiteDefinition(TipOnly):
    def __init__(self):
        self.type = rt_util.REPOSITORY_SUITE_DEFINITION
        self.label = "Repository suite definition"
        self.valid_file_names = ["repository_dependencies.xml"]

    def is_valid_for_type(self, repository, revisions_to_check=None):
        """
        Inspect the received repository's contents to determine if they abide by the rules defined for
        the contents of this type.  If the received revisions_to_check is a list of changeset revisions,
        then inspection will be restricted to the revisions in the list.
        """
        repo = repository.hg_repo
        if revisions_to_check:
            changeset_revisions = revisions_to_check
        else:
            changeset_revisions = repo.changelog
        for changeset in changeset_revisions:
            ctx = repo[changeset]
            # Inspect all files in the changeset (in sorted order) to make sure there is only one and it
            # is named repository_dependencies.xml.
            files_changed_in_changeset = ctx.files()
            for file_path in files_changed_in_changeset:
                file_name = basic_util.strip_path(unicodify(file_path))
                if file_name not in self.valid_file_names:
                    return False
        return True
