from galaxy.web.base.controller import *
from galaxy.web.framework.helpers import time_ago, grids
from galaxy.util.sanitize_html import sanitize_html


class VisualizationListGrid( grids.Grid ):
    # Grid definition
    use_panels = True
    title = "Visualizations"
    model_class = model.Visualization
    default_sort_key = "-create_time"
    columns = [
        grids.GridColumn( "Title", key="title", attach_popup=True,
                         link=( lambda item: dict( controller="tracks", action="browser", id=item.id ) ) ),
        grids.GridColumn( "Type", key="type" ),
        grids.GridColumn( "Created", key="create_time", format=time_ago ),
        grids.GridColumn( "Last Updated", key="update_time", format=time_ago ),
    ]
    ## global_actions = [
    ##     grids.GridAction( "Add new page", dict( action='create' ) )
    ## ]
    operations = [
        grids.GridOperation( "View", allow_multiple=False, url_args=dict( controller="tracks", action='browser' ) ),
    ]
    def apply_default_filter( self, trans, query, **kwargs ):
        return query.filter_by( user=trans.user )

class VisualizationController( BaseController ):
    
    @web.expose
    def index( self, trans ):
        return trans.fill_template( "panels.mako", active_view='visualization', main_url=url_for( action='list' ) )
    
    list_grid = VisualizationListGrid()    
    @web.expose
    def list( self, trans, *args, **kwargs ):
        return self.list_grid( trans, *args, **kwargs )
    
    #@web.expose
    #@web.require_admin  
    #def index( self, trans, *args, **kwargs ):
    #    # Build grid
    #    grid = self.list( trans, *args, **kwargs )
    #    # Render grid wrapped in panels
    #    return trans.fill_template( "page/index.mako", grid=grid )
    
    