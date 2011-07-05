<%inherit file="/base.mako"/>
<%def name="title()">Change Default Permissions on New Datasets in This History</%def>
<%namespace file="/dataset/security_common.mako" import="render_permission_form" />

%if trans.user:
    <% history = trans.get_history() %>
    ${render_permission_form( history, history.name, h.url_for(), trans.user.all_roles() )}
%endif
