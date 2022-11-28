<%!
    def inherit( context ):
        return '/base.mako'

    from galaxy.model import History, StoredWorkflow, Page
    from galaxy.web.framework.helpers import iff
%>
<%inherit file="${inherit( context )}"/>
<%namespace file="/tagging_common.mako" import="render_individual_tagging_element, render_community_tagging_element, community_tag_js" />
<%namespace file="/display_common.mako" import="*" />

##
## Functions used by base.mako to display content.
##

<%def name="title()">
    ${iff( item.published, "Published ", iff( item.importable , "Accessible ", iff( item.users_shared_with, "Shared ", "Private " ) ) ) + get_class_display_name( item.__class__ )} | ${get_item_name( item ) | h}
</%def>

<%def name="init()">
<%
    self.has_left_panel=False
    self.has_right_panel=True
    self.message_box_visible=False
    self.active_view="shared"
    self.overlay_visible=False
%>
</%def>

<%def name="javascript_app()">
    ${parent.javascript_app()}
    ${community_tag_js( get_controller_name( item ) )}
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css(
        "embed_item",
        "library",
        "jquery-ui/smoothness/jquery-ui"
    )}

    <style type="text/css">
        .page-body {
            height: 100%;
            overflow: auto;
        }
        .page-meta {
            float: right;
            width: 27%;
            padding: 0.5em;
            margin: 0.25em;
            vertical-align: text-top;
            border: 2px solid #DDDDDD;
            border-top: 4px solid #DDDDDD;
        }

        ## Make sure that workflow steps do not get too long.
        .toolForm {
            max-width: 500px;
        }

        ## Space out tool forms in workflows.
        div.toolForm{
            margin-top: 10px;
            margin-bottom: 10px;
        }

    </style>
</%def>

<%def name="render_item_links( item )">
    ## Override.
</%def>

<%def name="render_item_header( item )">
    <h3 class="item_name">${get_item_name( item )| h}</h3>
    %if hasattr( item, "annotation") and item.annotation is not None:
        <div class="annotation">Annotation: ${item.annotation}</div>
    %endif
    <hr/>
</%def>

<%def name="render_item( item, item_data=None )">
    ## Override.
</%def>

## For base.mako
<%def name="body()">
    ${self.render_content()}
</%def>

##
## Render page content. Pages that inherit this page should override render_item_links() and render_item()
##
<%def name="render_content()">

    ## Get URL to other published items owned by user that owns this item.
    <%
        ##TODO: is there a better way to create this URL? Can't use 'f-username' as a key b/c it's not a valid identifier.
        modern_route = modern_route_for_controller(get_controller_name(item))
        item_plural = get_item_plural( item )
        href_to_all_items = h.url_for( controller='/' + modern_route, action='list_published')
        href_to_user_items = h.url_for( controller='/' + modern_route, action='list_published', xxx=item.user.username)
        href_to_user_items = href_to_user_items.replace( 'xxx', 'f-username')
    %>
    <div class="page-body p-3">
        <div class="page-item-header">
            ${self.render_item_header( item )}
        </div>
        ${self.render_item( item, item_data )}
    </div>
</%def>

<%def name="right_panel()">
    <%
        ## FIXME: duplicated from above for now
        modern_route = modern_route_for_controller(get_controller_name(item))
        item_plural = get_item_plural( item )
        href_to_all_items = h.url_for( controller='/' + modern_route , action='list_published')
        href_to_user_items = h.url_for( controller='/' + modern_route, action='list_published', xxx=item.user.username)
        href_to_user_items = href_to_user_items.replace( 'xxx', 'f-username')
    %>
    <div class="unified-panel-header" unselectable="on">
        <div class="unified-panel-header-inner">
            About this ${get_class_display_name( item.__class__ )}
            ${self.render_item_links( item )}
        </div>
    </div>
    <div class="unified-panel-body">
        <div style="overflow: auto; height: 100%;">
            <div class="p-3">
                <div style="float: right;"><img src="https://secure.gravatar.com/avatar/${h.md5(item.user.email)}?d=identicon"></div>
                <h4>Author</h4>
                <p>${item.user.username | h}</p>
                ## Related items.
                <h4>Related ${item_plural}</h4>
                <p>
                    <a href="${href_to_all_items}">All published ${item_plural.lower()}</a><br>
                    <a href="${href_to_user_items}">Published ${item_plural.lower()} by ${item.user.username | h}</a>
                </p>
                <div style="clear: both;"></div>
                ## Tags.
                <h4>Tags</h4>
                <p>
                ## Community tags.
                <div>
                    Community:
                    ${render_community_tagging_element(
                        tagged_item=item, 
                        tag_click_fn='community_tag_click', 
                        use_toggle_link=False 
                    )}
                    %if len ( item.tags ) == 0:
                        none
                    %endif
                </div>
                ## Individual tags.
                %if trans.get_user():
                    <p>
                    <div>
                        Yours:
                        ${render_individual_tagging_element(
                            user=trans.get_user(), 
                            tagged_item=item, 
                            elt_context='view.mako', 
                            use_toggle_link=False, 
                            tag_click_fn='community_tag_click'
                        )}
                    </div>
                %endif
            </div>
        </div>
    </div>
</%def>
