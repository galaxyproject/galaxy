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

<%namespace file="/refresh_frames.mako" import="handle_refresh_frames" />

<% _=n_ %>

<%def name="init()">
<%
    self.has_left_panel=False
    self.has_right_panel=False
    self.active_view=active_view
    self.message_box_visible=False
%>
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
    ${handle_refresh_frames()}
    <script type="text/javascript">
        if ( parent.handle_minwidth_hint )
        {
            parent.handle_minwidth_hint( -1 );
        }
    </script>
</%def>

##
## Override methods from base.mako and base_panels.mako
##

<%def name="center_panel()">
    ${render_large_message( message, status )}
</%def>

<%def name="body()">
    ${render_large_message( message, status )}
</%def>

## Render large message.
<%def name="render_large_message( message, status )">
    <div class="${status}messagelarge" style="margin: 1em">${_(message)}</div>
</%def>

## Render a message
<%def name="render_msg( msg, status='done' )">
    <div class="${status}message">${_(msg)}</div>
    <br/>
</%def>

