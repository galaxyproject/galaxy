import logging

from mercurial import hg, ui

import tool_shed.repository_types.util as rt_util
from tool_shed.repository_types.metadata import TipOnly
from tool_shed.util import basic_util

log = logging.getLogger( __name__ )


class ToolDependencyDefinition( TipOnly ):

    def __init__( self ):
        self.type = rt_util.TOOL_DEPENDENCY_DEFINITION
        self.label = 'Tool dependency definition'
        self.valid_file_names = [ 'tool_dependencies.xml' ]

    def is_valid_for_type( self, app, repository, revisions_to_check=None ):
        """
        Inspect the received repository's contents to determine if they abide by the rules defined for the contents of this type.
        If the received revisions_to_check is a list of changeset revisions, then inspection will be restricted to the revisions
        in the list.
        """
        repo = hg.repository( ui.ui(), repository.repo_path( app ) )
        if revisions_to_check:
            changeset_revisions = revisions_to_check
        else:
            changeset_revisions = repo.changelog
        for changeset in changeset_revisions:
            ctx = repo.changectx( changeset )
            # Inspect all files in the changeset (in sorted order) to make sure there is only one and it is named tool_dependencies.xml.
            files_changed_in_changeset = ctx.files()
            for file_path in files_changed_in_changeset:
                file_name = basic_util.strip_path( file_path )
                if file_name not in self.valid_file_names:
                    return False
        return True
