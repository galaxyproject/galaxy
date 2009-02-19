<%inherit file="/base.mako"/>
<%def name="title()">Change Default Permissions on New Datasets in This History</%def>
<%namespace file="/dataset/security_common.mako" import="render_permission_form" />

%if trans.user:
    ${render_permission_form( trans.history, trans.history.name, h.url_for(), trans.user.all_roles() )}
%endif
