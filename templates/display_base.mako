<%!
    def inherit( context ):
        if context.get('no_panels'):
            return '/base.mako'
        else:
            return '/webapps/galaxy/base_panels.mako'

    from galaxy.model import History, StoredWorkflow, Page
    from galaxy.web.framework.helpers import iff
%>
<%inherit file="${inherit( context )}"/>
<%namespace file="/tagging_common.mako" import="render_individual_tagging_element, render_community_tagging_element, community_tag_js" />
<%namespace file="/display_common.mako" import="*" />

##
## Functions used by base.mako and base_panels.mako to display content.
##

<%def name="title()">
    Galaxy | ${iff( item.published, "Published ", iff( item.importable , "Accessible ", iff( item.users_shared_with, "Shared ", "Private " ) ) ) + get_class_display_name( item.__class__ )} | ${get_item_name( item ) | h}
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

<%def name="javascripts()">
    ${parent.javascripts()}
    ${h.js(
        "libs/jquery/jstorage",
        "libs/jquery/jquery.event.drag",
        "libs/jquery/jquery.mousewheel",
        "libs/farbtastic",
        "libs/jquery/jquery.autocomplete",
    )}
    ${community_tag_js( get_controller_name( item ) )}
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css(
        "autocomplete_tagging",
        "embed_item",
        "jquery.rating",
        "library",
        "jquery-ui/smoothness/jquery-ui"
    )}

    <style type="text/css">
        .page-body {
            padding: 10px;
            ## float: left;
            ## width: 65%;
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
    <h3>Galaxy ${get_class_display_name( item.__class__ )} '${get_item_name( item )| h}'</h3>
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

## For base_panels.mako
<%def name="center_panel()">
    ${self.render_content()}
</%def>


##
## Render page content. Pages that inherit this page should override render_item_links() and render_item()
##
<%def name="render_content()">

    ## Get URL to other published items owned by user that owns this item.
    <%
        ##TODO: is there a better way to create this URL? Can't use 'f-username' as a key b/c it's not a valid identifier.
        controller_name = get_controller_name( item )
        item_plural = get_item_plural( item )
        href_to_all_items = h.url_for( controller='/' + controller_name, action='list_published')
        href_to_user_items = h.url_for( controller='/' + controller_name, action='list_published', xxx=item.user.username)
        href_to_user_items = href_to_user_items.replace( 'xxx', 'f-username')
    %>

    <div class="unified-panel-header" unselectable="on" style="overflow: hidden">
        <div class="unified-panel-header-inner">
            <div style="float: right">
                ${self.render_item_links( item )}
            </div>
            %if item.published:
                    <a href="${href_to_all_items}">Published ${item_plural}</a> |
                    <a href="${href_to_user_items}">${item.user.username}</a>
            %elif item.importable:
                Accessible ${get_class_display_name( item.__class__ )}
            %elif item.users_shared_with:
                Shared ${get_class_display_name( item.__class__ )}
            %else:
                Private ${get_class_display_name( item.__class__ )}
            %endif
            | ${get_item_name( item ) | h}
        </div>
    </div>

    <div class="unified-panel-body">
        <div style="overflow: auto; height: 100%;">
            <div class="page-body">
                <div>
                    ${self.render_item_header( item )}
                </div>

                ${self.render_item( item, item_data )}
            </div>


        </div>
    </div>
</%def>

<%def name="right_panel()">

    <%
        ## FIXME: duplicated from above for now
        controller_name = get_controller_name( item )
        item_plural = get_item_plural( item )
        href_to_all_items = h.url_for( controller='/' + controller_name, action='list_published')
        href_to_user_items = h.url_for( controller='/' + controller_name, action='list_published', xxx=item.user.username)
        href_to_user_items = href_to_user_items.replace( 'xxx', 'f-username')
    %>

    <div class="unified-panel-header" unselectable="on">
        <div class="unified-panel-header-inner">
            About this ${get_class_display_name( item.__class__ )}
        </div>
    </div>

    <div class="unified-panel-body">
        <div style="overflow: auto; height: 100%;">
            <div style="padding: 10px;">

                <div style="float: right;"><img src="https://secure.gravatar.com/avatar/${h.md5(item.user.email)}?d=identicon"></div>

                <h4>Author</h4>

                <p>${item.user.username | h}</p>

                ## Related items.
                <h4>Related ${item_plural}</h4>
                <p>
                    <a href="${href_to_all_items}">All published ${item_plural.lower()}</a><br>
                    <a href="${href_to_user_items}">Published ${item_plural.lower()} by ${item.user.username | h}</a>

                ## Rating.
                <h4>Rating</h4>

                <%
                    label = "ratings"
                    if num_ratings == 1:
                        label = "rating"
                %>
                <div style="padding-bottom: 0.75em; float: left">
                    Community<br>
                    <span style="font-size:80%">
                        (<span id="num_ratings">${num_ratings}</span> ${label},
                         <span id="ave_rating">${"%.1f" % ave_item_rating}</span> average)
                    <span>
                </div>
                <div style="float: right">
                    <input name="star1" type="radio" class="community_rating_star star" disabled="disabled" value="1"
                    %if ave_item_rating > 0 and ave_item_rating <= 1.5:
                        checked="checked"
                    %endif

                    />
                    <input name="star1" type="radio" class="community_rating_star star" disabled="disabled" value="2"
                    %if ave_item_rating > 1.5 and ave_item_rating <= 2.5:
                        checked="checked"
                    %endif
                    />
                    <input name="star1" type="radio" class="community_rating_star star" disabled="disabled" value="3"
                    %if ave_item_rating > 2.5 and ave_item_rating <= 3.5:
                        checked="checked"
                    %endif
                    />
                    <input name="star1" type="radio" class="community_rating_star star" disabled="disabled" value="4"
                    %if ave_item_rating > 3.5 and ave_item_rating <= 4.5:
                        checked="checked"
                    %endif
                    />
                    <input name="star1" type="radio" class="community_rating_star star" disabled="disabled" value="5"
                    %if ave_item_rating > 4.5:
                        checked="checked"
                    %endif
                    />
                </div>
                <div style="clear: both;"></div>
                %if trans.get_user():
                    <div style="float: left">
                        Yours<br><span id="rating_feedback" style="font-size:80%; display: none">(thanks!)</span>
                    </div>
                    <div style="float: right">
                        <input name="star2" type="radio" class="user_rating_star" value="1"
                        %if user_item_rating == 1:
                            checked="checked"
                        %endif
                        />
                        <input name="star2" type="radio" class="user_rating_star" value="2"
                        %if user_item_rating == 2:
                            checked="checked"
                        %endif
                        />
                        <input name="star2" type="radio" class="user_rating_star" value="3"
                        %if user_item_rating == 3:
                            checked="checked"
                        %endif
                        />
                        <input name="star2" type="radio" class="user_rating_star" value="4"
                        %if user_item_rating == 4:
                            checked="checked"
                        %endif
                        />
                        <input name="star2" type="radio" class="user_rating_star" value="5"
                        %if user_item_rating == 5:
                            checked="checked"
                        %endif
                        />
                    </div>
                %endif
                <div style="clear: both;"></div>

                ## Tags.
                <h4>Tags</h4>
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
                %if trans.get_user():
                    <p>
                    <div>
                        Yours:
                        ${render_individual_tagging_element( user=trans.get_user(), tagged_item=item, elt_context='view.mako', use_toggle_link=False, tag_click_fn='community_tag_click' )}
                    </div>
                %endif
            </div>
        </div>
    </div>

</%def>
