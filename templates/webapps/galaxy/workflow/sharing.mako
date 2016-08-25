##
## Template for "Share or Download"
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
<%namespace file="/slug_editing_js.mako" import="*" />


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
    self.active_view="workflow"
%>
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
    ${slug_editing_js(item)}
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    <style>
        ## Put some whitespace before each section header.
        h3 {
            margin-top: 1em;
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
        .sharing-section{
            margin-top: 1em;
        }
    </style>
</%def>

<%def name="center_panel()">
    ${self.body()}
</%def>


## Share and Publish section

<%def name="render_sharing(item)">
    ## Set use_panels var for use in page's URLs.
    <% use_panels = context.get('use_panels', False)  %>
    <% controller_name = get_controller_name( item ) %>
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
    ## Require that user have a public username before sharing or publishing an item.
    %if trans.get_user().username is None or trans.get_user().username is "":
        <p>To make a ${item_class_name_lc} accessible via link or publish it, you must create a public username:</p>

        <form action="${h.url_for( controller=controller_name, action='set_public_username', id=trans.security.encode_id( item.id ) )}"
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
        <h3>Share</h3>
        <div>
            %if item.importable:
                <%
                    item_status = "accessible via link"
                    if item.published:
                        item_status = item_status + " and published"
                %>
                This ${item_class_name_lc} is currently <strong>${item_status}</strong>.
                <div>
                    Anyone can view and import this ${item_class_name_lc} by visiting the following URL:
                    <blockquote>
                        <%
                            url = h.url_for( controller=controller_name, action='display_by_username_and_slug', username=trans.get_user().username, slug=item.slug, qualified=True )
                            url_parts = url.split("/")
                        %>
                        <a id="item-url" href="${url}" target="_top">${url}</a>
                        <span id="item-url-text" style="display: none">
                            ${"/".join( url_parts[:-1] )}/<span id='item-identifier'>${url_parts[-1]}</span>
                        </span>

                        <a href="#" id="edit-identifier"><img src="${h.url_for('/static/images/fugue/pencil.png')}"/></a>
                    </blockquote>

                    %if item.published:
                        This ${item_class_name_lc} is publicly listed and searchable in Galaxy's <a href='${h.url_for( controller=controller_name, action='list_published' )}' target="_top">Published ${item_class_plural_name}</a> section.
                    %endif
                </div>
                <div>
                    <form action="${h.url_for( controller=controller_name, action='sharing', id=trans.security.encode_id( item.id ) )}" method="POST">
                        %if not item.published:
                            ## Item is importable but not published. User can disable importable or publish.
                            <input class="action-button" type="submit" name="disable_link_access" value="Disable Access to ${item_class_name} Link">
                            <div class="toolParamHelp">Disables ${item_class_name_lc}'s link so that it is not accessible.</div>
                            <br />
                            <input class="action-button" type="submit" name="publish" value="Publish ${item_class_name}" method="POST">
                            <div class="toolParamHelp">Publishes the ${item_class_name_lc} to Galaxy's <a href='${h.url_for( controller=controller_name, action='list_published' )}' target="_top">Published ${item_class_plural_name}</a> section, where it is publicly listed and searchable.</div>
                        <br />
                        %else: ## item.published == True
                            ## Item is importable and published. User can unpublish or disable import and unpublish.
                            <input class="action-button" type="submit" name="unpublish" value="Unpublish ${item_class_name}">
                            <div class="toolParamHelp">Removes this ${item_class_name_lc} from Galaxy's <a href='${h.url_for(controller=controller_name, action='list_published' )}' target="_top">Published ${item_class_plural_name}</a> section so that it is not publicly listed or searchable.</div>
                            <br />
                            <input class="action-button" type="submit" name="disable_link_access_and_unpublish" value="Disable Access to ${item_class_name} via Link and Unpublish">
                            <div class="toolParamHelp">Disables this ${item_class_name_lc}'s link so that it is not accessible and removes ${item_class_name_lc} from Galaxy's <a href='${h.url_for(controller=controller_name, action='list_published' )}' target='_top'>Published ${item_class_plural_name}</a> section so that it is not publicly listed or searchable.</div>
                        %endif
                    </form>
                </div>
            %else:
                <p>This ${item_class_name_lc} is currently restricted so that only you and the users listed below can access it.</p>
                <form action="${h.url_for(controller=controller_name, action='sharing', id=trans.security.encode_id(item.id) )}" method="POST">
                    <input class="action-button" type="submit" name="make_accessible_via_link" value="Make ${item_class_name} Accessible via Link">
                    <div class="toolParamHelp">Generates a web link that you can share with other people so that they can view and import the ${item_class_name_lc}.</div>

                    <br />
                    <input class="action-button" type="submit" name="make_accessible_and_publish" value="Make ${item_class_name} Accessible and Publish" method="POST">
                    <div class="toolParamHelp">
                        Makes the ${item_class_name_lc} accessible via link (see above) and publishes the ${item_class_name_lc} to Galaxy's <a href='${h.url_for(controller=controller_name, action='list_published' )}' target='_top'>Published ${item_class_plural_name}</a> section, where it is publicly listed and searchable.
                    </div>
                </form>
            %endif
            ##
            ## Sharing with Galaxy users.
            ##
            <div class="sharing-section">
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

                        <a class="action-button"
                           href="${h.url_for(controller=controller_name, action='share', id=trans.security.encode_id(item.id), use_panels=use_panels )}">
                            <span>Share with another user</span>
                        </a>
                    %else:
                        <p>You have not shared this ${item_class_name_lc} with any users yet.</p>
                        <a class="action-button" href="${h.url_for(controller=controller_name, action='share', id=trans.security.encode_id(item.id), use_panels=use_panels )}">
                            <span>Share with a user</span>
                        </a>
                    %endif
                </div>
            </div>
        </div>
    %endif
</%def>


## Download and Export section
<%def name="render_download_to_file(item)">
    <hr/>
    <h3>Export</h3>
    <div class="sharing-section">
        <a class="action-button" href="${h.url_for( controller=self.controller, action='display_by_username_and_slug', username=item.user.username, slug=item.slug, format='json-download' )}">
        Download
        </a>
    ${get_class_display_name( item.__class__ ).lower()} as a file so that it can be saved or imported into another Galaxy server.
    </div>
</%def>


<%def name="render_url_for_importing(item)">
    <div class="sharing-section">
    %if item.importable:
        Use this URL to import the ${get_class_display_name( item.__class__ ).lower()} directly into another Galaxy server:
        <div class="display-url">
            ${h.url_for(controller=self.controller, action='display_by_username_and_slug', username=item.user.username,
                        slug=item.slug, format='json', qualified=True )}
        </div>
        (Copy this URL into the box titled 'Workflow URL' in the Import Workflow page.)
    %else:
        This ${get_class_display_name( item.__class__ ).lower()} must be accessible. Please use the option above to "Make Workflow Accessible and Publish" before receiving a URL for importing to another Galaxy.</a>
    %endif
    </div>
</%def>

<%def name="render_header()">
    <a href="${h.url_for(controller=self.controller, action="list" )}">Go back to ${self.item_class_plural_name} List</a>
</%def>


<%def name="render_export_to_myexp(item)">
    ##
    ## Renders form for exporting workflow to myExperiment.
    ##
    <div class="sharing-section">
        <span>Export to the <a href="http://www.myexperiment.org/" target="_blank">www.myexperiment.org</a> site.</span>
        <form action="${h.url_for(controller='workflow', action='export_to_myexp', id=trans.security.encode_id( item.id ) )}"
                method="POST">
            <div class="form-row">
                <label>myExperiment username:</label>
                <input type="text" name="myexp_username" value="" size="25" placeholder="username" autocomplete="off"/>
            </div>
            <div class="form-row">
                <label>myExperiment password:</label>
                <input type="password" name="myexp_password" value="" size="25" placeholder="password" autocomplete="off"/>
            </div>
            <div class="form-row">
                <input type="submit" value="Export to myExperiment"/>
            </div>
        </form>
    </div>
</%def>


<%def name="render_more(item)">
    ## Add link to render as SVG image.
    <div class="sharing-section">
        <a class="action-button" href="${h.url_for(controller='workflow', action='gen_image', id=trans.security.encode_id( item.id ) )}">
            Create image
        </a>
        of ${get_class_display_name( item.__class__ ).lower()} in SVG format
    </div>
    ## Add form to export to myExperiment.
    <div class="sharing-section">
        ${self.render_export_to_myexp(item)}
    </div>
</%def>


<%def name="body()">
    <div style="overflow: auto; height: 100%;">
        <div class="page-container" style="padding: 10px;">
            ${self.render_header()}
            <h2>${get_class_display_name( item.__class__ )} '${get_item_name( item ) | h}'</h2>
            <hr/>
            ${self.render_sharing(item)}
            ${self.render_download_to_file(item)}
            ${self.render_url_for_importing(item)}
            ${self.render_more(item)}
        </div>
    </div>
</%def>
