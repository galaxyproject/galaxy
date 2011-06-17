##
## Base template for sharing or publishing an item. Template expects the following parameters:
## (a) item - item to be shared.
##
<%!
    def inherit(context):
        if context.get('use_panels', False) == True:
            if context.get('webapp'):
                webapp = context.get('webapp')
            else:
                webapp = 'galaxy'
            return '/webapps/%s/base_panels.mako' % webapp
        else:
            return '/base.mako'
%>
<%inherit file="${inherit(context)}"/>

<%namespace file="/display_common.mako" import="*" />
<%namespace file="/message.mako" import="render_msg" />

##
## Page methods.
##

<%def name="init()">
<%
    self.has_left_panel=False
    self.has_right_panel=False
    self.message_box_visible=False
    self.overlay_visible=False
    self.message_box_class=""
    self.active_view=""
    self.body_class=""
%>
</%def>

<%def name="title()">
    Sharing and Publishing ${get_class_display_name( item.__class__ )} '${get_item_name( item )}'
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
    <script type="text/javascript">
    $(document).ready( function() {
        //
        // Set up slug-editing functionality.
        //
        var on_start = function( text_elt ) {
            // Replace URL with URL text.
            $('#item-url').hide();
            $('#item-url-text').show();
            
            // Allow only lowercase alphanumeric and '-' characters in slug.
            text_elt.keyup(function(){
                text_elt.val( $(this).val().replace(/\s+/g,'-').replace(/[^a-zA-Z0-9\-]/g,'').toLowerCase() )
            });
        };
        
        var on_finish = function( text_elt ) {
            // Replace URL text with URL.
            $('#item-url-text').hide();
            $('#item-url').show();
            
            // Set URL to new value.
            var new_url = $('#item-url-text').text();
            var item_url_obj = $('#item-url');
            item_url_obj.attr( "href", new_url );
            item_url_obj.text( new_url );
        };
        
        <% controller_name = get_controller_name( item ) %>
        async_save_text("edit-identifier", "item-identifier", "${h.url_for( controller=controller_name, action='set_slug_async', id=trans.security.encode_id( item.id ) )}", "new_slug", null, false, 0, on_start, on_finish); 
    });
    </script>
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    <style>
        ## Put some whitespace before each section header.
        h3 {
            margin-top: 2em;
        }
        input.action-button {
            margin-left: 0;
        }
        ## If page is displayed in panels, pad from edges for readability.
        %if context.get('use_panels'):
            div#center {
                padding: 10px;
            }
        %endif
    </style>
</%def>

<%def name="center_panel()">
    ${self.body()}
</%def>

<%def name="body()">
    ## Set use_panels var for use in page's URLs.
    <% use_panels = context.get('use_panels', False)  %>

    ## Render message.
    %if message:
        ${render_msg( message, status )}
    %endif

    <%
        #
        # Setup and variables needed for page.
        #
    
        # Get class name strings.
        item_class_name = get_class_display_name( item.__class__ ) 
        item_class_name_lc = item_class_name.lower()
        item_class_plural_name = get_class_plural_display_name( item.__class__ )
        item_class_plural_name_lc = item_class_plural_name.lower()
        
        # Get item name.
        item_name = get_item_name(item)
    %>

    <h2>Share or Publish ${item_class_name} '${item_name}'</h2>

    ## Require that user have a public username before sharing or publishing an item.
    %if trans.get_user().username is None or trans.get_user().username is "":
        <p>To make a ${item_class_name_lc} accessible via link or publish it, you must create a public username:</p>
        
        <form action="${h.url_for( action='set_public_username', id=trans.security.encode_id( item.id ) )}"     
                method="POST">
            <div class="form-row">
                <label>Public Username:</label>
                <div class="form-row-input">
                    <input type="text" name="username" size="40"/>
                </div>
            </div>
            <div style="clear: both"></div>
            <div class="form-row">
                <input class="action-button" type="submit" name="Set Username" value="Set Username"/>
            </div>
        </form>
    %else:
        ## User has a public username, so private sharing and publishing options.
        <h3>Making ${item_class_name} Accessible via Link and Publishing It</h3>
    
            <div>
                %if item.importable:
                    <% 
                        item_status = "accessible via link" 
                        if item.published:
                            item_status = item_status + " and published"    
                    %>
                    This ${item_class_name_lc} is currently <strong>${item_status}</strong>. 
                    <div>
                        <p>Anyone can view and import this ${item_class_name_lc} by visiting the following URL:

                        <blockquote>
                            <% 
                                url = h.url_for( action='display_by_username_and_slug', username=trans.get_user().username, slug=item.slug, qualified=True ) 
                                url_parts = url.split("/")
                            %>
                            <a id="item-url" href="${url}" target="_top">${url}</a>
                            <span id="item-url-text" style="display: none">
                                ${"/".join( url_parts[:-1] )}/<span id='item-identifier'>${url_parts[-1]}</span>
                            </span>
                            
                            <a href="#" id="edit-identifier"><img src="${h.url_for('/static/images/fugue/pencil.png')}"/></a>
                        </blockquote>
        
                        %if item.published:
                            This ${item_class_name_lc} is publicly listed and searchable in Galaxy's <a href='${h.url_for( action='list_published' )}' target="_top">Published ${item_class_plural_name}</a> section.
                        %endif
                    </div>
        
                    <p>You can:
                    <div>
                    <form action="${h.url_for( action='sharing', id=trans.security.encode_id( item.id ) )}" method="POST">
                        %if not item.published:
                            ## Item is importable but not published. User can disable importable or publish.
                            <input class="action-button" type="submit" name="disable_link_access" value="Disable Access to ${item_class_name} Link">
                            <div class="toolParamHelp">Disables ${item_class_name_lc}'s link so that it is not accessible.</div>
                            <br />
                            <input class="action-button" type="submit" name="publish" value="Publish ${item_class_name}" method="POST">
                            <div class="toolParamHelp">Publishes the ${item_class_name_lc} to Galaxy's <a href='${h.url_for( action='list_published' )}' target="_top">Published ${item_class_plural_name}</a> section, where it is publicly listed and searchable.</div>

                        <br />
                        %else: ## item.published == True
                            ## Item is importable and published. User can unpublish or disable import and unpublish.
                            <input class="action-button" type="submit" name="unpublish" value="Unpublish ${item_class_name}">
                            <div class="toolParamHelp">Removes this ${item_class_name_lc} from Galaxy's <a href='${h.url_for( action='list_published' )}' target="_top">Published ${item_class_plural_name}</a> section so that it is not publicly listed or searchable.</div>
                            <br />
                            <input class="action-button" type="submit" name="disable_link_access_and_unpublish" value="Disable Access to ${item_class_name} via Link and Unpublish">
                            <div class="toolParamHelp">Disables this ${item_class_name_lc}'s link so that it is not accessible and removes ${item_class_name_lc} from Galaxy's <a href='${h.url_for( action='list_published' )}' target='_top'>Published ${item_class_plural_name}</a> section so that it is not publicly listed or searchable.</div>
                        %endif
                    </form>
                    </div>
   
                %else:
   
                    <p>This ${item_class_name_lc} is currently restricted so that only you and the users listed below can access it. You can:</p>
                    
                    <form action="${h.url_for( action='sharing', id=trans.security.encode_id(item.id) )}" method="POST">
                        <input class="action-button" type="submit" name="make_accessible_via_link" value="Make ${item_class_name} Accessible via Link">
                        <div class="toolParamHelp">Generates a web link that you can share with other people so that they can view and import the ${item_class_name_lc}.</div>
        
                        <br />
                        <input class="action-button" type="submit" name="make_accessible_and_publish" value="Make ${item_class_name} Accessible and Publish" method="POST">
                        <div class="toolParamHelp">Makes the ${item_class_name_lc} accessible via link (see above) and publishes the ${item_class_name_lc} to Galaxy's <a href='${h.url_for( action='list_published' )}' target='_top'>Published ${item_class_plural_name}</a> section, where it is publicly listed and searchable.</div>
                    </form>
       
                %endif

        ##
        ## Sharing with Galaxy users.
        ##
        <h3>Sharing ${item_class_name} with Specific Users</h3>

            <div>
                %if item.users_shared_with:

                    <p>
                        The following users will see this ${item_class_name_lc} in their ${item_class_name_lc} list and will be
                        able to view, import, and run it.
                    </p>
            
                    <table class="colored" border="0" cellspacing="0" cellpadding="0" width="100%">
                        <tr class="header">
                            <th>Email</th>
                            <th></th>
                        </tr>
                        %for i, association in enumerate( item.users_shared_with ):
                            <% user = association.user %>
                            <tr>
                                <td>
                                    <div class="menubutton popup" id="user-${i}-popup">${user.email}</div>
                                </td>
                                <td>
                                    <div popupmenu="user-${i}-popup">
                                    <a class="action-button" href="${h.url_for( action='sharing', id=trans.security.encode_id( item.id ), unshare_user=trans.security.encode_id( user.id ), use_panels=use_panels )}">Unshare</a>
                                    </div>
                                </td>
                            </tr>    
                        %endfor
                    </table>
    
                    <p>
                    <a class="action-button" 
                       href="${h.url_for( action='share', id=trans.security.encode_id(item.id), use_panels=use_panels )}">
                        <span>Share with another user</span>
                    </a>

                %else:

                    <p>You have not shared this ${item_class_name_lc} with any users.</p>
    
                    <a class="action-button" 
                       href="${h.url_for( action='share', id=trans.security.encode_id(item.id), use_panels=use_panels )}">
                        <span>Share with a user</span>
                    </a>
                    <br />
    
                %endif
            </div>
        </div>
    %endif

    <br /><br />
    <a href="${h.url_for( action="list" )}">Back to ${item_class_plural_name} List</a>
</%def>