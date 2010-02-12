##
## Base file for generating HTML for embedded objects.
##
## parameters: item, item_data
##
<%namespace file="/display_common.mako" import="*" />

## HTML structure.
<div class='embedded-item'>
    <div class='title'>
        ${self.title( item )}
    </div>
    <hr/>
    <div class='summary-content'>
        ${self.content( item, item_data )}
    </div>
    <div class='item-content'>
    </div>
</div>

<%def name="title( item )">
    Galaxy ${get_class_display_name( item.__class__ )} | ${get_item_name( item )}
    <%
        item_controller = "/%s" % get_controller_name( item )
        item_user = get_item_user( item )
        item_slug = get_item_slug( item )
        display_href = h.url_for( controller=item_controller, action='display_by_username_and_slug', username=item_user.username, slug=item_slug )
    %>
    <a class="display_in_embed icon-button toggle-expand" item_id="${trans.security.encode_id( item.id )}" item_class="$item.__class__.__name__" href="${display_href}"></a>
    <a class="toggle-contract icon-button" href="${display_href}"></a>
    
    ## Use a hidden var to store the ajax URL for getting an item's content.
    <input type="hidden" name="ajax-item-content-url" value="${h.url_for( controller=item_controller, action='get_item_content_async', id=trans.security.encode_id( item.id ) )}"/>
</%def>

## Methods to override to generate content.
<%def name="content( item, item_data )">
</%def>
