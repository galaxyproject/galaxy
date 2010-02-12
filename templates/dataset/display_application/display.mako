<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%def name="title()">Display Application: ${display_link.link.display_application.name}  ${display_link.link.name}</%def>
<% refresh_rate = 10 %>
%if refresh:
<script type="text/javascript">  
    setTimeout( "location.reload(true);", ${ refresh_rate * 1000 } );
</script>
%endif
%for message, message_type in msg:
    ${render_msg( message, message_type )}
%endfor
%if refresh:
<p>
This page will <a href="javascript:location.reload(true);">refresh</a> after ${refresh_rate} seconds.
</p>
%endif
