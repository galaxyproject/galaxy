<%inherit file="/base_panels.mako"/>
<%namespace file="./tagging_common.mako" import="render_individual_tagging_element, render_community_tagging_element" />

<%!
    from galaxy.model import History, StoredWorkflow, Page
%>

<%def name="init()">
<%
    self.has_left_panel=False
    self.has_right_panel=False
    self.message_box_visible=False
%>
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
    ${h.js( "galaxy.base", "jquery", "json2", "jquery.autocomplete", "autocomplete_tagging" )}

    <script type="text/javascript">
    //
    // Handle click on community tag.
    //
    function community_tag_click(tag_name, tag_value) 
    {
        <% controller_name = get_controller_name( item ) %>
        var href = '${h.url_for ( controller='/' + controller_name , action='list_published')}';
        href = href + "?f-tags=" + tag_name;
        if (tag_value != null && tag_value != "")
            href = href + ":" + tag_value;
        self.location = href;
    }
    </script>
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "autocomplete_tagging" )}
    <style type="text/css">
        .page-body
        {
            padding: 10px;
            float: left;
            width: 65%;
        }
        .page-meta
        {
            float: right;
            width: 27%;
            padding: 0.5em;
            margin: 0.25em;
            vertical-align: text-top;
            border: 2px solid #DDDDDD;
            border-top: 4px solid #DDDDDD;
        }
    </style>
</%def>

<%def name="render_item_links( item )">
    Item Links
</%def>

<%def name="render_item( item, item_data=None )">
    Item
</%def>

<%def name="get_item_name( item )">
    <% return item.name %>
</%def>


##
## Page content. Pages that inherit this page should override render_item_links() and render_item()
##
<%def name="center_panel()">
    
    ## Get URL to other published items owned by user that owns this item.
    <%
        ##TODO: is there a better way to create this URL? Can't use 'f-username' as a key b/c it's not a valid identifier.
        controller_name = get_controller_name( item )
        item_plural = get_item_plural( item )
        href_to_all_items = h.url_for( controller='/' + controller_name, action='list_published')
        href_to_user_items = h.url_for( controller='/' + controller_name, action='list_published', xxx=item.user.username)
        href_to_user_items = href_to_user_items.replace( 'xxx', 'f-username')
    %>
    
    <div class="unified-panel-header" unselectable="on">
        <div class="unified-panel-header-inner">
            <a href="${href_to_all_items}">Published ${item_plural}</a> | 
            <a href="${href_to_user_items}">${item.user.username}</a> | ${self.get_item_name( item )}
        </div>
    </div>
    
    <div class="unified-panel-body">
        <div style="overflow: auto; height: 100%;">        
            <div class="page-body">
                <div style="padding: 0px 0px 5px 0px">
                    ${self.render_item_links( item )}
                </div>
                
                ${self.render_item( item, item_data )}
            </div>
        
            <div class="page-meta">
                ## Page meta.
                <div><strong>Related ${item_plural}</strong></div>
                <p>
                    <a href="${href_to_all_items}">All published ${item_plural.lower()}</a><br>
                    <a href="${href_to_user_items}">${item_plural} owned by ${item.user.username}</a>
            
                ## Tags.
                <div><strong>Tags</strong></div>
                <p>
                ## Community tags.
                <div>
                    Community:
                    ${render_community_tagging_element( tagged_item=item, tag_click_fn='community_tag_click', use_toggle_link=False )}
                    %if len ( item.tags ) == 0:
                        none
                    %endif
                </div>
                ## Individual tags.
                <p>
                <div>
                    Yours:
                    ${render_individual_tagging_element( user=trans.get_user(), tagged_item=item, elt_context='view.mako', use_toggle_link=False, tag_click_fn='community_tag_click' )}
                </div>
            </div>
        </div>
    </div>
</%def>


##
## Utility methods.
##

## Get plural term for item.
<%def name="get_item_plural( item )">
    <%
        items_plural = "items"
        if isinstance( item, History ):
            items_plural = "Histories"
        elif isinstance( item, StoredWorkflow ):
            items_plural = "Workflows"
        elif isinstance( item, Page ):
            items_plural = "Pages"
        return items_plural
    %>
</%def>

## Returns the controller name for an item based on its class.
<%def name="get_controller_name( item )">
    <%
        if isinstance( item, History ):
            return "history"
        elif isinstance( item, StoredWorkflow ):
            return "workflow"
        elif isinstance( item, Page ):
            return "page"
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