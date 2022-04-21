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

## Download and Export section
<%def name="render_download_to_file(item)">
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
    <a href="${h.url_for('/workflows/list')}">Go back to ${self.item_class_plural_name} List</a>
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
        <div class="page-container p-2">
            ${self.render_header()}
            <h2>${get_class_display_name( item.__class__ )} '${get_item_name( item ) | h}'</h2>
            <hr />
            ${self.render_download_to_file(item)}
            ${self.render_url_for_importing(item)}
            ${self.render_more(item)}
        </div>
    </div>
</%def>
