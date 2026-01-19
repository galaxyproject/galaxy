<%inherit file="/base.mako"/>

<%namespace file="/message.mako" import="render_msg" />

<%def name="title()">Logout</%def>

<%def name="body()">
    %if message:
        ${render_msg( message, status )}
    %endif
</%def>
