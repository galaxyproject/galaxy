##
## Base template for sharing an item with an individual user. Template expects the following parameters:
## (a) item - item to be shared.
##
<%!
    def inherit(context):
        if context.get('use_panels'):
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

<%def name="stylesheets()">
    ${parent.stylesheets()}
    <style>
        ## If page is displayed in panels, pad from edges for readabilit.
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

<%def name="body()">
    %if message:
    <%
    if messagetype is UNDEFINED:
        mt = "done"
    else:
        mt = messagetype
    %>
    <p />
    <div class="${mt}message">
        ${message}
    </div>
    <p />
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
    
    <div class="toolForm">
        <div class="toolFormTitle">Share ${item_class_name} '${item_name}' with Another User</div>
            <div class="toolFormBody">
                <form action="${h.url_for( action='share', id=trans.security.encode_id( item.id ) )}" method="POST">
                    <div class="form-row">
                        <label>
                            Email address of user to share with
                        </label>
                        <div style="float: left; width: 250px; margin-right: 10px;">
                            <input type="text" name="email" value="${email}" size="40">
                        </div>
                        <div style="clear: both"></div>
                    </div>
                    <div class="form-row">
                        <input type="submit" value="Share"></input>
                    </div>
                    <div class="form-row">
                        <a href="${h.url_for( action="sharing", id=trans.security.encode_id( item.id ) )}">Back to ${item_class_name}'s Sharing Home</a>
                    </div>
                    
                </form>
            </div>
        </div>
    </div>
</%def>