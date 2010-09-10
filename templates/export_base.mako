##
## Base template for exporting an item. Template expects the following parameters:
## (a) item - item to be exported.
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

<%namespace file="./display_common.mako" import="*" />
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
%>
</%def>

<%def name="title()">
    Export ${get_class_display_name( item.__class__ )} '${get_item_name( item )}'
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    <style>
        ## Put some whitespace before each section header.
        h3
        {
            margin-top: 2em;
        }
        input.action-button
        {
            margin-left: 0;
        }
        ## If page is displayed in panels, pad from edges for readability.
        %if context.get('use_panels'):
        div#center
        {
            padding: 10px;
        }
        %endif
    </style>
</%def>

<%def name="center_panel()">
    ${self.body()}
</%def>

<%def name="render_download_to_file(item)">
    <h3>Download to File</h3>
    
    <a href="${h.url_for( action='export_to_file', id=trans.security.encode_id( item.id ) )}">
        Download ${get_class_display_name( item.__class__ ).lower()} to file so that it can be saved or imported into another Galaxy server.</a>
</%def>

<%def name="render_more(item)">
    ## Override.
</%def>

<%def name="render_footer()">
    <p><br><br>
    <a href=${h.url_for( action="list" )}>Back to ${self.item_class_plural_name} List</a>
</%def>

<%def name="body()">
    <%
        item_name = get_item_name(item)
    %>
    <h2>Download or Export ${self.item_class_name} '${item_name}'</h2>

    ${self.render_download_to_file(item)}
    
    ${self.render_more(item)}
    
    ${self.render_footer()}
</%def>