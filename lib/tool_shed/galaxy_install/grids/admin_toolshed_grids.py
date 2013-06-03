import logging

from galaxy import model, util
from galaxy.web.framework.helpers import iff, grids
from galaxy.model.orm import or_
from tool_shed.util import tool_dependency_util

log = logging.getLogger( __name__ )


class InstalledRepositoryGrid( grids.Grid ):


    class NameColumn( grids.TextColumn ):

        def get_value( self, trans, grid, tool_shed_repository ):
            if tool_shed_repository.update_available:
                return '<div class="count-box state-color-running">%s</div>' % tool_shed_repository.name
            return tool_shed_repository.name


    class DescriptionColumn( grids.TextColumn ):

        def get_value( self, trans, grid, tool_shed_repository ):
            return tool_shed_repository.description


    class OwnerColumn( grids.TextColumn ):

        def get_value( self, trans, grid, tool_shed_repository ):
            return tool_shed_repository.owner


    class RevisionColumn( grids.TextColumn ):

        def get_value( self, trans, grid, tool_shed_repository ):
            return tool_shed_repository.changeset_revision


    class StatusColumn( grids.TextColumn ):

        def get_value( self, trans, grid, tool_shed_repository ):
            status_label = tool_shed_repository.status
            if tool_shed_repository.status in [ trans.model.ToolShedRepository.installation_status.CLONING,
                                                trans.model.ToolShedRepository.installation_status.SETTING_TOOL_VERSIONS,
                                                trans.model.ToolShedRepository.installation_status.INSTALLING_REPOSITORY_DEPENDENCIES,
                                                trans.model.ToolShedRepository.installation_status.INSTALLING_TOOL_DEPENDENCIES,
                                                trans.model.ToolShedRepository.installation_status.LOADING_PROPRIETARY_DATATYPES ]:
                bgcolor = trans.model.ToolShedRepository.states.INSTALLING
            elif tool_shed_repository.status in [ trans.model.ToolShedRepository.installation_status.NEW,
                                                  trans.model.ToolShedRepository.installation_status.UNINSTALLED ]:
                bgcolor = trans.model.ToolShedRepository.states.UNINSTALLED
            elif tool_shed_repository.status in [ trans.model.ToolShedRepository.installation_status.ERROR ]:
                bgcolor = trans.model.ToolShedRepository.states.ERROR
            elif tool_shed_repository.status in [ trans.model.ToolShedRepository.installation_status.DEACTIVATED ]:
                bgcolor = trans.model.ToolShedRepository.states.WARNING
            elif tool_shed_repository.status in [ trans.model.ToolShedRepository.installation_status.INSTALLED ]:
                if tool_shed_repository.missing_repository_dependencies:
                    bgcolor = trans.model.ToolShedRepository.states.WARNING
                    status_label = '%s, missing repository dependencies' % status_label
                elif tool_shed_repository.missing_tool_dependencies:
                    bgcolor = trans.model.ToolShedRepository.states.WARNING
                    status_label = '%s, missing tool dependencies' % status_label
                else:
                    bgcolor = trans.model.ToolShedRepository.states.OK
            else:
                bgcolor = trans.model.ToolShedRepository.states.ERROR
            rval = '<div class="count-box state-color-%s">%s</div>' % ( bgcolor, status_label )
            return rval


    class ToolShedColumn( grids.TextColumn ):

        def get_value( self, trans, grid, tool_shed_repository ):
            return tool_shed_repository.tool_shed


    class DeletedColumn( grids.DeletedColumn ):

            def get_accepted_filters( self ):
                """ Returns a list of accepted filters for this column. """
                accepted_filter_labels_and_vals = { "Active" : "False", "Deactivated or uninstalled" : "True", "All": "All" }
                accepted_filters = []
                for label, val in accepted_filter_labels_and_vals.items():
                   args = { self.key: val }
                   accepted_filters.append( grids.GridColumnFilter( label, args) )
                return accepted_filters
    # Grid definition
    title = "Installed tool shed repositories"
    model_class = model.ToolShedRepository
    template='/admin/tool_shed_repository/grid.mako'
    default_sort_key = "name"
    columns = [
        NameColumn( "Name",
                    key="name",
                    link=( lambda item: iff( item.status in [ model.ToolShedRepository.installation_status.CLONING ],
                                             None,
                                             dict( operation="manage_repository", id=item.id ) ) ),
                    attach_popup=True ),
        DescriptionColumn( "Description" ),
        OwnerColumn( "Owner" ),
        RevisionColumn( "Revision" ),
        StatusColumn( "Installation Status",
                      filterable="advanced" ),
        ToolShedColumn( "Tool shed" ),
        # Columns that are valid for filtering but are not visible.
        DeletedColumn( "Status",
                       key="deleted",
                       visible=False,
                       filterable="advanced" )
    ]
    columns.append( grids.MulticolFilterColumn( "Search repository name", 
                                                cols_to_filter=[ columns[0] ],
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    global_actions = []
    operations = [ grids.GridOperation( "Get updates",
                                        allow_multiple=False,
                                        condition=( lambda item: not item.deleted and item.status not in \
                                            [ model.ToolShedRepository.installation_status.ERROR, model.ToolShedRepository.installation_status.NEW ] ),
                                        async_compatible=False,
                                        url_args=dict( controller='admin_toolshed', action='browse_repositories', operation='get updates' ) ),
                   grids.GridOperation( "Install",
                                        allow_multiple=False,
                                        condition=( lambda item: not item.deleted and item.status == model.ToolShedRepository.installation_status.NEW ),
                                        async_compatible=False,
                                        url_args=dict( controller='admin_toolshed', action='manage_repository', operation='install' ) ),
                   grids.GridOperation( "Deactivate or uninstall",
                                        allow_multiple=False,
                                        condition=( lambda item: not item.deleted and item.status not in \
                                            [ model.ToolShedRepository.installation_status.ERROR, model.ToolShedRepository.installation_status.NEW ] ),
                                        async_compatible=False,
                                        url_args=dict( controller='admin_toolshed', action='browse_repositories', operation='deactivate or uninstall' ) ),
                   grids.GridOperation( "Reset to install",
                                        allow_multiple=False,
                                        condition=( lambda item: ( item.status == model.ToolShedRepository.installation_status.ERROR ) ),
                                        async_compatible=False,
                                        url_args=dict( controller='admin_toolshed', action='browse_repositories', operation='reset to install' ) ),
                   grids.GridOperation( "Activate or reinstall",
                                        allow_multiple=False,
                                        condition=( lambda item: item.deleted ),
                                        async_compatible=False,
                                        url_args=dict( controller='admin_toolshed', action='browse_repositories', operation='activate or reinstall' ) ) ]
    standard_filters = []
    default_filter = dict( deleted="False" )
    num_rows_per_page = 50
    preserve_state = False
    use_paging = False

    def build_initial_query( self, trans, **kwd ):
        return trans.sa_session.query( self.model_class )


class RepositoryInstallationGrid( grids.Grid ):


    class NameColumn( grids.TextColumn ):

        def get_value( self, trans, grid, tool_shed_repository ):
            return tool_shed_repository.name


    class DescriptionColumn( grids.TextColumn ):

        def get_value( self, trans, grid, tool_shed_repository ):
            return tool_shed_repository.description


    class OwnerColumn( grids.TextColumn ):

        def get_value( self, trans, grid, tool_shed_repository ):
            return tool_shed_repository.owner


    class RevisionColumn( grids.TextColumn ):

        def get_value( self, trans, grid, tool_shed_repository ):
            return tool_shed_repository.changeset_revision


    class StatusColumn( grids.TextColumn ):

        def get_value( self, trans, grid, tool_shed_repository ):
            status_label = tool_shed_repository.status
            if tool_shed_repository.status in [ trans.model.ToolShedRepository.installation_status.CLONING,
                                                trans.model.ToolShedRepository.installation_status.SETTING_TOOL_VERSIONS,
                                                trans.model.ToolShedRepository.installation_status.INSTALLING_TOOL_DEPENDENCIES,
                                                trans.model.ToolShedRepository.installation_status.LOADING_PROPRIETARY_DATATYPES ]:
                bgcolor = trans.model.ToolShedRepository.states.INSTALLING
            elif tool_shed_repository.status in [ trans.model.ToolShedRepository.installation_status.NEW,
                                                 trans.model.ToolShedRepository.installation_status.UNINSTALLED ]:
                bgcolor = trans.model.ToolShedRepository.states.UNINSTALLED
            elif tool_shed_repository.status in [ trans.model.ToolShedRepository.installation_status.ERROR ]:
                bgcolor = trans.model.ToolShedRepository.states.ERROR
            elif tool_shed_repository.status in [ trans.model.ToolShedRepository.installation_status.DEACTIVATED ]:
                bgcolor = trans.model.ToolShedRepository.states.WARNING
            elif tool_shed_repository.status in [ trans.model.ToolShedRepository.installation_status.INSTALLED ]:
                if tool_shed_repository.missing_tool_dependencies or tool_shed_repository.missing_repository_dependencies:
                    bgcolor = trans.model.ToolShedRepository.states.WARNING
                if tool_shed_repository.missing_tool_dependencies and not tool_shed_repository.missing_repository_dependencies:
                    status_label = '%s, missing tool dependencies' % status_label
                if tool_shed_repository.missing_repository_dependencies and not tool_shed_repository.missing_tool_dependencies:
                    status_label = '%s, missing repository dependencies' % status_label
                if tool_shed_repository.missing_tool_dependencies and tool_shed_repository.missing_repository_dependencies:
                    status_label = '%s, missing both tool and repository dependencies' % status_label
                if not tool_shed_repository.missing_tool_dependencies and not tool_shed_repository.missing_repository_dependencies:
                    bgcolor = trans.model.ToolShedRepository.states.OK
            else:
                bgcolor = trans.model.ToolShedRepository.states.ERROR
            rval = '<div class="count-box state-color-%s" id="RepositoryStatus-%s">%s</div>' % \
                ( bgcolor, trans.security.encode_id( tool_shed_repository.id ), status_label )
            return rval

    title = "Monitor installing tool shed repositories"
    template = "admin/tool_shed_repository/repository_installation_grid.mako"
    model_class = model.ToolShedRepository
    default_sort_key = "-create_time"
    num_rows_per_page = 50
    preserve_state = True
    use_paging = False
    columns = [
        NameColumn( "Name",
                    link=( lambda item: iff( item.status in \
                                             [ model.ToolShedRepository.installation_status.NEW,
                                               model.ToolShedRepository.installation_status.CLONING,
                                               model.ToolShedRepository.installation_status.SETTING_TOOL_VERSIONS,
                                               model.ToolShedRepository.installation_status.INSTALLING_REPOSITORY_DEPENDENCIES,
                                               model.ToolShedRepository.installation_status.INSTALLING_TOOL_DEPENDENCIES,
                                               model.ToolShedRepository.installation_status.LOADING_PROPRIETARY_DATATYPES,
                                               model.ToolShedRepository.installation_status.UNINSTALLED ], \
                                             None, dict( action="manage_repository", id=item.id ) ) ),
                    filterable="advanced" ),
        DescriptionColumn( "Description",
                    filterable="advanced" ),
        OwnerColumn( "Owner",
                    filterable="advanced" ),
        RevisionColumn( "Revision",
                    filterable="advanced" ),
        StatusColumn( "Installation Status",
                      filterable="advanced",
                      label_id_prefix="RepositoryStatus-" )
    ]
    operations = []

    def build_initial_query( self, trans, **kwd ):
        clause_list = []
        tool_shed_repository_ids = util.listify( kwd.get( 'tool_shed_repository_ids', None ) )
        if tool_shed_repository_ids:
            for tool_shed_repository_id in tool_shed_repository_ids:
                clause_list.append( self.model_class.table.c.id == trans.security.decode_id( tool_shed_repository_id ) )
            if clause_list:
                return trans.sa_session.query( self.model_class ) \
                                       .filter( or_( *clause_list ) )
        for tool_shed_repository in trans.sa_session.query( self.model_class ) \
                                                    .filter( self.model_class.table.c.deleted == False ):
            if tool_shed_repository.status in [ trans.model.ToolShedRepository.installation_status.NEW,
                                               trans.model.ToolShedRepository.installation_status.CLONING,
                                               trans.model.ToolShedRepository.installation_status.SETTING_TOOL_VERSIONS,
                                               trans.model.ToolShedRepository.installation_status.INSTALLING_TOOL_DEPENDENCIES,
                                               trans.model.ToolShedRepository.installation_status.LOADING_PROPRIETARY_DATATYPES ]:
                clause_list.append( self.model_class.table.c.id == tool_shed_repository.id )
        if clause_list:
            return trans.sa_session.query( self.model_class ) \
                                   .filter( or_( *clause_list ) )
        return trans.sa_session.query( self.model_class ) \
                               .filter( self.model_class.table.c.status == trans.model.ToolShedRepository.installation_status.NEW )

    def apply_query_filter( self, trans, query, **kwd ):
        tool_shed_repository_id = kwd.get( 'tool_shed_repository_id', None )
        if tool_shed_repository_id:
            return query.filter_by( tool_shed_repository_id=trans.security.decode_id( tool_shed_repository_id ) )
        return query


class ToolDependencyGrid( grids.Grid ):


    class NameColumn( grids.TextColumn ):

        def get_value( self, trans, grid, tool_dependency ):
            return tool_dependency.name


    class VersionColumn( grids.TextColumn ):

        def get_value( self, trans, grid, tool_dependency ):
            return tool_dependency.version


    class TypeColumn( grids.TextColumn ):

        def get_value( self, trans, grid, tool_dependency ):
            return tool_dependency.type


    class StatusColumn( grids.TextColumn ):

        def get_value( self, trans, grid, tool_dependency ):
            if tool_dependency.status in [ trans.model.ToolDependency.installation_status.INSTALLING ]:
                bgcolor = trans.model.ToolDependency.states.INSTALLING
            elif tool_dependency.status in [ trans.model.ToolDependency.installation_status.NEVER_INSTALLED,
                                             trans.model.ToolDependency.installation_status.UNINSTALLED ]:
                bgcolor = trans.model.ToolDependency.states.UNINSTALLED
            elif tool_dependency.status in [ trans.model.ToolDependency.installation_status.ERROR ]:
                bgcolor = trans.model.ToolDependency.states.ERROR
            elif tool_dependency.status in [ trans.model.ToolDependency.installation_status.INSTALLED ]:
                bgcolor = trans.model.ToolDependency.states.OK
            rval = '<div class="count-box state-color-%s" id="ToolDependencyStatus-%s">%s</div>' % \
                ( bgcolor, trans.security.encode_id( tool_dependency.id ), tool_dependency.status )
            return rval

    title = "Tool Dependencies"
    template = "admin/tool_shed_repository/tool_dependencies_grid.mako"
    model_class = model.ToolDependency
    default_sort_key = "-create_time"
    num_rows_per_page = 50
    preserve_state = True
    use_paging = False
    columns = [
        NameColumn( "Name",
                    link=( lambda item: iff( item.status in \
                                             [ model.ToolDependency.installation_status.NEVER_INSTALLED,
                                               model.ToolDependency.installation_status.INSTALLING,
                                               model.ToolDependency.installation_status.UNINSTALLED ], \
                                             None, dict( action="manage_tool_dependencies", operation='browse', id=item.id ) ) ),
                    filterable="advanced" ),
        VersionColumn( "Version",
                       filterable="advanced" ),
        TypeColumn( "Type",
                    filterable="advanced" ),
        StatusColumn( "Installation Status",
                      filterable="advanced" ),
    ]
    operations = [
        grids.GridOperation( "Install",
                             allow_multiple=True,
                             condition=( lambda item: item.status in [ model.ToolDependency.installation_status.NEVER_INSTALLED,
                                                                       model.ToolDependency.installation_status.UNINSTALLED ] ) ),
        grids.GridOperation( "Uninstall",
                             allow_multiple=True,
                             allow_popup=False,
                             condition=( lambda item: item.status in [ model.ToolDependency.installation_status.INSTALLED,
                                                                       model.ToolDependency.installation_status.ERROR ] ) )
    ]

    def build_initial_query( self, trans, **kwd ):
        tool_dependency_ids = tool_dependency_util.get_tool_dependency_ids( as_string=False, **kwd )
        if tool_dependency_ids:
            clause_list = []
            for tool_dependency_id in tool_dependency_ids:
                clause_list.append( self.model_class.table.c.id == trans.security.decode_id( tool_dependency_id ) )
            return trans.sa_session.query( self.model_class ) \
                                   .filter( or_( *clause_list ) )
        return trans.sa_session.query( self.model_class )

    def apply_query_filter( self, trans, query, **kwd ):
        tool_dependency_id = kwd.get( 'tool_dependency_id', None )
        if tool_dependency_id:
            return query.filter_by( tool_dependency_id=trans.security.decode_id( tool_dependency_id ) )
        return query
