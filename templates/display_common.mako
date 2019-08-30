##
## Utilities for sharing items and displaying shared items.
## HACK: these should probably go in the web helper object.
##
## TODO: FIXME Cannot import model here, because grids are
## used across webapps, and each webapp has its own model.

<%! from galaxy import model %>
<%! from galaxy.util import unicodify %>

## Get display name for a class.
<%def name="get_class_display_name( a_class )">
<%
    ## Start with exceptions, end with default.
    if a_class is model.StoredWorkflow:
        return "Workflow"
    else:
        return a_class.__name__
%>
</%def>

<%def name="get_item_name( item )">
    <% 
        # Start with exceptions, end with default.
        if type( item ) is model.Page:
            item_name = item.title
        elif type( item ) is model.Visualization:
            item_name = item.title
        elif hasattr( item, 'get_display_name'):
            item_name = item.get_display_name()
        else:
            item_name = item.name
        
        # Encode in unicode.
        return unicodify(item_name)
    %>
</%def>

## Get plural display name for a class.
<%def name="get_class_plural_display_name( a_class )">
<%
    # Start with exceptions, end with default.
    if a_class is model.History:
        return "Histories"
    elif a_class is model.FormDefinitionCurrent:
        return "Forms"
    else:
        return get_class_display_name( a_class ) + "s"
%>
</%def>

## Get display name for a class.
<%def name="get_class_display_name( a_class )">
<%
    ## Start with exceptions, end with default.
    if a_class is model.StoredWorkflow:
        return "Workflow"
    elif a_class is model.HistoryDatasetAssociation:
        return "Dataset"
    else:
        return a_class.__name__
%>
</%def>

## Get plural term for item.
<%def name="get_item_plural( item )">
    <% return get_class_plural( item.__class__ ) %>
</%def>

## Get plural term for class.
<%def name="get_class_plural( a_class )">
<%
    if a_class == model.History:
        class_plural = "Histories"
    elif a_class == model.StoredWorkflow:
        class_plural = "Workflows"
    elif a_class == model.Page:
        class_plural = "Pages"
    elif a_class == model.Library:
        class_plural = "Libraries"
    elif a_class == model.HistoryDatasetAssociation:
        class_plural = "Datasets"
    elif a_class == model.FormDefinitionCurrent:
        class_plural = "Forms"
    else:
        class_plural = "items"
    return class_plural
%>
</%def>

## Returns the controller name for an item based on its class.
<%def name="get_controller_name( item )">
    <%
        if isinstance( item, model.History ):
            return "history"
        elif isinstance( item, model.StoredWorkflow ):
            return "workflow"
        elif isinstance( item, model.HistoryDatasetAssociation ):
            return "dataset"
        elif isinstance( item, model.Page ):
            return "page"
        elif isinstance( item, model.Visualization ):
            return "visualization"
    %>
</%def>

<%def name="modern_route_for_controller( controller )">
    <%
        if controller == "history":
            return "histories"
        elif controller == "workflow":
            return "workflows"
        elif controller == "dataset":
            return "datasets"
        elif controller == "page":
            return "pages"
        elif controller == "visualization":
            return "visualizations"
        else:
            return controller
    %>
</%def>

## Returns item user/owner.
<%def name="get_item_user( item )">
    <%
        # Exceptions first, default last.
        if isinstance( item, model.HistoryDatasetAssociation ):
            return item.history.user
        else:
            return item.user
    %>
</%def>

## Returns item slug.
<%def name="get_item_slug( item )">
    <%
        # Exceptions first, default last.
        if isinstance( item, model.HistoryDatasetAssociation ):
            return trans.security.encode_id( item.id )
        else:
            return item.slug
    %>
</%def>

## Return a link to view a history.
<%def name="get_history_link( history, qualify=False )">
    %if history.slug and history.user.username:
        <% return h.url_for( controller='/history', action='display_by_username_and_slug', username=history.user.username, slug=history.slug, qualified=qualify ) %>
    %else:
        <% return h.url_for("/histories/view", id=trans.security.encode_id( history.id ), qualified=qualify) %>
    %endif
</%def>

## Render message.
<%def name="render_message( message, status )">
    %if message:
        <p>
            <div class="${status}message transient-message">${util.restore_text( message )}</div>
            <div style="clear: both"></div>
        </p>
    %endif
</%def>

