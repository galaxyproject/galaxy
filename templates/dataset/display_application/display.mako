<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%def name="title()">Display Application: ${display_link.link.display_application.name}  ${display_link.link.name}</%def>
%for message, message_type in msg:
    ${render_msg( message, message_type )}
%endfor
%if refresh:
<%def name="metas()"><meta http-equiv="refresh" content="10" /></%def>
<p>
This page will <a href="${trans.request.url}">refresh</a> after 10 seconds.
</p>
%endif
