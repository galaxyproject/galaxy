##
## Utilities for sharing items and displaying shared items.
## HACK: these should probably go in the web helper object.
##

<%! from galaxy import model %>

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
		if type( item ) is model.Page:
			return item.title
		if hasattr( item, 'get_display_name'):
		    return item.get_display_name()
		return item.name
	%>
</%def>

## Get plural display name for a class.
<%def name="get_class_plural_display_name( a_class )">
<%
    ## Start with exceptions, end with default.
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
        class_plural = a_class.__name__ + "s"
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
        <% return h.url_for( controller='/history', action='view', id=trans.security.encode_id( history.id ), qualified=qualify ) %>
    %endif
</%def>

