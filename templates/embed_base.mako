##
## Base file for generating HTML for embedded objects.
##
## parameters: item, item_data
##
<%namespace file="/display_common.mako" import="*" />

## HTML structure.
<div class='embedded-item display ${get_class_display_name( item.__class__ ).lower()}'>
    <div class='title'>
        ${self.render_title( item )}
    </div>
    <div class='summary-content'>
        ${self.render_summary_content( item, item_data )}
    </div>
    <div class='expanded-content'>
        <hr/>
        <div class='item-content'></div>
    </div>
</div>

## Render item links.
<%def name="render_item_links( item )">
    <%
        item_display_name = get_class_display_name( item.__class__ ).lower()
        item_controller = "/%s" % get_controller_name( item )
        item_user = get_item_user( item )
        item_slug = get_item_slug( item )
        display_href = h.url_for( controller=item_controller, action='display_by_username_and_slug', username=item_user.username, slug=item_slug )
    %>
    
    ## Links for importing and viewing an item.
    <a href="${h.url_for( controller=item_controller, action='imp', id=trans.security.encode_id( item.id ) )}" title="Import ${item_display_name}" class="icon-button import tooltip"></a>
    <a class="icon-button go-to-full-screen tooltip" href="${display_href}" title="Go to ${item_display_name}"></a>
</%def>

<%def name="render_title( item )">
    <%
        item_display_name = get_class_display_name( item.__class__ ).lower()
        item_controller = "/%s" % get_controller_name( item )
        item_user = get_item_user( item )
        item_slug = get_item_slug( item )
        display_href = h.url_for( controller=item_controller, action='display_by_username_and_slug', username=item_user.username, slug=item_slug )
    %>
    <div style="float: left">
        <a class="display_in_embed icon-button toggle-expand tooltip" item_id="${trans.security.encode_id( item.id )}" item_class="$item.__class__.__name__" href="${display_href}"
            title="Show ${item_display_name} content"></a>
        <a class="toggle icon-button tooltip" href="${display_href}" title="Hide ${item_display_name} content"></a>
    </div>
    <div style="float: right;">
        ${self.render_item_links( item )}
    </div>
    <h4><a class="toggle-embed tooltip" href="${display_href}" title="Show or hide ${item_display_name} content">Galaxy ${get_class_display_name( item.__class__ )} | ${get_item_name( item )}</a></h4>
    %if hasattr( item, "annotation") and item.annotation:
        <div class="annotation">${item.annotation}</div>
    %endif
    
    ## Use a hidden var to store the ajax URL for getting an item's content.
    <input type="hidden" name="ajax-item-content-url" value="${h.url_for( controller=item_controller, action='get_item_content_async', id=trans.security.encode_id( item.id ) )}"/>
</%def>

## Methods to override to render summary content.
<%def name="render_summary_content( item, item_data )">
</%def>
