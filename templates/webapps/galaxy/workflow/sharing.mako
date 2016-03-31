##
## Base template for sharing or publishing an item. Template expects the following parameters:
## (a) item - item to be shared.
##
<%!
    def inherit(context):
        if context.get('use_panels', False) == True:
            if context.get('webapp'):
                app_name = context.get('webapp')
            elif context.get('app'):
                app_name = context.get('app').name
            else:
                app_name = 'galaxy'
            return '/webapps/%s/base_panels.mako' % app_name
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

    # Get class name strings.
    self.item_class_name = get_class_display_name( item.__class__ )
    self.item_class_name_lc = self.item_class_name.lower()
    self.item_class_plural_name = get_class_plural_display_name( item.__class__ )
    self.item_class_plural_name_lc = self.item_class_plural_name.lower()
    self.controller = get_controller_name(item)
%>
</%def>


<%def name="stylesheets()">
    ${parent.stylesheets()}
    <style>
        ## Put some whitespace before each section header.
        h3 {
            margin-top: 1.5em;
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
        .display-url {
            margin: 0.5em 0em 0.5em 0.5em;
            font-weight: bold;
        }
    </style>
</%def>

<%def name="center_panel()">
    ${self.body()}
</%def>



## Share and Publish section

##
## Share workflow with indiviual Galaxy users
##

<%def name="render_sharing_for_users(item)">
    <h3>Share workflow with Individual Users</h3>
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
                                <a class="action-button" href="${h.url_for(controller=controller_name, action='sharing', id=trans.security.encode_id( item.id ), unshare_user=trans.security.encode_id( user.id ), use_panels=use_panels )}">Unshare</a>
                                </div>
                            </td>
                        </tr>
                    %endfor
                </table>

                <p>
                <a class="action-button"
                   href="${h.url_for(controller=controller_name, action='share', id=trans.security.encode_id(item.id), use_panels=use_panels )}">
                    <span>Share with another user</span>
                </a>
            ## %else:
            ##     <p>You have not shared this ${item_class_name_lc} with any users.</p>

            ##     <a class="action-button"
            ##        href="${h.url_for(controller=controller_name, action='share', id=trans.security.encode_id(item.id), use_panels=use_panels )}">
            ##         <span>Share with a user</span>
            ##     </a>
            ##     <br />

            %endif
    </div>
</%def>


## Download and Export section

<%def name="render_url_for_importing(item)">
    <h3>URL for Importing to Another Galaxy</h3>

    %if item.importable:
        Use this URL to import the ${get_class_display_name( item.__class__ ).lower()} directly into another Galaxy server:
        <div class="display-url">
            ${h.url_for(controller=self.controller, action='display_by_username_and_slug', username=item.user.username,
                        slug=item.slug, format='json', qualified=True )}
        </div>
        (Copy this URL into the box titled 'Workflow URL' in the Import Workflow page.)
    %else:
        <a href="${h.url_for(controller=self.controller, action='sharing', id=trans.security.encode_id( item.id ) )}">This  ${get_class_display_name( item.__class__ ).lower()} must be accessible before it can be imported into another Galaxy.</a>
    %endif
</%def>

<%def name="render_download_to_file(item)">
    <h3>Download to File</h3>

    <a href="${h.url_for( controller=self.controller, action='display_by_username_and_slug', username=item.user.username,
                          slug=item.slug, format='json-download' )}">
        Download ${get_class_display_name( item.__class__ ).lower()} to file so that it can be saved or imported into another Galaxy server.</a>
</%def>

<%def name="render_footer()">
    <p><br><br>
    <a href="${h.url_for(controller=self.controller, action="list" )}">Back to ${self.item_class_plural_name} List</a>
</%def>

<%def name="render_export_to_myexp(item)">
    ##
    ## Renders form for exporting workflow to myExperiment.
    ##
    <h3>Export to myExperiment</h3>

    <div class="toolForm">
        <form action="${h.url_for(controller='workflow', action='export_to_myexp', id=trans.security.encode_id( item.id ) )}"
                method="POST">
            <div class="form-row">
                <label>myExperiment username:</label>
                <input type="text" name="myexp_username" value="" size="40"/>
            </div>
            <div class="form-row">
                <label>myExperiment password:</label>
                <input type="password" name="myexp_password" value="" size="40"/>
            </div>
            <div class="form-row">
                <input type="submit" value="Export"/>
            </div>
        </form>
    </div>
</%def>

<%def name="render_more(item)">
    ## Add form to export to myExperiment.
    ${self.render_export_to_myexp(item)}
    ## Add link to render as SVG image.
    <h3>Create Image</h3>

    <a href="${h.url_for(controller='workflow', action='gen_image', id=trans.security.encode_id( item.id ) )}">
        Create image of ${get_class_display_name( item.__class__ ).lower()} in SVG format
    </a>
</%def>


<%def name="body()">
    <%
        item_name = get_item_name(item)
    %>

    <h2>Sharing and Publishing or Download and Export ${get_class_display_name( item.__class__ )} '${get_item_name( item ) | h}'</h2>

    ${self.render_sharing_for_users(item)}

    ${self.render_download_to_file(item)}

	${self.render_url_for_importing(item)}

	${self.render_more(item)}

	${self.render_footer()}
</%def>
